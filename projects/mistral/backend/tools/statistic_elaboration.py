import os
import subprocess

import eccodes
from mistral.exceptions import PostProcessingException
from restapi.exceptions import RestApiException
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

# conversion from grib1 to grib2 style
ed1to2 = {3: 0, 4: 1, 5: 4, 0: 254}


def validate_statistic_elaboration_params(params):
    input = params["input-timerange"]
    output = params["output-timerange"]
    if input != output:
        if input == 254:
            if output == 1:
                raise RestApiException(
                    "Parameters for statistic elaboration are not correct",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            else:
                return
        if input == 0:
            if output != 254:
                raise RestApiException(
                    "Parameters for statistic elaboration are not correct",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            else:
                return
        else:
            raise RestApiException(
                "Parameters for statistic elaboration are not correct",
                status_code=hcodes.HTTP_BAD_REQUEST,
            )
    if input == output:
        if input == 254:
            raise RestApiException(
                "Parameters for statistic elaboration are not correct",
                status_code=hcodes.HTTP_BAD_REQUEST,
            )


def pp_statistic_elaboration(params, input, output, fileformat):
    log.debug("Statistic elaboration postprocessor")

    # get timeranges tuples
    trs = []
    for i in params:
        timerange = (i.get("input-timerange"), i.get("output-timerange"))
        trs.append(timerange)
    log.debug("timeranges: {}", trs)

    fileouput_to_join = []
    filebase, fileext = os.path.splitext(output)
    # split the input file according to the input timeranges
    file_not_for_pp = filebase + f"_others.{fileformat}.tmp"
    with open(input, mode="r") as filein:
        fd = {}
        fdother = None
        while True:
            gid = eccodes.codes_grib_new_from_file(filein)
            if gid is None:
                break
            match = False
            for tr in trs:
                if match_timerange(gid, tr[0]):
                    if fd.get(tr, None) is None:  # better way?
                        # create name for the temporary output
                        file_for_pp = filebase + f"_%d_%d.{fileformat}.tmp" % tr
                        fd[tr] = open(file_for_pp, "wb")
                    match = True
                    # write to file/pipe for tr
                    eccodes.codes_write(gid, fd[tr])

            if not match:
                if fdother is None:
                    fdother = open(file_not_for_pp, "wb")
                # write to file "other"
                eccodes.codes_write(gid, fdother)
            eccodes.codes_release(gid)

    if os.path.exists(file_not_for_pp):
        fileouput_to_join.append(file_not_for_pp)
    # postprocess each file coming from the splitted input
    check_input_for_pp = False
    for tr in trs:
        p = next(
            item
            for item in params
            if item["input-timerange"] == tr[0] and item["output-timerange"] == tr[1]
        )
        splitted_input = filebase + f"_%d_%d.{fileformat}.tmp" % tr
        tmp_output = filebase + f"_%d_%d_result.{fileformat}.tmp" % tr
        if os.path.exists(splitted_input):
            pp_output = run_statistic_elaboration(
                params=p, input=splitted_input, output=tmp_output, fileformat=fileformat
            )
            log.debug("output: {}", pp_output)
            fileouput_to_join.append(pp_output)
            check_input_for_pp = True

    # join all the fileoutput
    cat_cmd = ["cat"]
    # check if there are some postprocessed files
    if not check_input_for_pp:
        message = "Error in post-processing: Timeranges for statistic elaboration not found in the requested data"
        log.warning(message)
        raise PostProcessingException(message)

    check_fileoutput_exists = False
    for f in fileouput_to_join:
        if os.path.exists(f):
            check_fileoutput_exists = True
            cat_cmd.append(f)
    if not check_fileoutput_exists:
        message = "Error in post-processing: no results"
        log.warning(message)
        raise PostProcessingException(message)

    with open(output, mode="w") as outfile:
        ext_proc = subprocess.Popen(cat_cmd, stdout=outfile)
        ext_proc.wait()
        if ext_proc.wait() != 0:
            raise Exception("Failure in post processing")


def run_statistic_elaboration(params, input, output, fileformat):
    log.debug("postprocessing file {}", input)
    step = ""
    interval = params.get("interval")
    if interval == "years":
        step = "{:04d}000000 00:00:00.000".format(params.get("step"))
    if interval == "months":
        step = "0000{:02d}0000 00:00:00.000".format(params.get("step"))
    if interval == "days":
        step = "000000{:04d} 00:00:00.000".format(params.get("step"))
    if interval == "hours":
        step = "0000000000 {:02d}:00:00.000".format(params.get("step"))

    libsim_tool = ""
    if fileformat.startswith("grib"):
        libsim_tool = "vg6d_transform"
    else:
        libsim_tool = "v7d_transform"

    try:
        post_proc_cmd = []
        post_proc_cmd.append(libsim_tool)
        post_proc_cmd.append(
            "--comp-stat-proc={}:{}".format(
                params.get("input-timerange"), params.get("output-timerange")
            )
        )
        post_proc_cmd.append(f"--comp-step={step}")
        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        log.debug("post process exit code : {}", proc.wait())
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")
        else:
            return output

    except Exception as perr:
        log.warning(perr)
        message = "Error in post-processing: no results"
        raise PostProcessingException(message)


def match_timerange(gid, g2tr):
    ed = eccodes.codes_get(gid, "editionNumber", ktype=int)
    if ed == 1:  # grib1
        tri = eccodes.codes_get(gid, "timeRangeIndicator")
        # special case 2 in grib1 (= anywhere in the interval) matches
        # both max and min in grib2, libsim will do the work
        if tri == 2 and (g2tr == 2 or g2tr == 3):
            return True
        # convert to grib2 style
        return ed1to2.get(tri, None) == g2tr
    elif ed == 2:  # grib2
        try:
            tsp = int(eccodes.codes_get(gid, "typeOfStatisticalProcessing"))
        # From Mattia: KeyValueNotFoundError does not exist.. what do you want to catch?
        # except KeyValueNotFoundError:
        except BaseException:
            tsp = 254  # instantaneous
        return tsp == g2tr
    else:  # should never be true
        return False
