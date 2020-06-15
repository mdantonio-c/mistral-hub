import os

from flask import send_from_directory
from mistral.services.requests_manager import RequestManager
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

DOWNLOAD_DIR = "/data"


class FileDownload(EndpointResource):

    labels = ["file"]
    _GET = {
        "/data/<filename>": {
            "summary": "Download output file",
            "responses": {
                "200": {
                    "description": "found the file to download",
                    "schema": {"$ref": "#/definitions/Fileoutput"},
                },
                "404": {"description": "file not found"},
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self, filename):

        user = self.get_user()
        db = self.get_service_instance("sqlalchemy")
        # check for file existence, ownership and location
        if RequestManager.check_fileoutput(db, user, filename, DOWNLOAD_DIR):
            user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
            log.info("directory: {}", user_dir)
            # download the file as a response attachment
            return send_from_directory(user_dir, filename, as_attachment=True)

        else:
            raise RestApiException(
                "File not found", status_code=hcodes.HTTP_BAD_NOTFOUND
            )
