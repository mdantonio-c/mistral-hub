import shlex
import subprocess
from pathlib import Path

from mistral.endpoints import PostProcessorsType
from mistral.exceptions import PostProcessingException
from restapi.utilities.logs import log


def pp_derived_variables(
    params: PostProcessorsType, tmp_extraction: Path, user_dir: Path, fileformat: str
) -> Path:
    log.debug("Derived variable postprocessor")

    try:
        tmp_outfile = tmp_extraction
        # command for postprocessor
        if fileformat.startswith("grib"):
            pp1_output_filename = f"{tmp_extraction.stem}-pp1_output.grib.tmp"
        else:
            pp1_output_filename = f"{tmp_extraction.stem}-pp1_output.bufr.tmp"
        pp1_output = user_dir.joinpath(pp1_output_filename)
        libsim_tool = ""
        if fileformat.startswith("grib"):
            libsim_tool = "vg6d_transform"
        else:
            libsim_tool = "v7d_transform"
        post_proc_cmd = shlex.split(
            "{} --output-variable-list={} {} {} {}".format(
                libsim_tool,
                ",".join(params.get("variables")),
                "--input-format=BUFR --output-format=BUFR"
                if libsim_tool == "v7d_transform"
                else "",
                tmp_outfile,
                pp1_output,
            )
        )
        log.debug("funziona?")
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")
        else:
            return pp1_output

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)
