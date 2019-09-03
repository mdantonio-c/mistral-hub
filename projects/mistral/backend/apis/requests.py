import json

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.requests_manager import RequestManager as repo
from sqlalchemy.orm import joinedload

log = get_logger(__name__)
DOWNLOAD_DIR = '/data'


class UserRequests(EndpointResource):

    @catch_error()
    def get(self, request_id=None):
        param = self.get_input()
        sort = param.get('sort-by')
        sort_order = param.get('sort-order')
        filter = param.get('filter')
        get_total = param.get('get_total', False)
        if not get_total:
            page, limit = self.get_paging()
            # offset = (current_page - 1) * limit
            log.debug("paging: page {0}, limit {1}".format(page, limit))

        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')
        if get_total:
            counter = repo.count_user_requests(db, user.id)
            return {"total": counter}

        # get user requests list
        # res = repo.get_user_requests(db, user.id, sort_by=sort, sort_order=sort_order, filter=filter)
        data = []
        requests = db.Request.query.filter_by(user_id=user.id) \
            .options(joinedload(db.Request.fileoutput)) \
            .order_by(db.Request.submission_date.desc()) \
            .paginate(page, limit, False).items
        log.debug(requests)
        for r in requests:
            item = {
                'id': r.id,
                'name': r.name,
                'args': json.loads(r.args),
                'submission_date': r.submission_date.isoformat(),
                'status': r.status,
                'task_id': r.task_id
            }
            if r.end_date is not None:
                item['end_date'] = r.end_date.isoformat()
            if r.error_message is not None:
                item['error_message'] = r.error_message
            if r.fileoutput is not None:
                log.debug(r.fileoutput.filename)
                item['fileoutput'] = r.fileoutput.filename
                item['filesize'] = r.fileoutput.size
            data.append(item)

        return self.force_response(
            data, code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    def delete(self, request_id):
        log.debug("delete request %s" % request_id)

        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')
        # check if the request exists
        if not repo.check_request(db, single_request_id=request_id):
            raise RestApiException(
                "The request doesn't exist",
                status_code=hcodes.HTTP_BAD_NOTFOUND)

        # check if the current user is the owner of the request
        if repo.check_owner(db, user.id, single_request_id=request_id):

            # delete request and fileoutput entry from database. Delete fileoutput from user folder
            repo.delete_request_record(db, user, request_id, DOWNLOAD_DIR)

            return self.force_response('Removed request {}'.format(request_id))
        else:
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED)
