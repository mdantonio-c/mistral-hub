# -*- coding: utf-8 -*-

import os
from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger

log = get_logger(__name__)


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

        # ########## INIT ##########

        task = CeleryExt.data_extract.apply_async(
            args=[],
            countdown=10
        )
        return self.force_response(
            task.id, code=hcodes.HTTP_OK_ACCEPTED)
