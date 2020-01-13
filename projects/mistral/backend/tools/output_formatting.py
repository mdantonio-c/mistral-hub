import subprocess

from restapi.utilities.logs import log
from mistral.exceptions import PostProcessingException


def pp_output_formatting(output_format, input, output):
    try:
        if output_format == 'json':
            log.debug('Output formatting to {}', output_format)
            post_proc_cmd = []
            post_proc_cmd.append('dbamsg')
            post_proc_cmd.append('dump')
            post_proc_cmd.append('--json')
            post_proc_cmd.append('-t')
            post_proc_cmd.append('bufr')
            post_proc_cmd.append(input)
            post_proc_cmd.append('>')
            post_proc_cmd.append(output)

            log.debug('Post process command: {}>', post_proc_cmd)

            proc = subprocess.Popen(post_proc_cmd)
            # wait for the process to terminate
            if proc.wait() != 0:
                raise Exception('Failure in post-processing')
            else:
                return output
        else:
            # up to now we have only one postprocessor for output formatting. Here we can add others in future if needed
            return input

    except Exception as perr:
        log.warning(perr)
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)
