"""High-level helpers shared by the data-ready and schedule integration tests.

The data-ready area of the suite repeatedly performs the same kinds of setup:

- build a payload for ``/api/data/ready``,
- create a temporary user with the right dataset permissions,
- create or delete schedules and synthetic request rows,
- poll the API until asynchronous side effects become visible.

Keeping that logic here lets the test modules read as short behavior stories,
instead of being buried under repetitive API plumbing and cleanup details.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    register_test_user_cleanup,
)
from mistral.tests.helpers.polling import wait_until
from mistral.tests.helpers.runtime import TestRuntime
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

DATA_READY_DATASET_NAME = "lm5"
SECOND_DATA_READY_DATASET_NAME = "lm2.2"
DATA_READY_DATASETS = [DATA_READY_DATASET_NAME, SECOND_DATA_READY_DATASET_NAME]


def build_data_ready_payload(
    *,
    model: str,
    cluster: str = "g100",
    rundate: str,
) -> str:
    """Return the exact JSON body expected by the ``/api/data/ready`` endpoint.

    Tests call this helper when they want to trigger the data-ready workflow with
    a specific forecast model, cluster name, and run date, without repeating the
    request-shaping logic inline in every scenario.
    """
    return json.dumps({"Model": model, "Cluster": cluster, "rundate": rundate})


def create_data_ready_user(
    base: BaseTests,
    client: FlaskClient,
    test_runtime: TestRuntime,
    dataset_names: list[str],
) -> AuthenticatedTestUser:
    """Create and log in a temporary user tailored to data-ready scenarios.

    The returned user is configured with enough quota and permissions to create
    schedules, trigger data-ready events, and access the datasets listed in
    ``dataset_names``. The helper also resolves dataset names to the numeric ids
    required by the user-creation API.
    """
    db = sqlalchemy.get_instance()
    dataset_ids = [str(test_runtime.dataset_id(db, name)) for name in dataset_names]

    data: dict[str, Any] = {
        "disk_quota": 1073741824,
        "max_output_size": 1073741824,
        "allowed_postprocessing": True,
        "allowed_schedule": True,
        "open_dataset": True,
        "datasets": json.dumps(dataset_ids),
    }

    uuid, created_user = base.create_user(client, data, ["admin_root"])
    headers, _ = base.do_login(
        client, created_user.get("email"), created_user.get("password")
    )

    user = db.User.query.filter_by(uuid=uuid).first()
    assert user is not None

    return AuthenticatedTestUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
    )


def create_schedule(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    body: str,
) -> str:
    """Submit one schedule definition through the public API and return its id.

    The helper keeps tests focused on schedule behavior instead of on response
    parsing. It asserts that the schedule was accepted and extracts the created
    identifier from the JSON payload returned by the endpoint.
    """
    response = client.post(
        f"{API_URI}/schedules",
        headers=headers,
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 202
    return str(base.get_content(response).get("schedule_id"))


def set_schedule_active(
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
    *,
    is_active: bool,
) -> None:
    """Enable or disable an existing schedule through the public API.

    Several data-ready scenarios need the same schedule definition but with a
    different activation state. This helper centralizes the ``PATCH`` request and
    asserts that the state change succeeded.
    """
    response = client.patch(
        f"{API_URI}/schedules/{schedule_id}",
        headers=headers,
        data=json.dumps({"is_active": is_active}),
        content_type="application/json",
    )
    assert response.status_code == 200


def delete_request(client: FlaskClient, headers: Any, request_id: int | str) -> None:
    """Delete one request row through the public requests endpoint.

    Tests use this during cleanup or when they need to remove an automatically
    created request row before building a more controlled scenario.
    """
    response = client.delete(f"{API_URI}/requests/{request_id}", headers=headers)
    assert response.status_code == 200


def delete_schedule(client: FlaskClient, headers: Any, schedule_id: int | str) -> None:
    """Delete one schedule through the public schedules endpoint.

    This is a small convenience wrapper used mainly by cleanup code so that test
    bodies do not need to repeat status-code assertions for schedule teardown.
    """
    response = client.delete(f"{API_URI}/schedules/{schedule_id}", headers=headers)
    assert response.status_code == 200


def list_user_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> list[dict[str, Any]]:
    """Return the authenticated user's visible requests as a plain Python list.

    The requests endpoint may legitimately return an empty payload. This helper
    normalizes that case to ``[]`` so tests can reason about cardinality without
    repeating defensive response handling.
    """
    response = client.get(f"{API_URI}/requests", headers=headers)
    assert response.status_code == 200
    return base.get_content(response) or []


def list_user_schedules(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> list[dict[str, Any]]:
    """Return the authenticated user's visible schedules as a plain list.

    Like the matching request helper, this function hides small response-shape
    details and guarantees that callers always receive a list they can iterate or
    count safely.
    """
    response = client.get(f"{API_URI}/schedules", headers=headers)
    assert response.status_code == 200
    return base.get_content(response) or []


def list_schedule_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
) -> list[dict[str, Any]]:
    """Return only the concrete request rows generated by one schedule.

    The schedule-requests endpoint can include entries that are not plain request
    dictionaries. This helper filters those out so the calling tests can compare
    request counts and inspect request payloads without additional guarding code.
    """
    response = client.get(
        f"{API_URI}/schedules/{schedule_id}/requests?last=False",
        headers=headers,
    )
    assert response.status_code == 200
    content = base.get_content(response) or []
    return [item for item in content if isinstance(item, dict)]


def wait_for_schedule_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
    *,
    expected_count: int,
    timeout: float = 60,
    interval: float = 5,
) -> list[dict[str, Any]]:
    """Poll one schedule until the API exposes the expected number of requests.

    Even in tests, the observable state can lag slightly behind the triggering
    action. This helper performs the retry loop and returns the final request list
    only when the desired count is visible.
    """
    def expected_requests():
        """Expose the request list only when the target count has been reached."""
        requests = list_schedule_requests(base, client, headers, schedule_id)
        return requests if len(requests) == expected_count else False

    return wait_until(
        expected_requests,
        timeout=timeout,
        interval=interval,
        message=(
            f"Expected {expected_count} requests for schedule {schedule_id}"
        ),
    )


def post_data_ready(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    *,
    model: str,
    rundate: str,
    cluster: str = "g100",
) -> tuple[Any, Any]:
    """Submit one data-ready event and return both the raw and parsed responses.

    Some tests need access to the raw Flask response object, while others care
    mainly about the decoded JSON body. This helper returns both so the caller can
    assert on status code and payload without issuing the request twice.
    """
    body = build_data_ready_payload(model=model, rundate=rundate, cluster=cluster)
    response = client.post(
        f"{API_URI}/data/ready",
        headers=headers,
        data=body,
        content_type="application/json",
    )
    return response, base.get_content(response)


def trigger_data_ready_and_wait_accepted(
    client: FlaskClient,
    headers: Any,
    *,
    model: str,
    rundate: str,
    cluster: str = "g100",
    timeout: float = 30,
    interval: float = 3,
):
    """Retry ``/api/data/ready`` until the endpoint accepts the event with ``202``.

    The endpoint can briefly reject or delay acceptance while the surrounding
    runtime settles. Instead of making each test sleep blindly, this helper polls
    the endpoint until the expected acceptance response appears or the timeout is
    reached.
    """
    body = build_data_ready_payload(model=model, rundate=rundate, cluster=cluster)

    def data_ready_accepted():
        """Yield the response object only when the endpoint reports acceptance."""
        response = client.post(
            f"{API_URI}/data/ready",
            headers=headers,
            data=body,
            content_type="application/json",
        )
        return response if response.status_code == 202 else False

    return wait_until(
        data_ready_accepted,
        timeout=timeout,
        interval=interval,
        message="data/ready did not return 202 within timeout",
    )


def create_schedule_request_record(
    db,
    user_id: int,
    request_name: str,
    *,
    dataset_name: str,
    reftime: str,
    schedule_id: str,
    submission_date: datetime | None = None,
    status: str | None = None,
):
    """Insert a synthetic schedule request row directly into the test database.

    Periodic-schedule tests often need a pre-existing request history in order to
    verify whether a new data-ready event should generate an additional request.
    This helper seeds that history without invoking the real extraction worker.
    """
    request = repo.create_request_record(
        db,
        user_id,
        request_name,
        {
            "datasets": dataset_name,
            "reftime": reftime,
            "filters": [],
            "postprocessors": [],
            "output_format": None,
            "only_reliable": True,
            "pushing_queue": None,
        },
        schedule_id,
        True,
    )

    if submission_date is not None:
        request.submission_date = submission_date
    if status is not None:
        request.status = status

    db.session.add(request)
    db.session.commit()
    return request


def delete_all_user_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> None:
    """Best-effort cleanup helper that deletes every request visible to the user."""
    for request in list_user_requests(base, client, headers):
        delete_request(client, headers, request.get("id"))


def delete_all_user_schedules(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> None:
    """Best-effort cleanup helper that deletes every schedule visible to the user."""
    for schedule in list_user_schedules(base, client, headers):
        schedule_id = schedule.get("schedule_id") or schedule.get("id")
        if schedule_id is None:
            continue
        delete_schedule(client, headers, schedule_id)


def register_data_ready_user_cleanup(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    user: AuthenticatedTestUser,
) -> None:
    """Register all cleanup actions typically needed by a data-ready scenario.

    Data-ready tests can create schedules, requests, user files, and the user
    itself. This helper registers teardown in the correct order so later tests do
    not inherit residual state from earlier scenarios.
    """
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    cleanup_registry.add(
        lambda: delete_all_user_schedules(base, client, user.headers)
    )
    cleanup_registry.add(
        lambda: delete_all_user_requests(base, client, user.headers)
    )


def register_schedule_cleanup(
    client: FlaskClient,
    cleanup_registry,
    headers: Any,
    schedule_id: str,
) -> None:
    """Register deferred deletion for a schedule created during the current test.

    Tests that create schedules usually want cleanup to happen even if an assert
    fails midway. This helper attaches that teardown step to the shared cleanup
    registry.
    """
    cleanup_registry.add(lambda: delete_schedule(client, headers, schedule_id))