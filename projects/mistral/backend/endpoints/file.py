import os

from flask import send_from_directory
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.exceptions import NotFound
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log


class FileDownload(EndpointResource):

    labels = ["file"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/data/<filename>",
        summary="Download output file",
        responses={200: "Found the file to download", 404: "File not found"},
    )
    # 200: {'schema': {'$ref': '#/definitions/Fileoutput'}}
    def get(self, filename):

        user = self.get_user()
        db = self.get_service_instance("sqlalchemy")

        # check for file existence, ownership and location
        if not SqlApiDbManager.check_fileoutput(db, user, filename, DOWNLOAD_DIR):
            raise NotFound("File not found")

        user_dir = os.path.join(DOWNLOAD_DIR, user.uuid, "outputs")
        log.info("directory: {}", user_dir)
        # download the file as a response attachment
        return send_from_directory(user_dir, filename, as_attachment=True)
