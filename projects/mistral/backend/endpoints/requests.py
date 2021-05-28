from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.endpoints.schemas import TotalSchema
from restapi.exceptions import NotFound, ServerError, Unauthorized
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log
from sqlalchemy.orm import joinedload


class UserRequests(EndpointResource):

    labels = ["requests"]

    @decorators.auth.require()
    @decorators.get_pagination
    @decorators.marshal_with(TotalSchema, code=206)
    @decorators.endpoint(
        path="/requests",
        summary="Get requests filtered by uuid.",
        responses={
            200: "List of requests of an user",
            206: "Total number of elements is returned",
            404: "User has no requests",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Requests'}}
    def get(
        self, get_total, page, size, sort_order, sort_by, input_filter, request_id=None
    ):

        user = self.get_user()
        # Can't happen since auth is required
        if not user:  # pragma: no cover
            raise ServerError("User misconfiguration")

        db = sqlalchemy.get_instance()
        if get_total:
            counter = repo.count_user_requests(db, user.id)
            return self.pagination_total(counter)

        # offset = (page - 1) * size

        log.debug("paging: page {0}, size {1}", page, size)

        # get user requests list
        # res = repo.get_user_requests(
        #     db, user.id, sort_by=sort_by, sort_order=sort_order
        # )
        data = []
        requests = (
            db.Request.query.filter_by(user_id=user.id,archived=False)
            .options(joinedload(db.Request.fileoutput))
            .order_by(db.Request.submission_date.desc())
            .paginate(page, size, False)
            .items
        )
        # log.debug(requests)
        for r in requests:
            args = r.args
            # filter the dictionary None elements
            # and rename the dataset key to make it compatible with the
            # input data extraction request
            filtered_args = {k: v for k, v in args.items() if v is not None}
            filtered_args["dataset_names"] = filtered_args.pop("datasets")
            item = {
                "id": r.id,
                "name": r.name,
                "args": filtered_args,
                "submission_date": r.submission_date.isoformat(),
                "status": r.status,
                "task_id": r.task_id,
                "opendata": r.opendata,
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

        return self.response(data)

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
        # Can't happen since auth is required
        if not user:  # pragma: no cover
            raise ServerError("User misconfiguration")

        db = sqlalchemy.get_instance()
        # check if the request exists
        if not repo.check_request(db, request_id=request_id):
            raise NotFound("The request doesn't exist")

        # check if the current user is the owner of the request
        if repo.check_owner(db, user.id, request_id=request_id):

            # delete request and fileoutput entry from database.
            # Delete fileoutput from user folder
            repo.delete_request_record(db, user, request_id)

            return self.response(f"Removed request {request_id}")
        else:
            # should be Forbidden...
            raise Unauthorized("This request doesn't come from the request's owner")


class CloneUserRequests(EndpointResource):
    @decorators.auth.require()
    @decorators.endpoint(
        path="/requests/<request_id>/clone",
        summary="Get a request to be cloned.",
        responses={
            200: "A user request query model",
            404: "No user request found",
        },
    )
    def get(self, request_id):
        log.debug(f"Request for cloning query - ID<{request_id}>")

        user = self.get_user()
        # Can't happen since auth is required
        if not user:  # pragma: no cover
            raise ServerError("User misconfiguration")

        db = sqlalchemy.get_instance()
        # check if the request exists
        if not repo.check_request(db, request_id=request_id):
            raise NotFound(f"User request <{request_id}> not found")
        # check if the current user is the owner of the request
        if not repo.check_owner(db, user.id, request_id=request_id):
            raise Unauthorized("This request doesn't come from the request's owner")

        user_request = repo.get_user_request_by_id(db, request_id)
        args = user_request.args
        # setup request query model
        args_datasets = args.get("datasets")
        args["datasets"] = [
            ds
            for ds in repo.get_datasets(db, user, licenceSpecs=True)
            if ds["id"] in args_datasets
        ]
        return self.response(args)
