import math
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from marshmallow import ValidationError, pre_load
from mistral.endpoints import DOWNLOAD_DIR, PostProcessorsType
from mistral.exceptions import DiskQuotaException, MaxOutputSizeExceeded
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from mistral.tasks import data_extraction as data_ext
from mistral.tasks.data_extraction_utilities import queue_sorting
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import spare_point_interpol as pp3_3
from restapi import decorators
from restapi.connectors import celery, rabbitmq, sqlalchemy
from restapi.exceptions import (  # ServerError
    BadRequest,
    Forbidden,
    NotFound,
    ServiceUnavailable,
    Unauthorized,
)
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log

OUTPUT_FORMATS = ["json", "bufr"]

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

SUBTYPES = [
    "near",
    "bilin",
    "average",
    "min",
    "max",
]

TIMERANGES = [0, 1, 2, 3, 4, 6, 254]


class AVProcessor(Schema):
    # Derived variables post-processing
    processor_type = fields.Str(required=True)
    # "derived_variables"

    variables = fields.List(
        fields.Str(
            validate=validate.OneOf(DERIVED_VARIABLES),
            metadata={
                "description": "The list of requested derived variables to be calculated."
            },
        ),
        unique=True,
        min_items=1,
        required=True,
    )


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
        metadata={
            "description": "file to define the target spare points",
        },
    )
    file_format = fields.Str(
        required=True, data_key="format", validate=validate.OneOf(["shp", "geojson"])
    )
    sub_type = fields.Str(required=True, validate=validate.OneOf(SUBTYPES))


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
        metadata={
            "description": "Interval of elaboration",
        },
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
    trans_type = fields.Str(required=False, validate=validate.OneOf(["zoom"]))


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
        metadata={
            "description": "grib template for interpolation",
        },
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


class DataExtraction(Schema):
    request_name = fields.Str(required=True)
    reftime = fields.Nested(Reftime, allow_none=True)
    dataset_names = fields.List(
        fields.Str(metadata={"description": "Dataset name"}),
        unique=True,
        min_items=1,
        required=True,
        metadata={
            "description": "Data belong to the datasets of the list.",
        },
    )
    filters = fields.Nested(
        Filters, metadata={"description": "Apply different filtering criteria."}
    )
    output_format = fields.Str(required=False)
    only_reliable = fields.Bool(required=False)
    postprocessors = fields.List(
        Postprocessors(metadata={"description": "Post-processing request details"}),
        metadata={
            "description": "Apply one or more post-processing to the filtered data."
        },
    )
    force_obs_download = fields.Bool(
        required=False,
        metadata={
            "description": "If set to True, download of observed data will be attempted even if the"
            " estimated data size exceeds the allowed user quota."
        },
    )

    @pre_load
    def check_output_format(self, data, **kwargs):
        if "output_format" in data and data["output_format"] not in OUTPUT_FORMATS:
            raise ValidationError(
                f"Invalid 'output_format'. Allowed values are: {OUTPUT_FORMATS}. For forecast "
                f"datasets, do not include the 'output_format' parameter (it defaults to 'grib')."
            )
        return data

    @pre_load
    def check_postprocessors_unique_type(self, data, **kwargs):
        if data.get("postprocessors"):
            postprocessor_types = []
            for p in data.get("postprocessors"):
                if type(p) == dict and "processor_types" in p.keys():
                    postprocessor_types.append(p.get("processor_type"))
            if len(postprocessor_types) != len(set(postprocessor_types)):
                raise ValidationError("Postprocessors list contains duplicates")

            pp3_list = [
                "grid_cropping",
                "grid_interpolation",
                "spare_point_interpolation",
            ]
            if len(set(postprocessor_types).intersection(set(pp3_list))) > 1:
                raise ValidationError(
                    "Only one geographical postprocessing at a time can be executed"
                )
        return data


class Data(EndpointResource, Uploader):
    labels = ["data"]

    @decorators.auth.require()
    @decorators.use_kwargs({"push": fields.Bool(required=False)}, location="query")
    @decorators.use_kwargs(DataExtraction)
    @decorators.endpoint(
        path="/data",
        summary="Request for data extraction.",
        responses={
            202: "Data extraction request queued",
            400: "Parameters for post processing are not correct",
            403: "Requested data exceeds allowed size",
            500: "File for spare point interpolation post processor is corrupted",
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
        postprocessors: Optional[List[PostProcessorsType]] = None,
        push: bool = False,
        force_obs_download: bool = False,
    ) -> Response:

        db = sqlalchemy.get_instance()
        log.info(f"request for data extraction coming from user UUID: {user.uuid}")

        # check if the user has a limit of number of requests par hour
        repo.check_user_request_limit(db, user)

        # check for existing dataset(s)
        datasets = repo.get_datasets(db, user)
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get("id", "") == ds_name), None)
            if not found:
                raise NotFound(
                    f"Dataset '{ds_name}' not found: check for dataset name of for your authorizations "
                )

        # get the format of the datasets
        dataset_format = arki.get_datasets_format(dataset_names)
        if not dataset_format:
            raise BadRequest(
                "Invalid set of datasets : datasets have different formats"
            )

        # check the licence group
        license_group = repo.get_license_group(db, dataset_names)
        if not license_group:
            raise BadRequest(
                "Invalid set of datasets : datasets belongs to different license groups"
            )

        # incoming filters: <dict> in form of filter_name: list_of_values
        # e.g. 'level': [{...}, {...}] or 'level: {...}'
        # clean up filters from unknown values
        if filters:
            filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        parsed_reftime = {}
        if reftime:
            dt_from = reftime.get("date_from")
            dt_to = reftime.get("date_to")

            if dt_from:
                parsed_reftime["from"] = dt_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            else:  # pragma: no cover
                log.warning("Missing date_from in reftime")

            if dt_to:
                parsed_reftime["to"] = dt_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            else:  # pragma: no cover
                log.warning("Missing date_to in reftime")

        # clean up processors from unknown values
        # processors = [i for i in processors if arki.is_processor_allowed(i.get('type'))]
        if postprocessors:
            # check if the user is authorized for postprocessors
            allowed_postprocessing = repo.get_user_permissions(
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

            # check if requested space post processing are available for the chosen datasets
            if dataset_format == "bufr":
                for p in postprocessors:
                    if (
                        p.get("processor_type") == "grid_cropping"
                        or p.get("processor_type") == "grid_interpolation"
                    ):
                        raise BadRequest(
                            "Post processors unaivailable for the requested datasets"
                        )

        # check if the output format is compatible with the chosen datasets
        if output_format is not None:
            postprocessors_list = []
            if postprocessors:
                postprocessors_list = [i.get("processor_type") for i in postprocessors]
            # spare point interpolation has bufr as output format
            if (
                dataset_format == "grib"
                and "spare_point_interpolation" not in postprocessors_list
            ):
                raise BadRequest(
                    f"The chosen datasets does not support {output_format} output format"
                )

        # get queue for pushing notifications
        pushing_queue = None
        if push:
            pushing_queue = user.amqp_queue
            if not pushing_queue:
                raise Forbidden("User's queue for push notification does not exists")
            rabbit = rabbitmq.get_instance()
            # check if the queue exists
            if not rabbit.queue_exists(pushing_queue):
                raise Forbidden("User's queue for push notification does not exists")

        data_type = arki.get_datasets_category(dataset_names)

        if only_reliable:
            # check if the option is possible for the selected datasets
            if data_type != "OBS" and "multim-forecast" not in dataset_names:
                raise BadRequest(
                    "The chosen datasets do not support 'only quality controlled data' option "
                )

        # In a future size estimation may be implemented for multim-forecast dataset data as well
        if data_type == "OBS" and not postprocessors and not force_obs_download:
            esti_obs_data_size = None

            try:

                esti_obs_data_size = get_observed_data_size_count(
                    parsed_reftime, dataset_names, filters, license_group, output_format
                )

            except Exception as e:
                log.warning(f"Unable to get summary stats: {e}")
                # raise ServerError(f"Unable to get summary stats: {e}")

            if esti_obs_data_size:
                try:

                    check_user_quota_for_observed_data(user.id, db, esti_obs_data_size)

                except DiskQuotaException:
                    raise Forbidden(
                        "The requested data size is estimated to exceed the available user quota."
                    )

                except MaxOutputSizeExceeded:
                    raise Forbidden(
                        "The requested data size is estimated to exceed the maximum limit for output size."
                    )

        # run the following steps in a transaction
        task = None
        try:
            request = repo.create_request_record(
                db,
                user.id,
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
            )

            c = celery.get_instance()
            # get the correct celery queue to redirect the request
            celery_queue = queue_sorting(data_type, reftime)
            task = c.celery_app.send_task(
                "data_extract",
                args=(
                    user.id,
                    dataset_names,
                    parsed_reftime,
                    filters,
                    postprocessors,
                    output_format,
                    request.id,
                    only_reliable,
                    pushing_queue,
                    None,
                    False,
                    False,
                    force_obs_download,
                ),
                countdown=1,
                queue=celery_queue,
                routing_key=celery_queue,
            )

            request.task_id = task.id
            request.status = task.status  # 'PENDING'
            db.session.commit()
            log.info("Request successfully saved: <ID:{}>", request.id)
        except Exception:
            db.session.rollback()
            raise SystemError("Unable to submit the request")

        if not task:
            raise ServiceUnavailable(
                "Unable to submit the request",
            )

        r = {"request_id": request.id, "task_id": task.id}
        return self.response(r, code=202)


def get_observed_data_size_count(
    parsed_reftime, dataset_names, filters, license_group, output_format
):

    dballe_fields, dballe_queries = dballe.parse_query_for_data_extraction(
        dataset_names, filters, parsed_reftime
    )

    db_type = dballe.get_db_type(
        dballe_queries[dballe_fields.index("datetimemin")][0],
        dballe_queries[dballe_fields.index("datetimemax")][0],
    )

    explorer = dballe.build_explorer(
        db_type, license_group=license_group, network_list=dataset_names
    )

    summary = dballe.get_summary(
        dataset_names, explorer, None, fields=dballe_fields, queries=dballe_queries
    )

    if summary and "s" in summary:
        esti_obs_data_size = (
            summary["s"] if output_format != "json" else math.floor(summary["s"] * 2.8)
        )
    else:
        esti_obs_data_size = None

    log.debug(
        f"estimated observed data size for the request: {esti_obs_data_size} "
        f"({data_ext.human_size(esti_obs_data_size)})"
    )

    return esti_obs_data_size


def check_user_quota_for_observed_data(user_id, db, esti_obs_data_size):

    user = db.User.query.filter_by(id=user_id).first()

    max_output_size = repo.get_user_permissions(user, param="output_size")
    log.info(
        f"user max_output_size: {max_output_size} ({data_ext.human_size(max_output_size)})"
    )

    if max_output_size and esti_obs_data_size > max_output_size:
        message = (
            "The resulting output size exceed the size allowed for a single request"
        )
        raise MaxOutputSizeExceeded(message)

    # check for exceeding quota
    max_user_quota = db.session.query(db.User.disk_quota).filter_by(id=user_id).scalar()

    user_dir = DOWNLOAD_DIR.joinpath(user.uuid, "outputs")

    # check for current used space
    used_quota = (
        int(subprocess.check_output(["du", "-sb", user_dir]).split()[0])
        if user_dir.exists()
        else 0
    )
    log.info(f"user used disk quota: {used_quota} ({data_ext.human_size(used_quota)})")

    if used_quota + esti_obs_data_size > max_user_quota:
        free_space = max(max_user_quota - used_quota, 0)
        log.info(
            f"user free disk space: {free_space} ({data_ext.human_size(free_space)})"
        )

        message = "Disk quota exceeded: required size {}; remaining space {}".format(
            data_ext.human_size(esti_obs_data_size), data_ext.human_size(free_space)
        )
        raise DiskQuotaException(message)
