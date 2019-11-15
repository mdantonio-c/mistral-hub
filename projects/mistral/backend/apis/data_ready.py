# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi import decorators as decorate
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes

from utilities.logs import get_logger

log = get_logger(__name__)


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
        log.info("Cluster = %s", data.get("Cluster"))
        log.info("Model = %s", data.get("Model"))
        log.info("rundate = %s", data.get("rundate"))

        return self.force_response("1", code=hcodes.HTTP_OK_ACCEPTED)
