from mistral.endpoints.schemas import AccessKeySchema
from mistral.models.sqlalchemy import AccessKey
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import NotFound
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log


class AccessKeyResource(EndpointResource):
    @decorators.auth.require()
    @decorators.marshal_with(AccessKeySchema, code=200)
    @decorators.endpoint(
        path="/access-key",
        summary="Create or regenerate an access key",
        responses={200: "User access key created"},
    )
    def post(self, user: User) -> str:
        log.debug("Request for creating access-key for user: %s", user.uuid)
        existing = user.access_key

        db = sqlalchemy.get_instance()
        if existing:
            # revoke the old one
            log.debug(f"User access key already exists for user: {user.uuid}")
            log.info(f"Revoke {existing}")
            db.session.delete(existing)
            self.log_event(self.events.delete, existing)
            db.session.flush()

        # generate a new access key with a lifetime of 24 hours
        new_key = AccessKey.generate(user_id=user.id, lifetime_seconds=86400)
        log.debug(f"New access key for user: {new_key.key}")
        db.session.add(new_key)
        db.session.commit()

        self.log_event(self.events.create, new_key)
        return self.response(new_key)

    @decorators.auth.require()
    @decorators.marshal_with(AccessKeySchema, code=200)
    @decorators.endpoint(
        path="/access-key",
        summary="Get an access key",
        responses={200: "User access key retrieved", 404: "User access key not found"},
    )
    def get(self, user: User):
        key = user.access_key
        if not key:
            raise NotFound("GET: No access key found", is_warning=True)
        return self.response(key)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/access-key",
        summary="Revoke an access key",
        responses={204: "User access key revoked", 404: "No access key to revoke"},
    )
    def delete(self, user: User) -> Response:
        db = sqlalchemy.get_instance()
        key = user.access_key
        if not key:
            raise NotFound("REVOKE: No access key found", is_warning=True)
        db.session.delete(key)
        db.session.commit()
        self.log_event(self.events.delete, key)

        return self.empty_response()
