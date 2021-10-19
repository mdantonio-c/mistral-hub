import subprocess
from pathlib import Path

from mistral.exceptions import PostProcessingException
from restapi.utilities.logs import log


def pp_output_formatting(
    output_format: str, input_file: Path, output_file: Path
) -> Path:
    try:
        if output_format == "json":
            log.debug("Output formatting to {}", output_format)
            post_proc_cmd = []
            post_proc_cmd.append("dbamsg")
            post_proc_cmd.append("dump")
            post_proc_cmd.append("--json")
            post_proc_cmd.append("-t")
            post_proc_cmd.append("bufr")
            post_proc_cmd.append(str(input_file))

            log.debug("Post process command: {}>", post_proc_cmd)

            with open(output_file, mode="w") as outfile:
                proc = subprocess.Popen(post_proc_cmd, stdout=outfile)
                # wait for the process to terminate
                if proc.wait() != 0:
                    raise Exception("Failure in post-processing")
                else:
                    return output_file
        else:
            # up to now we have only one postprocessor for output formatting.
            # Here we can add others in future if needed
            return input_file

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)

    finally:
        # remove the input file
        input_file.unlink()
