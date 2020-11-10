import os

from flask import send_file
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.models import Schema, fields, validate
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
DEFAULT_PLATFORM = os.environ.get("PLATFORM", "GALILEO")


def check_platform_availability(platform):
    return os.access(os.path.join(MEDIA_ROOT, platform), os.X_OK)


def get_schema(set_required):
    attributes = {}
    attributes["run"] = fields.Str(validate=validate.OneOf(RUNS), required=True)
    attributes["res"] = fields.Str(validate=validate.OneOf(RESOLUTIONS), required=True)
    attributes["field"] = fields.Str(validate=validate.OneOf(FIELDS), required=True)
    attributes["area"] = fields.Str(validate=validate.OneOf(AREAS), required=True)
    attributes["platform"] = fields.Str(
        validate=validate.OneOf(PLATFORMS), required=set_required
    )
    attributes["level_pe"] = fields.Str(
        validate=validate.OneOf(LEVELS_PE), required=False
    )
    attributes["level_pr"] = fields.Str(
        validate=validate.OneOf(LEVELS_PR), required=False
    )
    attributes["env"] = fields.Str(validate=validate.OneOf(ENVS), required=False)

    return Schema.from_dict(attributes)
    # schema = Schema.from_dict(attributes)
    # return schema()


class MapEndpoint(EndpointResource):
    def __init__(self):
        super().__init__()
        self.base_path = None

    def set_base_path(self, field, platform, env, run, res):
        # flood fields have a different path
        if (field == "percentile") or (field == "probability"):
            self.base_path = os.path.join(
                MEDIA_ROOT,
                platform,
                env,
                f"PROB-{run}-2.2.web",
            )
        else:
            self.base_path = os.path.join(
                MEDIA_ROOT,
                platform,
                env,
                f"Magics-{run}-{res}.web",
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

    def __init__(self):
        super().__init__()

    @decorators.use_kwargs(get_schema(True), location="query")
    @decorators.endpoint(
        path="/maps/<map_offset>",
        summary="Get a forecast map for a specific run.",
        responses={
            200: "Map successfully retrieved",
            400: "Invalid parameters",
            404: "Map does not exists",
        },
    )
    def get(
        self,
        map_offset,
        run,
        res,
        field,
        area,
        platform,
        level_pe=None,
        level_pr=None,
        env="PROD",
    ):
        """Get a forecast map for a specific run."""
        # log.debug('Retrieve map image by offset <{}>'.format(map_offset))

        # flash flood offset is a bit more complicate
        if field == "percentile":
            map_offset = "_".join((map_offset, level_pe))
        elif field == "probability":
            map_offset = "_".join((map_offset, level_pr))

        log.debug(f"Retrieve map image by offset <{map_offset}>")

        self.set_base_path(field, platform, env, run, res)

        # Check if the images are ready: 2017112900.READY
        ready_file = self.get_ready_file(area)
        reftime = ready_file[:10]

        # get map image
        if field == "percentile":
            map_image_file = os.path.join(
                self.base_path,
                area,
                field,
                "{field}.{reftime}.{offset}.png".format(
                    field="perc6", reftime=reftime, offset=map_offset
                ),
            )
        elif field == "probability":
            map_image_file = os.path.join(
                self.base_path,
                area,
                field,
                "{field}.{reftime}.{offset}.png".format(
                    field="prob6", reftime=reftime, offset=map_offset
                ),
            )
        else:
            map_image_file = os.path.join(
                self.base_path,
                area,
                field,
                "{field}.{reftime}.{offset}.png".format(
                    field=field, reftime=reftime, offset=map_offset
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

    def __init__(self):
        super().__init__()

    @decorators.use_kwargs(get_schema(False), location="query")
    @decorators.endpoint(
        path="/maps/ready",
        summary="Get the last available map set for a specific run returning the reference time as well.",
        responses={
            200: "Map set successfully retrieved",
            400: "Invalid parameters",
            404: "Map set does not exists",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Mapset'}}
    def get(
        self,
        run,
        res,
        field,
        area,
        platform=None,
        level_pe=None,
        level_pr=None,
        env="PROD",
    ):
        """
        Get the last available map set for a specific run returning the reference time as well.
        """

        log.debug(f"Retrieve map set for last run <{run}>")

        # only admin user can request for a specific platform
        if platform is not None and not self.verify_admin():
            platform = None

        # if PLATFORM is not provided, set as default the first available in the order: DEFAULT_PLATFORM + others
        if not platform:
            log.debug(f"PLATFORMS: {PLATFORMS}")
            log.debug(f"DEFAULT PLATFORM: {DEFAULT_PLATFORM}")
            platforms_to_be_check = [DEFAULT_PLATFORM] + list(
                set(PLATFORMS) - {DEFAULT_PLATFORM}
            )
        else:
            platforms_to_be_check = [platform]
        for platform in platforms_to_be_check:
            if not check_platform_availability(platform):
                log.warning(f"platform {platform} not available")
                continue
            else:
                platform = platform
                break
        else:
            raise RestApiException(
                "Map service is currently unavailable", hcodes.HTTP_SERVICE_UNAVAILABLE
            )

        if field == "percentile" or field == "probability":
            # force GALILEO as platform
            platform = "GALILEO"
            log.warning("Forcing platform to {} because field is {}", platform, field)

        self.set_base_path(field, platform, env, run, res)

        # Check if the images are ready: 2017112900.READY
        ready_file = self.get_ready_file(area)
        reftime = ready_file[:10]

        data = {"reftime": reftime, "offsets": [], "platform": platform}

        # load image offsets
        images_path = os.path.join(self.base_path, area, field)

        list_file = sorted(os.listdir(images_path))

        if field == "percentile" or field == "probability":
            # flash flood offset is a bit more complicate
            for f in list_file:
                if os.path.isfile(os.path.join(images_path, f)):
                    offset = f.split(".")[-2]
                    # offset is like this now: 0006_10
                    offset, level = offset.split("_")
                    # log.debug('data offsets: {}, level: {}'.format(offset,level))
                    # log.debug('level_pe: {}, level_pr: {}'.format(params['level_pe'],params['level_pr']))

                    if field == "percentile" and level_pe == level:
                        data["offsets"].append(offset)
                    elif field == "probability" and level_pr == level:
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

    def __init__(self):
        super().__init__()

    @decorators.use_kwargs(get_schema(True), location="query")
    @decorators.endpoint(
        path="/maps/legend",
        summary="Get a specific forecast map legend.",
        responses={
            200: "Legend successfully retrieved",
            400: "Invalid parameters",
            404: "Legend does not exists",
        },
    )
    def get(
        self, run, res, field, area, platform, level_pe=None, level_pr=None, env="PROD"
    ):
        """Get a forecast legend for a specific run."""
        # NOTE: 'area' param is not strictly necessary here although present among the parameters of the request
        log.debug(
            "Retrieve legend for run <{run}, {res}, {field}>".format(
                run=run, res=res, field=field
            )
        )

        self.set_base_path(field, platform, env, run, res)

        # Get legend image
        legend_path = os.path.join(self.base_path, "legends")
        if field == "percentile":
            map_legend_file = os.path.join(legend_path, "perc6" + ".png")
        elif field == "probability":
            map_legend_file = os.path.join(legend_path, "prob6" + ".png")
        else:
            map_legend_file = os.path.join(legend_path, field + ".png")
        log.debug(map_legend_file)
        if not os.path.isfile(map_legend_file):
            raise RestApiException(
                f"Map legend not found for field <{field}>",
                hcodes.HTTP_BAD_NOTFOUND,
            )
        return send_file(map_legend_file, mimetype="image/png")
