"""Test di integrazione su modello e ora di run non coincidenti (schedule data-ready).

Verificano che il task ``launch_all_on_data_ready_extractions``
(tasks/on_data_ready_extractions.py), avviato da ``POST /api/data/ready``, scarti le
schedule quando il modello o l'ora del run notificato non corrispondono.
"""

from datetime import datetime, timedelta

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.schedules import build_crontab_schedule
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    SECOND_DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
    register_schedule_cleanup,
    trigger_data_ready_inline,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def _mismatching_rundate(reference_datetime) -> str:
    """Restituisce un rundate spostato di un'ora per forzare un'ora di run diversa.

    Il valore, nel formato ``%Y%m%d%H``, viene inviato a ``POST /api/data/ready``.
    """
    return (reference_datetime + timedelta(hours=1)).strftime("%Y%m%d%H")


def test_data_ready_skips_schedule_for_different_model_dataset(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Verifica che un evento data-ready di un altro modello non attivi la schedule.

    La schedule chiede ``lm5`` ma ``POST /api/data/ready`` notifica ``lm2.2``: il task
    ``launch_all_on_data_ready_extractions`` deve scartarla senza creare richieste.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    now = datetime.now()
    schedule_body = build_crontab_schedule(
        request_name="test_different_model_dataset",
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

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=SECOND_DATA_READY_DATASET_NAME,
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


def test_data_ready_skips_schedule_for_different_runhour(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Verifica che un'ora di run diversa da quella filtrata non attivi la schedule.

    ``POST /api/data/ready`` notifica un run spostato di un'ora rispetto al filtro
    ``run`` della schedule: il task ``launch_all_on_data_ready_extractions`` deve
    scartarla senza creare richieste.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    now = datetime.now()
    schedule_body = build_crontab_schedule(
        request_name="test_runhour",
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

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=_mismatching_rundate(dataset_window.ref_from),
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