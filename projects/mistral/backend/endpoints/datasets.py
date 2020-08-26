from mistral.services.arkimet import BeArkimet as arki
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.models import fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class Datasets(EndpointResource):

    labels = ["dataset"]

    @decorators.auth.require()
    @decorators.use_kwargs(
        {"licenceSpecs": fields.Bool(required=False)}, locations=["query"]
    )
    @decorators.endpoint(
        path="/datasets",
        summary="Get a dataset.",
        description="Return a single dataset filtered by name",
        responses={
            200: "Dataset successfully retrieved",
            404: "Dataset does not exists",
        },
    )
    @decorators.endpoint(
        path="/datasets/<dataset_name>",
        summary="Get a dataset.",
        description="Return a single dataset filtered by name",
        responses={
            200: "Dataset successfully retrieved",
            404: "Dataset does not exists",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Dataset'}}
    def get(self, dataset_name=None, licenceSpecs=False):
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
        if licenceSpecs:
            db = self.get_service_instance("sqlalchemy")
            for ds in datasets:
                if "license" in ds:
                    license_name = ds["license"]
                    license = db.License.query.filter_by(name=license_name).first()
                    if license:
                        ds["license_description"] = license.descr
                        ds["license_url"] = license.url
                        group_license_id = license.group_license_id
                        gp_license = db.GroupLicense.query.filter_by(
                            id=group_license_id
                        ).first()
                        ds["group_license"] = gp_license.name
                        ds["group_license_description"] = gp_license.descr

                if "attribution" in ds:
                    attribution_name = ds["attribution"]
                    attribution = db.Attribution.query.filter_by(
                        name=attribution_name
                    ).first()
                    if attribution:
                        ds["attribution_description"] = attribution.descr
                        ds["attribution_url"] = attribution.url

        return self.response(datasets)
