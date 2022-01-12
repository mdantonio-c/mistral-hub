from typing import Any

from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import Conflict, DatabaseDuplicatedEntry, NotFound
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import Role, User


class License(Schema):
    id = fields.Str()
    name = fields.String()
    descr = fields.Str()
    url = fields.URL()


# Output Schema
class LicGroup(Schema):
    id = fields.Str()
    name = fields.Str()
    descr = fields.Str()
    is_public = fields.Bool()
    dballe_dsn = fields.Str()
    license = fields.Nested(License(many=True))


class LicGroupInput(Schema):
    name = fields.Str(required=True, metadata={"label": "Name"})
    descr = fields.Str(required=True, metadata={"label": "Description"})
    is_public = fields.Bool(
        required=True, metadata={"label": " Is an open license group"}
    )
    dballe_dsn = fields.Str(
        required=False,
        metadata={
            "label": "DBAll-e DSN name",
            "description": " Required if the License Group includes observations datasets",
        },
    )


class AdminLicGroups(EndpointResource):

    labels = ["management"]
    private = True

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.marshal_with(LicGroup(many=True), code=200)
    @decorators.endpoint(
        path="/admin/licensegroups",
        summary="List of license groups",
        responses={
            200: "List of license groups successfully retrieved",
        },
    )
    def get(self, user: User) -> Response:
        db = sqlalchemy.get_instance()
        lic_groups = []
        for gl in db.GroupLicense.query.all():
            el = SqlApiDbManager._get_license_group_response(gl)
            el["license"] = []
            for lic in gl.license:
                lic_el = SqlApiDbManager._get_license_response(lic)
                el["license"].append(lic_el)
            lic_groups.append(el)

        return self.response(lic_groups)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(LicGroupInput)
    @decorators.endpoint(
        path="/admin/licensegroups",
        summary="Create a new license group",
        responses={
            200: "The id of the new license group is returned",
            409: "Request is invalid due to conflicts",
        },
    )
    def post(self, user: User, **kwargs: Any) -> Response:
        db = sqlalchemy.get_instance()
        try:
            new_gl = db.GroupLicense(**kwargs)
            db.session.add(new_gl)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))

        return self.response(new_gl.id)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(LicGroupInput)
    @decorators.endpoint(
        path="/admin/licensegroups/<lic_group_id>",
        summary="Modify a license group",
        responses={
            204: "License group successfully modified",
            404: "group not found",
            409: "Request is invalid due to conflicts",
        },
    )
    def put(self, lic_group_id: str, user: User, **kwargs: Any) -> Response:

        db = sqlalchemy.get_instance()
        lgroup = db.GroupLicense.query.filter_by(id=lic_group_id).first()
        if not lgroup:
            raise NotFound("This license group cannot be found")

        try:
            for field, value in kwargs.items():
                setattr(lgroup, field, value)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))

        return self.empty_response()

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.endpoint(
        path="/admin/licensegroups/<lic_group_id>",
        summary="Delete a license group",
        responses={
            204: "License group successfully deleted",
            404: "License group not found",
        },
    )
    def delete(self, lic_group_id: str, user: User) -> Response:
        db = sqlalchemy.get_instance()
        lgroup = db.GroupLicense.query.filter_by(id=lic_group_id).first()
        if not lgroup:
            raise NotFound("This license group cannot be found")

        db.session.delete(lgroup)
        db.session.commit()

        return self.empty_response()
