import datetime

from marshmallow import ValidationError, pre_load
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import spare_point_interpol as pp3_3
from mistral.tools import statistic_elaboration as pp2
from restapi import decorators
from restapi.exceptions import BadRequest, Forbidden, NotFound, RestApiException
from restapi.models import AdvancedList, InputSchema, fields, validate
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

OUTPUT_FORMATS = ["json", "bufr", "grib"]
DERIVED_VARIABLES = [
    "B12194",  # Air density
    "B13003",  # Relative humidity
    "B11001",  # Wind direction
    "B11002",  # Wind speed
    "B11003",  # U-component
    "B11004",  # V-component
    "B12103",  # Dew-point temperature
    "B13001",  # Specific humidity
    "B13003",  # Relative humidity
    "B13205",  # Snowfall (grid-scale + convective)
]


class AVProcessor(InputSchema):
    # Derived variables post-processing
    processor_type = fields.Str(required=True, data_key="type")
    # "derived_variables"

    variables = AdvancedList(
        fields.Str(
            validate=validate.OneOf(DERIVED_VARIABLES),
            description="The list of requested derived variables to be calculated.",
        ),
        unique=True,
        min_items=1,
        required=True,
    )


SUBTYPES = [
    "near",
    "bilin",
    "average",
    "min",
    "max",
]


class SPIProcessor(InputSchema):
    # Spare points interpolation postprocessor
    processor_type = fields.Str(
        required=True, data_key="type", description="description of the postprocessor"
    )
    # "spare_point_interpolation"
    coord_filepath = fields.Url(
        required=True,
        relative=True,
        require_tls=False,
        schems=None,
        data_key="coord-filepath",
        description="file to define the target spare points",
    )
    file_format = fields.Str(
        required=True, data_key="format", validate=validate.OneOf(["shp", "geojson"])
    )
    sub_type = fields.Str(
        required=True, data_key="sub-type", validate=validate.OneOf(SUBTYPES)
    )


TIMERANGES = [0, 1, 2, 3, 4, 6, 254]


class SEProcessor(InputSchema):
    # Statistic Elaboration post-processing
    processor_type = fields.Str(
        required=True, data_key="type", description="description of the postprocessor"
    )
    # "statistic_elaboration"
    input_timerange = fields.Integer(
        required=True, data_key="input-timerange", validate=validate.OneOf(TIMERANGES)
    )
    output_timerange = fields.Integer(
        required=True, data_key="output-timerange", validate=validate.OneOf(TIMERANGES)
    )
    interval = fields.Str(
        required=True,
        validate=validate.OneOf(["hours", "days", "months", "years"]),
        description="Interval of elaboration",
    )
    step = fields.Integer(required=True, description="step range")

    @pre_load
    def timeranges_validation(self, data, **kwargs):
        tr_input = data.get("input-timerange")
        tr_output = data.get("output-timerange")
        if tr_input != tr_output:
            if tr_input == 254:
                if tr_output == 1:
                    raise ValidationError("invalid input/output timerange combination")
            elif tr_input == 0:
                if tr_output != 254:
                    raise ValidationError("invalid input/output timerange combination")
            else:
                raise ValidationError("invalid input/output timerange combination")
        elif tr_input == tr_output == 254:
            raise ValidationError("invalid input/output timerange combination")
        return data


class CropBoundings(InputSchema):
    ilon = fields.Number()
    ilat = fields.Number()
    flon = fields.Number()
    flat = fields.Number()


class GCProcessor(InputSchema):
    #  Grid cropping post processor
    processor_type = fields.Str(
        required=True, data_key="type", description="description of the postprocessor"
    )
    # "grid_cropping"
    boundings = fields.Nested(
        CropBoundings, description="boundings of the cropped grid"
    )
    sub_type = fields.Str(
        required=True, data_key="sub-type", validate=validate.OneOf(["coord", "bbox"])
    )


class InterpolBoundings(InputSchema):
    x_min = fields.Number(data_key="x-min")
    x_max = fields.Number(data_key="x-max")
    y_min = fields.Number(data_key="y-min")
    y_max = fields.Number(data_key="y-max")


class Nodes(InputSchema):
    nx = fields.Integer()
    ny = fields.Integer()


class GIProcessor(InputSchema):
    # Grid interpolation post processor to interpolate data on a new grid
    processor_type = fields.Str(
        required=True, data_key="type", description="description of the postprocessor"
    )
    # "grid_interpolation"
    boundings = fields.Nested(
        InterpolBoundings, description="boundings of the target grid"
    )
    nodes = fields.Nested(Nodes, description="number of nodes of the target grid")
    template = fields.Url(
        relative=True,
        require_tls=False,
        schems=None,
        description="grib template for interpolation",
    )
    sub_type = fields.Str(
        required=True, data_key="sub-type", validate=validate.OneOf(SUBTYPES)
    )


class Postprocessors(fields.Field):
    postprocessors = {
        "spare_point_interpolation": SPIProcessor,
        "derived_variables": AVProcessor,
        "statistic_elaboration": SEProcessor,
        "grid_cropping": GCProcessor,
        "grid_interpolation": GIProcessor,
    }

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""
        return "".join(str(d) for d in value)

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            if value.get("type") not in self.postprocessors:
                raise ValidationError("unknown postprocessor")
            postprocessor_schema = self.postprocessors.get(value.get("type"))
            valid_data = postprocessor_schema().load(value, unknown=None, partial=None)

        except ValidationError as error:
            raise ValidationError(
                error.messages, valid_data=error.valid_data
            ) from error
        return valid_data


class Reftime(InputSchema):
    date_from = fields.DateTime(required=True, data_key="from")
    date_to = fields.DateTime(required=True, data_key="to")

    @pre_load
    def check_reftime(self, data, **kwargs):
        if data["from"] > data["to"]:
            raise ValidationError("Invalid reftime: <from> greater than <to>")
        return data


class Filters(InputSchema):
    area = fields.List(fields.Dict())
    level = fields.List(fields.Dict())
    origin = fields.List(fields.Dict())
    proddef = fields.List(fields.Dict())
    product = fields.List(fields.Dict())
    quantity = fields.List(fields.Dict())
    run = fields.List(fields.Dict())
    task = fields.List(fields.Dict())
    timerange = fields.List(fields.Dict())
    network = fields.List(fields.Dict())


class PeriodSettings(InputSchema):
    every = fields.Integer(required=True)
    period = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["days", "hours", "minutes", "seconds", "microseconds"]
        ),
    )


class CrontabSettings(InputSchema):
    minute = fields.Integer(
        validate=validate.Range(min=0, max=59, min_inclusive=False, max_inclusive=False)
    )
    hour = fields.Integer(
        validate=validate.Range(min=0, max=23, min_inclusive=False, max_inclusive=False)
    )
    day_of_week = fields.Integer(
        validate=validate.Range(min=0, max=7, min_inclusive=False, max_inclusive=False)
    )
    day_of_month = fields.Integer(
        validate=validate.Range(min=0, max=31, min_inclusive=False, max_inclusive=False)
    )
    month_of_year = fields.Integer(
        validate=validate.Range(min=1, max=12, min_inclusive=False, max_inclusive=False)
    )

    @pre_load
    def crontab_min_item(self, data, **kwargs):
        if not data:
            raise ValidationError(
                "At least 1 param for crontab setting has to be specified"
            )
        return data


class ScheduledDataExtraction(InputSchema):
    request_name = fields.Str(required=True, data_key="name")
    reftime = fields.Nested(Reftime, allow_none=True)
    dataset_names = AdvancedList(
        fields.Str(description="Dataset name"),
        unique=True,
        min_items=1,
        required=True,
        data_key="datasets",
        description="Data belong to the datasets of the list.",
    )
    filters = fields.Nested(Filters, description="Apply different filtering criteria.")
    output_format = fields.Str(validate=validate.OneOf(OUTPUT_FORMATS))
    postprocessors = fields.List(
        Postprocessors(description="Post-processing request details"),
        unique=True,
        description="Apply one or more post-processing to the filtered data.",
    )
    period_settings = fields.Nested(
        PeriodSettings,
        data_key="period-settings",
        description="Settings for the periodic request",
    )
    crontab_settings = fields.Nested(
        CrontabSettings,
        data_key="crontab-settings",
        description="Settings for the crontab request",
    )
    data_ready = fields.Bool(
        data_key="on-data-ready",
        description="Activate data extraction when requested data is ready",
    )

    @pre_load
    def validate_schedule(self, data, **kwargs):
        # validate postprocessing
        if data.get("postprocessors"):
            postprocessor_types = []
            # check if postprocessor types are unique
            for p in data.get("postprocessors"):
                postprocessor_types.append(p.get("type"))
            if len(postprocessor_types) != len(set(postprocessor_types)):
                raise ValidationError("Postprocessors list contains duplicates")

            # check if only one geographic postprocessor is required
            pp3_list = [
                "grid_cropping",
                "grid_interpolation",
                "spare_point_interpolation",
            ]
            if len(set(postprocessor_types).intersection(set(pp3_list))) > 1:
                raise ValidationError(
                    "Only one geographical postprocessing at a time can be executed"
                )
        schedule_settings = ["period-settings", "crontab-settings", "on-data-ready"]
        if not any([i in data for i in schedule_settings]):
            raise ValidationError("At least one schedule setting has to be specified")
        return data


class Schedules(EndpointResource):
    labels = ["schedule"]
    _GET = {
        "/schedules/<schedule_id>": {
            "summary": "Get user schedules.",
            "description": "Returns a single schedule by ID",
            "responses": {
                "200": {
                    "description": "List of user schedules.",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "403": {"description": "User not allowed to get the schedule"},
                "404": {"description": "The schedule does not exists"},
            },
        },
        "/schedules": {
            "summary": "Get user schedules.",
            "description": "Returns a single schedule by ID",
            "responses": {
                "200": {
                    "description": "List of user schedules.",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "403": {"description": "User not allowed to get the schedule"},
                "404": {"description": "The schedule does not exists"},
            },
        },
    }
    _POST = {
        "/schedules": {
            "summary": "Request for scheduling a data extraction.",
            "responses": {
                "201": {"description": "scheduled request successfully created"},
                "400": {"description": "invalid scheduled request"},
                "404": {
                    "description": "Cannot schedule the request: dataset not found"
                },
            },
        }
    }
    _PATCH = {
        "/schedules/<schedule_id>": {
            "summary": "enable or disable a schedule",
            "responses": {
                "200": {"description": "schedule is succesfully disable/enable"},
                "404": {"description": "schedule not found"},
                "400": {"description": "schedule is already enabled/disabled"},
            },
        }
    }
    _DELETE = {
        "/schedules/<schedule_id>": {
            "summary": "delete a schedule",
            "responses": {
                "200": {"description": "schedule is succesfully disable/enable"},
                "404": {"description": "schedule not found"},
            },
        }
    }

    @decorators.auth.require()
    @decorators.use_kwargs({"push": fields.Bool(required=False)}, locations=["query"])
    @decorators.use_kwargs(ScheduledDataExtraction)
    def post(
        self,
        request_name,
        dataset_names,
        reftime=None,
        filters=None,
        output_format=None,
        postprocessors=None,
        period_settings=None,
        crontab_settings=None,
        data_ready=False,
        push=False,
    ):
        user = self.get_user()
        log.info(f"request for data extraction coming from user UUID: {user.uuid}")

        time_delta = None
        reftime_to = None
        parsed_reftime = {}
        if reftime:
            reftime_to = reftime.get("date_to")
            reftime_from = reftime.get("date_from")
            time_delta = reftime_to - reftime_from
            parsed_reftime["from"] = reftime_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            parsed_reftime["to"] = reftime_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

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
        # clean up filters from unknown values
        if filters:
            filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        # clean up processors from unknown values
        # processors = [
        #     i for i in processors if arki.is_processor_allowed(i.get('type'))
        # ]
        if postprocessors:
            for p in postprocessors:
                p_type = p.get("processor_type")
                if p_type == "derived_variables" or p_type == "statistic_elaboration":
                    continue
                if p_type == "grid_interpolation":
                    if "template" in p:
                        template_file = p.get("template")
                        pp3_1.check_template_filepath(template_file)
                    pp3_1.get_trans_type(p)
                elif p_type == "grid_cropping":
                    p["trans_type"] = "zoom"
                elif p_type == "spare_point_interpolation":
                    pp3_3.get_trans_type(p)
                    pp3_3.check_coord_filepath(p)
                else:
                    raise BadRequest(f"Unknown post-processor type for {p_type}")

        # get the format of the datasets
        dataset_format = arki.get_datasets_format(dataset_names)
        if not dataset_format:
            raise BadRequest(
                "Invalid set of datasets : datasets have different formats"
            )

        # check if the output format chosen by the user is compatible with the datasets
        if output_format is not None:
            postprocessors_list = []
            if postprocessors:
                postprocessors_list = [i.get("processor_type") for i in postprocessors]
            if dataset_format != output_format:
                if dataset_format == "grib":
                    # spare point interpolation has bufr as output format
                    if "spare_point_interpolation" not in postprocessors_list:
                        raise BadRequest(
                            f"The chosen datasets does not support {output_format} output format"
                        )
                if dataset_format == "bufr" and output_format == "grib":
                    raise BadRequest(
                        f"The chosen datasets does not support {output_format} output format"
                    )
            else:
                if (
                    dataset_format == "grib"
                    and "spare_point_interpolation" in postprocessors_list
                ):
                    raise BadRequest(
                        f"The chosen postprocessor does not support {output_format} output format",
                    )

        # check if the schedule is a 'on-data-ready' one
        if not data_ready:
            # with forecast schedules the data_ready flag is applied by default
            # if reftime_to is today or yesterday
            # data ready option is not for observed data
            if dataset_format == "grib":
                today = datetime.date.today()
                yesterday = today - datetime.timedelta(days=1)
                # if the date of reftime['to'] is today or yesterday
                # the request can be considered a data-ready one
                refdate = reftime_to.date()
                if refdate == today or refdate == yesterday:
                    data_ready = True
                # TODO what if reftime is None?

        # get queue for pushing notifications
        pushing_queue = None
        if push:
            pushing_queue = user.amqp_queue
            rabbit = self.get_service_instance("rabbitmq")
            # check if the queue exists
            if not rabbit.queue_exists(pushing_queue):
                raise Forbidden("User's queue for push notification does not exists")

        db = self.get_service_instance("sqlalchemy")
        celery = self.get_service_instance("celery")

        name = None
        try:
            if period_settings is not None:
                every = period_settings.get("every")
                period = period_settings.get("period")
                log.info("Period settings [{} {}]", every, period)

                # get schedule id in postgres database
                # as scheduled request name for mongodb
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    request_name,
                    {
                        "datasets": dataset_names,
                        "reftime": parsed_reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
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
                    res = celery.delete_periodic_task(name=name)
                    log.debug("Previous task deleted = {}", res)

                    request_id = None
                    celery.create_periodic_task(
                        name=name,
                        task="mistral.tasks.data_extraction.data_extract",
                        every=every,
                        period=period,
                        args=[
                            user.id,
                            dataset_names,
                            parsed_reftime,
                            filters,
                            postprocessors,
                            output_format,
                            request_id,
                            pushing_queue,
                            name_int,
                        ],
                    )
                    log.info("Scheduling periodic task")

            elif crontab_settings is not None:
                log.info("Crontab settings {}", crontab_settings)
                # get scheduled request id in postgres database
                # as scheduled request name for mongodb
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    request_name,
                    {
                        "datasets": dataset_names,
                        "reftime": parsed_reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
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
                    celery.create_crontab_task(
                        name=name,
                        task="mistral.tasks.data_extraction.data_extract",
                        **crontab_settings,
                        args=[
                            user.id,
                            dataset_names,
                            parsed_reftime,
                            filters,
                            postprocessors,
                            output_format,
                            request_id,
                            pushing_queue,
                            name_int,
                        ],
                    )
                    log.info("Scheduling crontab task")
            else:
                # if it is only a data-ready schedule, save the schedule in db
                log.info("Save a data ready schedule without additional settings")
                # get scheduled request id in postgres database
                name_int = RequestManager.create_schedule_record(
                    db,
                    user,
                    request_name,
                    {
                        "datasets": dataset_names,
                        "reftime": parsed_reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
                        "output_format": output_format,
                        "pushing_queue": pushing_queue,
                    },
                    on_data_ready=data_ready,
                    time_delta=time_delta,
                )
                name = str(name_int)

            if data_ready:
                # submit the first request
                request_id = None
                celery.data_extract.apply_async(
                    args=[
                        user.id,
                        dataset_names,
                        parsed_reftime,
                        filters,
                        postprocessors,
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

    @decorators.auth.require()
    @decorators.get_pagination
    @decorators.use_kwargs(
        {
            "sort_order": fields.Str(
                validate=validate.OneOf(["asc", "desc"]), required=False
            ),
            "sort_by": fields.Str(required=False),
        },
        locations=["query"],
    )
    def get(
        self,
        schedule_id=None,
        get_total=None,
        page=None,
        size=None,
        sort_order=None,
        sort_by=None,
    ):

        user = self.get_user()

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
                db, user.id, sort_by=sort_by, sort_order=sort_order
            )

        return self.response(res, code=hcodes.HTTP_OK_BASIC)

    @decorators.auth.require()
    @decorators.use_kwargs(
        {
            "is_active": fields.Bool(
                required=True, description="Enable or disable the schedule"
            )
        }
    )
    def patch(self, schedule_id, is_active):
        user = self.get_user()

        db = self.get_service_instance("sqlalchemy")
        celery = self.get_service_instance("celery")

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        schedule = db.Schedule.query.get(schedule_id)
        if schedule.on_data_ready is False:
            # retrieving mongodb task
            task = celery.get_periodic_task(name=schedule_id)
            log.debug("Periodic task - {}", task)
            # disable the schedule deleting it from mongodb
            if is_active is False:
                if task is None:
                    raise RestApiException(
                        "Scheduled task is already disabled",
                        status_code=hcodes.HTTP_BAD_CONFLICT,
                    )
                celery.delete_periodic_task(name=schedule_id)
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
                        celery.create_periodic_task(
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
                        celery.create_crontab_task(
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

    @decorators.auth.require()
    def delete(self, schedule_id):
        user = self.get_user()

        db = self.get_service_instance("sqlalchemy")
        celery = self.get_service_instance("celery")

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        # delete schedule in mongodb
        celery.delete_periodic_task(name=schedule_id)

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
    _GET = {
        "/schedules/<schedule_id>/requests": {
            "summary": "Get requests related to a given schedule.",
            "responses": {
                "200": {
                    "description": "List of requests for a given schedule.",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "404": {"description": "Schedule not found."},
                "403": {"description": "Cannot access a schedule not belonging to you"},
            },
        }
    }

    @decorators.auth.require()
    @decorators.use_kwargs(
        {"get_total": fields.Bool(required=False), "last": fields.Bool(required=False)},
        locations=["query"],
    )
    def get(self, schedule_id, get_total=False, last=True):
        """
        Get all submitted requests for this schedule
        :param schedule_id:
        :return:
        """
        log.debug("get scheduled requests")

        db = self.get_service_instance("sqlalchemy")

        # check if the schedule exists
        if not RequestManager.check_request(db, schedule_id=schedule_id):
            raise RestApiException(
                f"The schedule ID {schedule_id} doesn't exist",
                status_code=hcodes.HTTP_BAD_NOTFOUND,
            )

        # check for schedule ownership
        user = self.get_user()
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
        if last:
            res = RequestManager.get_last_scheduled_request(db, schedule_id)
            if res is None:
                raise RestApiException(
                    "No successful request is available for schedule ID {} yet".format(
                        schedule_id
                    ),
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )
        else:
            res = RequestManager.get_schedule_requests(db, schedule_id)
        return self.response(res, code=hcodes.HTTP_OK_BASIC)
