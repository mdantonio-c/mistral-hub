from typing import Tuple

from restapi.connectors import sqlalchemy
from restapi.connectors.sqlalchemy import SQLAlchemy
from restapi.customizer import BaseCustomizer, FlaskRequest, Props, User
from restapi.exceptions import NotFound
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource


class Datasets(Schema):
    id = fields.Str()
    name = fields.Str()


class Customizer(BaseCustomizer):
    @staticmethod
    def custom_user_properties_pre(properties: Props) -> Tuple[Props, Props]:
        extra_properties = {}
        for p in ("datasets",):
            if p in properties:
                extra_properties[p] = properties.pop(p, None)

        properties.setdefault("open_dataset", True)
        # 1 GB, as defined in sqlalchemy model
        properties.setdefault("disk_quota", 1073741824)
        properties.setdefault("requests_expiration_days", 180)
        properties.setdefault("requests_expiration_delete", False)
        properties.setdefault("max_output_size", 1073741824)
        properties.setdefault("max_templates", 1)
        properties.setdefault("allowed_postprocessing", False)
        properties.setdefault("allowed_schedule", True)
        properties.setdefault("allowed_obs_archive", True)
        properties.setdefault("request_par_hour", 10)
        return properties, extra_properties

    @staticmethod
    def custom_user_properties_post(  # type: ignore[override]
        user: User, properties: Props, extra_properties: Props, db: SQLAlchemy
    ) -> None:

        datasets = []
        for dataset_id in extra_properties.get("datasets", []):
            dat = db.Datasets.query.filter_by(id=int(dataset_id)).first()
            if not dat:
                raise NotFound(f"Dataset {dataset_id} not found")

            datasets.append(dat)

        user.datasets = datasets

    @staticmethod
    def manipulate_profile(ref: EndpointResource, user: User, data: Props) -> Props:
        data["disk_quota"] = user.disk_quota
        data["amqp_queue"] = user.amqp_queue
        data["requests_expiration_days"] = user.requests_expiration_days
        data["requests_expiration_delete"] = user.requests_expiration_delete
        data["open_dataset"] = user.open_dataset
        data["datasets"] = user.datasets
        data["max_templates"] = user.max_templates
        data["max_output_size"] = user.max_output_size
        data["allowed_postprocessing"] = user.allowed_postprocessing
        data["allowed_schedule"] = user.allowed_schedule
        data["allowed_obs_archive"] = user.allowed_obs_archive
        data["request_par_hour"] = user.request_par_hour

        return data

    @staticmethod
    def get_custom_input_fields(request: FlaskRequest, scope: int) -> Props:

        # prevent queries at server startup
        if request:
            db = sqlalchemy.get_instance()
            datasets = db.Datasets.query.all()
        else:
            datasets = []

        required = request and request.method == "POST"

        if scope == BaseCustomizer.ADMIN:
            return {
                "disk_quota": fields.Int(
                    required=required,
                    # validate=validate.Range(min=0, max=???),
                    validate=validate.Range(min=0),
                    metadata={
                        "label": "Disk quota",
                        "description": "Disk quota in bytes",
                    },
                ),
                "requests_expiration_days": fields.Int(
                    required=False,
                    load_default=180,
                    validate=validate.Range(min=1, max=180),
                    metadata={
                        "label": "Requests expiration in days",
                        "description": "Number of days after which requests will be archived or deleted",
                    },
                ),
                "open_dataset": fields.Boolean(
                    metadata={
                        "label": "Enable access to Open Datasets",
                    },
                    required=False,
                ),
                "datasets": fields.List(
                    fields.Str(
                        validate=validate.OneOf(
                            choices=[str(v.id) for v in datasets],
                            labels=[v.name for v in datasets],
                        )
                    ),
                    required=False,
                    metadata={
                        "label": "Allowed additional datasets",
                        "description": "",
                    },
                    unique=True,
                ),
                "max_templates": fields.Int(
                    required=required,
                    validate=validate.Range(min=0, max=999),
                    metadata={
                        "label": "Max templates (0 to disable)",
                        "description": "Maximum number of templates the user can upload",
                    },
                ),
                "max_output_size": fields.Int(
                    required=required,
                    validate=validate.Range(min=0),
                    metadata={
                        "label": "Max output size",
                        "description": "Maximum amount of data the user can request at once",
                    },
                ),
                "allowed_postprocessing": fields.Boolean(
                    required=required,
                    metadata={
                        "label": "Postprocessing",
                        "description": "Allow postprocessing tools",
                    },
                ),
                "allowed_schedule": fields.Boolean(
                    required=required,
                    metadata={"label": "Schedule", "description": "Allow schedules"},
                ),
                "allowed_obs_archive": fields.Boolean(
                    required=required,
                    metadata={
                        "label": "Observed Archive",
                        "description": "Allow access to observed archive",
                    },
                ),
                "request_par_hour": fields.Int(
                    required=required,
                    validate=validate.Range(min=0, max=999),
                    metadata={
                        "label": "Requests per hour (0 to disable)",
                        "description": "Maximum number of allowed requests per hour",
                    },
                ),
                "amqp_queue": fields.Str(
                    required=False,
                    metadata={
                        "label": "AMQP queue",
                        "description": "AMQP queue used to notify the user",
                    },
                ),
            }

        # these are editable fields in profile
        if scope == BaseCustomizer.PROFILE:
            return {
                "requests_expiration_days": fields.Int(
                    required=False,
                    load_default=180,
                    validate=validate.Range(min=1, max=180),
                    metadata={
                        "label": "Requests expiration in days(max 180)",
                        "description": "Number of days after which requests will be archived or deleted",
                    },
                ),
                "requests_expiration_delete": fields.Boolean(
                    required=False,
                    metadata={
                        "label": "Delete expired requests (unless they will be archived)",
                        "description": "If set false expired request will be archive instead of deleted",
                    },
                ),
            }

        # these are additional fields in registration form
        if scope == BaseCustomizer.REGISTRATION:
            return {}

        return {}

    @staticmethod
    def get_custom_output_fields(request: FlaskRequest) -> Props:
        return {
            "disk_quota": fields.Int(),
            "requests_expiration_days": fields.Int(),
            "requests_expiration_delete": fields.Boolean(),
            "open_dataset": fields.Boolean(),
            "datasets": fields.Nested(Datasets(many=True)),
            "max_templates": fields.Int(),
            "max_output_size": fields.Int(),
            "allowed_postprocessing": fields.Boolean(),
            "allowed_schedule": fields.Boolean(),
            "allowed_obs_archive": fields.Boolean(),
            "request_par_hour": fields.Int(),
            "amqp_queue": fields.Str(),
        }
