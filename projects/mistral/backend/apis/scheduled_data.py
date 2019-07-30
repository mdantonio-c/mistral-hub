from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager

log = get_logger(__name__)


class ScheduledData(EndpointResource):

    @catch_error()
    def post(self):

        user = self.get_current_user()
        criteria = self.get_input()
        self.validate_input(criteria, 'DataScheduling')

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

        period_settings = criteria.get('period-settings')
        if period_settings is not None:
            every = period_settings.get('every')
            period = period_settings.get('period')
            log.info("Period settings [{} {}]".format(every, period))
            RequestManager.create_scheduled_request_record(db, user, filters, every=every, period=period)

        crontab_settings = criteria.get('crontab-settings')
        if crontab_settings is not None:
            #minute =
            log.info("crontab task")
            RequestManager.create_scheduled_request_record(db, user, filters, crontab_settings=crontab_settings)

        # obj = CeleryExt.get_periodic_task(name='add every 10')
        # log.critical(obj)

        # remove previous task
        # res = CeleryExt.delete_periodic_task(name='add every 10')
        # log.debug("Previous task deleted = %s", res)
        #
        # CeleryExt.create_periodic_task(
        #     name='add every 10',
        #     task="mistral.tasks.data_extraction.add",
        #     every=10,
        #     period='seconds',
        #     args=[7, 7],
        # )

        log.info("Scheduling periodic task")

        # Calls test('world') every 30 seconds
        # sender.add_periodic_task(30.0, add.s(5, 5), expires=10)

        # Executes every Monday morning at 7:30 a.m.
        # sender.add_periodic_task(
        #     crontab(hour=7, minute=30, day_of_week=1),
        #     add.s(1, 1),
        # )

        return self.force_response("Scheduled")

    @catch_error()
    def delete(self):
        return self.force_response("Removed")