from restapi.connectors import celery, rabbitmq, sqlalchemy
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi.utilities.logs import log

db = sqlalchemy.get_instance()
c = celery.get_instance()

# get all the schedules
schedules_list = db.Schedule.query.all()
for schedule in schedules_list:
    if not schedule.is_enabled:
        print(f"Skipping {schedule.id}: schedule is not enabled")
        continue
    if schedule.on_data_ready:
        print(f"Skipping {schedule.id}: schedule is on_data_ready")
        continue
    # retrieving celery task
    task = c.get_periodic_task(name=schedule.id)
    if task:
        print(f"Skipping {schedule.id}: schedule is already enabled: Periodic task - {task}")
        continue

    # recreate the schedule in celery retrieving the schedule from postgres
    schedule_response = SqlApiDbManager.get_schedule_by_id(db, schedule.id)
    #print(f"schedule response: {schedule_response}")

    # recreate the schedule in celery retrieving the schedule from postgres
    try:
        request_id = None
        if "periodic" in schedule_response:
            c.create_periodic_task(
                name=str(schedule.id),
                task="data_extract",
                every=schedule_response["every"],
                period=schedule_response["period"],
                args=[
                    schedule.user_id,
                    schedule_response["args"]["datasets"],
                    schedule_response["args"]["reftime"],
                    schedule_response["args"]["filters"],
                    schedule_response["args"]["postprocessors"],
                    schedule_response["args"]["output_format"],
                    request_id,
                    schedule_response["args"]["only_reliable"],
                    schedule_response["args"]["pushing_queue"],
                    schedule.id,
                    False,
                    schedule_response["opendata"],
                ],
            )

        if "crontab" in schedule_response:

            cronsettings = schedule_response["crontab_settings"]

            c.create_crontab_task(
                name=str(schedule.id),
                task="data_extract",
                minute=str(cronsettings.get("minute")),
                hour=str(cronsettings.get("hour")),
                day_of_week=str(cronsettings.get("day_of_week", "*")),
                day_of_month=str(cronsettings.get("day_of_month", "*")),
                month_of_year=str(cronsettings.get("month_of_year", "*")),
                args=[
                    schedule.user_id,
                    schedule_response["args"]["datasets"],
                    schedule_response["args"]["reftime"],
                    schedule_response["args"]["filters"],
                    schedule_response["args"]["postprocessors"],
                    schedule_response["args"]["output_format"],
                    request_id,
                    schedule_response["args"]["only_reliable"],
                    schedule_response["args"]["pushing_queue"],
                    schedule.id,
                    False,
                    schedule_response["opendata"],
                ],
            )

    except Exception as e:
        print(f"Unable to enable the request {schedule.id}. content {schedule_response}, exc: {e}")
