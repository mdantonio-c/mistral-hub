# -*- coding: utf-8 -*-

import os
from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from flask import request

from jsonschema.exceptions import ValidationError
# from mistral.apis import validator
from utilities.globals import mem
from bravado_core.validate import validate_object

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
        datasets = criteria.get('datasets', [])

        # TODO check for existing dataset(s)

        filters = criteria.get('filters')
        # TODO check for valid and allowed filters

        task = CeleryExt.data_extract.apply_async(
            args=[user.uuid, datasets, filters],
            countdown=1
        )
        return self.force_response(
            task.id, code=hcodes.HTTP_OK_ACCEPTED)
