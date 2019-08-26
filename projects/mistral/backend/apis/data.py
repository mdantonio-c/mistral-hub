# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager as repo

log = get_logger(__name__)


class Data(EndpointResource):

    @catch_error()
    def post(self):

        user = self.get_current_user()
        log.info('request for data extraction coming from user UUID: {}'.format(user.uuid))
        criteria = self.get_input()

        self.validate_input(criteria, 'DataExtraction')
        product_name = criteria.get('name')
        dataset_names = criteria.get('datasets')
        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get('id', '') == ds_name), None)
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)
        # incoming filters: <dict> in form of filter_name: list_of_values
        # e.g. 'level': [{...}, {...}] or 'level: {...}'
        filters = criteria.get('filters')
        # clean up filters from unknown values
        filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        # run the following steps in a transaction
        db = self.get_service_instance('sqlalchemy')
        try:
            request = repo.create_request_record(db, user.uuid, product_name, {
                'datasets': dataset_names,
                'filters': filters,
            })

            task = CeleryExt.data_extract.apply_async(
                args=[user.uuid, product_name, dataset_names, filters, request.id],
                countdown=1
            )

            request.task_id = task.id
            request.status = task.status  # 'PENDING'
            db.session.commit()
            log.info('Request successfully saved: <ID:{}>'.format(request.id))
        except Exception as error:
            db.session.rollback()
            raise SystemError("Unable to submit the request")

        return self.force_response(
            {'task_id': task.id, 'task_status': task.status}, code=hcodes.HTTP_OK_ACCEPTED)
