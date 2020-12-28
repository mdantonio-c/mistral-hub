import datetime
import glob
import json
import os
import shutil
import subprocess
import tarfile

from celery import states
from celery.exceptions import Ignore
from mistral.endpoints import DOWNLOAD_DIR, OPENDATA_DIR
from mistral.exceptions import (
    AccessToDatasetDenied,
    DiskQuotaException,
    EmptyOutputFile,
    PostProcessingException,
)
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from mistral.tools import derived_variables as pp1
from mistral.tools import grid_cropping as pp3_2
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import output_formatting
from mistral.tools import spare_point_interpol as pp3_3
from mistral.tools import statistic_elaboration as pp2
from restapi.connectors import rabbitmq, smtp, sqlalchemy
from restapi.connectors.celery import CeleryExt
from restapi.utilities.logs import log
from restapi.utilities.templates import get_html_template

celery_app = CeleryExt.celery_app


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(
    self,
    user_id,
    datasets,
    reftime=None,
    filters=None,
    postprocessors=[],
    output_format=None,
    request_id=None,
    amqp_queue=None,
    schedule_id=None,
    data_ready=False,
    opendata=False,
):
    with celery_app.app.app_context():
        log.info("Start task [{}:{}]", self.request.id, self.name)
        extra_msg = ""
        try:
            db = sqlalchemy.get_instance()
            schedule = None
            output_dir = None
            outfile = None
            if schedule_id is not None:
                # load schedule for this request
                schedule = db.Schedule.query.get(schedule_id)
                if schedule is None:
                    raise ReferenceError(
                        "Cannot find schedule reference for task {}".format(
                            self.request.id
                        )
                    )
                # adapt the request reftime
                if reftime and not data_ready:
                    reftime = adapt_reftime(db, schedule, reftime)

                # create an entry in request db linked to the scheduled request entry
                request_name = SqlApiDbManager.get_schedule_name(db, schedule_id)
                request = SqlApiDbManager.create_request_record(
                    db,
                    user_id,
                    request_name,
                    {
                        "datasets": datasets,
                        "reftime": reftime,
                        "filters": filters,
                        "postprocessors": postprocessors,
                        "output_format": output_format,
                    },
                    schedule_id=schedule_id,
                    opendata=opendata,
                )
                # update the entry with celery task id
                request.task_id = self.request.id
                request.status = states.STARTED
                request_id = request.id
                db.session.commit()
                log.debug("Schedule at: {}, Request <ID:{}>", schedule_id, request.id)
            else:
                # load request by id
                request = db.Request.query.get(request_id)
                if request is None:
                    raise ReferenceError(
                        f"Cannot find request reference for task {self.request.id}"
                    )

            # get the format of the datasets
            dataset_format = arki.get_datasets_format(datasets)
            # get the category of the datasets
            data_type = arki.get_datasets_category(datasets)
            # check user authorization for the requested datasets
            user = db.User.query.filter_by(id=user_id).first()
            auth_datasets = SqlApiDbManager.get_datasets(db, user)
            auth_datasets_names = []
            for ds in auth_datasets:
                auth_datasets_names.append(ds["id"])
            if not all(elem in auth_datasets_names for elem in datasets):
                raise AccessToDatasetDenied(
                    "user is not allowed to access the requested datasets"
                )

            # create a query for arkimet
            if data_type != "OBS" and "multim-forecast" not in datasets:
                query = ""  # default to no matchers
                if filters is not None:
                    query = arki.parse_matchers(filters)
                    log.debug("Arkimet query: {}", query)
                if reftime:
                    reftime_query = arki.parse_reftime(reftime["from"], reftime["to"])
                    query = (
                        ";".join([reftime_query, query])
                        if query != ""
                        else reftime_query
                    )

            # create download user dir if it doesn't exist
            uuid = SqlApiDbManager.get_uuid(db, user_id)
            if not amqp_queue:
                output_dir = os.path.join(DOWNLOAD_DIR, uuid, "outputs")
            else:
                # create a temporary outfile directory
                output_dir = os.path.join(DOWNLOAD_DIR, "tmp_outfiles", uuid)
            os.makedirs(output_dir, exist_ok=True)

            # check that the datasets are all under the same license
            arki.check_compatible_licenses(db, datasets)

            # max filename len = 64
            out_filename = "data-{utc_now}-{id}.{fileformat}".format(
                utc_now=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                id=self.request.id,
                fileformat=dataset_format,
            )
            if opendata:
                # get opendata folder as output dir
                output_dir = OPENDATA_DIR

            # final result
            outfile = os.path.join(output_dir, out_filename)
            log.debug("outfile: {}", outfile)

            if not amqp_queue:
                if data_type != "OBS" and "multim-forecast" not in datasets:
                    esti_data_size = check_user_quota(
                        user_id,
                        output_dir,
                        db,
                        datasets=datasets,
                        query=query,
                        schedule_id=schedule_id,
                    )
                # observed data. in future the if statement will be for data using arkimet and data using dballe
                else:
                    log.debug("observation in dballe")

            if postprocessors:
                log.debug(postprocessors)
                # check if requested postprocessors are enabled
                for p in postprocessors:
                    pp_type = p.get("processor_type")
                    enabled_postprocessors = (
                        "derived_variables",
                        "grid_interpolation",
                        "grid_cropping",
                        "spare_point_interpolation",
                        "statistic_elaboration",
                    )
                    if pp_type not in enabled_postprocessors:
                        raise ValueError("Unknown post-processor: {}", pp_type)

                    log.debug("Data extraction with post-processing <{}>", pp_type)

                # temporarily save the data extraction output
                tmp_outfile = os.path.join(output_dir, out_filename + ".tmp")
                # call data extraction
                if data_type != "OBS" and "multim-forecast" not in datasets:
                    arki.arkimet_extraction(datasets, query, tmp_outfile)
                else:
                    # dballe_extraction(datasets, filters, reftime, outfile)
                    observed_extraction(
                        user_id,
                        output_dir,
                        db,
                        datasets,
                        filters,
                        reftime,
                        tmp_outfile,
                        amqp_queue=amqp_queue,
                        schedule_id=schedule_id,
                    )

                # case of single postprocessor
                if len(postprocessors) == 1:
                    try:
                        p = postprocessors[0]
                        pp_type = p.get("processor_type")

                        if pp_type == "derived_variables":
                            pp1_output = pp1.pp_derived_variables(
                                datasets=datasets,
                                params=p,
                                tmp_extraction=tmp_outfile,
                                user_dir=output_dir,
                                fileformat=dataset_format,
                            )
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ["cat", tmp_outfile, pp1_output]
                            with open(outfile, mode="w") as out:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=out)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception("Failure in data extraction")

                        elif pp_type == "statistic_elaboration":
                            params = []
                            params.append(p)
                            pp2.pp_statistic_elaboration(
                                params=params,
                                input=tmp_outfile,
                                output=outfile,
                                fileformat=dataset_format,
                            )

                        elif pp_type == "grid_interpolation":
                            pp3_1.pp_grid_interpolation(
                                params=p, input=tmp_outfile, output=outfile
                            )

                        elif pp_type == "grid_cropping":
                            pp3_2.pp_grid_cropping(
                                params=p, input=tmp_outfile, output=outfile
                            )

                        elif pp_type == "spare_point_interpolation":
                            # change output extension from .grib to .BUFR
                            outfile_name, outfile_ext = os.path.splitext(out_filename)
                            out_filename = outfile_name + ".BUFR"
                            outfile = os.path.join(output_dir, out_filename)
                            # bufr_outfile = outfile_name+'.BUFR'
                            # pp3_3.pp_sp_interpolation(params=p, input=tmp_outfile, output=bufr_outfile,fileformat=dataset_format)
                            pp3_3.pp_sp_interpolation(
                                params=p,
                                input=tmp_outfile,
                                output=outfile,
                                fileformat=dataset_format,
                            )

                    finally:
                        # always remove tmp file
                        tmp_filelist = glob.glob(os.path.join(output_dir, "*.tmp"))
                        for f in tmp_filelist:
                            os.remove(f)
                        # if pp_type == 'spare_point_interpolation':
                        #     # remove the temporary folder where the files for the interpolation were uploaded
                        #     uploaded_filepath = Path(p.get('coord-filepath'))
                        #     shutil.rmtree(uploaded_filepath.parent)

                # case of multiple postprocessor
                else:
                    try:

                        tmp_extraction_basename = os.path.basename(tmp_outfile)
                        pp_output = None
                        if any(
                            d["processor_type"] == "derived_variables"
                            for d in postprocessors
                        ):
                            p = next(
                                item
                                for item in postprocessors
                                if item["processor_type"] == "derived_variables"
                            )
                            pp1_output = pp1.pp_derived_variables(
                                datasets=datasets,
                                params=p,
                                tmp_extraction=tmp_outfile,
                                user_dir=output_dir,
                                fileformat=dataset_format,
                            )
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ["cat", tmp_outfile, pp1_output]
                            # new temp file as pp output
                            new_tmp_extraction_filename = tmp_extraction_basename.split(
                                "."
                            )[0] + "-pp1.{fileformat}.tmp".format(
                                fileformat=dataset_format
                            )
                            pp_output = os.path.join(
                                output_dir, new_tmp_extraction_filename
                            )
                            with open(pp_output, mode="w") as pp1_outfile:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=pp1_outfile)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception("Failure in data extraction")
                        if any(
                            d["processor_type"] == "statistic_elaboration"
                            for d in postprocessors
                        ):
                            p = []
                            for item in postprocessors:
                                if item["processor_type"] == "statistic_elaboration":
                                    p.append(item)
                            # check if the input has to be the previous postprocess output
                            pp_input = ""
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split(
                                "."
                            )[0] + "-pp2.{fileformat}.tmp".format(
                                fileformat=dataset_format
                            )
                            pp_output = os.path.join(
                                output_dir, new_tmp_extraction_filename
                            )
                            pp2.pp_statistic_elaboration(
                                params=p,
                                input=pp_input,
                                output=pp_output,
                                fileformat=dataset_format,
                            )
                        if any(
                            d["processor_type"] == "grid_cropping"
                            for d in postprocessors
                        ):
                            p = next(
                                item
                                for item in postprocessors
                                if item["processor_type"] == "grid_cropping"
                            )
                            # check if the input has to be the previous postprocess output
                            pp_input = ""
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split(
                                "."
                            )[0] + "-pp3_2.{fileformat}.tmp".format(
                                fileformat=dataset_format
                            )
                            pp_output = os.path.join(
                                output_dir, new_tmp_extraction_filename
                            )
                            pp3_2.pp_grid_cropping(
                                params=p, input=pp_input, output=pp_output
                            )
                        if any(
                            d["processor_type"] == "grid_interpolation"
                            for d in postprocessors
                        ):
                            p = next(
                                item
                                for item in postprocessors
                                if item["processor_type"] == "grid_interpolation"
                            )
                            # check if the input has to be the previous postprocess output
                            pp_input = ""
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split(
                                "."
                            )[0] + "-pp3_1.{fileformat}.tmp".format(
                                fileformat=dataset_format
                            )
                            pp_output = os.path.join(
                                output_dir, new_tmp_extraction_filename
                            )
                            pp3_1.pp_grid_interpolation(
                                params=p, input=pp_input, output=pp_output
                            )
                        if any(
                            d["processor_type"] == "spare_point_interpolation"
                            for d in postprocessors
                        ):
                            p = next(
                                item
                                for item in postprocessors
                                if item["processor_type"] == "spare_point_interpolation"
                            )
                            # check if the input has to be the previous postprocess output
                            pp_input = ""
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            # new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp3_3.grib.tmp'
                            new_tmp_extraction_filename = (
                                tmp_extraction_basename.split(".")[0] + ".bufr"
                            )
                            out_filename = new_tmp_extraction_filename
                            pp_output = os.path.join(
                                output_dir, new_tmp_extraction_filename
                            )
                            pp3_3.pp_sp_interpolation(
                                params=p,
                                input=pp_input,
                                output=pp_output,
                                fileformat=dataset_format,
                            )
                        # rename the final output of postprocessors as outfile unless it is not a bufr file
                        if pp_output.split(".")[-1] != "bufr":
                            log.debug("dest: {}".format(str(outfile)))
                            os.rename(pp_output, outfile)
                        # else:
                        #     # if it is a bufr file, the filename resulting from the pp is will be the new outifle filename
                        #     outfile = pp_output
                    finally:
                        log.debug("end of multiple postprocessors")
                    #     # remove all tmp file
                    #     tmp_filelist = glob.glob(os.path.join(output_dir, "*.tmp"))
                    #     for f in tmp_filelist:
                    #         os.remove(f)
                    # if there is, remove the temporary folder where the files for the sp_interpolation were uploaded
                    # if os.path.isdir(os.path.join(UPLOAD_PATH,uuid)):
                    #     shutil.rmtree(os.path.join(UPLOAD_PATH,uuid))
            else:
                if data_type != "OBS" and "multim-forecast" not in datasets:
                    arki.arkimet_extraction(datasets, query, outfile)
                else:
                    # dballe_extraction(datasets, filters, reftime, outfile)
                    observed_extraction(
                        user_id,
                        output_dir,
                        db,
                        datasets,
                        filters,
                        reftime,
                        outfile,
                        amqp_queue=amqp_queue,
                        schedule_id=schedule_id,
                    )

            if output_format:
                filebase, fileext = os.path.splitext(out_filename)
                input = os.path.join(output_dir, out_filename)
                output = os.path.join(output_dir, filebase + "." + output_format)
                out_filepath = output_formatting.pp_output_formatting(
                    output_format, input, output
                )
                out_filename = os.path.basename(out_filepath)
                # rename outfile correctly
                outfile = os.path.join(output_dir, out_filename)

            if not amqp_queue:
                # get the actual data size
                data_size = os.path.getsize(os.path.join(output_dir, out_filename))
                log.debug(f"Actual resulting data size: {data_size}")
                if data_type != "OBS" and "multim-forecast" not in datasets:
                    if data_size > esti_data_size:
                        log.warning(
                            "Actual resulting data exceeds estimation of {}",
                            human_size(data_size - esti_data_size),
                        )
                else:
                    # check if the user space is not exceeded (for the observations we can't calculate the esti_data_size so this check is done after the extraction)
                    check_user_quota(
                        user_id,
                        output_dir,
                        db,
                        output_filename=out_filename,
                        schedule_id=schedule_id,
                    )

            # target result
            target_filename = os.path.basename(outfile)

            # create fileoutput record in db
            if not amqp_queue:
                if not opendata or data_size > 0:
                    SqlApiDbManager.create_fileoutput_record(
                        db, user_id, request_id, target_filename, data_size
                    )
                    request.status = states.SUCCESS
                else:
                    # remove the empty output file
                    if os.path.exists(outfile):
                        os.remove(outfile)
                    request.status = states.FAILURE
                    request.error_message = "The resulting output file was empty"
            else:
                # update request status
                request.status = states.SUCCESS

        except ReferenceError as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(state=states.FAILURE, meta=str(exc))
            raise Ignore()
        except DiskQuotaException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(state=states.FAILURE, meta=str(exc))
            raise Ignore()
        except PostProcessingException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(state=states.FAILURE, meta=str(exc))
            raise Ignore()
        except AccessToDatasetDenied as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(state=states.FAILURE, meta=str(exc))
            raise Ignore()
        except EmptyOutputFile as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(state=states.FAILURE, meta=str(exc))
            raise Ignore()

        except Exception as exc:
            # handle all the other exceptions
            request.status = states.FAILURE
            request.error_message = "Failed to extract data"
            log.exception("Failed to extract data: {}", repr(exc))
            raise exc
        finally:
            if output_dir:
                # remove tmp file
                tmp_filelist = glob.glob(os.path.join(output_dir, "*.tmp"))
                for f in tmp_filelist:
                    os.remove(f)

            request.end_date = datetime.datetime.utcnow()
            db.session.commit()
            log.info("Terminate task {} with state {}", self.request.id, request.status)
            if amqp_queue:
                extra_msg = push_data_to_queue(amqp_queue, outfile, output_dir, request)
            notificate_by_email(db, user_id, request, extra_msg, amqp_queue)


def check_user_quota(
    user_id,
    user_dir,
    db,
    datasets=None,
    query=None,
    output_filename=None,
    schedule_id=None,
):
    if datasets:
        # check the output size
        esti_data_size = arki.estimate_data_size(datasets, query)
    elif output_filename:
        esti_data_size = os.path.getsize(os.path.join(user_dir, output_filename))

    log.debug(
        "Resulting output size: {} ({})", esti_data_size, human_size(esti_data_size)
    )
    # check for current used space
    used_quota = int(subprocess.check_output(["du", "-sb", user_dir]).split()[0])
    log.info("Current used space: {} ({})", used_quota, human_size(used_quota))

    # check for exceeding quota
    max_user_quota = db.session.query(db.User.disk_quota).filter_by(id=user_id).scalar()
    log.debug("MAX USER QUOTA for user<{}>: {}", user_id, max_user_quota)
    if used_quota + esti_data_size > max_user_quota:
        free_space = max(max_user_quota - used_quota, 0)
        # save error message in db
        message = "Disk quota exceeded: required size {}; remaining space {}".format(
            human_size(esti_data_size), human_size(free_space)
        )
        # check if this request comes from a schedule. If so deactivate the schedule.
        if schedule_id is not None:
            # load schedule for this request
            schedule = db.Schedule.query.get(schedule_id)
            log.debug("Deactivate periodic task for schedule {}", schedule_id)
            if schedule.on_data_ready is False:
                if not CeleryExt.delete_periodic_task(name=str(schedule_id)):
                    raise Exception(
                        f"Cannot delete periodic task for schedule {schedule_id}"
                    )
            SqlApiDbManager.update_schedule_status(db, schedule_id, False)
            message += f' <br/><br/>Schedule "{schedule.name}" was temporary disabled for limit quota exceeded.'
        # for already extracted observed data, delete the file
        if output_filename:
            fileoutput = os.path.join(user_dir, output_filename)
            os.remove(fileoutput)

        raise DiskQuotaException(message)
    return esti_data_size


def observed_extraction(
    user_id,
    user_dir,
    db,
    datasets,
    filters,
    reftime,
    outfile,
    amqp_queue=None,
    schedule_id=None,
):
    # parsing the query
    fields, queries = dballe.parse_query_for_data_extraction(datasets, filters, reftime)

    # get db type
    if reftime:
        db_type = dballe.get_db_type(
            date_min=queries[fields.index("datetimemin")][0],
            date_max=queries[fields.index("datetimemax")][0],
        )
    else:
        db_type = "mixed"

    queried_reftime = None
    if "multim-forecast" in datasets:
        # multimodel case
        if reftime:
            interval = None
            queried_reftime = queries[fields.index("datetimemax")][0]
            # extend the reftime
            # datetimemin, datetimemax se timerange in query diventa interval il timerange maggiore
            q_for_multimodel_reftime = {}
            q_for_multimodel_reftime["datetimemin"] = queries[
                fields.index("datetimemin")
            ][0]
            # check if the datetimemin coincide with a multimodel run
            if (
                not q_for_multimodel_reftime["datetimemin"].hour == 0
                and q_for_multimodel_reftime["datetimemin"].minute == 0
            ):
                first_run = (
                    q_for_multimodel_reftime["datetimemin"] + datetime.timedelta(days=1)
                ).replace(hour=0, minute=0)
                if queried_reftime < first_run:
                    # the result will be empty
                    raise EmptyOutputFile("The requested query does not giany results")
                else:
                    q_for_multimodel_reftime["datetimemin"] = queries[
                        fields.index("datetimemin")
                    ][0] = first_run
            q_for_multimodel_reftime["datetimemax"] = queries[
                fields.index("datetimemax")
            ][0]
            max_trange_interval = None
            if ["trange"] in fields:
                req_trange_list = queries[fields.index("trange")]
                for t in req_trange_list:
                    if not max_trange_interval:
                        # get the timerange p1 value
                        max_trange_interval = t[1]
                    else:
                        if t[1] > max_trange_interval:
                            max_trange_interval = t[1]
            if max_trange_interval:
                # get the timerange p1 in hour as interval to extend the reftime fo multimodel query
                interval = max_trange_interval / 3600
            queries[fields.index("datetimemax")][
                0
            ] = dballe.extend_reftime_for_multimodel(
                q_for_multimodel_reftime, db_type, interval
            )
            if db_type == "arkimet":
                # check if db_type is changed (from arkimet to mixed) with the extended query
                db_type = dballe.get_db_type(
                    date_min=queries[fields.index("datetimemin")][0],
                    date_max=queries[fields.index("datetimemax")][0],
                )

    if db_type == "arkimet" and not amqp_queue:
        # check using arkimet if the estimated filesize does not exceed the disk quota
        query = ""
        if reftime:
            query = arki.parse_reftime(reftime["from"], reftime["to"])
        check_user_quota(
            user_id,
            user_dir,
            db,
            datasets=datasets,
            query=query,
            schedule_id=schedule_id,
        )

    # extract the data
    if db_type == "mixed":
        # TODO
        dballe.extract_data_for_mixed(
            datasets, fields, queries, outfile, queried_reftime
        )
    else:
        dballe.extract_data(
            datasets, fields, queries, outfile, db_type, queried_reftime
        )


def notificate_by_email(db, user_id, request, extra_msg, amqp_queue=None):
    """Send email notification. """
    user_email = db.session.query(db.User.email).filter_by(id=user_id).scalar()
    if amqp_queue:
        body_msg = request.error_message or f"Your data has been pushed to {amqp_queue}"
    else:
        body_msg = request.error_message or "Your data is ready for downloading"
    body_msg += extra_msg

    replaces = {"title": request.name, "status": request.status, "message": body_msg}
    body = get_html_template("data_extraction_result.html", replaces)
    with smtp.get_instance() as smtp_client:
        smtp_client.send(
            body, "MeteoHub: data extraction completed", user_email, plain_body=body
        )


def push_data_to_queue(amqp_queue, outfile, output_dir, request):
    # send a message in the queue
    extra_msg = ""
    try:
        with rabbitmq.get_instance() as rabbit:
            # case 1 if output send the file
            if os.path.exists(outfile):
                filebase, fileext = os.path.splitext(outfile)
                if fileext == ".json":
                    with open(outfile) as f:
                        jsondata = json.dumps(f.read())
                        rabbit_msg = json.loads(jsondata)
                    rabbit.send_json(
                        rabbit_msg,
                        routing_key=amqp_queue,
                    )
                else:
                    with open(outfile, "rb") as f:
                        rabbit_msg = f.read()
                    rabbit.send(
                        rabbit_msg,
                        routing_key=amqp_queue,
                    )
                log.debug("sending fileoutput to {}", amqp_queue)
            # case 2 no output --> notify failure and error message
            else:
                rabbit_msg = request.error_message
                log.debug("no output: sending error message to {}", amqp_queue)
                rabbit.send_json(
                    rabbit_msg,
                    routing_key=amqp_queue,
                )

            rabbit.disconnect()
    except BaseException:
        extra_msg = f"failed communication with {amqp_queue} amqp queue"
    finally:
        if os.path.exists(output_dir):
            # to be sure it is the tmp dir
            if "/data/tmp_outfiles" in output_dir:
                shutil.rmtree(output_dir)
        return extra_msg


def human_size(bytes, units=[" bytes", "KB", "MB", "GB", "TB", "PB", "EB"]):
    """Returns a human readable string reprentation of bytes
    :rtype: string
    """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


def adapt_reftime(db, schedule, reftime):
    new_reftime = None
    if reftime is not None:
        new_reftime = {}
        time_delta_from = schedule.time_delta
        # get the interval
        if not schedule.is_crontab:
            schedule_interval = datetime.timedelta(
                **{schedule.period.name: schedule.every}
            )
        else:
            cron_settings = json.loads(schedule.crontab_settings)
            if "day_of_week" in cron_settings:
                schedule_interval = datetime.timedelta(
                    **{"days": cron_settings["day_of_week"]}
                )
            elif "day_of_month" in cron_settings:
                if not "month of year" in cron_settings:
                    days_in_month_dict = {
                        1: 31,
                        2: 28,
                        3: 31,
                        4: 30,
                        5: 31,
                        6: 30,
                        7: 31,
                        8: 31,
                        9: 30,
                        10: 31,
                        11: 30,
                        12: 31,
                    }
                    # interval is the number of the day of the past month
                    schedule_interval = datetime.timedelta(
                        **{
                            "days": days_in_month_dict[
                                datetime.datetime.now().month - 1
                            ]
                        }
                    )
                else:
                    schedule_interval = datetime.timedelta(days=365)
            else:
                schedule_interval = datetime.timedelta(days=1)

        # check if there are submitted requests
        last_r = (
            db.Request.query.filter_by(schedule_id=schedule.id)
            .order_by(db.Request.submission_date.desc())
            .first()
        )
        if last_r:
            # get the reftime of the last submitted request
            if last_r.args["reftime"]:
                last_reftime_to = datetime.datetime.strptime(
                    last_r.args["reftime"]["to"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
        else:
            # get the reftime of the schedule
            last_reftime_to = datetime.datetime.strptime(
                reftime["to"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )

        now = datetime.datetime.utcnow()
        # get the delta for the reftime to (including the case a schedule has been switched off for some time)
        time_delta_to = schedule_interval * (
            int((now - last_reftime_to) / schedule_interval)
        )
        # get the new reftimes
        new_reftime_to = last_reftime_to + time_delta_to
        new_reftime_from = new_reftime_to - time_delta_from
        new_reftime["from"] = new_reftime_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        new_reftime["to"] = new_reftime_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return new_reftime


def package_data_license(user_dir, out_file, license_file):
    """
    Create a tar.gz including output and license files.
    :param user_dir:
    :param out_file:
    :param license_file:
    :return:
    """
    utc_now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ.%f")
    tar_filename = f"data-{utc_now}.tar.gz"
    tar_file = os.path.join(user_dir, tar_filename)
    with tarfile.open(tar_file, "w:gz") as tar:
        log.debug("--TAR ARCHIVE-------------------------")
        log.debug("data file: {}", out_file)
        tar.add(out_file, arcname=os.path.basename(out_file))
        log.debug("license file: {}", license_file)
        tar.add(license_file, arcname="LICENSE")
        log.debug("--------------------------------------")
    # delete out_filename
    os.remove(out_file)
    return tar_filename
