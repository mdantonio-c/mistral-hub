
import os
from mimetypes import MimeTypes

from restapi.rest.definition import EndpointResource
from restapi.services.download import Downloader
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.requests_manager import RequestManager
from flask import send_from_directory


log = get_logger(__name__)
DOWNLOAD_DIR = '/data'


class FileDownload(EndpointResource, Downloader):

    @catch_error()
    def get(self, filename):

        user = self.get_current_user()
        db = self.get_service_instance('sqlalchemy')
        # check if the file exists, the current user is the owner and if it is in its folder
        if RequestManager.check_fileoutput(db,  user, filename, DOWNLOAD_DIR):
            user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
            log.info('directory: {}'.format(user_dir))
            # download the file as a response attachment
            # return send_from_directory(user_dir, filename, as_attachment=True)

            filepath = os.path.join(user_dir, filename)
            mime = MimeTypes()
            mime_type = mime.guess_type(filepath)
            return self.send_file_streamed(filepath, mime_type[0])

        else:
            raise RestApiException(
                "File not found",
                status_code=hcodes.HTTP_BAD_NOTFOUND)