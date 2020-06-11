import copy
import os

from flask import send_file
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

MEDIA_ROOT = "/meteo/"

RUNS = ["00", "12"]
RESOLUTIONS = ["lm2.2", "lm5"]
FIELDS = [
    "prec3",
    "prec6",
    "t2m",
    "wind",
    "cloud",
    "cloud_hml",
    "humidity",
    "snow3",
    "snow6",
    "percentile",
    "probability",
]
LEVELS_PE = ["1", "10", "25", "50", "75", "99"]
LEVELS_PR = ["5", "10", "20", "50"]
AREAS = ["Italia", "Nord_Italia", "Centro_Italia", "Sud_Italia", "Area_Mediterranea"]
PLATFORMS = ["GALILEO", "MEUCCI"]
ENVS = ["PROD", "DEV"]


def validate_meteo_params(params):
    if "run" not in params or params["run"] not in RUNS:
        raise RestApiException(
            f"Please specify a valid run. Expected one of {RUNS}",
            status_code=hcodes.HTTP_BAD_REQUEST,
        )
    # TODO validate parameters


def set_platform_optional(params):
    for d in params:
        if d["name"] == "platform":
            d["required"] = False
    return params


def check_platform_availability(platform):
    return os.access(os.path.join(MEDIA_ROOT, platform), os.X_OK)


class MapEndpoint(EndpointResource):

    __meteo_params__ = [
        {
            "name": "run",
            "in": "query",
            "required": True,
            "type": "string",
            "enum": RUNS,
            "description": "Execution of the forecast model",
        },
        {
            "name": "res",
            "in": "query",
            "required": True,
            "type": "string",
            "enum": RESOLUTIONS,
            "description": "Resolution of the forecast model",
        },
        {
            "name": "field",
            "in": "query",
            "required": True,
            "type": "string",
            "enum": FIELDS,
            "description": "Forecast parameter (e.g. temperature, humidity etc.)",
        },
        {
            "name": "level_pe",
            "in": "query",
            "required": False,
            "type": "string",
            "enum": LEVELS_PE,
            "description": "Flash flood percentile level (1, 10, 25, 50, 75, 99)",
        },
        {
            "name": "level_pr",
            "in": "query",
            "required": False,
            "type": "string",
            "enum": LEVELS_PR,
            "description": "Flash flood probability level (5, 10, 20, 50)",
        },
        {
            "name": "area",
            "in": "query",
            "required": True,
            "type": "string",
            "enum": AREAS,
            "description": "Forecast area",
        },
        {
            "name": "platform",
            "in": "query",
            "required": True,
            "type": "string",
            "enum": PLATFORMS,
            "description": "HPC cluster",
        },
        {
            "name": "env",
            "in": "query",
            "default": "PROD",
            "type": "string",
            "enum": ENVS,
            "description": "Execution environment",
        },
    ]

    def __init__(self):
        super().__init__()
        self.base_path = None

    def set_base_path(self, params):
        # flood fields have a different path
        if (params["field"] == "percentile") or (params["field"] == "probability"):
            self.base_path = os.path.join(
                MEDIA_ROOT,
                params["platform"],
                params["env"],
                "PROB-{}-2.2.web".format(params["run"]),
            )
        else:
            self.base_path = os.path.join(
                MEDIA_ROOT,
                params["platform"],
                params["env"],
                "Magics-{}-{}.web".format(params["run"], params["res"]),
            )
        log.debug(f"base_path: {self.base_path}")

    def get_ready_file(self, area):
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
            raise RestApiException(
                "no .READY files found", status_code=hcodes.HTTP_BAD_NOTFOUND
            )
        return ready_files[0]


class MapImage(MapEndpoint):
    labels = ["map image"]
    _GET = {
        "/maps/<map_offset>": {
            "summary": "Get a forecast map for a specific run.",
            "parameters": MapEndpoint.__meteo_params__,
            "responses": {
                "200": {"description": "Map successfully retrieved"},
                "400": {"description": "Invalid parameters"},
                "404": {"description": "Map does not exists"},
            },
        }
    }

    def __init__(self):
        super().__init__()

    @decorators.catch_errors()
    def get(self, map_offset):
        """Get a forecast map for a specific run."""
        params = self.get_input()
        # validate_meteo_params(params)
        # log.debug('Retrieve map image by offset <{}>'.format(map_offset))

        # flash flood offset is a bit more complicate
        if params["field"] == "percentile":
            map_offset = "_".join((map_offset, params["level_pe"]))
        elif params["field"] == "probability":
            map_offset = "_".join((map_offset, params["level_pr"]))

        log.debug(f"Retrieve map image by offset <{map_offset}>")

        self.set_base_path(params)

        # Check if the images are ready: 2017112900.READY
        ready_file = self.get_ready_file(params["area"])
        reftime = ready_file[:10]

        # get map image
        if params["field"] == "percentile":
            map_image_file = os.path.join(
                self.base_path,
                params["area"],
                params["field"],
                "{field}.{reftime}.{offset}.png".format(
                    field="perc6", reftime=reftime, offset=map_offset
                ),
            )
        elif params["field"] == "probability":
            map_image_file = os.path.join(
                self.base_path,
                params["area"],
                params["field"],
                "{field}.{reftime}.{offset}.png".format(
                    field="prob6", reftime=reftime, offset=map_offset
                ),
            )
        else:
            map_image_file = os.path.join(
                self.base_path,
                params["area"],
                params["field"],
                "{field}.{reftime}.{offset}.png".format(
                    field=params["field"], reftime=reftime, offset=map_offset
                ),
            )

        log.debug(f"map_image_file: {map_image_file}")

        if not os.path.isfile(map_image_file):
            raise RestApiException(
                f"Map image not found for offset {map_offset}", hcodes.HTTP_BAD_NOTFOUND
            )
        return send_file(map_image_file, mimetype="image/png")


class MapSet(MapEndpoint):
    labels = ["map set"]
    _GET = {
        "/maps/ready": {
            "summary": "Get the last available map set for a specific run returning the reference time as well.",
            "parameters": set_platform_optional(
                copy.deepcopy(MapEndpoint.__meteo_params__)
            ),
            "responses": {
                "200": {
                    "description": "Map set successfully retrieved",
                    "schema": {"$ref": "#/definitions/Mapset"},
                },
                "400": {"description": "Invalid parameters"},
                "404": {"description": "Map set does not exists"},
            },
        }
    }

    def __init__(self):
        super().__init__()

    @decorators.catch_errors()
    def get(self):
        """
        Get the last available map set for a specific run returning the reference time as well.
        """
        # includes pre-set defaults
        params = self.get_input()
        # validate_meteo_params(params)
        log.debug("Retrieve map set for last run <{}>".format(params["run"]))

        # only admin user can request for a specific platform
        if params.get("platform") is not None and not self.auth.verify_admin():
            params["platform"] = None

        # if PLATFORM is not provided, set as default the first available in the order: GALILEO, MEUCCI
        if "platform" not in params or params["platform"] is None:
            platforms_to_be_check = PLATFORMS
        else:
            platforms_to_be_check = [params["platform"]]
        for platform in platforms_to_be_check:
            if not check_platform_availability(platform):
                log.warning(f"platform {platform} not available")
                continue
            else:
                params["platform"] = platform
                break
        else:
            raise RestApiException(
                "Map service is currently unavailable", hcodes.HTTP_SERVICE_UNAVAILABLE
            )

        self.set_base_path(params)

        # Check if the images are ready: 2017112900.READY
        ready_file = self.get_ready_file(params["area"])
        reftime = ready_file[:10]

        data = {"reftime": reftime, "offsets": [], "platform": params["platform"]}

        # load image offsets
        images_path = os.path.join(self.base_path, params["area"], params["field"])

        list_file = sorted(os.listdir(images_path))

        if params["field"] == "percentile" or params["field"] == "probability":
            # flash flood offset is a bit more complicate
            for f in list_file:
                if os.path.isfile(os.path.join(images_path, f)):
                    offset = f.split(".")[-2]
                    # offset is like this now: 0006_10
                    offset, level = offset.split("_")
                    # log.debug('data offsets: {}, level: {}'.format(offset,level))
                    # log.debug('level_pe: {}, level_pr: {}'.format(params['level_pe'],params['level_pr']))

                    if params["field"] == "percentile" and params["level_pe"] == level:
                        data["offsets"].append(offset)
                    elif (
                        params["field"] == "probability" and params["level_pr"] == level
                    ):
                        data["offsets"].append(offset)
        else:
            data["offsets"] = [
                f.split(".")[-2]
                for f in list_file
                if os.path.isfile(os.path.join(images_path, f))
            ]

        log.debug("data offsets: {}".format(data["offsets"]))

        return self.response(data)


class MapLegend(MapEndpoint):
    labels = ["legend"]
    _GET = {
        "/maps/legend": {
            "summary": "Get a specific forecast map legend.",
            "parameters": MapEndpoint.__meteo_params__,
            "responses": {
                "200": {"description": "Legend successfully retrieved"},
                "400": {"description": "Invalid parameters"},
                "404": {"description": "Legend does not exists"},
            },
        }
    }

    def __init__(self):
        super().__init__()

    @decorators.catch_errors()
    def get(self):
        """Get a forecast legend for a specific run."""
        params = self.get_input()
        # validate_meteo_params(params)
        # NOTE: 'area' param is not strictly necessary here although present among the parameters of the request
        log.debug(
            "Retrieve legend for run <{run}, {res}, {field}>".format(
                run=params["run"], res=params["res"], field=params["field"]
            )
        )

        self.set_base_path(params)

        # Get legend image
        legend_path = os.path.join(self.base_path, "legends")
        if params["field"] == "percentile":
            map_legend_file = os.path.join(legend_path, "perc6" + ".png")
        elif params["field"] == "probability":
            map_legend_file = os.path.join(legend_path, "prob6" + ".png")
        else:
            map_legend_file = os.path.join(legend_path, params["field"] + ".png")
        log.debug(map_legend_file)
        if not os.path.isfile(map_legend_file):
            raise RestApiException(
                "Map legend not found for field <{}>".format(params["field"]),
                hcodes.HTTP_BAD_NOTFOUND,
            )
        return send_file(map_legend_file, mimetype="image/png")
