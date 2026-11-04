from mistral.tools import perf
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import NotFound
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User


class PerfRequest(EndpointResource):
    # registered only when the instrumentation flag is on (issue 852, D-02)
    depends_on = ["PERF_INSTRUMENTATION"]
    labels = ["perf"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/perf/requests/<request_id>",
        summary="Get the performance record of an observed-data extraction request.",
        responses={
            200: "Performance record (api and/or task side)",
            404: "Record not found or not accessible",
        },
    )
    def get(self, request_id: str, user: User) -> Response:
        if not request_id.isdigit():
            raise NotFound("Performance record not found")
        db = sqlalchemy.get_instance()
        request = db.Request.query.get(int(request_id))
        if request is None or not perf.can_read(
            user.id, request.user_id, self.auth.is_admin(user)
        ):
            raise NotFound("Performance record not found")
        record = perf.read_record(request.id)
        if record is None:
            raise NotFound("Performance record not found")
        return self.response(record)
