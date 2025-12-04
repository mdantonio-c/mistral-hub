from datetime import datetime
from typing import Dict, Type, TypedDict, Union

from restapi.models import ISO8601UTC, Schema, fields


class AccessKeySchema(Schema):
    key = fields.Str()
    emitted = fields.DateTime(attribute="creation", format=ISO8601UTC)
    expiration = fields.DateTime(format=ISO8601UTC, allow_none=True)
    scope = fields.Str(allow_none=True)
