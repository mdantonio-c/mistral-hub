import json

from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.requests_manager import RequestManager as repo
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log
from sqlalchemy.orm import joinedload


class UserRequests(EndpointResource):

    labels = ["requests"]

    @decorators.auth.require()
    @decorators.get_pagination
    @decorators.endpoint(
        path="/requests",
        summary="Get requests filtered by uuid.",
        responses={200: "List of requests of an user", 404: "User has no requests"},
    )
    # 200: {'schema': {'$ref': '#/definitions/Requests'}}
    def get(
        self, get_total, page, size, sort_order, sort_by, input_filter, request_id=None,
    ):

        user = self.get_user()

        db = self.get_service_instance("sqlalchemy")
        if get_total:
            counter = repo.count_user_requests(db, user.id)
            return self.response({"total": counter})

        # offset = (page - 1) * size

        log.debug("paging: page {0}, size {1}", page, size)

        # get user requests list
        # res = repo.get_user_requests(db, user.id, sort_by=sort_by, sort_order=sort_order)
        data = []
        requests = (
            db.Request.query.filter_by(user_id=user.id)
            .options(joinedload(db.Request.fileoutput))
            .order_by(db.Request.submission_date.desc())
            .paginate(page, size, False)
            .items
        )
        log.debug(requests)
        for r in requests:
            item = {
                "id": r.id,
                "name": r.name,
                "args": json.loads(r.args),
                "submission_date": r.submission_date.isoformat(),
                "status": r.status,
                "task_id": r.task_id,
            }
            if r.schedule_id is not None:
                item["schedule_id"] = r.schedule_id
            if r.end_date is not None:
                item["end_date"] = r.end_date.isoformat()
            if r.error_message is not None:
                item["error_message"] = r.error_message
            if r.fileoutput is not None:
                log.debug(r.fileoutput.filename)
                item["fileoutput"] = r.fileoutput.filename
                item["filesize"] = r.fileoutput.size
            data.append(item)

        return self.response(data, code=hcodes.HTTP_OK_BASIC)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/requests/<request_id>",
        summary="Delete a request",
        responses={
            200: "Request deleted successfully.",
            404: "Request does not exist.",
        },
    )
    def delete(self, request_id):
        log.debug("delete request {}", request_id)

        user = self.get_user()

        db = self.get_service_instance("sqlalchemy")
        # check if the request exists
        if not repo.check_request(db, request_id=request_id):
            raise RestApiException(
                "The request doesn't exist", status_code=hcodes.HTTP_BAD_NOTFOUND
            )

        # check if the current user is the owner of the request
        if repo.check_owner(db, user.id, request_id=request_id):

            # delete request and fileoutput entry from database.
            # Delete fileoutput from user folder
            repo.delete_request_record(db, user, request_id, DOWNLOAD_DIR)

            return self.response(f"Removed request {request_id}")
        else:
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED,
            )
