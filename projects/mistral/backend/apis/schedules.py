from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager

log = get_logger(__name__)


class Schedules(EndpointResource):

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
        filters = criteria.get('filters', {})
        # clean up filters from unknown values
        filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        processors = criteria.get('postprocessors', [])
        # clean up processors from unknown values
        # processors = [i for i in processors if arki.is_processor_allowed(i.get('type'))]
        for p in processors:
            p_type = p.get('type')
            if p_type == 'additional_variables':
                self.validate_input(p, 'AVProcessor')
            else:
                raise RestApiException('Unknown post-processor type for {}'.format(p_type),
                                       status_code=hcodes.HTTP_BAD_REQUEST)

        db = self.get_service_instance('sqlalchemy')

        # check if scheduling parameters are correct
        if not self.settings_validation(criteria):
            raise RestApiException(
                "scheduling criteria are not valid",
                status_code=hcodes.HTTP_BAD_REQUEST)

        # parsing period settings
        period_settings = criteria.get('period-settings')
        if period_settings is not None:
            every = str(period_settings.get('every'))
            period = period_settings.get('period')
            log.info("Period settings [{} {}]".format(every, period))

            # get schedule id in postgres database as scheduled request name for mongodb
            try:
                name_int = RequestManager.create_schedule_record(db, user, product_name, {
                    'datasets': dataset_names,
                    'filters': filters,
                    'postprocessors': processors
                }, every=every, period=period)
                name = str(name_int)

                # remove previous task
                res = CeleryExt.delete_periodic_task(name=name)
                log.debug("Previous task deleted = %s", res)

                request_id = None

                CeleryExt.create_periodic_task(
                    name=name,
                    task="mistral.tasks.data_extraction.data_extract",
                    every=every,
                    period=period,
                    args=[user.id, dataset_names, filters, processors, request_id, name_int],
                )

                log.info("Scheduling periodic task")
            except Exception as error:
                db.session.rollback()
                raise SystemError("Unable to submit the request")

        crontab_settings = criteria.get('crontab-settings')
        if crontab_settings is not None:

            try:
                # get scheduled request id in postgres database as scheduled request name for mongodb
                name_int = RequestManager.create_schedule_record(db, user, product_name, {
                    'datasets': dataset_names,
                    'filters': filters,
                    'postprocessors': processors
                }, crontab_settings=crontab_settings)
                name = str(name_int)

                # parsing crontab settings
                for i in crontab_settings.keys():
                    val = crontab_settings.get(i)
                    str_val = str(val)
                    crontab_settings[i] = str_val

                request_id = None

                CeleryExt.create_crontab_task(
                    name=name,
                    task="mistral.tasks.data_extraction.data_extract",
                    **crontab_settings,
                    args=[user.id, dataset_names, filters, processors, request_id, name_int],
                )

                log.info("Scheduling crontab task")
            except Exception as error:
                db.session.rollback()
                raise SystemError("Unable to submit the request")

        return self.force_response('Scheduled task {}'.format(name))

    @staticmethod
    def settings_validation(criteria):
        # check if at least one scheduling parameter is in the request
        period_settings = criteria.get('period-settings')
        crontab_settings = criteria.get('crontab-settings')
        if period_settings or crontab_settings is not None:
            return True
        else:
            return False

    @catch_error()
    def get(self, schedule_id=None):
        param = self.get_input()
        sort = param.get('sort-by')
        sort_order = param.get('sort-order')
        get_total = param.get('get_total', False)

        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')
        if schedule_id is not None:
            # check for schedule ownership
            self.request_and_owner_check(db, user.id, schedule_id)
            # get schedule by id
            res = RequestManager.get_schedule_by_id(db, schedule_id)
        else:
            # get total count for user schedules
            if get_total:
                counter = RequestManager.count_user_schedules(db, user.id)
                return {"total": counter}
            # get user requests list
            res = RequestManager.get_user_schedules(db, user.id, sort_by=sort, sort_order=sort_order)

        return self.force_response(
            res, code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    def patch(self, schedule_id):
        param = self.get_input()
        is_active = param.get('is_active')
        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        # disable/enable the schedule
        periodic = CeleryExt.get_periodic_task(name=schedule_id)
        periodic.update(enabled=is_active)

        # update schedule status in database
        RequestManager.update_schedule_status(db, schedule_id, is_active)

        return self.force_response(
            "Schedule {}: enabled = {}".format(schedule_id, is_active), code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    def delete(self, schedule_id):
        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        # delete schedule in mongodb
        CeleryExt.delete_periodic_task(name=schedule_id)

        # delete schedule status in database
        RequestManager.delete_schedule(db, schedule_id)

        return self.force_response(
            "Schedule {} succesfully deleted".format(schedule_id), code=hcodes.HTTP_OK_BASIC)

    @staticmethod
    def request_and_owner_check(db, user_id, schedule_id):
        # check if the schedule exists
        if not RequestManager.check_request(db, schedule_id=schedule_id):
            raise RestApiException(
                "The request doesn't exist",
                status_code=hcodes.HTTP_BAD_NOTFOUND)

        # check if the current user is the owner of the request
        if not RequestManager.check_owner(db, user_id, schedule_id=schedule_id):
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_FORBIDDEN)


class ScheduledRequests(EndpointResource):

    @catch_error()
    def get(self, schedule_id):
        """
        Get all submitted requests for this schedule
        :param schedule_id:
        :return:
        """
        log.debug('get scheduled requests')
        param = self.get_input()
        get_total = param.get('get_total', False)
        last = param.get('last')
        if isinstance(last, str) and (last == '' or last.lower() == 'true'):
            last = True
        elif type(last) == bool:
            # do nothing
            pass
        else:
            last = False

        db = self.get_service_instance('sqlalchemy')

        # check if the schedule exists
        if not RequestManager.check_request(db, schedule_id=schedule_id):
            raise RestApiException(
                "The schedule ID {} doesn't exist".format(schedule_id),
                status_code=hcodes.HTTP_BAD_NOTFOUND)

        # check for schedule ownership
        user = self.get_current_user()
        if not RequestManager.check_owner(db, user.id, schedule_id=schedule_id):
            raise RestApiException(
                "This request doesn't come from the schedule's owner",
                status_code=hcodes.HTTP_BAD_FORBIDDEN)

        if get_total:
            # get total count for user schedules
            counter = RequestManager.count_schedule_requests(db, schedule_id)
            return {"total": counter}

        # get all submitted requests or the last for this schedule
        res = RequestManager.get_schedule_requests(db, schedule_id, last=last)
        return self.force_response(
            res, code=hcodes.HTTP_OK_BASIC)
