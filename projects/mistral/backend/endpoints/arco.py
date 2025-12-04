from mimetypes import MimeTypes
from pathlib import Path
from typing import Optional

import botocore
from flask import Response
from mistral.connectors import s3
from mistral.services.access_key_service import validate_access_key_from_request
from restapi import decorators
from restapi.config import APP_MODE
from restapi.exceptions import NotFound, Unauthorized
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log

BUCKET_NAME = "arco"


def guess_mime_type(path: str) -> Optional[str]:
    # guess_type expects a str as argument because
    # it is intended to be used with urls and not with paths
    mime_type = MimeTypes().guess_type(str(path))
    return mime_type[0]


class ArcoResource(EndpointResource):
    labels = ["arco"]

    @decorators.endpoint(
        path="/arco/<path:object_path>",
        summary="Access ARCO datasets",
        responses={200: "Data retrieved", 404: "Data not found"},
    )
    def get(self, object_path: str) -> Response:
        log.debug(f"Accessing ARCO dataset: {object_path}")

        # 1. Validate access key via Basic Auth
        authorized = validate_access_key_from_request()
        if not authorized:
            raise Unauthorized()

        # 2. Fetch S3 object
        try:
            conn = s3.get_instance()
            s3_object = conn.client.get_object(Bucket=BUCKET_NAME, Key=object_path)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise NotFound(f"The object '{object_path}' does not exist.") from e
            else:
                raise Exception from e

        # 3. return S3 data as HTTP response
        data = s3_object["Body"].read()
        filename = Path(object_path).name
        log.debug(f"Accessing ARCO dataset: {filename}")
        mime = guess_mime_type(filename)
        log.debug(f"Guessed mime type: {mime}")
        return Response(data, mimetype=mime)
