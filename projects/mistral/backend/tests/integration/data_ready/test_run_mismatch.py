"""Integration tests for model and run-hour mismatches in data-ready schedules."""

from datetime import datetime, timedelta

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.schedules import build_crontab_schedule
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    SECOND_DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
    post_data_ready,
    register_schedule_cleanup,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def _mismatching_rundate(reference_datetime) -> str:
    """Return a rundate string shifted by one hour to force a run mismatch."""
    # Entriamo nel blocco operativo dell'helper data-ready, mantenendo esplicito quale
    # stato viene letto o prodotto.
    return (reference_datetime + timedelta(hours=1)).strftime("%Y%m%d%H")


def test_data_ready_skips_schedule_for_different_model_dataset(
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_user,
) -> None:
    """Verify that a data-ready event for another model does not trigger the schedule."""
    # arrange
    # Prepariamo lo scenario data-ready con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    now = datetime.now()
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
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
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
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
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response, content = post_data_ready(
        data_ready_base,
        client,
        data_ready_admin_headers,
        model=SECOND_DATA_READY_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code in {200, 202}
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert content == "1"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )


def test_data_ready_skips_schedule_for_different_runhour(
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_user,
) -> None:
    """Verify that a mismatching run hour does not trigger the schedule."""
    # arrange
    # Prepariamo lo scenario data-ready con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    now = datetime.now()
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
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
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
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
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response, content = post_data_ready(
        data_ready_base,
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        rundate=_mismatching_rundate(dataset_window.ref_from),
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code in {200, 202}
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert content == "1"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )