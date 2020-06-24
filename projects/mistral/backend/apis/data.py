from flask_apispec import use_kwargs
from marshmallow import fields
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager as repo
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import spare_point_interpol as pp3_3
from mistral.tools import statistic_elaboration as pp2
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.services.uploader import Uploader
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class Data(EndpointResource, Uploader):
    labels = ["data"]
    _POST = {
        "/data": {
            "summary": "Request for data extraction.",
            "parameters": [
                {
                    "name": "criteria",
                    "in": "body",
                    "description": "Criteria for data extraction.",
                    "schema": {"$ref": "#/definitions/DataExtraction"},
                },
            ],
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

    @decorators.catch_errors()
    @decorators.auth.required()
    @use_kwargs({"push": fields.Bool(required=False)}, locations=["query"])
    def post(self, push=False):
        user = self.get_user()
        log.info(f"request for data extraction coming from user UUID: {user.uuid}")
        criteria = self.get_input()

        self.validate_input(criteria, "DataExtraction")
        product_name = criteria.get("name")
        dataset_names = criteria.get("datasets")
        reftime = criteria.get("reftime")
        output_format = criteria.get("output_format")

        if reftime is not None:
            # 'from' and 'to' both mandatory by schema
            # check from <= to
            if reftime["from"] > reftime["to"]:
                raise RestApiException(
                    "Invalid reftime: <from> greater than <to>",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get("id", "") == ds_name), None)
            if not found:
                raise RestApiException(
                    f"Dataset '{ds_name}' not found",
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )

        # get the format of the datasets
        dataset_format = arki.get_datasets_format(dataset_names)
        if not dataset_format:
            raise RestApiException(
                "Invalid set of datasets : datasets have different formats",
                status_code=hcodes.HTTP_BAD_REQUEST,
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

        # check if requested space post processing are available for the chosen datasets
        if dataset_format == "bufr":
            for p in processors:
                if (
                    p.get("type") == "grid_cropping"
                    or p.get("type") == "grid_interpolation"
                ):
                    raise RestApiException(
                        "Post processors unaivailable for the requested datasets",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )

        # check if the output format chosen by the user is compatible with the chosen datasets
        if output_format is not None:
            postprocessors_list = [i.get("type") for i in processors]
            if dataset_format != output_format:
                if dataset_format == "grib":
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
            else:
                if (
                    dataset_format == "grib"
                    and "spare_point_interpolation" in postprocessors_list
                ):
                    raise RestApiException(
                        f"The chosen postprocessor does not support {output_format} output format",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )

        # get queue for pushing notifications
        pushing_queue = None
        if push:
            pushing_queue = user.amqp_queue
            rabbit = self.get_service_instance("rabbitmq")
            # check if the queue exists
            if not rabbit.queue_exists(pushing_queue):
                raise RestApiException(
                    "User's queue for push notification does not exists",
                    status_code=hcodes.HTTP_BAD_FORBIDDEN,
                )

        # run the following steps in a transaction
        db = self.get_service_instance("sqlalchemy")
        task = None
        try:
            request = repo.create_request_record(
                db,
                user.id,
                product_name,
                {
                    "datasets": dataset_names,
                    "reftime": reftime,
                    "filters": filters,
                    "postprocessors": processors,
                    "output_format": output_format,
                    "pushing_queue": pushing_queue,
                },
            )

            celery = self.get_service_instance("celery")
            task = celery.data_extract.apply_async(
                args=[
                    user.id,
                    dataset_names,
                    reftime,
                    filters,
                    processors,
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
