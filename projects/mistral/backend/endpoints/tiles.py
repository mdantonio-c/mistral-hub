import os

from restapi import decorators
from restapi.exceptions import NotFound
from restapi.models import fields, validate
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log

MEDIA_ROOT = "/meteo/"

RUNS = ["00", "12"]
DATASETS = {
    "lm5": {
        "area": "Area_Mediterranea",
        "start_offset": 0,
        "end_offset": 72,
        "step": 1,
        "boundaries": {
            "SW": (
                25.8,
                -30.9,
            ),
            "NE": (
                55.5,
                47.0,
            ),
        },
    },
    "lm2.2": {
        "area": "Italia",
        "start_offset": 0,
        "end_offset": 48,
        "step": 1,
        "boundaries": {
            "SW": (
                34.5,
                5.0,
            ),
            "NE": (
                48.0,
                21.2,
            ),
        },
    },
    "iff": {
        "area": "Italia",
        "start_offset": 6,
        "end_offset": 48,
        "step": 3,
        "boundaries": {
            "SW": (
                34.5,
                5.0,
            ),
            "NE": (
                48.0,
                21.2,
            ),
        },
    },
}
# PLATFORMS = ["GALILEO", "MEUCCI"]
# DEFAULT_PLATFORM = os.environ.get("PLATFORM", "GALILEO")


def check_platform_availability(platform):
    return os.access(os.path.join(MEDIA_ROOT, platform), os.X_OK)


class TilesEndpoint(EndpointResource):
    labels = ["tiled map ready"]

    def __init__(self):
        super().__init__()
        self.base_path = None

    @decorators.use_kwargs(
        {
            "dataset": fields.Str(
                required=True, validate=validate.OneOf(DATASETS.keys())
            ),
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
    def get(self, dataset, run=None):
        ready_file = None
        info = DATASETS.get(dataset)
        area = info.get("area")

        # check for run param: if not provided get the "last" run available
        if not run:
            log.debug("No run param provided: look for the last run available")
            ready_files = [
                x
                for x in (self._get_ready_file(area, r, dataset) for r in ["00", "12"])
                if x is not None
            ]
            try:
                ready_file = max(ready_files)
            except ValueError:
                log.warning("No Run is available: .READY file not found")
        else:
            ready_file = self._get_ready_file(area, run, dataset)
        ready_file = "..."

        if not ready_file:
            raise NotFound("No .READY file found")

        info["dataset"] = dataset
        info["reftime"] = ready_file[:10]
        info["platform"] = None
        return self.response(info)

    def _get_ready_file(self, area, run, dataset):
        # e.g. Tiles-00-lm2.2.web
        self.base_path = os.path.join(MEDIA_ROOT, "PROD", f"Tiles-{run}-{dataset}.web")
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
