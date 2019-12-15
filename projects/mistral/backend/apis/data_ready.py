# -*- coding: utf-8 -*-

from mistral.services.requests_manager import RequestManager
from restapi.rest.definition import EndpointResource
from restapi import decorators as decorate
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class DataReady(EndpointResource):

    POST = {
        "/data/ready": {
            "summary": "Notify that a dataset is ready",
            "responses": {"202": {"description": "Notification received"}},
        }
    }

    @decorate.catch_error()
    @authentication.required()
    def post(self):

        data = self.get_input()
        log.info("Cluster = {}", data.get("Cluster"))
        log.info("Model = {}", data.get("Model"))
        log.info("rundate = {}", data.get("rundate"))

        db = self.get_service_instance('sqlalchemy')
        # Create as a method in RequestManager -> get_all_schedule_requests
        # scheduled_requests = []
        schedules_list = db.Schedule.query.all()
        for row in schedules_list:
            r = RequestManager._get_schedule_response(row)
            # scheduled_requests.append(r)

            # se tra gli args manca run significa che chiede sia 00 sia 12
            # reftime == 00 || reftime == 12,
            # quindi modificare reftime ricevuto per impostare la corsa successiva
            # == rundate at 00 || rundate at 12
            log.critical(r)

        # log.critical(scheduled_requests)

        return self.force_response("1", code=hcodes.HTTP_OK_ACCEPTED)
