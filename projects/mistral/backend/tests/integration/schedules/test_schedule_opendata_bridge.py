"""Integration tests for the bridge between data-ready schedules and opendata.

These scenarios verify the end-to-end handoff from a schedule-generated request
to the creation of an opendata package that can later be listed and downloaded.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

import mistral.endpoints.data_ready as data_ready_endpoint
import mistral.endpoints.schedules as schedules_endpoint
import mistral.tasks.on_data_ready_extractions as on_data_ready_task
from mistral.tests.helpers.celery_fakes import (
    AcceptTasksWithoutRunningCelery,
    InlineDataExtractCelery,
)
from mistral.tests.helpers.schedules import (
    build_crontab_schedule,
    build_on_data_ready_schedule,
)
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
    register_schedule_cleanup,
    trigger_data_ready_and_wait_accepted,
    wait_for_schedule_requests,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window
from mistral.tests.helpers.polling import wait_until


pytestmark = [pytest.mark.integration, pytest.mark.runtime_sensitive]

BRIDGE_DATASET_NAME = DATA_READY_DATASET_NAME


class ScheduleRequestFailed(AssertionError):
    """Raised when a schedule-generated request reaches FAILURE while polling."""

    pass


# =============================================================================
# Two Test Paths: On-Data-Ready (Inline) vs. Crontab (RedBeat/Beat)
# =============================================================================
# This file tests the bridge from schedules to opendata in two ways:
#
# 1. ON-DATA-READY path (test_on_data_ready_schedule_publishes_opendata_package):
#    - The test monkeypatches Celery to intercept tasks before they hit the broker.
#    - The /api/data/ready endpoint is reached, the task is accepted locally,
#      and the nested data_extract task runs immediately in-process.
#    - The entire flow is synchronous and deterministic within the test.
#    - Use this path when you want to verify endpoint logic and immediate extraction.
#
# 2. CRONTAB path (test_crontab_schedule_publishes_opendata_package):
#    - The test creates a real schedule entry in Redis using RedBeat (the scheduler backend).
#    - The running celerybeat container picks up that entry from Redis.
#    - When the scheduled minute arrives, celerybeat puts the task in the RabbitMQ broker.
#    - The async celery workers consume the task and execute the extraction.
#    - The test polls for the result, waiting for both beat and workers to do their work.
#    - Use this path when you want to verify real schedule persistence and async execution.
#
# The on-data-ready path is faster and fully isolated; the crontab path exercises
# real infrastructure (Redis, RabbitMQ, celerybeat, workers) and is therefore a
# more complete integration test.
# =============================================================================


def _trigger_data_ready_schedule_inline(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    schedules_admin_headers,
    *,
    model: str,
    rundate: str,
):
    """Drive one data-ready schedule to a real inline extraction.

    The test keeps the real HTTP endpoint and the real data-ready scheduling
    logic, but replaces the Celery transport twice:

    - the endpoint submission is accepted locally instead of going to the broker,
    - the nested ``data_extract`` task is executed immediately in-process.
    """
    monkeypatch.setattr(
        data_ready_endpoint.celery,
        "get_instance",
        lambda: AcceptTasksWithoutRunningCelery(
            "launch_all_on_data_ready_extractions"
        ),
    )
    response = trigger_data_ready_and_wait_accepted(
        client,
        schedules_admin_headers,
        model=model,
        rundate=rundate,
    )
    monkeypatch.setattr(
        on_data_ready_task.celery,
        "get_instance",
        lambda: InlineDataExtractCelery(),
    )
    on_data_ready_task.launch_all_on_data_ready_extractions.run(
        model,
        datetime.strptime(rundate, "%Y%m%d%H"),
    )
    return response


def _wait_for_successful_schedule_request(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
    *,
    timeout: float = 120,
    interval: float = 5,
    grace_timeout: float = 0,
) -> dict[str, Any]:
    """Poll one schedule until it exposes a successful request with a real file output.

    The normal timeout covers the expected dispatch window. A second optional
    grace window exists only for the async-real crontab path, where celerybeat
    and workers may occasionally surface the request later than the nominal
    bound even though the flow eventually succeeds.
    """
    def successful_request():
        """Return the request once it succeeds with a concrete output filename."""
        requests = list_schedule_requests(base, client, headers, schedule_id)
        if len(requests) != 1:
            return False

        request = requests[0]
        if request.get("status") == "FAILURE":
            raise ScheduleRequestFailed(
                request.get("error message")
                or f"Scheduled request {request['id']} failed"
            )

        if (
            request.get("status") == "SUCCESS"
            and request.get("fileoutput")
            and request.get("fileoutput") != "no file available"
        ):
            return request

        return False

    try:
        return wait_until(
            successful_request,
            timeout=timeout,
            interval=interval,
            message=(
                f"Expected schedule {schedule_id} to produce a successful opendata request"
            ),
        )
    except AssertionError:
        if grace_timeout <= 0:
            raise

    return wait_until(
        successful_request,
        timeout=grace_timeout,
        interval=interval,
        message=(
            "Expected schedule {schedule_id} to produce a successful opendata "
            "request even after the additional grace window"
        ).format(schedule_id=schedule_id),
    )


def _wait_for_listing_entry(
    client: FlaskClient,
    dataset_name: str,
    filename: str,
    headers: Any,
    *,
    query: str,
    timeout: float = 60,
    interval: float = 3,
) -> dict[str, Any]:
    """Poll the dataset opendata listing until a specific published filename appears."""
    endpoint = f"{API_URI}/datasets/{dataset_name}/opendata?q={query}"
    base = BaseTests()

    def listed_package():
        """Return the package row once the expected filename becomes visible in listing."""
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200
        content = base.get_content(response) or []
        for package in content:
            if package.get("filename") == filename:
                return package
        return False

    return wait_until(
        listed_package,
        timeout=timeout,
        interval=interval,
        message=(
            f"Expected opendata listing for dataset {dataset_name} to expose {filename}"
        ),
    )


def _next_crontab_run_time() -> datetime:
    """Return the next safe minute for a real crontab schedule execution.

    This helper is used only in the crontab path (see note at top of file).
    When the test starts too close to the current minute boundary, scheduling the
    task for the very next minute can race with RedBeat pickup and celerybeat.
    A small extra minute keeps the test deterministic while still much tighter
    than the legacy fixed sleeps.
    """
    now = datetime.now()
    minutes_ahead = 2 if now.second >= 45 else 1
    return now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_ahead)


@pytest.mark.deterministic
def test_on_data_ready_schedule_publishes_opendata_package(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    schedules_admin_headers,
    schedules_user,
) -> None:
    """Verify that a successful on-data-ready schedule publishes a downloadable opendata package."""
    # arrange
    dataset_window = fetch_dataset_window(
        client,
        schedules_user.headers,
        BRIDGE_DATASET_NAME,
    )
    schedule_body = build_on_data_ready_schedule(
        request_name="test_schedule_opendata_bridge",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[BRIDGE_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        opendata=True,
    )
    monkeypatch.setattr(
        schedules_endpoint.celery,
        "get_instance",
        lambda: AcceptTasksWithoutRunningCelery("data_extract"),
    )
    schedule_id = create_schedule(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_body,
    )
    register_schedule_cleanup(
        client,
        cleanup_registry,
        schedules_user.headers,
        schedule_id,
    )

    # act
    response = _trigger_data_ready_schedule_inline(
        monkeypatch,
        client,
        schedules_admin_headers,
        model=BRIDGE_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
    )
    published_request = _wait_for_successful_schedule_request(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_id,
    )
    listed_package = _wait_for_listing_entry(
        client,
        BRIDGE_DATASET_NAME,
        published_request["fileoutput"],
        schedules_user.headers,
        query=f"reftime:={dataset_window.ref_from.strftime('%Y-%m-%d %H:%M')}",
    )
    download_response = client.get(
        f"{API_URI}/opendata/{published_request['fileoutput']}",
        headers=schedules_user.headers,
    )

    try:
        # assert
        assert response.status_code == 202
        assert published_request["status"] == "SUCCESS"
        assert published_request["fileoutput"] == listed_package["filename"]
        assert listed_package["date"] == dataset_window.ref_from.strftime("%Y-%m-%d")
        assert download_response.status_code == 200
        assert download_response.data
        assert (
            published_request["fileoutput"]
            in download_response.headers["Content-Disposition"]
        )
    finally:
        download_response.close()


@pytest.mark.async_real
def test_crontab_schedule_publishes_opendata_package(
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    schedules_user,
) -> None:
    """Verify that a pure crontab schedule eventually publishes a downloadable opendata package."""
    # arrange
    dataset_window = fetch_dataset_window(
        client,
        schedules_user.headers,
        BRIDGE_DATASET_NAME,
    )
    trigger_at = _next_crontab_run_time()
    schedule_body = build_crontab_schedule(
        request_name="test_crontab_schedule_opendata_bridge",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[BRIDGE_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        hour=trigger_at.hour,
        minute=trigger_at.minute,
        opendata=True,
    )
    schedule_id = create_schedule(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_body,
    )
    register_schedule_cleanup(
        client,
        cleanup_registry,
        schedules_user.headers,
        schedule_id,
    )

    # act
    published_request = _wait_for_successful_schedule_request(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_id,
        timeout=180,
        interval=5,
        grace_timeout=180,
    )
    listed_package = _wait_for_listing_entry(
        client,
        BRIDGE_DATASET_NAME,
        published_request["fileoutput"],
        schedules_user.headers,
        query=(
            "reftime:>={date_from},<={date_to}".format(
                date_from=dataset_window.ref_from.strftime("%Y-%m-%d %H:%M"),
                date_to=dataset_window.ref_to.strftime("%Y-%m-%d %H:%M"),
            )
        ),
        timeout=60,
        interval=3,
    )
    download_response = client.get(
        f"{API_URI}/opendata/{published_request['fileoutput']}",
        headers=schedules_user.headers,
    )

    try:
        # assert
        assert published_request["status"] == "SUCCESS"
        assert published_request["fileoutput"] == listed_package["filename"]
        assert listed_package["date"] == "from {date_from} to {date_to}".format(
            date_from=dataset_window.ref_from.strftime("%Y-%m-%d"),
            date_to=dataset_window.ref_to.strftime("%Y-%m-%d"),
        )
        assert download_response.status_code == 200
        assert download_response.data
        assert (
            published_request["fileoutput"]
            in download_response.headers["Content-Disposition"]
        )
    finally:
        download_response.close()