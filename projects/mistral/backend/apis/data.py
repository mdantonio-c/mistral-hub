# -*- coding: utf-8 -*-

import os
from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager

logger = get_logger(__name__)


class Data(EndpointResource):

    # @catch_error()
    # def get(self, task_id):

    #     celery = self.get_service_instance('celery')

    #     task_result = celery.AsyncResult(task_id)
    #     res = task_result.result
    #     if not isinstance(res, dict):
    #         res = str(res)
    #     return {
    #         'status': task_result.status,
    #         'output': res,
    #     }

    @catch_error()
    def post(self):

        user = self.get_current_user()
        logger.info('request for data extraction coming from user UUID: {}'.format(user.uuid))
        criteria = self.get_input()

        self.validate_input(criteria, 'DataExtraction')
        dataset_names = criteria.get('datasets')
        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get('id', '') == ds_name), None)
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)

        filters = criteria.get('filters')

        db= self.get_service_instance('sqlalchemy')

        request_id = RequestManager.create_request_table(db,user,filters)
        logger.info('current request id: {}'.format(request_id))

        task = CeleryExt.data_extract.apply_async(
            args=[user.uuid, dataset_names, filters],
            countdown=1
        )
        return self.force_response(
            task.id, code=hcodes.HTTP_OK_ACCEPTED)
