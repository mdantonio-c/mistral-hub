# -*- coding: utf-8 -*-

import os
from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger

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
        input_parameters = self.get_input()

        datasets = input_parameters.get('datasets', [])
        if not datasets:
            raise RestApiException(
                "Please specify at least one dataset",
                status_code=hcodes.HTTP_BAD_REQUEST)
        # TODO check for existing dataset(s)

        filters = input_parameters.get('filters')
        # TODO check for valid and allowed filters

        task = CeleryExt.data_extract.apply_async(
            args=[user.uuid, datasets, filters],
            countdown=1
        )
        return self.force_response(
            task.id, code=hcodes.HTTP_OK_ACCEPTED)
