import subprocess

from restapi.utilities.logs import log
from mistral.exceptions import PostProcessingException


def pp_grid_cropping(params, input, output):
    log.debug('Grid cropping postprocessor')
    try:
        post_proc_cmd = []
        post_proc_cmd.append('vg6d_transform')
        post_proc_cmd.append('--trans-mode=s')  # parametro opzionale per limitare l'uso della memoria elaborando un messaggio alla volta
        post_proc_cmd.append('--trans-type={}'.format(params.get('trans-type')))
        post_proc_cmd.append('--sub-type={}'.format(params.get('sub-type')))

        if 'ilon' in params['boundings']:
            post_proc_cmd.append('--ilon={}'.format(params['boundings']['ilon']))
        if 'ilat' in params['boundings']:
            post_proc_cmd.append('--ilat={}'.format(params['boundings']['ilat']))
        if 'flon' in params['boundings']:
            post_proc_cmd.append('--flon={}'.format(params['boundings']['flon']))
        if 'flat' in params['boundings']:
            post_proc_cmd.append('--flat={}'.format(params['boundings']['flat']))

        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        log.debug('Post process command: {}>', post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        log.warning(perr)
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)
