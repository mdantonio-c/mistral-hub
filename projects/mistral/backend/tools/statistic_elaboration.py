import subprocess
from pathlib import Path
from typing import Any, Dict, List

import dballe
import eccodes
from mistral.endpoints import PostProcessorsType
from mistral.exceptions import PostProcessingException
from restapi.utilities.logs import log

# conversion from grib1 to grib2 style
ed1to2 = {3: 0, 4: 1, 5: 4, 0: 254}


def pp_statistic_elaboration(
    params: PostProcessorsType,
    input_file: Path,
    output_file: Path,
    fileformat: str,
) -> None:
    log.debug("Statistic elaboration postprocessor")

    # Create the list of timeranges tuples
    # Note: trs is a list because this post processor was originally intended to be
    # requestable multiple times. This functionality is not available but we kept
    # this part of implemented code ready for this opportunity
    trs = [(params.get("input_timerange"), params.get("output_timerange"))]
    log.debug("timeranges: {}", trs)

    fileouput_to_join: List[Path] = []
    # split the input file according to the input timeranges
    file_not_for_pp = Path(f"{output_file.stem}_others.{fileformat}.tmp")
    if fileformat == "grib":
        with open(input_file) as filein:
            fd: Dict[tuple[int, int], Any] = {}
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
                            file_for_pp = (
                                f"{output_file.stem}_%d_%d.{fileformat}.tmp" % tr
                            )
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
    else:
        with open(input_file, "rb") as in_file:
            with open(file_not_for_pp, "wb") as no_match_file:
                for tr in trs:
                    file_for_pp = f"{output_file.stem}_%d_%d.{fileformat}.tmp" % tr
                    log.debug("file for post process {} ", file_for_pp)
                    with open(file_for_pp, "wb") as match_file:
                        importer = dballe.Importer("BUFR")
                        exporter = dballe.Exporter("BUFR")

                        with importer.from_file(in_file) as fp:
                            for msgs in fp:
                                for msg in msgs:
                                    count_vars = 0
                                    count_vars_nm = 0
                                    new_msg = dballe.Message("generic")

                                    new_msg.set_named("year", msg.get_named("year"))
                                    new_msg.set_named("month", msg.get_named("month"))
                                    new_msg.set_named("day", msg.get_named("day"))
                                    new_msg.set_named("hour", msg.get_named("hour"))
                                    new_msg.set_named("minute", msg.get_named("minute"))
                                    new_msg.set_named("second", msg.get_named("second"))
                                    new_msg.set_named("rep_memo", msg.report)
                                    new_msg.set_named(
                                        "longitude", int(msg.coords[0] * 10 ** 5)
                                    )
                                    new_msg.set_named(
                                        "latitude", int(msg.coords[1] * 10 ** 5)
                                    )
                                    if msg.ident:
                                        new_msg.set_named("ident", msg.ident)

                                    new_msg_nm = new_msg
                                    for data in msg.query_data({"query": "attrs"}):
                                        variable = data["variable"]
                                        attrs = variable.get_attrs()
                                        v = dballe.var(
                                            data["variable"].code,
                                            data["variable"].get(),
                                        )
                                        for a in attrs:
                                            v.seta(a)

                                        if data["trange"].pind == tr[0]:
                                            new_msg.set(
                                                data["level"], data["trange"], v
                                            )
                                            count_vars += 1
                                        else:
                                            new_msg_nm.set(
                                                data["level"], data["trange"], v
                                            )
                                            count_vars_nm += 1

                                    for data in msg.query_station_data(
                                        {"query": "attrs"}
                                    ):
                                        variable = data["variable"]
                                        attrs = variable.get_attrs()
                                        v = dballe.var(
                                            data["variable"].code,
                                            data["variable"].get(),
                                        )
                                        for a in attrs:
                                            v.seta(a)

                                        new_msg.set(dballe.Level(), dballe.Trange(), v)
                                        new_msg_nm.set(
                                            dballe.Level(), dballe.Trange(), v
                                        )
                                    if count_vars > 0:
                                        match_file.write(exporter.to_binary(new_msg))
                                    if count_vars_nm > 0:
                                        no_match_file.write(
                                            exporter.to_binary(new_msg_nm)
                                        )

    if file_not_for_pp.exists():
        fileouput_to_join.append(file_not_for_pp)
    # postprocess each file coming from the splitted input
    check_input_for_pp = False
    for tr in trs:
        splitted_input = Path(f"{output_file.stem}_%d_%d.{fileformat}.tmp" % tr)
        tmp_output = Path(f"{output_file.stem}_%d_%d_result.{fileformat}.tmp" % tr)
        if splitted_input.exists():
            pp_output = run_statistic_elaboration(
                params=params,
                input_file=splitted_input,
                output_file=tmp_output,
                fileformat=fileformat,
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
        if f.exists():
            check_fileoutput_exists = True
            cat_cmd.append(str(f))
    if not check_fileoutput_exists:
        message = "Error in post-processing: no results"
        log.warning(message)
        raise PostProcessingException(message)

    with open(output_file, mode="w") as outfile:
        ext_proc = subprocess.Popen(cat_cmd, stdout=outfile)
        ext_proc.wait()
        if ext_proc.wait() != 0:
            raise Exception("Failure in post processing")


def run_statistic_elaboration(
    params: PostProcessorsType, input_file: Path, output_file: Path, fileformat: str
) -> Path:
    log.debug("postprocessing file {}", input_file)
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

    if fileformat.startswith("grib"):
        libsim_tool = "vg6d_transform"
    else:
        libsim_tool = "v7d_transform"

    try:
        post_proc_cmd = []
        post_proc_cmd.append(libsim_tool)
        post_proc_cmd.append(
            "--comp-stat-proc={}:{}".format(
                params.get("input_timerange"), params.get("output_timerange")
            )
        )
        post_proc_cmd.append(f"--comp-step={step}")
        if not fileformat.startswith("grib"):
            post_proc_cmd.append("--input-format=BUFR")
            post_proc_cmd.append("--output-format=BUFR")
        post_proc_cmd.append(str(input_file))
        post_proc_cmd.append(str(output_file))
        log.debug("Post process command: {}>", post_proc_cmd)

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        log.debug("post process exit code : {}", proc.wait())
        if proc.wait() != 0:
            raise Exception("Failure in post-processing")
        else:
            return output_file

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
