# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki

from utilities.logs import get_logger

logger = get_logger(__name__)


class Datasets(EndpointResource):

    # schema_expose = True
    labels = ['dataset']
    GET = {
        '/datasets': {
            'summary': 'Get a dataset.',
            'responses': {
                '200': {
                    'description': 'Dataset successfully retrieved',
                    'schema': {'$ref': '#/definitions/Dataset'},
                },
                '404': {'description': 'Dataset does not exists'},
            },
            'description': 'Return a single dataset filtered by name',
        },
        '/datasets/<dataset_name>': {
            'summary': 'Get a dataset.',
            'responses': {
                '200': {
                    'description': 'Dataset successfully retrieved',
                    'schema': {'$ref': '#/definitions/Dataset'},
                },
                '404': {'description': 'Dataset does not exists'},
            },
            'description': 'Return a single dataset filtered by name',
        },
    }

    @catch_error()
    @authentication.required()
    def get(self, dataset_name=None):
        """ Get all the datasets or a specific one if a name is provided."""
        try:
            datasets = arki.load_datasets()
        except Exception:
            raise SystemError("Error loading the datasets")
        if dataset_name is not None:
            # retrieve dataset by name
            logger.debug("retrieve dataset by name '{}'".format(dataset_name))
            matched_ds = next(
                (ds for ds in datasets if ds.get('id', '') == dataset_name), None
            )
            if not matched_ds:
                raise RestApiException(
                    "Dataset not found for name: {}".format(dataset_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )
            return self.force_response(matched_ds)
        return self.force_response(datasets)
