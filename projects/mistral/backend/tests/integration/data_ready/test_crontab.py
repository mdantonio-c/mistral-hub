"""Integration tests for crontab mismatch behavior in data-ready schedules."""

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.schedules import build_crontab_schedule
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
    trigger_data_ready_and_wait_accepted,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_data_ready_skips_schedule_when_full_crontab_does_not_match(
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_user,
) -> None:
    """Verify that a fully specified crontab mismatch prevents request generation."""
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    schedule_body = build_crontab_schedule(
        request_name="test_full_crontab_mismatch",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        minute=59,
        hour=23,
        day_of_week=6,
        day_of_month=30,
        month_of_year=11,
        on_data_ready=True,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )

    # act
    response = trigger_data_ready_and_wait_accepted(
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        rundate="2021101900",
    )

    # assert
    assert response.status_code == 202
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )


def test_data_ready_skips_schedule_when_partial_crontab_does_not_match(
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_user,
) -> None:
    """Verify that even a partial crontab mismatch prevents request generation."""
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    schedule_body = build_crontab_schedule(
        request_name="test_partial_crontab_mismatch",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        minute=59,
        hour=23,
        day_of_week=2,
        month_of_year=11,
        on_data_ready=True,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )

    # act
    response = trigger_data_ready_and_wait_accepted(
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        rundate="2021101900",
    )

    # assert
    assert response.status_code == 202
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )