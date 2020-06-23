import json

from mistral.services.requests_manager import RequestManager as repo
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log
from sqlalchemy.orm import joinedload

DOWNLOAD_DIR = "/data"


class UserRequests(EndpointResource):

    labels = ["requests"]
    GET = {
        "/requests": {
            "summary": "Get requests filtered by uuid.",
            "parameters": [
                {
                    "name": "perpage",
                    "in": "query",
                    "description": "Number of videos returned",
                    "type": "integer",
                },
                {
                    "name": "currentpage",
                    "in": "query",
                    "description": "Page number",
                    "type": "integer",
                },
                {
                    "name": "sort-order",
                    "in": "query",
                    "description": "sort order",
                    "type": "string",
                    "enum": ["asc", "desc"],
                },
                {
                    "name": "sort-by",
                    "in": "query",
                    "description": "params to sort requests",
                    "type": "string",
                },
                {
                    "name": "get_total",
                    "in": "query",
                    "description": "Retrieve total number of requests",
                    "type": "boolean",
                    "default": False,
                },
            ],
            "responses": {
                "200": {
                    "description": "List of requests of an user",
                    "schema": {"$ref": "#/definitions/Requests"},
                },
                "404": {"description": "User has no requests"},
                "401": {
                    "description": "Current user is not allowed to see requests of the user in query"
                },
            },
        }
    }
    DELETE = {
        "/requests/<request_id>": {
            "summary": "Delete a request",
            "responses": {
                "200": {"description": "Request deleted successfully."},
                "404": {"description": "Request does not exist."},
                "401": {
                    "description": "The user is not authorized to delete this request."
                },
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self, request_id=None):
        param = self.get_input()
        # sort = param.get('sort-by')
        # sort_order = param.get('sort-order')
        get_total = param.get("get_total", False)
        if not get_total:
            page, limit = self.get_paging()
            # offset = (current_page - 1) * limit
            log.debug("paging: page {0}, limit {1}", page, limit)

        user = self.get_current_user()

        db = self.get_service_instance("sqlalchemy")
        if get_total:
            counter = repo.count_user_requests(db, user.id)
            return self.response({"total": counter})

        # get user requests list
        # res = repo.get_user_requests(db, user.id, sort_by=sort, sort_order=sort_order)
        data = []
        requests = (
            db.Request.query.filter_by(user_id=user.id)
            .options(joinedload(db.Request.fileoutput))
            .order_by(db.Request.submission_date.desc())
            .paginate(page, limit, False)
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

    @decorators.catch_errors()
    @decorators.auth.required()
    def delete(self, request_id):
        log.debug("delete request {}", request_id)

        user = self.get_current_user()

        db = self.get_service_instance("sqlalchemy", global_instance=False)
        # check if the request exists
        if not repo.check_request(db, request_id=request_id):
            raise RestApiException(
                "The request doesn't exist", status_code=hcodes.HTTP_BAD_NOTFOUND
            )

        # check if the current user is the owner of the request
        if repo.check_owner(db, user.id, request_id=request_id):

            # delete request and fileoutput entry from database. Delete fileoutput from user folder
            repo.delete_request_record(db, user, request_id, DOWNLOAD_DIR)

            return self.response(f"Removed request {request_id}")
        else:
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED,
            )
