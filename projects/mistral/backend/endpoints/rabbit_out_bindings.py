from typing import Any, Dict

from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import rabbitmq, sqlalchemy
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource
from restapi.services.authentication import Role
from restapi.utilities.logs import log

EXCHANGE = "obs-data-output"


class Bindings(Schema):
    exchange = fields.Str()
    bindings = fields.Dict(fields.Str, fields.List(fields.Str))


class OutputBindings(EndpointResource):

    labels = ["admin"]

    @staticmethod
    def get_queue(user):
        # Naming convention?
        return f"{user}"

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.marshal_with(Bindings, code=200)
    @decorators.endpoint(
        path="/outbindings",
        summary="List of bindings between networks and user data queues",
        responses={"200": "List of bindings is returned"},
    )
    def get(self):

        db = sqlalchemy.get_instance()
        rabbit = rabbitmq.get_instance(verification=1)

        if not rabbit.exchange_exists(EXCHANGE):
            rabbit.create_exchange(EXCHANGE)

        data: Dict[str, Any] = {"exchange": EXCHANGE, "bindings": {}}

        datasets = SqlApiDbManager.get_datasets(db, user=None)
        for d in datasets:
            data["bindings"].setdefault(d.get("id"), [])

        bindings = rabbit.get_bindings(EXCHANGE)
        if bindings:
            for row in bindings:
                network = row["routing_key"]
                queue = row["queue"]

                if network not in data["bindings"]:
                    log.warning(
                        "Unknown network {} associated to {}", network, EXCHANGE
                    )
                    continue

                data["bindings"][network].append(queue)

        return self.response(data)

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.endpoint(
        path="/outbindings/<user>/<network>",
        summary="Allow a user to receive a network...",
        responses={"200": "User allowed"},
    )
    def post(self, user, network):

        rabbit = rabbitmq.get_instance()

        queue = self.get_queue(user)

        if not rabbit.exchange_exists(EXCHANGE):
            rabbit.create_exchange(EXCHANGE)

        if not rabbit.queue_exists(queue):
            rabbit.create_queue(queue)

        if rabbit.channel:
            rabbit.channel.queue_bind(queue, EXCHANGE, routing_key=network)

        return self.empty_response()

    @decorators.auth.require_all(Role.ADMIN)
    @decorators.endpoint(
        path="/outbindings/<user>/<network>",
        summary="Disallow a user from receiving a network",
        responses={"200": "User disallowed"},
    )
    def delete(self, user, network):

        rabbit = rabbitmq.get_instance()

        queue = self.get_queue(user)

        if rabbit.exchange_exists(EXCHANGE) and rabbit.queue_exists(queue):

            if rabbit.channel:
                rabbit.channel.queue_unbind(queue, EXCHANGE, routing_key=network)

        return self.empty_response()
