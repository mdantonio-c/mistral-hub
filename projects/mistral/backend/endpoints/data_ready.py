import datetime
import os

from mistral.services.arkimet import BeArkimet as arki
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import celery, sqlalchemy
from restapi.models import fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log


class DataReady(EndpointResource):
    @decorators.auth.require()
    @decorators.use_kwargs(
        {
            "cluster": fields.String(required=True, data_key="Cluster"),
            "model": fields.String(required=True, data_key="Model"),
            "rundate": fields.DateTime(required=True, format="%Y%m%d%H"),
        }
    )
    @decorators.endpoint(
        path="/data/ready",
        summary="Notify that a dataset is ready",
        responses={202: "Notification received"},
    )
    def post(self, cluster, model, rundate):

        cluster = cluster.lower()
        log.info("Cluster = {}\tModel = {}\trundate = {}", cluster, model, rundate)

        # check which cluster is currently exported on filesystem
        if cluster == "g100" or cluster == "galileo" or cluster == "meucci":
            exported_platform = os.environ.get("PLATFORM", "G100").lower()
            if exported_platform != cluster:
                log.debug(
                    "The endpoint was called by {} while the exported platform is {}",
                    cluster,
                    exported_platform,
                )
                return self.response("1", code=202)

        db = sqlalchemy.get_instance()

        schedules_list = db.Schedule.query.all()
        log.debug("rundate type: {}", type(rundate))
        log.debug("reftime {}", rundate.isoformat())
        for row in schedules_list:
            r = SqlApiDbManager._get_schedule_response(row)

            # e.g. 13
            request_id = r["id"]

            # e.g. DEmo-scheduled
            request_name = r["name"]

            name = f"{request_name} (id={request_id})"

            # e.g. True
            enabled = r["enabled"]
            if not enabled:
                log.debug("Skipping {}: schedule is not enabled", name)
                continue

            # e.g. True
            on_data_ready = r["on_data_ready"]
            if not on_data_ready:
                log.debug("Skipping {}: schedule is not on_data_ready", name)
                continue

            # e.g. '2019-12-13T15:52:30.834060'
            # creation_date = r['creation_date']

            # e.g. ['lm5']
            datasets = r["args"]["datasets"]

            if len(datasets) == 0:
                log.warning(
                    "Schedule {} requires no dataset: {}, skipping", name, datasets
                )
                continue

            if len(datasets) >= 2:
                # Still unsupported
                log.warning(
                    "Schedule {} requires more than a dataset: {}, skipping",
                    name,
                    datasets,
                )
                continue

            if datasets[0] != model:
                log.debug(
                    "Skipping {}: schedule is looking for dataset {}", name, datasets
                )
                continue

            # check if schedule is requesting a runhour
            filters = r["args"]["filters"]
            if filters and "run" in filters:
                requested_runs = []
                for e in filters["run"]:
                    run_arg = arki.decode_run(e)
                    splitted_run = run_arg.split(",")
                    requested_runs.append(splitted_run[1])
                log.debug("runs: {}", requested_runs)
                runhour = str(rundate.time())[0:5]
                if runhour not in requested_runs:
                    log.debug(
                        "Skipping {}: schedule is requesting {} runhour",
                        name,
                        requested_runs,
                    )
                    continue

            # check if there are others schedule params
            if r["period"] or r["crontab_set"]:
                req_date = datetime.datetime.strptime(
                    rundate.isoformat(), "%Y-%m-%dT%H:%M:%S"
                )
                # get the last request
                last_req = SqlApiDbManager.get_last_scheduled_request(db, r["id"])
                if last_req:
                    submission_date = datetime.datetime.strptime(
                        last_req["submission_date"], "%Y-%m-%dT%H:%M:%S.%f"
                    ).date()
                else:
                    # if there aren't any previous requests consider
                    # the submission date of the schedule itself
                    submission_date = datetime.datetime.strptime(
                        r["creation_date"], "%Y-%m-%dT%H:%M:%S.%f"
                    ).date()
                # periodic schedules
                if r["period"] == "days":
                    day_interval = r["every"]
                    timedelta = datetime.timedelta(days=day_interval)
                    next_submission = submission_date + timedelta
                    if req_date.date() != next_submission:
                        log.debug(
                            "Skipping {}: scheduling period does not coincide",
                            name,
                        )
                        continue
                # crontab schedules
                elif r["crontab_set"]:
                    crontab_dic = eval(r["crontab_set"])
                    if "day_of_month" in crontab_dic and "month_of_year" in crontab_dic:
                        if (
                            req_date.day != crontab_dic["day_of_month"]
                            or req_date.month != crontab_dic["month_of_year"]
                        ):
                            log.debug(
                                "Skipping {}: scheduling is for {}/{}",
                                name,
                                crontab_dic["month_of_year"],
                                crontab_dic["day_of_month"],
                            )
                            continue
                    elif "day_of_week" in crontab_dic:
                        if req_date.weekday() != crontab_dic["day_of_week"]:
                            log.debug(
                                "Skipping {}: schedule is for an other day of the week",
                                name,
                            )
                            continue

            log.info("Checking schedule: {}\n{}", name, r)

            reftime = {
                "from": rundate.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "to": rundate.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }

            filters = r["args"].get("filters")
            processors = r["args"].get("processors")
            output_format = r["args"].get("output_format")
            pushing_queue = r["args"].get("pushing_queue")
            opendata = r["opendata"]

            try:

                c = celery.get_instance()
                # copied from "submit first request for scheduled ondataready
                request_to_be_created_id = None
                data_ready = True
                c.celery_app.send_task(
                    "data_extract",
                    args=[
                        r.get("user_id"),
                        datasets,
                        reftime,
                        filters,
                        processors,
                        output_format,
                        request_to_be_created_id,
                        None,
                        pushing_queue,
                        request_id,
                        data_ready,
                        opendata,
                    ],
                    countdown=1,
                )

                log.info("Request successfully submitted: <ID:{}>", request_id)
            except Exception as error:
                log.error(error)
                raise SystemError("Unable to submit the request")

        return self.response("1", code=202)
