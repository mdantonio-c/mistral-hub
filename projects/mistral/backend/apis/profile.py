from restapi.models import fields, validate


class CustomProfile:
    def __init__(self):
        pass

    @staticmethod
    def manipulate(ref, user, data):
        data["disk_quota"] = user.disk_quota
        data["amqp_queue"] = user.amqp_queue
        data["requests_expiration_days"] = user.requests_expiration_days

        return data

    @staticmethod
    def get_custom_fields(request):

        required = request and request.method == "POST"

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
            "requests_expiration_days": fields.Str(
                required=False,
                missing=0,
                label="Requests expirations",
                description="Number of days after which requests will be cleaned",
            ),
        }
