import subprocess
import os
import shutil
from pathlib import Path

from restapi.utilities.logs import get_logger
from mistral.exceptions import PostProcessingException
from restapi.utilities.htmlcodes import hcodes
from restapi.exceptions import RestApiException


logger = get_logger(__name__)


def get_trans_type(params):
    # get trans-type according to the sub-type coming from the request
    sub_type = params['sub-type']
    if sub_type in ("near", "bilin"):
        params['trans-type'] = "inter"
    if sub_type in ("average", "min", "max"):
        params['trans-type'] = "polyinter"

def validate_spare_point_interpol_params(params):
    coord_filepath = params['coord-filepath']
    if not os.path.exists(coord_filepath):
        raise RestApiException('the coord-filepath does not exists',
                               status_code=hcodes.HTTP_BAD_REQUEST)

    filebase, fileext = os.path.splitext(coord_filepath)
    if fileext.strip('.') != params['format']:
        raise RestApiException('format parameter is not correct',
                               status_code=hcodes.HTTP_BAD_REQUEST)
    # if a file is a shapefile, check if .shx and .dbf are in the same folder. If not ask the user to upload all the files again
    if params['format'] == 'shp':
        if not os.path.exists(filebase + '.shx') or not os.path.exists(filebase + '.dbf'):
            # delete the folder with the corrupted files
            uploaded_filepath = Path(params['coord-filepath'])
            shutil.rmtree(uploaded_filepath.parent)
            raise RestApiException('Sorry.The file for the interpolation is corrupted. Please try to upload it again',
                                   status_code=hcodes.HTTP_SERVER_ERROR)

def pp_sp_interpolation(params, input, output,fileformat):
    logger.debug('Spare point interpolation postprocessor')
    try:
        post_proc_cmd = []

        if fileformat.startswith('grib'):
            post_proc_cmd.append('vg6d_getpoint')
            post_proc_cmd.append('--trans-type={}'.format(params.get('trans-type')))
        else:
            post_proc_cmd.append('v7d_transform')
            post_proc_cmd.append('--pre-trans-type={}'.format(params.get('trans-type')))

        post_proc_cmd.append('--sub-type={}'.format(params.get('sub-type')))
        post_proc_cmd.append('--coord-format={}'.format(params.get('format')))
        post_proc_cmd.append('--coord-file={}'.format(params.get('coord-filepath')))
        post_proc_cmd.append('--output-format=BUFR')
        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        logger.debug('Post process command: {}>'.format(post_proc_cmd))

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        logger.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)