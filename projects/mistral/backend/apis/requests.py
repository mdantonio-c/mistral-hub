from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.requests_manager import RequestManager

import datetime

log = get_logger(__name__)


class UserRequests(EndpointResource):
    @catch_error()
    def get(self):
        param= self.get_input()
        uuid = param.get('uuid')
        #log.info('parameters: {}'.format(uuid))

        db = self.get_service_instance('sqlalchemy')

        # get user requests list
        request_list = RequestManager.get_user_requests(db,uuid)

        return self.force_response(
            request_list, code=hcodes.HTTP_OK_BASIC)