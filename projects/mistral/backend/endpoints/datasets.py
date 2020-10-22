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
        {"licenceSpecs": fields.Bool(required=False)}, location="query"
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

        db = self.get_service_instance("sqlalchemy")
        user = self.get_user()
        # get user authorized licence group
        user_license_groups = [lg.name for lg in user.group_license]
        user_datasets_auth = [ds.name for ds in user.datasets]

        for ds in datasets:
            ds_entry = db.Datasets.query.filter_by(name=ds["name"]).first()
            license = db.License.query.filter_by(id=ds_entry.license_id).first()
            group_license = db.GroupLicense.query.filter_by(
                id=license.group_license_id
            ).first()
            # check the licence group authorization for the user
            if group_license.name not in user_license_groups:
                # looking for exception: check the authorized datasets
                if ds["name"] not in user_datasets_auth:
                    # remove the dataset from the response
                    datasets.remove(ds)
                    continue

            if licenceSpecs:
                attribution = db.Attribution.query.filter_by(
                    id=ds_entry.attribution_id
                ).first()
                ds["license_description"] = license.descr
                ds["license_url"] = license.url
                ds["group_license"] = group_license.name
                ds["group_license_description"] = group_license.descr
                ds["attribution_description"] = attribution.descr
                ds["attribution_url"] = attribution.url

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
