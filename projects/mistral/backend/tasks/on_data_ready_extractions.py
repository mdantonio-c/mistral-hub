import json
from datetime import datetime, timedelta

from mistral.services.arkimet import BeArkimet as arki
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi.connectors import celery, sqlalchemy
from restapi.connectors.celery import CeleryExt
from restapi.utilities.logs import log
from sqlalchemy.orm import object_session


@CeleryExt.task(idempotent=False)
def launch_all_on_data_ready_extractions(
    self,
    model,
    rundate,
):
    log.info("Start task [{}:{}]", self.request.id, self.name)

    db = sqlalchemy.get_instance()
    schedules_list = db.Schedule.query.all()
    log.debug("rundate type: {}", type(rundate))
    log.debug("reftime {}", rundate.isoformat())
    for row in schedules_list:
        if object_session(row) is None:
            row = db.session.merge(row)
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
            log.warning("Schedule {} requires no dataset: {}, skipping", name, datasets)
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
            log.debug("Skipping {}: schedule is looking for dataset {}", name, datasets)
            continue

        # check if schedule is requesting a runhour
        runhour = str(rundate.time())[0:5]
        filters = r["args"]["filters"]
        if filters and "run" in filters:
            requested_runs = []
            for e in filters["run"]:
                try:
                    run_arg = arki.decode_run(e)
                except ValueError:
                    log.error(f"Skipping: unable to decode run {e}")
                    continue
                splitted_run = run_arg.split(",")
                requested_runs.append(splitted_run[1])
            log.debug("runs: {}", requested_runs)
            if runhour not in requested_runs:
                log.debug(
                    "Skipping {}: schedule is requesting {} runhour",
                    name,
                    requested_runs,
                )
                continue

        # check if there are others schedule params
        if r["period"] or r["crontab_set"]:

            req_date = rundate

            # get the last request
            last_req = SqlApiDbManager.get_last_scheduled_request(db, r["id"])

            # dates are serialized with isoformat(), that omits zero microseconds
            if last_req:

                submission_date = datetime.fromisoformat(
                    last_req["submission_date"]
                ).date()

            else:
                # if there aren't any previous requests consider
                # the submission date of the schedule itself
                submission_date = datetime.fromisoformat(r["creation_date"]).date()
            # periodic schedules
            if r["period"] == "days":
                day_interval = r["every"]
                next_submission = submission_date + timedelta(days=day_interval)
                # a missed event does not block the schedule:
                # it restarts with the first event after the expected date
                if req_date.date() < next_submission:
                    log.debug(
                        "Skipping {}: scheduling period has not elapsed yet",
                        name,
                    )
                    continue
            # crontab schedules
            elif r["crontab_set"]:
                crontab_dic = json.loads(r["crontab_set"])
                # all the settings have to match, as in the celery crontab used by
                # the other schedules: day_of_week has sunday = 0
                if (
                    (
                        "day_of_week" in crontab_dic
                        and req_date.isoweekday() % 7 != crontab_dic["day_of_week"]
                    )
                    or (
                        "day_of_month" in crontab_dic
                        and req_date.day != crontab_dic["day_of_month"]
                    )
                    or (
                        "month_of_year" in crontab_dic
                        and req_date.month != crontab_dic["month_of_year"]
                    )
                ):
                    log.debug(
                        "Skipping {}: crontab settings {} do not match the run date",
                        name,
                        crontab_dic,
                    )
                    continue

        log.info("Checking schedule: {}\n{}", name, r)
        reftime = {
            "from": rundate.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "to": rundate.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }

        filters = r["args"].get("filters")
        postprocessors = r["args"].get("postprocessors")
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
                args=(
                    r.get("user_id"),
                    datasets,
                    reftime,
                    filters,
                    postprocessors,
                    output_format,
                    request_to_be_created_id,
                    None,
                    pushing_queue,
                    request_id,
                    data_ready,
                    opendata,
                ),
                countdown=1,
                queue="operational_forecast",
                routing_key="operational_forecast",
            )

            log.info(
                "Data ready request extraction successfully submitted: <ID:{}>",
                request_id,
            )
        except Exception as error:
            log.error(
                "Task [{}:{}], launching data ready request extraction failed with error: {}",
                self.request.id,
                self.name,
                error,
            )
            log.info(
                "Terminated task [{}:{}] due to error.",
                self.request.id,
                self.name,
            )
            raise SystemError("Unable to submit the data ready request extraction")

    log.info("Successfully terminated task [{}:{}]", self.request.id, self.name)
