"""Integration tests for baseline data-ready behaviors and schedule gating rules."""

from datetime import datetime, timedelta

import pytest
from restapi.tests import API_URI, FlaskClient

from mistral.tests.helpers.schedules import (
    build_crontab_schedule,
    build_on_data_ready_schedule,
)
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    SECOND_DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
    post_data_ready,
    register_schedule_cleanup,
    set_schedule_active,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_data_ready_non_filesystem_export_returns_one(
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
) -> None:
    """Verify that a non-filesystem data-ready event is accepted and returns the sentinel payload `1`."""
    # arrange
    rundate = "2023020217"

    # act
    response, content = post_data_ready(
        data_ready_base,
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        cluster="meucci",
        rundate=rundate,
    )

    # assert
    assert response.status_code in {200, 202}
    assert content == "1"


def test_data_ready_schedule_rejects_dataset_not_enabled(
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
) -> None:
    """Verify that schedules targeting datasets outside the enabled data-ready set are rejected."""
    # arrange
    response = client.get(f"{API_URI}/datasets", headers=data_ready_admin_headers)
    assert response.status_code == 200
    datasets = data_ready_base.get_content(response)
    dataset_name = next(
        dataset["id"]
        for dataset in datasets
        if dataset["id"]
        not in {DATA_READY_DATASET_NAME, SECOND_DATA_READY_DATASET_NAME}
    )

    schedule_body = build_on_data_ready_schedule(
        request_name="test_no_dataready",
        date_from=(datetime.now() - timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        ),
        date_to=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        dataset_names=[dataset_name],
        opendata=False,
    )

    # act
    response = client.post(
        f"{API_URI}/schedules",
        headers=data_ready_admin_headers,
        data=schedule_body,
        content_type="application/json",
    )

    # assert
    assert response.status_code == 400
    assert "Data-ready service is not available" in data_ready_base.get_content(
        response
    )


def test_data_ready_skips_inactive_schedule(
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_user,
) -> None:
    """Verify that an inactive on-data-ready schedule does not spawn any request."""
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    now = datetime.now()
    schedule_body = build_crontab_schedule(
        request_name="test_schedule_not_active",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        hour=now.hour,
        minute=now.minute,
        on_data_ready=True,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )
    register_schedule_cleanup(
        client,
        cleanup_registry,
        data_ready_user.headers,
        schedule_id,
    )
    set_schedule_active(
        client,
        data_ready_user.headers,
        schedule_id,
        is_active=False,
    )

    # act
    response, content = post_data_ready(
        data_ready_base,
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
    )

    # assert
    assert response.status_code in {200, 202}
    assert content == "1"
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )


def test_data_ready_skips_schedule_without_on_data_ready_flag(
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_user,
) -> None:
    """Verify that ordinary schedules ignore data-ready events when the flag is disabled."""
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    now = datetime.now()
    schedule_body = build_crontab_schedule(
        request_name="test_not_on_data_ready",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        hour=now.hour,
        minute=now.minute,
        on_data_ready=False,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )
    register_schedule_cleanup(
        client,
        cleanup_registry,
        data_ready_user.headers,
        schedule_id,
    )

    # act
    response, content = post_data_ready(
        data_ready_base,
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
    )

    # assert
    assert response.status_code in {200, 202}
    assert content == "1"
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )