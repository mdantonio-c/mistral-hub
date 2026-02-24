from datetime import datetime
from typing import Dict, Type, TypedDict, Union

from restapi.models import ISO8601UTC, Schema, fields


class AccessKeySchema(Schema):
    key = fields.Str()
    emitted = fields.DateTime(attribute="creation", format=ISO8601UTC)
    expiration = fields.DateTime(format=ISO8601UTC, required=False, allow_none=True)
    scope = fields.Str(required=False, allow_none=True)


class DatasetSchema(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=False, allow_none=True)
    category = fields.Str(required=True)
    format = fields.Str(required=True)
    source = fields.Str(required=True)
    bounding = fields.Str(required=False, allow_none=True)

    # Attribution
    attribution = fields.Str(required=True)
    attribution_description = fields.Str(required=False, allow_none=True)
    attribution_url = fields.Str(required=False, allow_none=True)

    # License / group
    group_license = fields.Str(required=False, allow_none=True)
    group_license_description = fields.Str(required=False, allow_none=True)
    license = fields.Str(required=True)
    license_description = fields.Str(required=False, allow_none=True)
    license_url = fields.Str(required=False, allow_none=True)

    is_public = fields.Boolean(required=True)
    authorized = fields.Boolean(required=True)
