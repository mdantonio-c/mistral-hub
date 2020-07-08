import os
from datetime import datetime

from flask import send_file
from flask_apispec import use_kwargs
from marshmallow import fields, validate
from restapi import decorators
from restapi.exceptions import RestApiException
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
    _GET = {
        "/tiles": {
            "summary": "Get the last available tiled map set as a reference time.",
            "responses": {
                "200": {"description": "Tiled map successfully retrieved"},
                "400": {"description": "Invalid parameters"},
                "404": {"description": "Tiled map does not exists"},
            },
        }
    }

    def __init__(self):
        super().__init__()
        self.base_path = None

    @decorators.catch_errors()
    @use_kwargs(
        {
            "res": fields.Str(validate=validate.OneOf(RESOLUTIONS), required=True),
            "run": fields.Str(validate=validate.OneOf(RUNS))
        },
        locations=["query"],
    )
    def get(self, res, run=None):
        ready_file = None
        # check the available platform by looking first at the default one
        log.debug(f"PLATFORMS: {PLATFORMS}")
        log.debug(f"DEFAULT PLATFORM: {DEFAULT_PLATFORM}")
        platforms_to_be_check = [DEFAULT_PLATFORM] + list(set(PLATFORMS) - set([DEFAULT_PLATFORM]))
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
            log.debug(f"No run param provided: look for the last run available")
            # here now is a UTC time
            now = datetime.utcnow()
            log.debug(f"now = {now}", now)
            # if it is past 12 UTC, check the availability of run 12, otherwise get run 00
            todayAt12 = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
            log.debug(f"today at 12 = {todayAt12}", todayAt12)
            # use default run in case run at 12 is not available
            run = "00"
            if now > todayAt12:
                log.debug("12:00 o'clock has passed")
                try:
                    ready_file = self._get_ready_file(platform, area, "12", res)
                except FileNotFoundError as e:
                    log.debug(f"Run at 12:00 is not yet available")

        if not ready_file:
            try:
                ready_file = self._get_ready_file(platform, area, run, res)
            except FileNotFoundError as e:
                raise RestApiException(
                    str(e), status_code=hcodes.HTTP_BAD_NOTFOUND
                )

        data = {"reftime": ready_file[:10], "platform": platform}
        return self.response(data)

    def _get_ready_file(self, platform, area, run, res):
        # e.g. Tiles-00-lm2.2.web
        self.base_path = os.path.join(
            MEDIA_ROOT, platform, "PROD", f"Tiles-{run}-{res}.web"
        )
        ready_path = os.path.join(self.base_path, area)
        log.debug(f"ready_path: {ready_path}")

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
        else:
            raise FileNotFoundError("no .READY files found")
        return ready_files[0]
