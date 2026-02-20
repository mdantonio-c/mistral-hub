from datetime import timedelta
from typing import Any, Dict, List, Optional

from celery.schedules import crontab, schedule
from redbeat.schedulers import RedBeatSchedulerEntry
from restapi.connectors import celery


def create_periodic_task_with_routing(
    name: str,
    task: str,
    every: int,
    period="seconds",
    args=None,
    kwargs=None,
    queue=None,
    routing_key=None,
):
    """
    Function to extend builtin rapydo celery.create_periodic_task method.
    Accept queue and routing key as additional parameters
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    # Convert interval
    td = timedelta(**{period: every})
    interval = schedule(run_every=td)

    # Build options
    options = {}
    if queue:
        options["queue"] = queue
    if routing_key:
        options["routing_key"] = routing_key

    # Create the RedBeat entry directly
    c = celery.get_instance()
    entry = RedBeatSchedulerEntry(
        name=name,
        task=task,
        schedule=interval,
        args=args,
        kwargs=kwargs,
        options=options,
        app=c.celery_app,
    )

    entry.save()
    return entry


def create_crontab_task_with_routing(
    name: str,
    task: str,
    minute: str,
    hour: str,
    day_of_week: str = "*",
    day_of_month: str = "*",
    month_of_year: str = "*",
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    queue=None,
    routing_key=None,
) -> None:

    """
    Function to extend builtin rapydo celery.create_crontab_task method.
    Accept queue and routing key as additional parameters
    """

    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    interval = crontab(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
    )

    options = {}
    if queue:
        options["queue"] = queue
    if routing_key:
        options["routing_key"] = routing_key

    # Create the RedBeat entry directly
    c = celery.get_instance()
    entry = RedBeatSchedulerEntry(
        name, task, interval, args=args, options=options, app=c.celery_app
    )
    entry.save()
