import datetime

from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User


class HourlyReport(EndpointResource):

    labels = ["request_hourly_report"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/hourly",
        summary="Get user remaining requests par hour",
        responses={200: "Request hourly report information"},
    )
    # 200: {'schema': {'$ref': '#/definitions/StorageUsage'}}
    def get(self, user: User) -> Response:
        """
        Get user remaining request par hour
        """

        db = sqlalchemy.get_instance()
        data = {}
        if user.request_par_hour:
            now = datetime.datetime.utcnow()
            last_hour = now.replace(minute=0, second=0, microsecond=0)
            request_count = (
                db.session.query(db.Request)
                .filter(db.Request.user_id == user.id)
                .filter(db.Request.submission_date > last_hour)
                .filter(db.Request.submission_date < now)
                .count()
            )
            data["submitted"] = request_count
            data["total"] = user.request_par_hour
            data["remaining"] = user.request_par_hour - request_count
        return self.response(data)
