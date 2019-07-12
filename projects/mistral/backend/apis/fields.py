# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from flask import Response
# from flask import json

logger = get_logger(__name__)


class Fields(EndpointResource):

    @catch_error()
    def get(self):
        """ Get all fields for given datasets"""
        params = self.get_input()
        ds = params.get('datasets')
        datasets = ds.split(',') if ds is not None else []

        # check for existing dataset(s)
        for ds_name in datasets:
            found = next((ds for ds in arki.load_datasets() if ds.get('id', '') == ds_name), None)
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)

        query = params.get('q')
        summary = arki.load_summary(datasets, query)
        return self.force_response(summary)
        # js = json.dumps(summary)
        # return Response(js, status=200, mimetype='application/json')
