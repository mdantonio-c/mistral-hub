from mistral.services.arkimet import BeArkimet as arki
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class Datasets(EndpointResource):

    labels = ["dataset"]
    _GET = {
        "/datasets": {
            "summary": "Get a dataset.",
            "responses": {
                "200": {
                    "description": "Dataset successfully retrieved",
                    "schema": {"$ref": "#/definitions/Dataset"},
                },
                "404": {"description": "Dataset does not exists"},
            },
            "description": "Return a single dataset filtered by name",
        },
        "/datasets/<dataset_name>": {
            "summary": "Get a dataset.",
            "responses": {
                "200": {
                    "description": "Dataset successfully retrieved",
                    "schema": {"$ref": "#/definitions/Dataset"},
                },
                "404": {"description": "Dataset does not exists"},
            },
            "description": "Return a single dataset filtered by name",
        },
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self, dataset_name=None):
        """ Get all the datasets or a specific one if a name is provided."""
        try:
            datasets = arki.load_datasets()
        except Exception as e:
            log.error(e)
            raise RestApiException(
                "Error loading the datasets", status_code=hcodes.HTTP_SERVER_ERROR
            )
        if dataset_name is not None:
            # retrieve dataset by name
            log.debug("retrieve dataset by name '{}'", dataset_name)
            matched_ds = next(
                (ds for ds in datasets if ds.get("id", "") == dataset_name), None
            )
            if not matched_ds:
                raise RestApiException(
                    f"Dataset not found for name: {dataset_name}",
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )
            return self.response(matched_ds)
        return self.response(datasets)
