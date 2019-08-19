from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.requests_manager import RequestManager as repo

import datetime

log = get_logger(__name__)
DOWNLOAD_DIR = '/data'


class UserRequests(EndpointResource):

    @catch_error()
    def get(self):
        param = self.get_input()
        # uuid = param.get('uuid')
        sort = param.get('sort-by')
        sort_order = param.get('sort-order')
        filter = param.get('filter')
        get_total = param.get('get_total', False)

        user = self.get_current_user()
        # log.info('current user:{}, requested user: {}'.format(user.uuid, uuid))
        # if user.uuid != uuid:
        #     raise RestApiException(
        #         "Operation not allowed",
        #         status_code=hcodes.HTTP_BAD_UNAUTHORIZED)

        db = self.get_service_instance('sqlalchemy')

        if get_total:
            counter = repo.count_user_requests(db, user.uuid)
            return {"total": counter}

        # get user requests list
        res = repo.get_user_requests(db, user.uuid, sort_by=sort, sort_order=sort_order,
                                                    filter=filter)
        return self.force_response(
            res, code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    def delete(self):
        param = self.get_input()
        request_id = param.get('id')

        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')
        # check if the current user is the owner of the request
        if repo.check_owner(db, user.uuid, single_request_id=request_id):

            # delete request and fileoutput entry from database. Delete fileoutput from user folder
            repo.delete_request_record(db,user.uuid, request_id,DOWNLOAD_DIR)


            return self.force_response('Removed request {}'.format(request_id))
        else:
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED)

