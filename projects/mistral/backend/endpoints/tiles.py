import os
from datetime import datetime

from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.models import fields, validate
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

MEDIA_ROOT = "/meteo/"

RUNS = ["00", "12"]
RESOLUTIONS = ["lm2.2", "lm5"]
PLATFORMS = ["GALILEO", "MEUCCI"]
DEFAULT_PLATFORM = os.environ.get("PLATFORM", "GALILEO")


def check_platform_availability(platform):
    return os.access(os.path.join(MEDIA_ROOT, platform), os.X_OK)


class TilesEndpoint(EndpointResource):
    labels = ["tiled map ready"]

    def __init__(self):
        super().__init__()
        self.base_path = None

    @decorators.use_kwargs(
        {
            "res": fields.Str(validate=validate.OneOf(RESOLUTIONS), required=True),
            "run": fields.Str(validate=validate.OneOf(RUNS)),
        },
        location="query",
    )
    @decorators.endpoint(
        path="/tiles",
        summary="Get the last available tiled map set as a reference time.",
        responses={
            200: "Tiled map successfully retrieved",
            400: "Invalid parameters",
            404: "Tiled map does not exists",
        },
    )
    def get(self, res, run=None):
        ready_file = None
        # check the available platform by looking first at the default one
        log.debug(f"PLATFORMS: {PLATFORMS}")
        log.debug(f"DEFAULT PLATFORM: {DEFAULT_PLATFORM}")
        platforms_to_be_check = [DEFAULT_PLATFORM] + list(
            set(PLATFORMS) - {DEFAULT_PLATFORM}
        )
        log.debug(f"platform to be check {platforms_to_be_check}")
        for p in platforms_to_be_check:
            if not check_platform_availability(p):
                log.warning(f"platform {p} not available")
                continue
            else:
                platform = p
                break
        else:
            raise RestApiException(
                "Map service is currently unavailable", hcodes.HTTP_SERVICE_UNAVAILABLE
            )

        area = "Italia" if res == "lm2.2" else "Area_Mediterranea"

        # check for run param: if not provided get the "last" run available
        if not run:
            log.debug("No run param provided: look for the last run available")
            ready_files = [
                x
                for x in (
                    self._get_ready_file(platform, area, r, res) for r in ["00", "12"]
                )
                if x is not None
            ]
            try:
                ready_file = max(ready_files)
            except ValueError:
                log.warning("No Run is available: .READY file not found")
        else:
            ready_file = self._get_ready_file(platform, area, run, res)
            if not ready_file:
                raise RestApiException(
                    f"No .READY file found for RUN at {run}:00",
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )

        data = {"reftime": ready_file[:10], "platform": platform}
        return self.response(data)

    def _get_ready_file(self, platform, area, run, res):
        # e.g. Tiles-00-lm2.2.web
        self.base_path = os.path.join(
            MEDIA_ROOT, platform, "PROD", f"Tiles-{run}-{res}.web"
        )
        ready_path = os.path.join(self.base_path, area)
        log.debug("ready_path: {}", ready_path)

        ready_files = []
        if os.path.exists(ready_path):
            ready_files = [
                f
                for f in os.listdir(ready_path)
                if os.path.isfile(os.path.join(ready_path, f)) and ".READY" in f
            ]

        # Check if .READY file exists (if not, images are not ready yet)
        log.debug(f"Looking for .READY files in: {ready_path}")
        if len(ready_files) > 0:
            log.debug(f".READY files found: {ready_files}")
            return ready_files[0]
