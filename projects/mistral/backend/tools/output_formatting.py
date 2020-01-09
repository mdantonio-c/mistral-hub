import subprocess

from restapi.utilities.logs import get_logger
from mistral.exceptions import PostProcessingException

logger = get_logger(__name__)


def pp_output_formatting(output_format,input, output):
    try:
        if output_format == 'json':
            logger.debug('Output formatting to {}'.format(output_format))
            post_proc_cmd = []
            post_proc_cmd.append('dbamsg')
            post_proc_cmd.append('dump')
            post_proc_cmd.append('--json')
            post_proc_cmd.append('-t')
            post_proc_cmd.append('bufr')
            post_proc_cmd.append(input)
            post_proc_cmd.append('>')
            post_proc_cmd.append(output)

            logger.debug('Post process command: {}>'.format(post_proc_cmd))

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
        logger.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)