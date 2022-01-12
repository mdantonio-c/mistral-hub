from typing import Any

from marshmallow import pre_load
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import Conflict, DatabaseDuplicatedEntry, NotFound
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import Role, User


class Datasets(Schema):
    name = fields.Str()
    id = fields.Str()


# Output Schema
class Attribution(Schema):
    id = fields.Str()
    name = fields.Str()
    descr = fields.Str()
    url = fields.URL()
    datasets = fields.Nested(Datasets(many=True))


class AttributionInput(Schema):
    name = fields.Str(required=True, metadata={"label": "Name"})
    descr = fields.Str(required=True, metadata={"label": "Description"})
    url = fields.URL(required=False, allow_none=True, metadata={"label": "Url"})

    @pre_load
    def null_url(self, data, **kwargs):
        if "url" in data and data["url"] == "":
            data["url"] = None
        return data


class AdminAttributions(EndpointResource):

    labels = ["management"]
    private = True

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.marshal_with(Attribution(many=True), code=200)
    @decorators.endpoint(
        path="/admin/attributions",
        summary="List of attributions",
        responses={
            200: "List of attributions successfully retrieved",
        },
    )
    def get(self, user: User) -> Response:
        db = sqlalchemy.get_instance()
        attributions = []
        for a in db.Attribution.query.all():
            el = {"id": a.id, "name": a.name, "descr": a.descr, "url": a.url}
            el["datasets"] = []
            for d in a.datasets:
                dataset_el = {"name": d.name, "id": d.arkimet_id}
                el["datasets"].append(dataset_el)
            attributions.append(el)

        return self.response(attributions)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(AttributionInput)
    @decorators.endpoint(
        path="/admin/attributions",
        summary="Create a new attribution",
        responses={
            200: "The id of the new attribution is returned",
            409: "Request is invalid due to conflicts",
        },
    )
    def post(self, user: User, **kwargs: Any) -> Response:
        db = sqlalchemy.get_instance()
        try:
            new_attr = db.Attribution(**kwargs)
            db.session.add(new_attr)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))

        return self.response(new_attr.id)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.use_kwargs(AttributionInput)
    @decorators.endpoint(
        path="/admin/attributions/<attribution_id>",
        summary="Modify an attribution",
        responses={
            204: "Attribution successfully modified",
            404: "Attribution not found",
            409: "Request is invalid due to conflicts",
        },
    )
    def put(self, attribution_id: str, user: User, **kwargs: Any) -> Response:

        db = sqlalchemy.get_instance()
        attribution = db.Attribution.query.filter_by(id=attribution_id).first()
        if not attribution:
            raise NotFound("This attribution group cannot be found")

        try:
            for field, value in kwargs.items():
                setattr(attribution, field, value)
            db.session.commit()
        except DatabaseDuplicatedEntry as exc:
            db.session.rollback()
            raise Conflict(str(exc))

        return self.empty_response()

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.endpoint(
        path="/admin/attributions/<attribution_id>",
        summary="Delete an attribution",
        responses={
            204: "Attribution successfully deleted",
            404: "Attribution not found",
        },
    )
    def delete(self, attribution_id: str, user: User) -> Response:
        db = sqlalchemy.get_instance()
        attribution = db.Attribution.query.filter_by(id=attribution_id).first()
        if not attribution:
            raise NotFound("This attribution cannot be found")

        db.session.delete(attribution)
        db.session.commit()

        return self.empty_response()
