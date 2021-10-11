from typing import Any, Dict, Optional, Union

from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import Conflict, DatabaseDuplicatedEntry, NotFound
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import Role, User


class License(Schema):
    id = fields.Str()
    name = fields.Str()
    descr = fields.Str()


class Attribution(Schema):
    id = fields.Str()
    name = fields.Str()
    descr = fields.Str()


def get_output_schema():
    # as defined in Marshmallow.schema.from_dict
    attributes: Dict[str, Union[fields.Field, type]] = {}

    attributes["id"] = fields.Str()
    attributes["arkimet_id"] = fields.Str()
    attributes["name"] = fields.Str()
    attributes["description"] = fields.Str()
    attributes["category"] = fields.Str(validate=validate.OneOf(["FOR", "OBS", "RAD"]))
    attributes["fileformat"] = fields.Str()
    attributes["bounding"] = fields.Str()

    attributes["license"] = fields.Nested(License)
    attributes["attribution"] = fields.Nested(Attribution)

    schema = Schema.from_dict(attributes, name="AttributionDefinition")
    return schema(many=True)


# Note that these are callables returning a model, not models!
# They will be executed a runtime
# Can't use request.method because it is not passed at loading time, i.e. the Specs will
# be created with empty request
def getInputSchema(request, is_post):
    db = sqlalchemy.get_instance()

    # as defined in Marshmallow.schema.from_dict
    attributes: Dict[str, Union[fields.Field, type]] = {}

    attributes["arkimet_id"] = fields.Str(
        required=is_post,
        metadata={
            "label": "Arkimet id",
            "description": "the name of dataset directory in Arkimet",
        },
    )
    attributes["name"] = fields.Str(required=is_post)
    attributes["description"] = fields.Str(required=is_post)
    attributes["category"] = fields.Str(
        required=is_post,
        validate=validate.OneOf(["FOR", "OBS", "RAD"]),
    )
    attributes["fileformat"] = fields.Str(required=is_post)
    attributes["bounding"] = fields.Str(required=False)

    license_keys = []
    license_labels = []

    for lic in db.License.query.all():
        license_keys.append(str(lic.id))
        license_labels.append(f"{lic.name} - {lic.descr}")

    default_license: Optional[Any] = None
    if len(license_keys) == 1:
        default_license = license_keys[0]
    else:
        default_license = None

    attributes["license"] = fields.Str(
        required=is_post,
        dump_default=default_license,
        validate=validate.OneOf(choices=license_keys, labels=license_labels),
        metadata={
            "label": "License",
            "description": "The dataset's license",
        },
    )

    attr_keys = []
    attr_labels = []

    for attr in db.Attribution.query.all():
        attr_keys.append(str(attr.id))
        attr_labels.append(f"{attr.name} - {attr.descr}")

    default_attr: Optional[Any] = None
    if len(attr_keys) == 1:
        default_attr = attr_keys[0]
    else:
        default_attr = None

    attributes["attribution"] = fields.Str(
        required=is_post,
        dump_default=default_attr,
        validate=validate.OneOf(choices=attr_keys, labels=attr_labels),
        metadata={
            "label": "Attribution",
            "description": "The dataset's attribution",
        },
    )

    return Schema.from_dict(attributes, name="AttributionDefinition")


def getPOSTInputSchema(request):
    return getInputSchema(request, True)


def getPUTInputSchema(request):
    return getInputSchema(request, False)


class AdminDatasets(EndpointResource):

    labels = ["admin"]
    private = True

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.marshal_with(get_output_schema(), code=200)
    @decorators.endpoint(
        path="/admin/datasets",
        summary="List of datasets",
        responses={200: "List of datasets successfully retrieved"},
    )
    def get(self, user: User) -> Response:
        db = sqlalchemy.get_instance()
        datasets = []
        for d in db.Datasets.query.all():
            el = {
                "id": d.id,
                "arkimet_id": d.arkimet_id,
                "name": d.name,
                "description": d.description,
                "category": d.category.name,
                "fileformat": d.fileformat,
                "bounding": d.bounding,
            }
            license = db.License.query.filter_by(id=d.license_id).first()
            el["license"] = {
                "id": license.id,
                "name": license.name,
                "descr": license.descr,
            }
            attr = db.Attribution.query.filter_by(id=d.attribution_id).first()
            el["attribution"] = {"id": attr.id, "name": attr.name, "descr": attr.descr}
            datasets.append(el)

        return self.response(datasets)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(getPOSTInputSchema)
    @decorators.endpoint(
        path="/admin/datasets",
        summary="Create a new dataset",
        responses={
            200: "The id of the new dataset is returned",
            409: "This dataset already exists",
        },
    )
    def post(self, user: User, **kwargs: Any) -> Response:

        license_id = kwargs.pop("license")
        attribution_id = kwargs.pop("attribution")
        db = sqlalchemy.get_instance()
        try:
            new_dataset = db.Datasets(**kwargs)
            db.session.add(new_dataset)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))
        license = db.License.query.filter_by(id=license_id).first
        attribution = db.Attribution.query.filter_by(id=attribution_id).first
        if not license:
            db.session.delete(new_dataset)
            db.session.commit()
            raise NotFound("This license ")
        if not attribution:
            db.session.delete(new_dataset)
            db.session.commit()
            raise NotFound("This attribution ")
        new_dataset.license_id = license_id
        new_dataset.attribution_id = attribution_id
        db.session.commit()

        return self.response(new_dataset.id)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(getPUTInputSchema)
    @decorators.endpoint(
        path="/admin/datasets/<dataset_id>",
        summary="Modify a dataset",
        responses={
            200: "Dataset successfully modified",
            404: "Dataset not found",
            409: "Request is invalid due to conflicts",
        },
    )
    def put(self, dataset_id: str, user: User, **kwargs: Any) -> Response:
        license_id = kwargs.pop("license", None)
        attribution_id = kwargs.pop("attribution", None)
        db = sqlalchemy.get_instance()

        dataset = db.Datasets.query.filter_by(id=dataset_id).first()
        if not dataset:
            raise NotFound("This dataset cannot be found")
        try:
            for field, value in kwargs.items():
                setattr(dataset, field, value)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))

        if license_id is not None:
            license = db.License.query.filter_by(id=license_id).first
            if not license:
                raise NotFound("This license")

            dataset.license_id = license_id
            db.session.commit()
        if attribution_id is not None:
            attribution = db.Attribution.query.filter_by(id=attribution_id).first
            if not attribution:
                raise NotFound("This attribution")

            dataset.attribution_id = attribution_id
            db.session.commit()

        return self.empty_response()

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.endpoint(
        path="/admin/datasets/<dataset_id>",
        summary="Delete a dataset",
        responses={200: "Dataset successfully deleted", 404: "Dataset not found"},
    )
    def delete(self, dataset_id: str, user: User) -> Response:

        db = sqlalchemy.get_instance()
        dataset = db.Datasets.query.filter_by(id=dataset_id).first()
        if not dataset:
            raise NotFound("This dataset cannot be found")

        db.session.delete(dataset)
        db.session.commit()

        return self.empty_response()
