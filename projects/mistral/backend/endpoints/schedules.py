from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

from marshmallow import ValidationError, pre_load
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import spare_point_interpol as pp3_3
from restapi import decorators
from restapi.connectors import celery, rabbitmq, sqlalchemy
from restapi.endpoints.schemas import TotalSchema
from restapi.exceptions import (
    BadRequest,
    Conflict,
    Forbidden,
    NotFound,
    ServerError,
    Unauthorized,
)
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log
from restapi.utilities.time import AllowedTimedeltaPeriods

OUTPUT_FORMATS = ["json", "bufr", "grib"]
DERIVED_VARIABLES = [
    "B12194",  # Air density
    "B12107",  # Virtual temperature
    "B11001",  # Wind direction
    "B11002",  # Wind speed
    "B11003",  # U-component
    "B11004",  # V-component
    "B12103",  # Dew-point temperature
    "B13001",  # Specific humidity
    "B13003",  # Relative humidity
    "B13205",  # Snowfall (grid-scale + convective)
]


class AVProcessor(Schema):
    # Derived variables post-processing
    processor_type = fields.Str(required=True)
    # "derived_variables"

    variables = fields.List(
        fields.Str(
            validate=validate.OneOf(DERIVED_VARIABLES),
            metadata={
                "description": "The list of requested derived variables to be calculated"
            },
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


class SPIProcessor(Schema):
    # Spare points interpolation postprocessor
    processor_type = fields.Str(
        required=True, metadata={"description": "description of the postprocessor"}
    )
    # "spare_point_interpolation"
    coord_filepath = fields.Url(
        required=True,
        relative=True,
        require_tld=False,
        metadata={"description": "file to define the target spare points"},
    )
    file_format = fields.Str(
        required=True, data_key="format", validate=validate.OneOf(["shp", "geojson"])
    )
    sub_type = fields.Str(required=True, validate=validate.OneOf(SUBTYPES))


TIMERANGES = [0, 1, 2, 3, 4, 6, 254]


class SEProcessor(Schema):
    # Statistic Elaboration post-processing
    processor_type = fields.Str(
        required=True, metadata={"description": "description of the postprocessor"}
    )
    # "statistic_elaboration"
    input_timerange = fields.Integer(required=True, validate=validate.OneOf(TIMERANGES))
    output_timerange = fields.Integer(
        required=True, validate=validate.OneOf(TIMERANGES)
    )
    interval = fields.Str(
        required=True,
        validate=validate.OneOf(["hours", "days", "months", "years"]),
        metadata={"description": "Interval of elaboration"},
    )
    step = fields.Integer(required=True, metadata={"description": "step range"})

    @pre_load
    def timeranges_validation(self, data, **kwargs):
        tr_input = data.get("input_timerange")
        tr_output = data.get("output_timerange")
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


class CropBoundings(Schema):
    ilon = fields.Number()
    ilat = fields.Number()
    flon = fields.Number()
    flat = fields.Number()


class GCProcessor(Schema):
    #  Grid cropping post processor
    processor_type = fields.Str(
        required=True, metadata={"description": "description of the postprocessor"}
    )
    # "grid_cropping"
    boundings = fields.Nested(
        CropBoundings, metadata={"description": "boundings of the cropped grid"}
    )
    sub_type = fields.Str(required=True, validate=validate.OneOf(["coord", "bbox"]))


class InterpolBoundings(Schema):
    x_min = fields.Number(data_key="x-min")
    x_max = fields.Number(data_key="x-max")
    y_min = fields.Number(data_key="y-min")
    y_max = fields.Number(data_key="y-max")


class Nodes(Schema):
    nx = fields.Integer()
    ny = fields.Integer()


class GIProcessor(Schema):
    # Grid interpolation post processor to interpolate data on a new grid
    processor_type = fields.Str(
        required=True, metadata={"description": "description of the postprocessor"}
    )
    # "grid_interpolation"
    boundings = fields.Nested(
        InterpolBoundings, metadata={"description": "boundings of the target grid"}
    )
    nodes = fields.Nested(
        Nodes, metadata={"description": "number of nodes of the target grid"}
    )
    template = fields.Url(
        relative=True,
        require_tld=False,
        metadata={"description": "grib template for interpolation"},
    )
    sub_type = fields.Str(required=True, validate=validate.OneOf(SUBTYPES))


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
            if not (
                postprocessor_schema := self.postprocessors.get(
                    value.get("processor_type")
                )
            ):
                raise ValidationError("unknown postprocessor")
            valid_data = postprocessor_schema().load(value, unknown=None, partial=None)

        except ValidationError as error:
            raise ValidationError(
                error.messages, valid_data=error.valid_data
            ) from error
        return valid_data


class Reftime(Schema):
    date_from = fields.DateTime(required=True, data_key="from")
    date_to = fields.DateTime(required=True, data_key="to")

    @pre_load
    def check_reftime(self, data, **kwargs):
        if data["from"] > data["to"]:
            raise ValidationError("Invalid reftime: <from> greater than <to>")
        return data


class Filters(Schema):
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


class PeriodSettings(Schema):
    every = fields.Integer(required=True)
    period = fields.Str(
        required=True,
        validate=validate.OneOf(["days", "hours", "minutes"]),
    )


class CrontabSettings(Schema):
    minute = fields.Integer(validate=validate.Range(min=0, max=59))
    hour = fields.Integer(validate=validate.Range(min=0, max=23))
    day_of_week = fields.Integer(
        validate=validate.Range(min=0, max=7, min_inclusive=False, max_inclusive=False)
    )
    day_of_month = fields.Integer(
        validate=validate.Range(min=0, max=31, min_inclusive=False, max_inclusive=False)
    )
    month_of_year = fields.Integer(validate=validate.Range(min=1, max=12))

    @pre_load
    def crontab_min_item(self, data, **kwargs):
        if not data:
            raise ValidationError(
                "At least 1 param for crontab setting has to be specified"
            )
        return data


class ScheduledDataExtraction(Schema):
    request_name = fields.Str(required=True)
    reftime = fields.Nested(Reftime, allow_none=True)
    dataset_names = fields.List(
        fields.Str(metadata={"description": "Dataset name"}),
        unique=True,
        min_items=1,
        required=True,
        metadata={"description": "Data belong to the datasets of the list."},
    )
    filters = fields.Nested(
        Filters, metadata={"description": "Apply different filtering criteria."}
    )
    output_format = fields.Str(validate=validate.OneOf(OUTPUT_FORMATS))
    only_reliable = fields.Bool(required=False)
    postprocessors = fields.List(
        Postprocessors(metadata={"description": "Post-processing request details"}),
        metadata={
            "description": "Apply one or more post-processing to the filtered data."
        },
    )
    period_settings = fields.Nested(
        PeriodSettings,
        data_key="period-settings",
        metadata={"description": "Settings for the periodic request"},
    )
    crontab_settings = fields.Nested(
        CrontabSettings,
        data_key="crontab-settings",
        metadata={"description": "Settings for the crontab request"},
    )
    data_ready = fields.Bool(
        data_key="on-data-ready",
        metadata={
            "description": "Activate data extraction when requested data is ready"
        },
    )
    opendata = fields.Bool(
        metadata={
            "description": "Schedule for data available in opendata folder for all users"
        },
    )

    @pre_load
    def validate_schedule(self, data, **kwargs):
        # validate postprocessing
        if data.get("postprocessors"):
            postprocessor_types = []
            # check if postprocessor types are unique
            for p in data.get("postprocessors"):
                postprocessor_types.append(p.get("processor_type"))
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


DATASET_ENABLED_TO_DATAREADY = ["lm2.2", "lm5"]
MIN_PERIOD = 15  # in minutes


class Schedules(EndpointResource):
    labels = ["schedule"]

    @decorators.auth.require()
    @decorators.get_pagination
    @decorators.marshal_with(TotalSchema, code=206)
    @decorators.endpoint(
        path="/schedules",
        summary="Get user schedules.",
        description="Returns a single schedule by id",
        responses={
            200: "List of user schedules.",
            206: "Total number of elements is returned",
            403: "User not allowed to get the schedule",
            404: "The schedule does not exists",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Requests'}}
    def get(
        self,
        get_total: bool,
        page: int,
        size: int,
        sort_by: str,
        sort_order: str,
        input_filter: str,
        user: User,
    ) -> Response:

        db = sqlalchemy.get_instance()

        # get total count for user schedules
        if get_total:
            counter = SqlApiDbManager.count_user_schedules(db, user.id)
            return self.pagination_total(counter)
        # get user requests list
        res = SqlApiDbManager.get_user_schedules(
            db, user.id, sort_by=sort_by, sort_order=sort_order
        )

        return self.response(res)


class SingleSchedule(EndpointResource):
    labels = ["schedule"]

    @decorators.auth.require()
    @decorators.use_kwargs({"push": fields.Bool(required=False)}, location="query")
    @decorators.use_kwargs(ScheduledDataExtraction)
    @decorators.endpoint(
        path="/schedules",
        summary="Request for scheduling a data extraction.",
        responses={
            201: "Scheduled request successfully created",
            400: "Invalid scheduled request",
            404: "Cannot schedule the request: dataset not found",
        },
    )
    def post(
        self,
        request_name: str,
        dataset_names: List[str],
        user: User,
        reftime: Optional[Dict[str, datetime]] = None,
        filters: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        output_format: Optional[str] = None,
        only_reliable: bool = False,
        postprocessors: Optional[List[Any]] = None,
        period_settings: Optional[Dict[str, Union[str, int]]] = None,
        crontab_settings: Optional[Dict[str, int]] = None,
        data_ready: bool = False,
        opendata: bool = False,
        push: bool = False,
    ) -> Response:

        log.info(f"request for data extraction coming from user UUID: {user.uuid}")
        db = sqlalchemy.get_instance()
        # check if the user is authorized to post a scheduled request
        is_allowed_schedule = SqlApiDbManager.get_user_permissions(
            user, param="allowed_schedule"
        )
        if not is_allowed_schedule:
            raise Unauthorized("user is not allowed to schedule a request")

        # check if the user has a limit of number of requests par hour
        SqlApiDbManager.check_user_request_limit(db, user)

        time_delta = None
        reftime_to = None
        parsed_reftime = {}
        log.debug(f"reftime: {reftime}")
        if reftime:
            reftime_to = reftime.get("date_to")
            reftime_from = reftime.get("date_from")
            if not reftime_to or not reftime_from:  # pragma: no cover
                raise BadRequest("Can't extra date_from and date_to from reftime")
            time_delta = reftime_to - reftime_from
            parsed_reftime["from"] = reftime_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            parsed_reftime["to"] = reftime_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # check for existing dataset(s)
        # check for existing dataset(s)
        datasets = SqlApiDbManager.get_datasets(db, user)
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get("id", "") == ds_name), None)
            if not found:
                raise NotFound(
                    f"Dataset '{ds_name}' not found: "
                    "check for dataset name of for your authorizations "
                )
        # check the licence group
        license_group = SqlApiDbManager.get_license_group(db, dataset_names)
        if not license_group:
            raise BadRequest(
                "Invalid set of datasets : datasets belongs to different license groups"
            )
        # incoming filters: <dict> in form of filter_name: list_of_values
        # e.g. 'level': [{...}, {...}] or 'level: {...}'
        # clean up filters from unknown values
        if filters:
            filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        if data_ready:
            # check if data ready function is enabled for the requested datasets
            if not all(elem in DATASET_ENABLED_TO_DATAREADY for elem in dataset_names):
                raise BadRequest(
                    "Data-ready service is not available for the selected datasets"
                )

        if opendata:
            # get user roles
            user_roles = [r.name for r in user.roles]
            # check if the user is allowed to post opendata schedule
            if "admin_root" not in user_roles:
                raise Forbidden("Only admins can post an opendata schedule")
            # check that only one dataset is request
            if len(dataset_names) > 1:
                raise BadRequest(
                    "Multi dataset for opendata schedules is not supported"
                )

            ds_entry = db.Datasets.query.filter_by(arkimet_id=dataset_names[0]).first()
            # check that the dataset is not of observed type
            if ds_entry.category.name == "OBS":
                raise BadRequest(
                    "Opendata schedules service is not intended for observed data"
                )
            # check that the dataset is a open one
            # get license
            license = db.License.query.filter_by(id=ds_entry.license_id).first()
            # get license group
            group_license = db.GroupLicense.query.filter_by(
                id=license.group_license_id
            ).first()
            if not group_license.is_public:
                raise BadRequest(
                    "the dataset requested for opendata schedule is not an open dataset"
                )

        if period_settings:
            # check if the requested period is > of the minimum period
            if period_settings.get("period", "") == "minutes":
                if int(period_settings.get("every", "0")) < MIN_PERIOD:
                    raise Forbidden(
                        f"Schedule frequency can't be lower than {MIN_PERIOD} minutes"
                    )

        # clean up processors from unknown values
        # processors = [
        #     i for i in processors if arki.is_processor_allowed(i.get('type'))
        # ]
        if postprocessors:
            allowed_postprocessing = SqlApiDbManager.get_user_permissions(
                user, param="allowed_postprocessing"
            )
            if not allowed_postprocessing:
                raise Unauthorized("user is not authorized to use postprocessing tools")
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
                # spare point interpolation has only bufr as output format
                if (
                    dataset_format == "grib"
                    and "spare_point_interpolation" not in postprocessors_list
                ):
                    raise BadRequest(
                        f"This dataset does not support {output_format} output format"
                    )
                if dataset_format == "bufr" and output_format == "grib":
                    raise BadRequest(
                        f"This dataset does not support {output_format} output format"
                    )
            else:
                if (
                    dataset_format == "grib"
                    and "spare_point_interpolation" in postprocessors_list
                ):
                    raise BadRequest(
                        f"This postprocessor does not support {output_format} format",
                    )

        # WE NEED THIS APPROXIMATION OF ON DATA READY
        # OR WE WILL USE ONLY THE DATA-READY FLAG OF THE FRONTEND?

        # # check if the schedule is a 'on-data-ready' one
        # if not data_ready:
        #     # with forecast schedules the data_ready flag is applied by default
        #     # if reftime_to is today or yesterday
        #     # data ready option is not for observed data
        #     if dataset_format == "grib":
        #         today = datetime.date.today()
        #         log.debug(f"today: {today}")
        #         yesterday = today - datetime.timedelta(days=1)
        #         # if the date of reftime['to'] is today or yesterday
        #         # the request can be considered a data-ready one
        #         if reftime_to is None:
        #             # FIXME what if reftime is None?
        #             raise BadRequest("Cannot schedule a full dataset request")
        #         refdate = reftime_to.date()
        #         if refdate == today or refdate == yesterday:
        #             data_ready = True

        # get queue for pushing notifications
        pushing_queue = None
        if push:
            pushing_queue = user.amqp_queue
            rabbit = rabbitmq.get_instance()
            # check if the queue exists
            if not rabbit.queue_exists(pushing_queue):
                raise Forbidden("User's queue for push notification does not exists")

        if only_reliable:
            # check if the option is possible for the selecte datasets
            data_type = arki.get_datasets_category(dataset_names)
            if data_type != "OBS" and "multim-forecast" not in dataset_names:
                raise BadRequest(
                    "The chosen datasets does not support 'only quality controlled data' option "
                )

        c = celery.get_instance()

        name = None
        try:
            if period_settings is not None:
                every = cast(int, period_settings.get("every"))
                period = cast(AllowedTimedeltaPeriods, period_settings.get("period"))
                log.info("Period settings [{} {}]", every, period)

                # get schedule id in postgres database
                # as scheduled request name for celery
                name_int = SqlApiDbManager.create_schedule_record(
                    db,
                    user,
                    request_name,
                    {
                        "datasets": dataset_names,
                        "reftime": parsed_reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
                        "output_format": output_format,
                        "only_reliable": only_reliable,
                        "pushing_queue": pushing_queue,
                    },
                    every=every,
                    period=period,
                    on_data_ready=data_ready,
                    time_delta=time_delta,
                    opendata=opendata,
                )
                name = str(name_int)

                if data_ready is False:
                    # remove previous task
                    res = c.delete_periodic_task(name=name)
                    log.debug("Previous task deleted = {}", res)

                    request_id = None
                    c.create_periodic_task(
                        name=name,
                        task="data_extract",
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
                            only_reliable,
                            pushing_queue,
                            name_int,
                            data_ready,
                            opendata,
                        ],
                    )
                    log.info("Scheduling periodic task")

            elif crontab_settings is not None:
                log.info("Crontab settings {}", crontab_settings)
                # get scheduled request id in postgres database
                # as scheduled request name for celery
                name_int = SqlApiDbManager.create_schedule_record(
                    db,
                    user,
                    request_name,
                    {
                        "datasets": dataset_names,
                        "reftime": parsed_reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
                        "output_format": output_format,
                        "only_reliable": only_reliable,
                        "pushing_queue": pushing_queue,
                    },
                    crontab_settings=crontab_settings,
                    on_data_ready=data_ready,
                    time_delta=time_delta,
                    opendata=opendata,
                )
                name = str(name_int)
                if data_ready is False:

                    request_id = None
                    c.create_crontab_task(
                        name=name,
                        task="data_extract",
                        minute=str(crontab_settings.get("minute")),
                        hour=str(crontab_settings.get("hour")),
                        day_of_week=str(crontab_settings.get("day_of_week", "*")),
                        day_of_month=str(crontab_settings.get("day_of_month", "*")),
                        month_of_year=str(crontab_settings.get("month_of_year", "*")),
                        args=[
                            user.id,
                            dataset_names,
                            parsed_reftime,
                            filters,
                            postprocessors,
                            output_format,
                            request_id,
                            only_reliable,
                            pushing_queue,
                            name_int,
                            data_ready,
                            opendata,
                        ],
                    )
                    log.info("Scheduling crontab task")
            else:
                # if it is only a data-ready schedule, save the schedule in db
                log.info("Save a data ready schedule without additional settings")
                # get scheduled request id in postgres database
                name_int = SqlApiDbManager.create_schedule_record(
                    db,
                    user,
                    request_name,
                    {
                        "datasets": dataset_names,
                        "reftime": parsed_reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
                        "output_format": output_format,
                        "only_reliable": only_reliable,
                        "pushing_queue": pushing_queue,
                    },
                    on_data_ready=data_ready,
                    time_delta=time_delta,
                    opendata=opendata,
                )
                name = str(name_int)

            if data_ready:
                # submit the first request
                request_id = None
                c.celery_app.send_task(
                    "data_extract",
                    args=(
                        user.id,
                        dataset_names,
                        parsed_reftime,
                        filters,
                        postprocessors,
                        output_format,
                        request_id,
                        only_reliable,
                        pushing_queue,
                        name,
                        data_ready,
                        opendata,
                    ),
                    countdown=1,
                )

        except Exception as error:
            log.error(error)
            db.session.rollback()
            raise SystemError("Unable to submit the request")

        if not name:
            raise ServerError("Unable to submit the request")

        r = {"schedule_id": name}
        return self.response(r, code=202)

    @decorators.auth.require()
    @decorators.get_pagination
    @decorators.marshal_with(TotalSchema, code=206)
    @decorators.endpoint(
        path="/schedules/<schedule_id>",
        summary="Get user schedules.",
        description="Returns a single schedule by id",
        responses={
            200: "List of user schedules.",
            206: "Total number of elements is returned",
            403: "User not allowed to get the schedule",
            404: "The schedule does not exists",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Requests'}}
    def get(
        self,
        get_total: bool,
        page: int,
        size: int,
        sort_by: str,
        sort_order: str,
        input_filter: str,
        schedule_id: str,
        user: User,
    ) -> Response:

        db = sqlalchemy.get_instance()

        # check for schedule ownership
        self.request_and_owner_check(db, user.id, schedule_id)
        # get schedule by id
        res = SqlApiDbManager.get_schedule_by_id(db, schedule_id)

        return self.response(res)

    @decorators.auth.require()
    @decorators.use_kwargs(
        {
            "is_active": fields.Bool(
                required=True,
                metadata={"description": "Enable or disable the schedule"},
            )
        }
    )
    @decorators.endpoint(
        path="/schedules/<schedule_id>",
        summary="Enable or disable a schedule",
        responses={
            200: "Schedule is succesfully disable/enable",
            404: "Schedule not found",
            400: "Schedule is already enabled/disabled",
        },
    )
    def patch(self, schedule_id: str, is_active: bool, user: User) -> Response:

        db = sqlalchemy.get_instance()
        c = celery.get_instance()

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        schedule = db.Schedule.query.get(schedule_id)
        if schedule.on_data_ready is False:
            # retrieving celery task
            task = c.get_periodic_task(name=schedule_id)
            log.debug("Periodic task - {}", task)
            # disable the schedule deleting it from celery
            if is_active is False:
                if task is None:
                    raise Conflict("Scheduled task is already disabled")
                c.delete_periodic_task(name=schedule_id)
            # enable the schedule
            if is_active is True:
                if task:
                    raise Conflict("Scheduled task is already enabled")

                # recreate the schedule in celery retrieving the schedule from postgres
                schedule_response = SqlApiDbManager.get_schedule_by_id(db, schedule_id)
                log.debug("schedule response: {}", schedule_response)

                # recreate the schedule in celery retrieving the schedule from postgres
                try:
                    request_id = None
                    if "periodic" in schedule_response:
                        c.create_periodic_task(
                            name=str(schedule_id),
                            task="data_extract",
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
                                schedule_response["args"]["only_reliable"],
                                schedule_response["args"]["pushing_queue"],
                                schedule_id,
                                False,
                                schedule_response["opendata"],
                            ],
                        )

                    if "crontab" in schedule_response:

                        cronsettings = schedule_response["crontab_settings"]

                        c.create_crontab_task(
                            name=str(schedule_id),
                            task="data_extract",
                            minute=str(cronsettings.get("minute")),
                            hour=str(cronsettings.get("hour")),
                            day_of_week=str(cronsettings.get("day_of_week")),
                            day_of_month=str(cronsettings.get("day_of_month")),
                            month_of_year=str(cronsettings.get("month_of_year")),
                            args=[
                                user.id,
                                schedule_response["args"]["datasets"],
                                schedule_response["args"]["reftime"],
                                schedule_response["args"]["filters"],
                                schedule_response["args"]["postprocessors"],
                                schedule_response["args"]["output_format"],
                                request_id,
                                schedule_response["args"]["only_reliable"],
                                schedule_response["args"]["pushing_queue"],
                                schedule_id,
                                False,
                                schedule_response["opendata"],
                            ],
                        )

                except Exception:
                    raise SystemError("Unable to enable the request")

        # update schedule status in database
        SqlApiDbManager.update_schedule_status(db, schedule_id, is_active)

        return self.response({"id": schedule_id, "enabled": is_active})

    @decorators.auth.require()
    @decorators.endpoint(
        path="/schedules/<schedule_id>",
        summary="Delete a schedule",
        responses={
            200: "Schedule is succesfully disable/enable",
            404: "Schedule not found",
        },
    )
    def delete(self, schedule_id: str, user: User) -> Response:

        db = sqlalchemy.get_instance()
        celery_app = celery.get_instance()

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.id, schedule_id)

        # delete schedule in celery
        celery_app.delete_periodic_task(name=schedule_id)

        # delete schedule status in database
        SqlApiDbManager.delete_schedule(db, schedule_id)

        return self.response(
            f"Schedule {schedule_id} successfully deleted",
        )

    @staticmethod
    def request_and_owner_check(db, user_id, schedule_id):
        # check if the schedule exists
        if not SqlApiDbManager.check_request(db, schedule_id=schedule_id):
            raise NotFound("The request doesn't exist")

        # check if the current user is the owner of the request
        if not SqlApiDbManager.check_owner(db, user_id, schedule_id=schedule_id):
            raise Forbidden("This request doesn't come from the request's owner")


class ScheduledRequests(EndpointResource):
    labels = ["scheduled_requests"]

    @decorators.auth.require()
    @decorators.use_kwargs(
        {"get_total": fields.Bool(required=False), "last": fields.Bool(required=False)},
        location="query",
    )
    @decorators.endpoint(
        path="/schedules/<schedule_id>/requests",
        summary="Get requests related to a given schedule.",
        responses={
            200: "List of requests for a given schedule.",
            404: "Schedule not found.",
            403: "Cannot access a schedule not belonging to you",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Requests'}}
    def get(
        self, schedule_id: str, user: User, get_total: bool = False, last: bool = True
    ) -> Response:
        """
        Get all submitted requests for this schedule
        :param schedule_id:
        :return:
        """
        log.debug("get scheduled requests")

        db = sqlalchemy.get_instance()

        # check if the schedule exists
        if not SqlApiDbManager.check_request(db, schedule_id=schedule_id):
            raise NotFound(f"The schedule ID {schedule_id} does not exist")

        # check for schedule ownership

        if not SqlApiDbManager.check_owner(db, user.id, schedule_id=schedule_id):
            raise Forbidden("This request doesn't come from the schedule's owner")

        if get_total:
            # get total count for user schedules
            counter = SqlApiDbManager.count_schedule_requests(db, schedule_id)
            return self.response({"total": counter})

        # get all submitted requests or the last for this schedule
        if last:
            res = SqlApiDbManager.get_last_scheduled_request(db, schedule_id)
            if res is None:
                raise NotFound(
                    "No successful request is available for schedule ID {} yet".format(
                        schedule_id
                    )
                )
        else:
            res = SqlApiDbManager.get_schedule_requests(db, schedule_id)
        return self.response(res)
