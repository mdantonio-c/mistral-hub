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
        # check if the file exists, the current user is the owner and if it is in its folder
        if RequestManager.check_fileoutput(db,  user.uuid, filename, DOWNLOAD_DIR):
            user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
            log.info('directory: {}'.format(user_dir))
            # download the file as a response attachment
            return send_from_directory(user_dir, filename, as_attachment=True)

        else:
            raise RestApiException(
                "File not found",
                status_code=hcodes.HTTP_BAD_NOTFOUND)

    @catch_error()
    def delete(self, filename):
        user = self.get_current_user()
        db = self.get_service_instance('sqlalchemy')
        # check if the file exists, the current user is the owner and if it is in its folder
        if RequestManager.check_fileoutput(db, user.uuid, filename, DOWNLOAD_DIR):

            #delete database entry
            RequestManager.delete_fileoutput(db, filename)

            #delete file
            filepath= os.path.join(DOWNLOAD_DIR, user.uuid,filename)
            os.remove(filepath)

            return self.force_response('Removed file {}'.format(filepath))
        else:
            raise RestApiException(
                "File not found",
                status_code=hcodes.HTTP_BAD_NOTFOUND)