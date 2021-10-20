import subprocess
from pathlib import Path

from mistral.endpoints import PostProcessorsType
from mistral.exceptions import PostProcessingException
from restapi.utilities.logs import log


def pp_grid_cropping(
    params: PostProcessorsType, input_file: Path, output_file: Path
) -> Path:
    log.debug("Grid cropping postprocessor")
    try:
        post_proc_cmd = []
        post_proc_cmd.append("vg6d_transform")
        # limit memory usage by elaborating a message at once
        post_proc_cmd.append("--trans-mode=s")
        post_proc_cmd.append("--trans-type={}".format(params.get("trans_type")))
        post_proc_cmd.append("--sub-type={}".format(params.get("sub_type")))

        if "ilon" in params["boundings"]:
            post_proc_cmd.append("--ilon={}".format(params["boundings"]["ilon"]))
        if "ilat" in params["boundings"]:
            post_proc_cmd.append("--ilat={}".format(params["boundings"]["ilat"]))
        if "flon" in params["boundings"]:
            post_proc_cmd.append("--flon={}".format(params["boundings"]["flon"]))
        if "flat" in params["boundings"]:
            post_proc_cmd.append("--flat={}".format(params["boundings"]["flat"]))

        post_proc_cmd.append(str(input_file))
        post_proc_cmd.append(str(output_file))
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")
        else:
            return output_file

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)
