"""Test di integrazione dei casi base del flusso data-ready.

Coprono ``POST /api/data/ready`` (endpoints/data_ready.py) e le regole con cui le
schedule on-data-ready vengono rifiutate o scartate (``POST /api/schedules`` in
endpoints/schedules.py e il task ``launch_all_on_data_ready_extractions``).
"""

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
    trigger_data_ready_inline,
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
    """Verifica che un evento data-ready di una piattaforma non esportata sia accettato.

    ``POST /api/data/ready`` con cluster ``meucci`` (diverso dalla piattaforma
    esportata sul filesystem) esce subito e risponde con il payload sentinella ``1``.
    """
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
    """Verifica che una schedule su dataset non abilitato al data-ready sia rifiutata.

    ``POST /api/schedules`` con flag on-data-ready risponde 400 se il dataset non e
    nella lista ``SingleSchedule.ON_DATA_READY_DATASETS`` (endpoints/schedules.py).
    """
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
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Verifica che una schedule on-data-ready inattiva non generi alcuna richiesta.

    La schedule viene disattivata con ``PATCH /api/schedules/<id>``; dopo
    ``POST /api/data/ready`` il task ``launch_all_on_data_ready_extractions``,
    eseguito inline, deve scartarla.
    """
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
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
    )

    # assert
    assert response.status_code in {200, 202}
    assert data_ready_base.get_content(response) == "1"
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )


def test_data_ready_skips_schedule_without_on_data_ready_flag(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Verifica che una schedule senza flag on-data-ready ignori gli eventi data-ready.

    Dopo ``POST /api/data/ready`` il task ``launch_all_on_data_ready_extractions``,
    eseguito inline, non deve creare richieste per la schedule crontab ordinaria.
    """
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
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
    )

    # assert
    assert response.status_code in {200, 202}
    assert data_ready_base.get_content(response) == "1"
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )