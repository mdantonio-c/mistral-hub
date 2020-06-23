import datetime

from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import spare_point_interpol as pp3_3
from mistral.tools import statistic_elaboration as pp2
from restapi import decorators
from restapi.connectors.celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class Schedules(EndpointResource):
    labels = ["schedule"]
    GET = {
        "/schedules/<schedule_id>": {
            "summary": "Get user schedules.",
            "description": "Returns a single schedule by ID",
            "tags": ["schedule"],
            "responses": {
                "200": {
                    "description": "List of user schedules.",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "401": {
                    "description": "This endpoint requires a valid authorization token"
                },
                "403": {"description": "User not allowed to get the schedule"},
                "404": {"description": "The schedule does not exists"},
            },
            "parameters": [
                {
                    "name": "sort-order",
                    "in": "query",
                    "description": "sort order",
                    "type": "string",
                    "enum": ["asc", "desc"],
                },
                {
                    "name": "sort-by",
                    "in": "query",
                    "description": "params to sort schedules",
                    "type": "string",
                },
                {
                    "name": "get_total",
                    "in": "query",
                    "description": "Retrieve total number of schedules",
                    "type": "boolean",
                    "default": False,
                },
            ],
        },
        "/schedules": {
            "summary": "Get user schedules.",
            "description": "Returns a single schedule by ID",
            "tags": ["schedule"],
            "responses": {
                "200": {
                    "description": "List of user schedules.",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "401": {
                    "description": "This endpoint requires a valid authorization token"
                },
                "403": {"description": "User not allowed to get the schedule"},
                "404": {"description": "The schedule does not exists"},
            },
            "parameters": [
                {
                    "name": "sort-order",
                    "in": "query",
                    "description": "sort order",
                    "type": "string",
                    "enum": ["asc", "desc"],
                },
                {
                    "name": "sort-by",
                    "in": "query",
                    "description": "params to sort schedules",
                    "type": "string",
                },
                {
                    "name": "get_total",
                    "in": "query",
                    "description": "Retrieve total number of schedules",
                    "type": "boolean",
                    "default": False,
                },
            ],
        },
    }
    POST = {
        "/schedules": {
            "summary": "Request for scheduling a data extraction.",
            "parameters": [
                {
                    "name": "scheduled_criteria",
                    "in": "body",
                    "description": "Criteria for scheduled data extraction.",
                    "schema": {"$ref": "#/definitions/DataScheduling"},
                },
                {
                    "name": "push",
                    "in": "query",
                    "description": "Enable push notification",
                    "type": "boolean",
                    "default": False,
                    "allowEmptyValue": True,
                },
            ],
            "responses": {
                "201": {"description": "scheduled request successfully created"},
                "400": {"description": "invalid scheduled request"},
                "404": {
                    "description": "impossible to schedule the request: dataset not found"
                },
            },
        }
    }
    PATCH = {
        "/schedules/<schedule_id>": {
            "summary": "enable or disable a schedule",
            "parameters": [
                {
                    "in": "path",
                    "name": "id",
                    "type": "integer",
                    "required": True,
                    "description": "schedule id",
                },
                {
                    "name": "action",
                    "in": "body",
                    "description": "action to do on schedule (enabling or disabling)",
                    "schema": {
                        "type": "object",
                        "required": ["is_active"],
                        "properties": {
                            "is_active": {
                                "type": "boolean",
                                "description": "requested value for is active property",
                            }
                        },
                    },
                },
            ],
            "responses": {
                "200": {"description": "schedule is succesfully disable/enable"},
                "404": {"description": "schedule not found"},
                "400": {"description": "schedule is already enabled/disabled"},
                "401": {
                    "description": "Current user is not allowed disable/enable the schedule in path"
                },
            },
        }
    }
    DELETE = {
        "/schedules/<schedule_id>": {
            "summary": "delete a schedule",
            "parameters": [
                {
                    "in": "path",
                    "name": "id",
                    "type": "integer",
                    "required": True,
                    "description": "schedule id",
                }
            ],
            "responses": {
                "200": {"description": "schedule is succesfully disable/enable"},
                "404": {"description": "schedule not found"},
                "401": {
                    "description": "Current user is not allowed disable/enable the schedule in path"
                },
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def post(self):
        user = self.get_current_user()
        log.info(f"request for data extraction coming from user UUID: {user.uuid}")
        criteria = self.get_input()

        self.validate_input(criteria, "DataExtraction")
        product_name = criteria.get("name")
        dataset_names = criteria.get("datasets")
        reftime = criteria.get("reftime")
        output_format = criteria.get("output_format")

        time_delta = None
        reftime_to = None
        if reftime is not None:
            # 'from' and 'to' both mandatory by schema
            # check from <= to
            if reftime["from"] > reftime["to"]:
                raise RestApiException(
                    "Invalid reftime: <from> greater than <to>",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            reftime_to = datetime.datetime.strptime(
                reftime["to"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            reftime_from = datetime.datetime.strptime(
                reftime["from"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            time_delta = reftime_to - reftime_from

        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get("id", "") == ds_name), None)
            if not found:
                raise RestApiException(
                    f"Dataset '{ds_name}' not found",
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )
        # incoming filters: <dict> in form of filter_name: list_of_values
        # e.g. 'level': [{...}, {...}] or 'level: {...}'
        filters = criteria.get("filters", {})
        # clean up filters from unknown values
        filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        processors = criteria.get("postprocessors", [])
        # clean up processors from unknown values
        # processors = [i for i in processors if arki.is_processor_allowed(i.get('type'))]
        for p in processors:
            p_type = p.get("type")
            if p_type == "derived_variables":
                self.validate_input(p, "AVProcessor")
            elif p_type == "grid_interpolation":
                self.validate_input(p, "GIProcessor")
                pp3_1.get_trans_type(p)
            elif p_type == "grid_cropping":
                self.validate_input(p, "GCProcessor")
                p["trans-type"] = "zoom"
            elif p_type == "spare_point_interpolation":
                self.validate_input(p, "SPIProcessor")
                pp3_3.get_trans_type(p)
                pp3_3.validate_spare_point_interpol_params(p)
            elif p_type == "statistic_elaboration":
                self.validate_input(p, "SEProcessor")
                pp2.validate_statistic_elaboration_params(p)
            else:
                raise RestApiException(
                    f"Unknown post-processor type for {p_type}",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # if there is a pp combination check if there is only one geographical postprocessor
        if len(processors) > 1:
            pp_list = []
            for p in processors:
                pp_list.append(p.get("type"))
            pp3_list = [
                "grid_cropping",
                "grid_interpolation",
                "spare_point_interpolation",
            ]
            if len(set(pp_list).intersection(set(pp3_list))) > 1:
                raise RestApiException(
                    "Only one geographical postprocessing at a time can be executed",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )

        # get the format of the datasets
        dataset_format = arki.get_datasets_format(dataset_names)
        if not dataset_format:
            raise RestApiException(
                "Invalid set of datasets : datasets have different formats",
                status_code=hcodes.HTTP_BAD_REQUEST,
            )
        # check if the output format chosen by the user is compatible with the chosen datasets
        if output_format is not None:
            if dataset_format != output_format:
                if dataset_format == "grib":
                    postprocessors_list = [i.get("type") for i in processors]
                    # spare point interpolation has bufr as output format
                    if "spare_point_interpolation" not in postprocessors_list:
                        raise RestApiException(
                            f"The chosen datasets does not support {output_format} output format",
                            status_code=hcodes.HTTP_BAD_REQUEST,
                        )
                if dataset_format == "bufr" and output_format == "grib":
                    raise RestApiException(
                        f"The chosen datasets does not support {output_format} output format",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )

        # check if the schedule is a 'on-data-ready' one
        data_ready = False
        # data ready option is not for observed data
        if dataset_format == "grib":
            # get today date
            today = datetime.date.today()
            # if the date of reftime['to'] is today or yesterday the request can be considered a data-ready one
            if reftime_to.date() == today or reftime_to.date() == today - datetime.timedelta(
                days=1
            ):
                data_ready = True
            # what if reftime is None?

        push = criteria.get("push")
        if isinstance(push, str) and (push.lower() == "true"):
            push = True
        elif type(push) == bool:
            # do nothing
            pass
        else:
            push = False
        # get queue for pushing notifications
        pushing_queue = None
        if push:
            # TODO build the queue name according to the chosen convention
            pushing_queue = user.id
            # rabbit = self.get_service_instance("rabbit")
            self.get_service_instance("rabbit")
            # TODO: check if pushing_queue exists,
            #  if not raise an error (401? user is not authorized to get push notification)

        db = self.get_service_instance("sqlalchemy", global_instance=False)

        # check if scheduling parameters are correct
        if not self.settings_validation(criteria):
            raise RestApiException(
                "scheduling criteria are not valid", status_code=hcodes.HTTP_BAD_REQUEST
            )
        name = None
        try:
            # parsing period settings
            period_settings = criteria.get("period-settings")
            if period_settings is not None:
                every = str(period_settings.get("every"))
                period = period_settings.get("period")
                log.info("Period settings [{} {}]", every, period)

                # get schedule id in postgres database as scheduled request name for mongodb
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    product_name,
                    {
                        "datasets": dataset_names,
                        "reftime": reftime,
                        "filters": filters,
                        "postprocessors": processors,
                        "output_format": output_format,
                        "pushing_queue": pushing_queue,
                    },
                    every=every,
                    period=period,
                    on_data_ready=data_ready,
                    time_delta=time_delta,
                )
                name = str(name_int)

                if data_ready is False:
                    # remove previous task
                    res = CeleryExt.delete_periodic_task(name=name)
                    log.debug("Previous task deleted = {}", res)

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
                            output_format,
                            request_id,
                            pushing_queue,
                            name_int,
                        ],
                    )
                    log.info("Scheduling periodic task")

            crontab_settings = criteria.get("crontab-settings")
            if crontab_settings is not None:
                log.info("Crontab settings {}", crontab_settings)
                # get scheduled request id in postgres database as scheduled request name for mongodb
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    product_name,
                    {
                        "datasets": dataset_names,
                        "reftime": reftime,
                        "filters": filters,
                        "postprocessors": processors,
                        "output_format": output_format,
                        "pushing_queue": pushing_queue,
                    },
                    crontab_settings=crontab_settings,
                    on_data_ready=data_ready,
                    time_delta=time_delta,
                )
                name = str(name_int)
                if data_ready is False:
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
                            output_format,
                            request_id,
                            pushing_queue,
                            name_int,
                        ],
                    )
                    log.info("Scheduling crontab task")
            if data_ready:
                # submit the first request
                request_id = None
                CeleryExt.data_extract.apply_async(
                    args=[
                        user.id,
                        dataset_names,
                        reftime,
                        filters,
                        processors,
                        output_format,
                        request_id,
                        pushing_queue,
                        name,
                    ],
                    countdown=1,
                )

        except Exception as error:
            log.error(error)
            db.session.rollback()
            raise SystemError("Unable to submit the request")
        if name:
            r = {"schedule_id": name}
        else:
            raise RestApiException(
                "Unable to submit the request", status_code=hcodes.HTTP_SERVER_ERROR,
            )
        return self.response(r, code=hcodes.HTTP_OK_ACCEPTED)

    @staticmethod
    def settings_validation(criteria):
        # check if at least one scheduling parameter is in the request
        period_settings = criteria.get("period-settings")
        crontab_settings = criteria.get("crontab-settings")
        on_data_ready = (
            criteria["on-data-ready"]
            if "on-data-ready" in criteria
            and isinstance(criteria["on-data-ready"], bool)
            else False
        )
        if period_settings or crontab_settings is not None:
            return True
        else:
            return on_data_ready

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self, schedule_id=None):
        param = self.get_input()
        sort = param.get("sort-by")
        sort_order = param.get("sort-order")
        get_total = param.get("get_total", False)

        user = self.get_current_user()

        db = self.get_service_instance("sqlalchemy")
        if schedule_id is not None:
            # check for schedule ownership
            self.request_and_owner_check(db, user.id, schedule_id)
            # get schedule by id
            res = RequestManager.get_schedule_by_id(db, schedule_id)
        else:
            # get total count for user schedules
            if get_total:
                counter = RequestManager.count_user_schedules(db, user.id)
                return self.response({"total": counter})
            # get user requests list
            res = RequestManager.get_user_schedules(
                db, user.id, sort_by=sort, sort_order=sort_order
            )

        return self.response(res, code=hcodes.HTTP_OK_BASIC)

    @decorators.catch_errors()
    @decorators.auth.required()
    def patch(self, schedule_id):
        param = self.get_input()
        is_active = param.get("is_active")
        user = self.get_current_user()

        db = self.get_service_instance("sqlalchemy", global_instance=False)

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        schedule = db.Schedule.query.get(schedule_id)
        if schedule.on_data_ready is False:
            # retrieving mongodb task
            task = CeleryExt.get_periodic_task(name=schedule_id)
            log.debug("Periodic task - {}", task)
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
                log.debug("schedule response: {}", schedule_response)

                # recreate the schedule in mongo retrieving the schedule from postgres
                try:
                    request_id = None
                    if "periodic" in schedule_response:
                        CeleryExt.create_periodic_task(
                            name=str(schedule_id),
                            task="mistral.tasks.data_extraction.data_extract",
                            every=schedule_response["every"],
                            period=schedule_response["period"],
                            args=[
                                user.id,
                                schedule_response["args"]["datasets"],
                                schedule_response["args"]["reftime"],
                                schedule_response["args"]["filters"],
                                schedule_response["args"]["postprocessors"],
                                schedule_response["args"]["output_format"],
                                request_id,
                                schedule_response["args"]["pushing_queue"],
                                schedule_id,
                            ],
                        )

                    if "crontab" in schedule_response:
                        # parsing crontab settings
                        crontab_settings = {}
                        for i in schedule_response["crontab_settings"].keys():
                            log.debug(i)
                            val = schedule_response["crontab_settings"].get(i)
                            str_val = str(val)
                            crontab_settings[i] = str_val
                        CeleryExt.create_crontab_task(
                            name=str(schedule_id),
                            task="mistral.tasks.data_extraction.data_extract",
                            **crontab_settings,
                            args=[
                                user.id,
                                schedule_response["args"]["datasets"],
                                schedule_response["args"]["reftime"],
                                schedule_response["args"]["filters"],
                                schedule_response["args"]["postprocessors"],
                                schedule_response["args"]["output_format"],
                                request_id,
                                schedule_response["args"]["pushing_queue"],
                                schedule_id,
                            ],
                        )

                except Exception:
                    raise SystemError("Unable to enable the request")

        # update schedule status in database
        RequestManager.update_schedule_status(db, schedule_id, is_active)

        return self.response(
            {"id": schedule_id, "enabled": is_active}, code=hcodes.HTTP_OK_BASIC
        )

    @decorators.catch_errors()
    @decorators.auth.required()
    def delete(self, schedule_id):
        user = self.get_current_user()

        db = self.get_service_instance("sqlalchemy", global_instance=False)

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        # delete schedule in mongodb
        CeleryExt.delete_periodic_task(name=schedule_id)

        # delete schedule status in database
        RequestManager.delete_schedule(db, schedule_id)

        return self.response(
            f"Schedule {schedule_id} succesfully deleted", code=hcodes.HTTP_OK_BASIC,
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
    labels = ["scheduled_requests"]
    GET = {
        "/schedules/<schedule_id>/requests": {
            "summary": "Get requests related to a given schedule.",
            "parameters": [
                {
                    "name": "get_total",
                    "in": "query",
                    "description": "Retrieve total number of requests",
                    "type": "boolean",
                    "default": False,
                },
                {
                    "name": "last",
                    "in": "query",
                    "description": "retrieve only the last submitted request",
                    "type": "boolean",
                    "allowEmptyValue": True,
                },
            ],
            "responses": {
                "200": {
                    "description": "List of requests for a given schedule.",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "404": {"description": "Schedule not found."},
                "403": {
                    "description": "User cannot access a schedule that does not belong to."
                },
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self, schedule_id):
        """
        Get all submitted requests for this schedule
        :param schedule_id:
        :return:
        """
        log.debug("get scheduled requests")
        param = self.get_input()
        get_total = param.get("get_total", False)
        last = param.get("last")
        if isinstance(last, str) and (last == "" or last.lower() == "true"):
            last = True
        elif type(last) == bool:
            # do nothing
            pass
        else:
            last = False

        db = self.get_service_instance("sqlalchemy")

        # check if the schedule exists
        if not RequestManager.check_request(db, schedule_id=schedule_id):
            raise RestApiException(
                f"The schedule ID {schedule_id} doesn't exist",
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
            return self.response({"total": counter})

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
            meta_response["total"] = RequestManager.count_schedule_requests(
                db, schedule_id
            )
        else:
            res = RequestManager.get_schedule_requests(db, schedule_id)
        return self.response(res, meta=meta_response, code=hcodes.HTTP_OK_BASIC)
