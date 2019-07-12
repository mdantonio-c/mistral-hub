# -*- coding: utf-8 -*-

import os
from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki

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
    def put(self):

        # Calls test('hello') every 10 seconds.
        task = CeleryExt.celery_app.add_periodic_task(
            10.0,
            CeleryExt.add.s(7, 7),
            name='add every 10'
        )

        log.info("Scheduling periodic task: %s", task)

        # Calls test('world') every 30 seconds
        # sender.add_periodic_task(30.0, add.s(5, 5), expires=10)

        # Executes every Monday morning at 7:30 a.m.
        # sender.add_periodic_task(
        #     crontab(hour=7, minute=30, day_of_week=1),
        #     add.s(1, 1),
        # )

        return self.empty_response()

    @catch_error()
    def post(self):

        user = self.get_current_user()
        log.info('request for data extraction coming from user UUID: {}'.format(user.uuid))
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

        task = CeleryExt.data_extract.apply_async(
            args=[user.uuid, dataset_names, filters],
            countdown=1
        )

        return self.force_response(
            task.id, code=hcodes.HTTP_OK_ACCEPTED)
