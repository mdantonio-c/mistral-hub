from typing import Any, Dict, Optional, Union

from marshmallow import pre_load
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import Conflict, DatabaseDuplicatedEntry, NotFound
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import Role, User


class Datasets(Schema):
    name = fields.Str()
    id = fields.Str()


class License_Group(Schema):
    id = fields.Str()
    name = fields.Str()
    descr = fields.Str()


def get_output_schema():
    # as defined in Marshmallow.schema.from_dict
    attributes: Dict[str, Union[fields.Field, type]] = {}

    attributes["id"] = fields.Str()
    attributes["name"] = fields.Str()
    attributes["descr"] = fields.Str()
    attributes["url"] = fields.URL()
    attributes["datasets"] = fields.List(fields.Nested(Datasets))

    attributes["group_license"] = fields.Nested(License_Group)

    schema = Schema.from_dict(attributes, name="LicenseDefinition")
    return schema(many=True)


class LicenseInput(Schema):
    @pre_load
    def null_url(self, data, **kwargs):
        if "url" in data and data["url"] == "":
            data["url"] = None
        return data


# Note that these are callables returning a model, not models!
# They will be executed a runtime
# Can't use request.method because it is not passed at loading time, i.e. the Specs will
# be created with empty request
def getInputSchema(request, is_post):
    db = sqlalchemy.get_instance()

    # as defined in Marshmallow.schema.from_dict
    attributes: Dict[str, Union[fields.Field, type]] = {}

    attributes["name"] = fields.Str(required=is_post)
    attributes["descr"] = fields.Str(required=is_post)
    attributes["url"] = fields.URL(required=False, allow_none=True)

    lgroup_keys = []
    lgroup_labels = []

    for lg in db.GroupLicense.query.all():
        lgroup_keys.append(str(lg.id))
        lgroup_labels.append(f"{lg.name} - {lg.descr}")

    default_group: Optional[Any] = None
    if len(lgroup_keys) == 1:
        default_group = lgroup_keys[0]
    else:
        default_group = None

    attributes["group_license"] = fields.Str(
        required=is_post,
        dump_default=default_group,
        validate=validate.OneOf(choices=lgroup_keys, labels=lgroup_labels),
        metadata={
            "label": "License Group",
            "description": "The license group to which the license belongs",
        },
    )

    return LicenseInput.from_dict(attributes, name="LicenseDefinition")


def getPOSTInputSchema(request):
    return getInputSchema(request, True)


def getPUTInputSchema(request):
    return getInputSchema(request, False)


class AdminLicenses(EndpointResource):

    labels = ["management"]
    private = True

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.marshal_with(get_output_schema(), code=200)
    @decorators.endpoint(
        path="/admin/licenses",
        summary="List of licenses",
        responses={200: "List of licenses successfully retrieved"},
    )
    def get(self, user: User) -> Response:
        db = sqlalchemy.get_instance()
        licenses = []
        for lic in db.License.query.all():
            el = SqlApiDbManager._get_license_response(lic)
            lic_group = {}
            lic_group_el = db.GroupLicense.query.filter_by(
                id=lic.group_license_id
            ).first()
            lic_group["id"] = lic_group_el.id
            lic_group["name"] = lic_group_el.name
            lic_group["descr"] = lic_group_el.descr
            el["group_license"] = lic_group
            el["datasets"] = []
            for d in lic.datasets:
                dataset_el = {"name": d.name, "id": d.arkimet_id}
                el["datasets"].append(dataset_el)
            licenses.append(el)

        return self.response(licenses)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(getPOSTInputSchema)
    @decorators.endpoint(
        path="/admin/licenses",
        summary="Create a new license",
        responses={
            200: "The id of the new license is returned",
            409: "This license already exists",
        },
    )
    def post(self, user: User, **kwargs: Any) -> Response:

        lgroup_id = kwargs.pop("group_license")
        db = sqlalchemy.get_instance()
        try:
            new_lic = db.License(**kwargs)
            db.session.add(new_lic)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))
        lic_group = db.GroupLicense.query.filter_by(id=lgroup_id).first
        if not lic_group:
            db.session.delete(new_lic)
            db.session.commit()
            raise NotFound("This license group")
        new_lic.group_license_id = lgroup_id
        db.session.commit()

        return self.response(new_lic.id)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(getPUTInputSchema)
    @decorators.endpoint(
        path="/admin/licenses/<license_id>",
        summary="Modify a license",
        responses={
            200: "License successfully modified",
            404: "license not found",
            409: "Request is invalid due to conflicts",
        },
    )
    def put(self, license_id: str, user: User, **kwargs: Any) -> Response:
        lgroup_id = kwargs.pop("group_license", None)
        db = sqlalchemy.get_instance()

        license = db.License.query.filter_by(id=license_id).first()
        if not license:
            raise NotFound("This license cannot be found")
        try:
            for field, value in kwargs.items():
                setattr(license, field, value)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))

        if lgroup_id is not None:
            lic_group = db.GroupLicense.query.filter_by(id=lgroup_id).first
            if not lic_group:
                raise NotFound("This license group")

            license.group_license_id = lgroup_id
            db.session.commit()

        return self.empty_response()

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.endpoint(
        path="/admin/licenses/<license_id>",
        summary="Delete a license",
        responses={200: "License successfully deleted", 404: "License not found"},
    )
    def delete(self, license_id: str, user: User) -> Response:

        db = sqlalchemy.get_instance()
        license = db.License.query.filter_by(id=license_id).first()
        if not license:
            raise NotFound("This license cannot be found")

        db.session.delete(license)
        db.session.commit()

        return self.empty_response()
