import shutil
import subprocess
from pathlib import Path

from mistral.endpoints import PostProcessorsType
from mistral.exceptions import PostProcessingException
from restapi.exceptions import BadRequest
from restapi.utilities.logs import log


def get_trans_type(params: PostProcessorsType) -> None:
    # get trans-type according to the sub-type coming from the request
    sub_type = params["sub_type"]
    if sub_type in ("near", "bilin"):
        params["trans_type"] = "inter"
    if sub_type in ("average", "min", "max"):
        params["trans_type"] = "polyinter"


def check_coord_filepath(params: PostProcessorsType) -> None:
    coord_filepath = Path(params["coord_filepath"])
    if not coord_filepath.exists():
        raise BadRequest("the coord-filepath does not exists")

    if coord_filepath.suffix.strip(".") != params["file_format"]:
        raise BadRequest("format parameter is not correct")

    # if a file is a shapefile, check if .shx and .dbf are in the same folder.
    # If not ask the user to upload all the files again
    if params["file_format"] == "shp":
        if (
            not coord_filepath.with_suffix(".shx").exists()
            or not coord_filepath.with_suffix(".dbf").exists()
        ):
            # delete the folder with the corrupted files
            uploaded_filepath = Path(params["coord_filepath"])
            shutil.rmtree(uploaded_filepath.parent)
            raise BadRequest(
                "Sorry. The file for the interpolation is corrupted. "
                "Please try to upload it again"
            )


def pp_sp_interpolation(
    params: PostProcessorsType, input_file: Path, output_folder: Path, fileformat: str
) -> Path:
    log.debug("Spare point interpolation postprocessor")
    try:

        output_file = output_folder.joinpath(f"{input_file.stem}").with_suffix(".bufr")

        post_proc_cmd = []

        if fileformat.startswith("grib"):
            post_proc_cmd.append("vg6d_getpoint")
            post_proc_cmd.append("--trans-type={}".format(params.get("trans_type")))
        else:
            post_proc_cmd.append("v7d_transform")
            post_proc_cmd.append("--pre-trans-type={}".format(params.get("trans_type")))
            post_proc_cmd.append("--input-format=BUFR")

        post_proc_cmd.append("--sub-type={}".format(params.get("sub_type")))
        post_proc_cmd.append("--coord-format={}".format(params.get("file_format")))
        post_proc_cmd.append("--coord-file={}".format(params.get("coord_filepath")))
        post_proc_cmd.append("--output-format=BUFR")
        post_proc_cmd.append(str(input_file))
        post_proc_cmd.append(str(output_file))
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")

        return output_file

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)
