from datetime import datetime, timedelta

from mistral.services.arkimet import BeArkimet as arki
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi.connectors import celery, sqlalchemy
from restapi.utilities.logs import log


db = sqlalchemy.get_instance()
schedules_list = db.Schedule.query.filter_by(user_id="61", is_enabled=True).all()
today= datetime.now().date()
run_list=[]
for i in range(7):
    day = today - timedelta(days=i)
    midnight = datetime.combine(day, datetime.min.time())  # 00:00
    noon = datetime.combine(day, datetime.min.time().replace(hour=12))  # 12:00
    run_list.append(midnight)
    run_list.append(noon)

for row in schedules_list:
    for rundate in run_list:
        r = SqlApiDbManager._get_schedule_response(row)
        request_id = r["id"]
        request_name = r["name"]
        name = f"{request_name} (id={request_id})"
        datasets = r["args"]["datasets"]
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
        if request_name == "radar opendata" or request_name == "multimodel opendata":
            runhour = str(rundate.time())[0:5]
            if runhour != 00:
                continue
            rundate_from = rundate.replace(hour=00, minute=00, second=0, microsecond=0)
            rundate_to = rundate.replace(hour=23, minute=55, second=0, microsecond=0)
            reftime = {
                "from": rundate_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "to": rundate_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
        else:
            reftime = {
                "from": rundate.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "to": rundate.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }

        filters = r["args"].get("filters")
        postprocessors = r["args"].get("postprocessors")
        output_format = r["args"].get("output_format")
        pushing_queue = r["args"].get("pushing_queue")
        opendata = r["opendata"]

        c = celery.get_instance()
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
        )

        log.info("Request successfully submitted: <ID:{}>", request_id)