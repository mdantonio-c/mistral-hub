"""Test con worker reale per la prima estrazione di una schedule on-data-ready.

``POST /schedules`` con ``on-data-ready`` salva la schedule e invia subito al
broker il primo ``data_extract``, senza alcuna voce in RedBeat.
Qui non si sostituisce nulla: un worker Celery reale esegue l'estrazione, il test
aspetta che la request vada a buon fine, scarica l'output e cancella la
schedule tramite l'API.

Il test resta nel proprio perimetro: l'utente temporaneo arriva dalla fixture
``schedules_user`` (``create_data_ready_user``, nessuna email reale), l'output
viene scritto nella cartella dell'utente invece che in quella opendata condivisa,
e il cleanup aspetta i worker prima di cancellare i dati dell'utente.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window
from mistral.tests.helpers.real_workers import (
    read_periodic_task,
    register_wait_for_user_requests,
    wait_for_finished_request,
)
from mistral.tests.helpers.schedules import build_on_data_ready_schedule
from restapi.tests import API_URI, BaseTests, FlaskClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.async_real,
    pytest.mark.runtime_sensitive,
]


def _single_schedule_request(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
) -> dict[str, Any] | None:
    """Restituisce l'unica request della schedule, o ``None`` finche non esiste.

    Legge le request tramite GET /schedules/<id>/requests.
    """
    requests = list_schedule_requests(base, client, headers, schedule_id)
    return requests[0] if len(requests) == 1 else None


def test_on_data_ready_schedule_first_extraction_runs_on_real_worker(
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    schedules_user,
) -> None:
    """Un worker reale esegue la prima estrazione di una schedule on-data-ready.

    Esercita POST /schedules, il task Celery ``data_extract``, GET /data/<file> e
    DELETE /schedules/<id>, senza lasciare voci periodiche in RedBeat.
    """
    # arrange
    # Registrata dopo il cleanup della fixture utente, l'attesa dei worker gira per
    # prima: la schedule, se resta, la cancella quel cleanup con Celery reale.
    register_wait_for_user_requests(
        schedules_base,
        client,
        cleanup_registry,
        schedules_user,
    )
    dataset_window = fetch_dataset_window(
        client,
        schedules_user.headers,
        DATA_READY_DATASET_NAME,
    )
    # opendata=False: l'output finisce nella cartella dell'utente temporaneo.
    schedule_body = build_on_data_ready_schedule(
        request_name=f"real-worker-odr-{uuid4().hex[:8]}",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        opendata=False,
    )

    # act
    schedule_id = create_schedule(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_body,
    )
    periodic_task = read_periodic_task(schedule_id)
    request = wait_for_finished_request(
        lambda: _single_schedule_request(
            schedules_base,
            client,
            schedules_user.headers,
            schedule_id,
        ),
        description=f"the first request of schedule {schedule_id}",
    )
    download_response = client.get(
        f"{API_URI}/data/{request.get('fileoutput')}",
        headers=schedules_user.headers,
    )
    delete_response = client.delete(
        f"{API_URI}/schedules/{schedule_id}",
        headers=schedules_user.headers,
    )
    get_after_delete = client.get(
        f"{API_URI}/schedules/{schedule_id}",
        headers=schedules_user.headers,
    )

    try:
        # assert
        # Una schedule solo on-data-ready non deve lasciare task periodici in RedBeat.
        assert periodic_task is None
        assert request["status"] == "SUCCESS", request.get("error message")
        # Il task_id lo scrive il task quando gira in Celery: in-process resta None.
        assert request["task_id"]
        assert (schedules_user.output_dir / request["fileoutput"]).is_file()
        assert download_response.status_code == 200
        assert len(download_response.data) == request["filesize"]
        assert delete_response.status_code == 200
        assert get_after_delete.status_code == 404
        assert read_periodic_task(schedule_id) is None
    finally:
        download_response.close()
