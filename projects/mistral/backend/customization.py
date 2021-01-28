from restapi.connectors import sqlalchemy
from restapi.customizer import BaseCustomizer
from restapi.exceptions import NotFound
from restapi.models import AdvancedList, Schema, fields, validate


class Datasets(Schema):
    id = fields.Str()
    name = fields.Str()


class Customizer(BaseCustomizer):
    @staticmethod
    def custom_user_properties_pre(properties):
        extra_properties = {}
        for p in ("datasets",):
            if p in properties:
                extra_properties[p] = properties.pop(p, None)
        return properties, extra_properties

    @staticmethod
    def custom_user_properties_post(user, properties, extra_properties, db):

        datasets = []
        for dataset_id in extra_properties.get("datasets", []):
            dat = db.Datasets.query.filter_by(id=int(dataset_id)).first()
            if not dat:
                raise NotFound(f"Dataset {dataset_id} not found")

            datasets.append(dat)

        # Self-registered users
        if "open_dataset" not in properties and "open_dataset" not in extra_properties:
            user.open_dataset = True

        user.datasets = datasets

    @staticmethod
    def manipulate_profile(ref, user, data):
        data["disk_quota"] = user.disk_quota
        data["amqp_queue"] = user.amqp_queue
        data["requests_expiration_days"] = user.requests_expiration_days
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
    def get_custom_input_fields(request, scope):

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
                    label="Disk quota",
                    description="Disk quota in bytes",
                ),
                "amqp_queue": fields.Str(
                    required=False,
                    label="AMQP queue",
                    description="AMQP queue used to notify the user",
                ),
                "requests_expiration_days": fields.Int(
                    required=False,
                    missing=0,
                    validate=validate.Range(min=0, max=365),
                    label="Requests expirations (in days, 0 to disable)",
                    description="Number of days after which requests will be cleaned",
                ),
                "open_dataset": fields.Boolean(
                    label="Enable access to Open Datasets",
                    required=False,
                ),
                "datasets": AdvancedList(
                    fields.Str(
                        validate=validate.OneOf(
                            choices=[str(v.id) for v in datasets],
                            labels=[v.name for v in datasets],
                        )
                    ),
                    required=False,
                    label="Allowed additional datasets",
                    description="",
                    unique=True,
                    multiple=True,
                ),
                "max_templates": fields.Int(
                    required=required,
                    validate=validate.Range(min=0, max=999),
                    label="Max # templates",
                    description="Maximum number of templates the user can upload",
                ),
                "max_output_size": fields.Int(
                    required=required,
                    validate=validate.Range(min=0),
                    label="Max output size",
                    description="Maximum amount of data the user can request at once",
                ),
                "allowed_postprocessing": fields.Boolean(
                    required=required,
                    label="Postprocessing",
                    description="Allow postprocessing tools",
                ),
                "allowed_schedule": fields.Boolean(
                    required=required, label="Schedule", description="Allow schedules"
                ),
                "allowed_obs_archive": fields.Boolean(
                    required=required,
                    label="Observed Archive",
                    description="Allow access to observed archive",
                ),
                "request_par_hour": fields.Int(
                    required=required,
                    validate=validate.Range(min=0, max=999),
                    label="Requests per hour",
                    description="Maximum number of allowed requests per hour",
                ),
            }

        # these are editable fields in profile
        if scope == BaseCustomizer.PROFILE:
            return {
                "requests_expiration_days": fields.Int(
                    required=False,
                    missing=0,
                    validate=validate.Range(min=0, max=365),
                    label="Requests expirations (in days, 0 to disable)",
                    description="Number of days after which requests will be cleaned",
                )
            }

        # these are additional fields in registration form
        if scope == BaseCustomizer.REGISTRATION:
            return {}

    @staticmethod
    def get_custom_output_fields(request):
        custom_fields = Customizer.get_custom_input_fields(
            request, scope=BaseCustomizer.ADMIN
        )

        custom_fields["datasets"] = fields.Nested(Datasets(many=True))

        return custom_fields
