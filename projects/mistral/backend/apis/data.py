from marshmallow import ValidationError, pre_load
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager as repo
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import spare_point_interpol as pp3_3
from restapi import decorators
from restapi.exceptions import BadRequest, Forbidden, NotFound, RestApiException
from restapi.models import AdvancedList, InputSchema, fields, validate
from restapi.rest.definition import EndpointResource
from restapi.services.uploader import Uploader
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


class DataExtraction(InputSchema):
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

    @pre_load
    def check_postprocessors_unique_type(self, data, **kwargs):
        if data.get("postprocessors"):
            postprocessor_types = []
            for p in data.get("postprocessors"):
                postprocessor_types.append(p.get("type"))
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
    _POST = {
        "/data": {
            "summary": "Request for data extraction.",
            "responses": {
                "202": {"description": "Data extraction request queued"},
                "400": {
                    "description": "Parameters for post processing are not correct"
                },
                "500": {
                    "description": "File for spare point interpolation post processor is corrupted"
                },
            },
        }
    }

    @decorators.auth.require()
    @decorators.use_kwargs({"push": fields.Bool(required=False)}, locations=["query"])
    @decorators.use_kwargs(DataExtraction)
    def post(
        self,
        request_name,
        dataset_names,
        reftime=None,
        filters=None,
        output_format=None,
        postprocessors=None,
        push=False,
    ):
        user = self.get_user()
        log.info(f"request for data extraction coming from user UUID: {user.uuid}")

        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get("id", "") == ds_name), None)
            if not found:
                raise NotFound(f"Dataset '{ds_name}' not found")

        # get the format of the datasets
        dataset_format = arki.get_datasets_format(dataset_names)
        if not dataset_format:
            raise BadRequest(
                "Invalid set of datasets : datasets have different formats"
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
            parsed_reftime["from"] = dt_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            parsed_reftime["to"] = dt_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # clean up processors from unknown values
        # processors = [i for i in processors if arki.is_processor_allowed(i.get('type'))]
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

        # check if the output format chosen by the user is compatible with the chosen datasets
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

        # get queue for pushing notifications
        pushing_queue = None
        if push:
            pushing_queue = user.amqp_queue
            rabbit = self.get_service_instance("rabbitmq")
            # check if the queue exists
            if not rabbit.queue_exists(pushing_queue):
                raise Forbidden("User's queue for push notification does not exists")

        # run the following steps in a transaction
        db = self.get_service_instance("sqlalchemy")
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
                    "pushing_queue": pushing_queue,
                },
            )

            celery = self.get_service_instance("celery")
            task = celery.data_extract.apply_async(
                args=[
                    user.id,
                    dataset_names,
                    parsed_reftime,
                    filters,
                    postprocessors,
                    output_format,
                    request.id,
                    pushing_queue,
                ],
                countdown=1,
            )

            request.task_id = task.id
            request.status = task.status  # 'PENDING'
            db.session.commit()
            log.info("Request successfully saved: <ID:{}>", request.id)
        except Exception:
            db.session.rollback()
            raise SystemError("Unable to submit the request")
        if task:
            r = {"task_id": task.id}

        else:
            raise RestApiException(
                "Unable to submit the request", status_code=hcodes.HTTP_SERVER_ERROR,
            )
        return self.response(r, code=hcodes.HTTP_OK_ACCEPTED)
