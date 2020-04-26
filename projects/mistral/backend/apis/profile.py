# -*- coding: utf-8 -*-
from marshmallow import fields


class CustomProfile(object):
    def __init__(self):
        pass

    @staticmethod
    def manipulate(ref, user, data):
        data['Disk Quota'] = user.disk_quota

        return data

    # strip_required is True when the model is invoked by put endpoints
    @staticmethod
    def get_custom_fields(strip_required=False):
        return {
            'disk_quota': fields.Int(
                required=not strip_required,
                label="Disk quota",
                description="Disk quota in bytes"
            )
        }
