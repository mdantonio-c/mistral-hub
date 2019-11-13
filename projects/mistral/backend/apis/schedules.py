from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager

log = get_logger(__name__)


class Schedules(EndpointResource):

    # schema_expose = True
    labels = ['schedule']
    GET = {
        '/schedules/<schedule_id>': {
            'summary': 'Get user schedules.',
            'description': 'Returns a single schedule by ID',
            'tags': ['schedule'],
            'responses': {
                '200': {
                    'description': 'List of user schedules.',
                    'schema': {'$ref': '#/definitions/Requests'},
                },
                '401': {
                    'description': 'This endpoint requires a valid authorization token'
                },
                '403': {'description': 'User not allowed to get the schedule'},
                '404': {'description': 'The schedule does not exists'},
            },
            'parameters': [
                {
                    'name': 'sort-order',
                    'in': 'query',
                    'description': 'sort order',
                    'type': 'string',
                    'enum': ['asc', 'desc'],
                },
                {
                    'name': 'sort-by',
                    'in': 'query',
                    'description': 'params to sort schedules',
                    'type': 'string',
                },
                {
                    'name': 'get_total',
                    'in': 'query',
                    'description': 'Retrieve total number of schedules',
                    'type': 'boolean',
                    'default': False,
                },
            ],
        },
        '/schedules': {
            'summary': 'Get user schedules.',
            'description': 'Returns a single schedule by ID',
            'tags': ['schedule'],
            'responses': {
                '200': {
                    'description': 'List of user schedules.',
                    'schema': {'$ref': '#/definitions/Requests'},
                },
                '401': {
                    'description': 'This endpoint requires a valid authorization token'
                },
                '403': {'description': 'User not allowed to get the schedule'},
                '404': {'description': 'The schedule does not exists'},
            },
            'parameters': [
                {
                    'name': 'sort-order',
                    'in': 'query',
                    'description': 'sort order',
                    'type': 'string',
                    'enum': ['asc', 'desc'],
                },
                {
                    'name': 'sort-by',
                    'in': 'query',
                    'description': 'params to sort schedules',
                    'type': 'string',
                },
                {
                    'name': 'get_total',
                    'in': 'query',
                    'description': 'Retrieve total number of schedules',
                    'type': 'boolean',
                    'default': False,
                },
            ],
        },
    }
    POST = {
        '/schedules': {
            'summary': 'Request for scheduling a data extraction.',
            'parameters': [
                {
                    'name': 'scheduled_criteria',
                    'in': 'body',
                    'description': 'Criteria for scheduled data extraction.',
                    'schema': {'$ref': '#/definitions/DataScheduling'},
                }
            ],
            'responses': {
                '201': {'description': 'succesfully created a scheduled request'},
                '400': {'description': 'scheduling criteria are not valid'},
                '404': {'description': 'dataset not found'},
            },
        }
    }
    PATCH = {
        '/schedules/<schedule_id>': {
            'summary': 'enable or disable a schedule',
            'parameters': [
                {
                    'in': 'path',
                    'name': 'id',
                    'type': 'integer',
                    'required': True,
                    'description': 'schedule id',
                },
                {
                    'name': 'action',
                    'in': 'body',
                    'description': 'action to do on schedule (enabling or disabling)',
                    'schema': {
                        'type': 'object',
                        'required': ['is_active'],
                        'properties': {
                            'is_active': {
                                'type': 'boolean',
                                'description': 'requested value for is active property',
                            }
                        },
                    },
                },
            ],
            'responses': {
                '200': {'description': 'schedule is succesfully disable/enable'},
                '404': {'description': 'schedule not found'},
                '400': {'description': 'schedule is already enabled/disabled'},
                '401': {
                    'description': 'Current user is not allowed disable/enable the schedule in path'
                },
            },
        }
    }
    DELETE = {
        '/schedules/<schedule_id>': {
            'summary': 'delete a schedule',
            'parameters': [
                {
                    'in': 'path',
                    'name': 'id',
                    'type': 'integer',
                    'required': True,
                    'description': 'schedule id',
                }
            ],
            'responses': {
                '200': {'description': 'schedule is succesfully disable/enable'},
                '404': {'description': 'schedule not found'},
                '401': {
                    'description': 'Current user is not allowed disable/enable the schedule in path'
                },
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
            if p_type == 'additional_variables':
                self.validate_input(p, 'AVProcessor')
            else:
                raise RestApiException(
                    'Unknown post-processor type for {}'.format(p_type),
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )

        db = self.get_service_instance('sqlalchemy')

        # check if scheduling parameters are correct
        if not self.settings_validation(criteria):
            raise RestApiException(
                "scheduling criteria are not valid", status_code=hcodes.HTTP_BAD_REQUEST
            )

        # parsing period settings
        period_settings = criteria.get('period-settings')
        if period_settings is not None:
            every = str(period_settings.get('every'))
            period = period_settings.get('period')
            log.info("Period settings [{} {}]".format(every, period))

            # get schedule id in postgres database as scheduled request name for mongodb
            try:
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    product_name,
                    {
                        'datasets': dataset_names,
                        'reftime': reftime,
                        'filters': filters,
                        'postprocessors': processors,
                    },
                    every=every,
                    period=period,
                )
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
                    args=[
                        user.id,
                        dataset_names,
                        reftime,
                        filters,
                        processors,
                        request_id,
                        name_int,
                    ],
                )

                log.info("Scheduling periodic task")
            except Exception as error:
                db.session.rollback()
                raise SystemError("Unable to submit the request")

        crontab_settings = criteria.get('crontab-settings')
        if crontab_settings is not None:
            log.info('Crontab settings {}'.format(crontab_settings))
            try:
                # get scheduled request id in postgres database as scheduled request name for mongodb
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    product_name,
                    {
                        'datasets': dataset_names,
                        'reftime': reftime,
                        'filters': filters,
                        'postprocessors': processors,
                    },
                    crontab_settings=crontab_settings,
                )
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
                    args=[
                        user.id,
                        dataset_names,
                        reftime,
                        filters,
                        processors,
                        request_id,
                        name_int,
                    ],
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
    @authentication.required()
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
            res = RequestManager.get_user_schedules(
                db, user.id, sort_by=sort, sort_order=sort_order
            )

        return self.force_response(res, code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    @authentication.required()
    def patch(self, schedule_id):
        param = self.get_input()
        is_active = param.get('is_active')
        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        # retrieving mongodb task
        task = CeleryExt.get_periodic_task(name=schedule_id)
        log.debug("Periodic task - {}".format(task))
        # disable the schedule deleting it from mongodb
        if is_active is False:
            if task is None:
                raise RestApiException(
                    "Scheduled task is already disabled",
                    status_code=hcodes.HTTP_BAD_CONFLICT,
                )
            CeleryExt.delete_periodic_task(name=schedule_id)
        # enable the schedule
        if is_active is True:
            if task:
                raise RestApiException(
                    "Scheduled task is already enabled",
                    status_code=hcodes.HTTP_BAD_CONFLICT,
                )

            # recreate the schedule in mongo retrieving the schedule from postgres
            schedule_response = RequestManager.get_schedule_by_id(db, schedule_id)
            log.debug("schedule response: {}".format(schedule_response))

            # recreate the schedule in mongo retrieving the schedule from postgres
            try:
                request_id = None
                if 'periodic' in schedule_response:
                    CeleryExt.create_periodic_task(
                        name=str(schedule_id),
                        task="mistral.tasks.data_extraction.data_extract",
                        every=schedule_response['every'],
                        period=schedule_response['period'],
                        args=[
                            user.id,
                            schedule_response['args']['datasets'],
                            schedule_response['args']['reftime'],
                            schedule_response['args']['filters'],
                            schedule_response['args']['postprocessors'],
                            request_id,
                            schedule_id,
                        ],
                    )

                if 'crontab' in schedule_response:
                    # parsing crontab settings
                    crontab_settings = {}
                    for i in schedule_response['crontab_settings'].keys():
                        log.debug(i)
                        val = schedule_response['crontab_settings'].get(i)
                        str_val = str(val)
                        crontab_settings[i] = str_val
                    CeleryExt.create_crontab_task(
                        name=str(schedule_id),
                        task="mistral.tasks.data_extraction.data_extract",
                        **crontab_settings,
                        args=[
                            user.id,
                            schedule_response['args']['datasets'],
                            schedule_response['args']['reftime'],
                            schedule_response['args']['filters'],
                            schedule_response['args']['postprocessors'],
                            request_id,
                            schedule_id,
                        ],
                    )

            except Exception as error:
                raise SystemError("Unable to enable the request")

        # update schedule status in database
        RequestManager.update_schedule_status(db, schedule_id, is_active)

        return self.force_response(
            {'id': schedule_id, 'enabled': is_active}, code=hcodes.HTTP_OK_BASIC
        )

    @catch_error()
    @authentication.required()
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
            "Schedule {} succesfully deleted".format(schedule_id),
            code=hcodes.HTTP_OK_BASIC,
        )

    @staticmethod
    def request_and_owner_check(db, user_id, schedule_id):
        # check if the schedule exists
        if not RequestManager.check_request(db, schedule_id=schedule_id):
            raise RestApiException(
                "The request doesn't exist", status_code=hcodes.HTTP_BAD_NOTFOUND
            )

        # check if the current user is the owner of the request
        if not RequestManager.check_owner(db, user_id, schedule_id=schedule_id):
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_FORBIDDEN,
            )


class ScheduledRequests(EndpointResource):

    # schema_expose = True
    labels = ['scheduled_requests']
    GET = {
        '/schedules/<schedule_id>/requests': {
            'summary': 'Get requests related to a given schedule.',
            'parameters': [
                {
                    'name': 'get_total',
                    'in': 'query',
                    'description': 'Retrieve total number of requests',
                    'type': 'boolean',
                    'default': False,
                },
                {
                    'name': 'last',
                    'in': 'query',
                    'description': 'retrieve only the last submitted request',
                    'type': 'boolean',
                    'allowEmptyValue': True,
                },
            ],
            'responses': {
                '200': {
                    'description': 'List of requests for a given schedule.',
                    'schema': {'$ref': '#/definitions/Requests'},
                },
                '404': {'description': 'Schedule not found.'},
                '403': {
                    'description': 'User cannot access a schedule that does not belong to.'
                },
            },
        }
    }

    @catch_error()
    @authentication.required()
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
                status_code=hcodes.HTTP_BAD_NOTFOUND,
            )

        # check for schedule ownership
        user = self.get_current_user()
        if not RequestManager.check_owner(db, user.id, schedule_id=schedule_id):
            raise RestApiException(
                "This request doesn't come from the schedule's owner",
                status_code=hcodes.HTTP_BAD_FORBIDDEN,
            )

        if get_total:
            # get total count for user schedules
            counter = RequestManager.count_schedule_requests(db, schedule_id)
            return {"total": counter}

        # get all submitted requests or the last for this schedule
        meta_response = {}
        if last:
            res = RequestManager.get_last_scheduled_request(db, schedule_id)
            if res is None:
                raise RestApiException(
                    "No successful request is available for schedule ID {} yet".format(
                        schedule_id
                    ),
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )
            # also return the total
            meta_response['total'] = RequestManager.count_schedule_requests(
                db, schedule_id
            )
        else:
            res = RequestManager.get_schedule_requests(db, schedule_id)
        return self.force_response(res, meta=meta_response, code=hcodes.HTTP_OK_BASIC)
