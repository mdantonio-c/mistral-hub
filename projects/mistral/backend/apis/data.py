# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.services.uploader import Uploader
from restapi.confs import UPLOAD_FOLDER
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager as repo

import os

log = get_logger(__name__)


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
            'responses': {'202': {'description': 'Data extraction request queued'}},
        }
    }
    PATCH = {
        '/data': {
            'summary': 'Uploading file for spare point interpolation postprocessor',
            'consumes': ['multipart/form-data'],
            'parameters': [
                {
                    'name': 'file',
                    'in': 'formData',
                    'description': 'spare point file for the interpolation',
                    'type': 'file',
                }
            ],
            'responses': {
                '202': {
                    'description': 'file uploaded',
                    'schema': {'$ref': '#/definitions/SparePointFile'}
                },
                '400':{
                    'description': 'file cannot be uploaded'
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
                self.validate_grid_interpol_params(p)
            elif p_type == 'grid_cropping':
                self.validate_input(p, 'GCProcessor')
            elif p_type == 'spare_point_interpolation':
                self.validate_input(p, 'SPIProcessor')
                self.validate_spare_point_interpol_params(p)
            else:
                raise RestApiException(
                    'Unknown post-processor type for {}'.format(p_type),
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
                },
            )

            task = CeleryExt.data_extract.apply_async(
                args=[user.id, dataset_names, reftime, filters, processors, request.id],
                countdown=1,
            )

            request.task_id = task.id
            request.status = task.status  # 'PENDING'
            db.session.commit()
            log.info('Request successfully saved: <ID:{}>'.format(request.id))
        except Exception as error:
            db.session.rollback()
            raise SystemError("Unable to submit the request")

        # return self.force_response(
        #     {'task_id': task.id, 'task_status': task.status}, code=hcodes.HTTP_OK_ACCEPTED)
        return self.empty_response()

    @catch_error()
    @authentication.required()
    def patch(self):
        user = self.get_current_user()

        # allowed formats for uploaded file
        self.allowed_exts = ['shp', 'grib_api']

        #use user.uuid as name for the subfolder where the file will be uploaded
        upload_response = self.upload(subfolder=user.uuid)

        if not upload_response.defined_content:
            # raise RestApiException(
            #     '{}'.format(next(iter(upload_response.errors))),
            #     status_code=hcodes.HTTP_BAD_REQUEST,
            # )
            raise RestApiException(
                upload_response.errors,
                status_code=hcodes.HTTP_BAD_REQUEST,
            )

        upload_filename = upload_response.defined_content['filename']
        upload_filepath = os.path.join(UPLOAD_FOLDER,user.uuid,upload_filename)
        log.debug('File uploaded. Filepath : {}'.format(upload_filepath))
        f = self.split_dir_and_extension(upload_filepath)
        r ={}
        r['filepath'] = upload_filepath
        r['format'] = f[1]
        return self.force_response(r)

    @staticmethod
    def validate_grid_interpol_params(params):
        trans_type = params['trans-type']
        sub_type = params['sub-type']
        if trans_type == "inter":
            if sub_type not in ("near","bilin"):
                raise RestApiException('{} is a bad interpolation sub-type for {}'.format(sub_type,trans_type),
                                       status_code=hcodes.HTTP_BAD_REQUEST)
        elif trans_type == "boxinter":
            if sub_type not in ("average","min","max"):
                raise RestApiException('{} is a bad interpolation sub type for {}'.format(sub_type,trans_type),
                                       status_code=hcodes.HTTP_BAD_REQUEST)

    @staticmethod
    def validate_spare_point_interpol_params(params):
        trans_type = params['trans-type']
        sub_type = params['sub-type']
        if trans_type == "inter":
            if sub_type not in ("near", "bilin"):
                raise RestApiException('{} is a bad interpolation sub-type for {}'.format(sub_type, trans_type),
                                       status_code=hcodes.HTTP_BAD_REQUEST)
        elif trans_type == "polyinter":
            if sub_type not in ("average", "min", "max"):
                raise RestApiException('{} is a bad interpolation sub type for {}'.format(sub_type, trans_type),
                                       status_code=hcodes.HTTP_BAD_REQUEST)
