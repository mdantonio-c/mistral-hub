from flask import send_from_directory
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import sqlalchemy
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
        db = sqlalchemy.get_instance()

        # check for file existence, ownership and location
        file_dir = SqlApiDbManager.check_fileoutput(db, user, filename)
        log.info("directory: {}", file_dir)
        # download the file as a response attachment
        return send_from_directory(file_dir, filename, as_attachment=True)
