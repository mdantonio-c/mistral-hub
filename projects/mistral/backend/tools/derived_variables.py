import shlex
import subprocess
from pathlib import Path

from mistral.endpoints import PostProcessorsType
from mistral.exceptions import PostProcessingException
from restapi.utilities.logs import log


def pp_derived_variables(
    params: PostProcessorsType, input_file: Path, output_folder: Path, fileformat: str
) -> Path:
    log.debug("Derived variable postprocessor")

    output_file_step1 = output_folder.joinpath(
        f"{input_file.stem}-pp1.{fileformat}.step1.tmp"
    )
    output_file_step2 = output_folder.joinpath(
        f"{input_file.stem}-pp1.{fileformat}.tmp"
    )
    try:
        # command for postprocessor
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
                input_file,
                output_file_step1,
            )
        )
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")

        # merge input file and the transform output
        cat_cmd = ["cat", str(input_file), str(output_file_step1)]

        with open(output_file_step2, mode="w") as pp1_outfile:
            ext_proc = subprocess.Popen(cat_cmd, stdout=pp1_outfile)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise Exception("Failure in data extraction")

        return output_file_step2
    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)
