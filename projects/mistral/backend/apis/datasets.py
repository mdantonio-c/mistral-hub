# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki

logger = get_logger(__name__)


class Datasets(EndpointResource):

    @catch_error()
    def get(self, dataset_name=None):
        """ Get all the datasets or a specific one if a name is provided."""
        datasets = arki.load_datasets()
        if dataset_name is not None:
            # retrieve dataset by name
            logger.debug("retrive datset by name '{}'".format(dataset_name))
            matched_ds = next((ds for ds in datasets if ds.get('id', '') == dataset_name), None)
            if not matched_ds:
                raise RestApiException(
                    "Dataset not found for name: {}".format(dataset_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)
            return self.force_response(matched_ds)
        return self.force_response(datasets)
