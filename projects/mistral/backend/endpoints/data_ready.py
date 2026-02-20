from datetime import datetime

from restapi import decorators
from restapi.config import get_backend_url
from restapi.connectors import celery, smtp
from restapi.env import Env
from restapi.models import fields, validate
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log

SUPPORTED_PLATFORMS = ["g100", "galileo", "meucci", "leonardo"]


class DataReady(EndpointResource):
    private = True

    @decorators.auth.require_any("operational")
    @decorators.use_kwargs(
        {
            "cluster": fields.String(
                required=True,
                data_key="Cluster",
                validate=validate.OneOf(SUPPORTED_PLATFORMS),
            ),
            "model": fields.String(required=True, data_key="Model"),
            "rundate": fields.DateTime(required=True, format="%Y%m%d%H"),
        }
    )
    @decorators.endpoint(
        path="/data/ready",
        summary="Notify that a dataset is ready",
        responses={202: "Notification received"},
    )
    def post(self, cluster: str, model: str, rundate: datetime, user: User) -> Response:

        cluster = cluster.lower()
        log.info("Cluster = {}\tModel = {}\trundate = {}", cluster, model, rundate)

        # check which cluster is currently exported on filesystem
        if cluster == "g100" or cluster == "galileo" or cluster == "meucci":
            exported_platform = Env.get("PLATFORM", "G100").lower()

            if exported_platform != cluster:
                log.debug(
                    "The endpoint was called by {} while the exported platform is {}",
                    cluster,
                    exported_platform,
                )
                return self.response("1", code=202)

        try:
            c = celery.get_instance()
            c.celery_app.send_task(
                "launch_all_on_data_ready_extractions",
                args=(
                    model,
                    rundate,
                ),
                countdown=1,
                queue="operational_forecast",
                routing_key="operational_forecast",
            )

            log.info(
                "The 'launch_all_on_data_ready_extractions' task was successfully submitted."
            )
        except Exception as error:
            log.error(
                f"The submission of the 'launch_all_on_data_ready_extractions' task failed with error: {error}"
            )
            smtp_client = smtp.get_instance()
            host = get_backend_url()
            smtp_client.send(
                f"The submission of the 'launch_all_on_data_ready_extractions' task failed with error: {error}.",
                f"Alert from {host} : On data ready schedules launcher error",
                to_address="mistral-support@cineca.it",
            )
            raise SystemError(
                "Unable to submit the 'launch_all_on_data_ready_extractions' task."
            )

        return self.response("1", code=202)
