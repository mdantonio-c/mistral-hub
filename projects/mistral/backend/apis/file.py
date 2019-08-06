from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.requests_manager import RequestManager
from flask import send_from_directory
import os


log = get_logger(__name__)
DOWNLOAD_DIR = '/data'


class FileDownload(EndpointResource):

    @catch_error()
    def get(self,filename):

        user = self.get_current_user()
        db = self.get_service_instance('sqlalchemy')
        # check if the file exists and if it is in the current user folder
        if RequestManager.check_fileoutput(db,  user.uuid, filename, DOWNLOAD_DIR):
            user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
            log.info('directory: {}'.format(user_dir))
            # download the file as a response attachment
            return send_from_directory(user_dir, filename, as_attachment=True)

        else:
            raise RestApiException(
                "File not found",
                status_code=hcodes.HTTP_BAD_NOTFOUND)