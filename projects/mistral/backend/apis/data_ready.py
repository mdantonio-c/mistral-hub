# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi import decorators as decorate
# from restapi.protocols.bearer import authentication
from utilities import htmlcodes as hcodes


class DataReady(EndpointResource):

    POST = {
        "/data/ready": {
            "summary": "Notify that a dataset is ready",
            "responses": {
                "202": {"description": "Notification received"}
            },
        }
    }

    @decorate.catch_error()
    # @authentication.required()
    def post(self):

        return self.force_response("1", code=hcodes.HTTP_OK_ACCEPTED)
