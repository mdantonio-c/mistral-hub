# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.services.uploader import Uploader
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager as repo
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import statistic_elaboration as pp2
from mistral.tools import spare_point_interpol as pp3_3



class Data(EndpointResource, Uploader):
    # schema_expose = True
    labels = ['data']
    POST = {
        '/data': {
            'summary': 'Request for data extraction.',
            'parameters': [
                {
                    'name': 'criteria',
                    'in': 'body',
                    'description': 'Criteria for data extraction.',
                    'schema': {'$ref': '#/definitions/DataExtraction'},
                }
            ],
            'responses': {
                '202': {
                    'description': 'Data extraction request queued'
                },
                '400': {
                    'description': 'Parameters for post processing are not correct'
                },
                '500': {
                    'description': 'File for spare point interpolation post processor is corrupted'
                }
            },
        }
    }

    @catch_error()
    @authentication.required()
    def post(self):
        user = self.get_current_user()
        log.info(
            'request for data extraction coming from user UUID: {}'.format(user.uuid)
        )
        criteria = self.get_input()

        self.validate_input(criteria, 'DataExtraction')
        product_name = criteria.get('name')
        dataset_names = criteria.get('datasets')
        reftime = criteria.get('reftime')
        output_format = criteria.get('output_format')
        if reftime is not None:
            # 'from' and 'to' both mandatory by schema
            # check from <= to
            if reftime['from'] > reftime['to']:
                raise RestApiException(
                    'Invalid reftime: <from> greater than <to>',
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get('id', '') == ds_name), None)
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )

        # get the format of the datasets
        dataset_format = arki.get_datasets_format(dataset_names)
        if not dataset_format:
            raise RestApiException(
                "Invalid set of datasets : datasets have different formats",
                status_code=hcodes.HTTP_BAD_REQUEST,
            )

        # incoming filters: <dict> in form of filter_name: list_of_values
        # e.g. 'level': [{...}, {...}] or 'level: {...}'
        filters = criteria.get('filters', {})
        # clean up filters from unknown values
        filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        processors = criteria.get('postprocessors', [])
        # clean up processors from unknown values
        # processors = [i for i in processors if arki.is_processor_allowed(i.get('type'))]
        for p in processors:
            p_type = p.get('type')
            if p_type == 'derived_variables':
                self.validate_input(p, 'AVProcessor')
            elif p_type == 'grid_interpolation':
                self.validate_input(p, 'GIProcessor')
                pp3_1.get_trans_type(p)
            elif p_type == 'grid_cropping':
                self.validate_input(p, 'GCProcessor')
                p['trans-type'] = "zoom"
            elif p_type == 'spare_point_interpolation':
                self.validate_input(p, 'SPIProcessor')
                pp3_3.get_trans_type(p)
                pp3_3.validate_spare_point_interpol_params(p)
            elif p_type == 'statistic_elaboration':
                self.validate_input(p, 'SEProcessor')
                pp2.validate_statistic_elaboration_params(p)
            else:
                raise RestApiException(
                    'Unknown post-processor type for {}'.format(p_type),
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # if there is a pp combination check if there is only one geographical postprocessor
        if len(processors) > 1:
            pp_list = []
            for p in processors:
                pp_list.append(p.get('type'))
            pp3_list = ['grid_cropping', 'grid_interpolation', 'spare_point_interpolation']
            if len(set(pp_list).intersection(set(pp3_list))) > 1:
                raise RestApiException(
                    'Only one geographical postprocessing at a time can be executed',
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # check if the output format chosen by the user is compatible with the chosen datasets
        if output_format is not None:
            postprocessors_list = [i.get('type') for i in processors]
            if dataset_format != output_format:
                if dataset_format == 'grib':
                    # spare point interpolation has bufr as output format
                    if 'spare_point_interpolation' not in postprocessors_list:
                        raise RestApiException(
                            'The chosen datasets does not support {} output format'.format(output_format),
                            status_code=hcodes.HTTP_BAD_REQUEST,
                        )
                if dataset_format == 'bufr' and output_format == 'grib':
                    raise RestApiException(
                        'The chosen datasets does not support {} output format'.format(output_format),
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )
            else:
                if dataset_format == 'grib' and 'spare_point_interpolation' in postprocessors_list:
                    raise RestApiException(
                        'The chosen postprocessor does not support {} output format'.format(output_format),
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )

        # run the following steps in a transaction
        db = self.get_service_instance('sqlalchemy')
        try:
            request = repo.create_request_record(
                db,
                user.id,
                product_name,
                {
                    'datasets': dataset_names,
                    'reftime': reftime,
                    'filters': filters,
                    'postprocessors': processors,
                    'output_format': output_format,
                },
            )

            task = CeleryExt.data_extract.apply_async(
                args=[user.id, dataset_names, reftime, filters, processors, output_format, request.id],
                countdown=1,
            )

            request.task_id = task.id
            request.status = task.status  # 'PENDING'
            db.session.commit()
            log.info('Request successfully saved: <ID:{}>', request.id)
        except Exception as error:
            db.session.rollback()
            raise SystemError("Unable to submit the request")

        # return self.force_response(
        #     {'task_id': task.id, 'task_status': task.status}, code=hcodes.HTTP_OK_ACCEPTED)
        return self.empty_response()
