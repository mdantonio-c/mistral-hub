# -*- coding: utf-8 -*-
from marshmallow import fields


class CustomProfile(object):
    def __init__(self):
        pass

    @staticmethod
    def manipulate(ref, user, data):
        data['Disk Quota'] = user.disk_quota

        return data

    @staticmethod
    def get_custom_fields():
        return {
            'disk_quota': fields.Int(
                required=True,
                label="Disk quota",
                description="Disk quota in bytes"
            )
        }
