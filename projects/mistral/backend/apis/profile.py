from marshmallow import fields, validate


class CustomProfile:
    def __init__(self):
        pass

    @staticmethod
    def manipulate(ref, user, data):
        data["disk_quota"] = user.disk_quota
        data["amqp_queue"] = user.amqp_queue

        return data

    # strip_required is True when the model is invoked by put endpoints
    @staticmethod
    def get_custom_fields(strip_required=False):
        return {
            "disk_quota": fields.Int(
                required=not strip_required,
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
        }
