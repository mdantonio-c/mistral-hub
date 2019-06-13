# -*- coding: utf-8 -*-

import os
from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger

logger = get_logger(__name__)


class Datasets(EndpointResource):

    @catch_error()
    def get(self, dataset_name=None):
        """ Get all the datasets or a specific one if a name is provided."""
        data = None
        if dataset_name is not None:
            try:
                # TODO retrieve dataset by name
                raise LookupError()
            except LookupError:
                raise RestApiException(
                    "Dataset not found for name: {}".format(dataset_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)
        else:
            # TODO retrieve all the datasets
            data = []
        return self.force_response(data)
