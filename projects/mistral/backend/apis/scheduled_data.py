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

        # parsing period settings
        period_settings = criteria.get('period-settings')
        if period_settings is not None:
            every = str(period_settings.get('every'))
            period = period_settings.get('period')
            log.info("Period settings [{} {}]".format(every, period))
            # get scheduled request id in postgres database as scheduled request name for mongodb
            name_int = RequestManager.create_scheduled_request_record(db, user, filters, every=every, period=period)
            name = str(name_int)

            # remove previous task
            res = CeleryExt.delete_periodic_task(name=name)
            log.debug("Previous task deleted = %s", res)

            CeleryExt.create_periodic_task(
                name=name,
                task="mistral.tasks.data_extraction.data_extract",
                every=every,
                period=period,
                args=[user.uuid, dataset_names, filters],
            )

            log.info("Scheduling periodic task")


        crontab_settings = criteria.get('crontab-settings')
        if crontab_settings is not None:
            # get scheduled request id in postgres database as scheduled request name for mongodb
            name_int =RequestManager.create_scheduled_request_record(db, user, filters, crontab_settings=crontab_settings)
            name = str(name_int)

            # parsing crontab settings
            for i in crontab_settings.keys():
                val = crontab_settings.get(i)
                str_val = str(val)
                crontab_settings[i] = str_val

            CeleryExt.create_crontab_task(
                name=name,
                task="mistral.tasks.data_extraction.data_extract",
                **crontab_settings,
                args=[user.uuid, dataset_names, filters],
            )

            log.info("Scheduling crontab task")

        return self.force_response('Scheduled task {}'.format(name))

    @catch_error()
    def delete(self):
        param = self.get_input()
        task_name = param.get('task')

        # delete request entry from database
        db = self.get_service_instance('sqlalchemy')
        RequestManager.delete_scheduled_request_record(db, task_name)

        CeleryExt.delete_periodic_task(name=task_name)

        return self.force_response('Removed task {}'.format(task_name))