from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.exceptions import NotFound, ServiceUnavailable
from restapi.models import fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log


class Datasets(EndpointResource):

    labels = ["dataset"]

    @decorators.auth.require()
    @decorators.use_kwargs(
        {"licenceSpecs": fields.Bool(required=False)}, location="query"
    )
    @decorators.endpoint(
        path="/datasets",
        summary="Get datasets",
        description="Return all available datasets",
        responses={
            200: "Datasets successfully retrieved",
        },
    )
    @decorators.endpoint(
        path="/datasets/<dataset_name>",
        summary="Get a dataset filtered by name",
        description="Return a single dataset filtered by name",
        responses={
            200: "Dataset successfully retrieved",
            404: "Dataset does not exists",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Dataset'}}
    def get(self, dataset_name=None, licenceSpecs=False):
        """ Get all the datasets or a specific one if a name is provided."""
        db = self.get_service_instance("sqlalchemy")
        user = self.get_user()
        try:
            datasets = SqlApiDbManager.get_datasets(
                db, user, licenceSpecs, authSpecs=True
            )
        except Exception as e:
            log.error(e)
            raise ServiceUnavailable("Error loading the datasets")

        if dataset_name is not None:
            # retrieve dataset by name
            log.debug("retrieve dataset by name '{}'", dataset_name)
            matched_ds = next(
                (ds for ds in datasets if ds.get("id", "") == dataset_name), None
            )
            if not matched_ds:
                raise NotFound(f"Dataset not found for name: {dataset_name}")
            return self.response(matched_ds)

        return self.response(datasets)
