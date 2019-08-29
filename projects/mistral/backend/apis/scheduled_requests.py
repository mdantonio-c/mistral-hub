from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.requests_manager import RequestManager

import datetime

log = get_logger(__name__)


class ScheduledRequests(EndpointResource):
    @catch_error()
    def get(self):
        param= self.get_input()
        scheduled_request_id = param.get('id')
        sort = param.get('sort-by')
        sort_order = param.get('sort-order')
        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')

        # check if the current user is the owner of the scheduled request
        if not RequestManager.check_owner(db, user.id, schedule_id=scheduled_request_id):
            raise RestApiException(
                    "Operation not allowed",
                    status_code=hcodes.HTTP_BAD_UNAUTHORIZED)

        #get requests list of a scheduled task
        submitted_request_list = RequestManager.get_schedule_requests(db,scheduled_request_id,sort_by=sort,sort_order= sort_order)

        return self.force_response(
                submitted_request_list, code=hcodes.HTTP_OK_BASIC)