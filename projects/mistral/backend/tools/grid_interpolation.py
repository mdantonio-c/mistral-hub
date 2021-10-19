import subprocess
from pathlib import Path

from mistral.exceptions import PostProcessingException
from restapi.endpoints import PostProcessorsType
from restapi.exceptions import BadRequest
from restapi.utilities.logs import log


def check_template_filepath(template_file: Path) -> None:
    if not template_file.exists():
        raise BadRequest("the template file does not exists")


def get_trans_type(params: PostProcessorsType) -> None:
    # get trans-type according to the sub-type coming from the request
    sub_type = params["sub_type"]
    if sub_type in ("near", "bilin"):
        params["trans_type"] = "inter"
    if sub_type in ("average", "min", "max"):
        params["trans_type"] = "boxinter"


def pp_grid_interpolation(
    params: PostProcessorsType, input: Path, output: Path
) -> Path:
    log.debug("Grid interpolation postprocessor")
    try:
        post_proc_cmd = []
        post_proc_cmd.append("vg6d_transform")
        post_proc_cmd.append("--trans-type={}".format(params.get("trans_type")))
        post_proc_cmd.append("--sub-type={}".format(params.get("sub_type")))

        # check if there is a grib file template or look for others interpolation params
        if "template" in params:
            post_proc_cmd.append(
                "--output-format=grib_api:{}".format(params["template"])
            )
        else:
            # vg6d_transform automatically provides defaults for missing optional params
            if "boundings" in params:
                if "x_min" in params["boundings"]:
                    post_proc_cmd.append(
                        "--x-min={}".format(params["boundings"]["x_min"])
                    )
                if "x_max" in params["boundings"]:
                    post_proc_cmd.append(
                        "--x-max={}".format(params["boundings"]["x_max"])
                    )
                if "y_min" in params["boundings"]:
                    post_proc_cmd.append(
                        "--y-min={}".format(params["boundings"]["y_min"])
                    )
                if "y_max" in params["boundings"]:
                    post_proc_cmd.append(
                        "--y-max={}".format(params["boundings"]["y_max"])
                    )
            if "nodes" in params:
                if "nx" in params["nodes"]:
                    post_proc_cmd.append("--nx={}".format(params["nodes"]["nx"]))
                if "ny" in params["nodes"]:
                    post_proc_cmd.append("--ny={}".format(params["nodes"]["ny"]))

        # post_proc_cmd.append('--display')
        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")
        else:
            return output

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)
