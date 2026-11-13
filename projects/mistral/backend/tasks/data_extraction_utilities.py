from datetime import datetime, timedelta, timezone

from restapi.utilities.logs import log


def queue_sorting(dataset_type, reftime=None):
    queue_map = {
        ("FOR", False): "archived_forecast",
        ("FOR", True): "operational_forecast",
        ("SEA", False): "archived_forecast",
        ("SEA", True): "operational_forecast",
        ("RAD", False): "archived_observed",
        ("RAD", True): "operational_observed",
        ("OBS", False): "archived_observed",
        ("OBS", True): "operational_observed",
    }
    days_for_operationals = timedelta(days=3)

    now = datetime.now(timezone.utc)
    date_from = None
    if reftime is not None and reftime.get("date_from") is not None:
        date_from = reftime["date_from"]
        # add timezone if it does not have it
        if date_from.tzinfo is None or date_from.tzinfo.utcoffset(date_from) is None:
            date_from = date_from.replace(tzinfo=timezone.utc)

    is_operational = date_from is not None and (now - date_from) < days_for_operationals
    lookup_key = (dataset_type, is_operational)
    if lookup_key not in queue_map:
        # no default queue: a request for an unsupported dataset type is not sent
        raise ValueError(f"Unsupported dataset type: {dataset_type}")
    celery_queue = queue_map[lookup_key]
    return celery_queue
