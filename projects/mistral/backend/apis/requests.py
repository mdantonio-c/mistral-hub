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
        sort = param.get('sort-by')
        sort_order = param.get('sort-order')
        filter = param.get('filter')
        user = self.get_current_user()
        log.info('current user:{}, requested user: {}'.format(user.uuid,uuid))
        if user.uuid==uuid:
            #log.info('parameters: {}'.format(uuid))

            db = self.get_service_instance('sqlalchemy')

            # get user requests list
            request_list = RequestManager.get_user_requests(db,uuid,sort_by=sort,sort_order= sort_order,filter=filter)

            return self.force_response(
                request_list, code=hcodes.HTTP_OK_BASIC)
        else:
            raise RestApiException(
                "Operation not allowed",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED)