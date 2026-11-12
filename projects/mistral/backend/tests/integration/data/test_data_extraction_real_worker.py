"""Test con worker reali per ``POST /data``, il flusso di estrazione piu usato.

L'endpoint salva la request e invia ``data_extract`` al broker.
Qui non si sostituisce nulla: un worker Celery reale esegue l'estrazione. I test
coprono il download riuscito, l'email di fallimento e il cleanup di una
request che i worker non hanno ancora finito.

I test restano nel loro perimetro: gli utenti temporanei sono creati da
``create_data_ready_user`` (nessuna email reale), il ``conftest.py`` radice li
salta se i worker non usano il mock SMTP, e il cleanup ferma i task dell'utente
prima di cancellarne request, file di output e cartella.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from mistral.tests.helpers.auth import AuthenticatedTestUser
from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_data_ready_user,
    list_user_requests,
    register_data_ready_user_cleanup,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window
from mistral.tests.helpers.polling import wait_until
from mistral.tests.helpers.real_workers import (
    FINISHED_STATES,
    RealWorkerCleanupWarning,
    register_wait_for_user_requests,
    wait_for_finished_request,
    wait_for_mock_email,
)
from restapi.connectors import celery, sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.async_real,
    pytest.mark.runtime_sensitive,
]

OUTPUT_SIZE_ERROR = (
    "The resulting output size exceeds the size allowed for a single request"
)


def _create_real_worker_user(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
    **limits: int,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo le cui estrazioni girano sui worker reali.

    Registra il cleanup dell'utente e salta il test se il dataset ``lm5`` manca.
    """
    base = BaseTests()
    try:
        user = create_data_ready_user(
            base,
            client,
            test_runtime,
            [DATA_READY_DATASET_NAME],
            **limits,
        )
    except LookupError:
        pytest.skip(
            f"Dataset '{DATA_READY_DATASET_NAME}' is not available in this environment"
        )
    register_data_ready_user_cleanup(base, client, cleanup_registry, user)
    # Registrata per ultima, l'attesa dei worker gira prima delle cancellazioni.
    register_wait_for_user_requests(base, client, cleanup_registry, user)
    return user


@pytest.fixture
def real_worker_user(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
) -> AuthenticatedTestUser:
    """Fixture: utente temporaneo le cui estrazioni girano sui worker reali."""
    return _create_real_worker_user(client, cleanup_registry, test_runtime)


def _submit_one_run(
    client: FlaskClient,
    user: AuthenticatedTestUser,
    name_prefix: str,
) -> tuple[str, dict[str, Any]]:
    """Invia ``POST /data`` per una sola run della finestra reale di ``lm5``.

    Restituisce il nome della request e il body della risposta 202.
    """
    dataset_window = fetch_dataset_window(
        client,
        user.headers,
        DATA_READY_DATASET_NAME,
    )
    request_name = f"{name_prefix}-{uuid4().hex[:8]}"
    # Una sola run della finestra reale di lm5 tiene l'estrazione piccola e veloce.
    response = client.post(
        f"{API_URI}/data",
        headers=user.headers,
        json={
            "request_name": request_name,
            "dataset_names": [DATA_READY_DATASET_NAME],
            "reftime": {"from": dataset_window.date_from, "to": dataset_window.date_to},
            "filters": {"run": [dataset_window.ref_run[0]]},
        },
    )
    # Senza il 202 non esiste una request da attendere.
    assert response.status_code == 202, response.data
    return request_name, BaseTests().get_content(response)


def _find_user_request(
    client: FlaskClient,
    headers: Any,
    request_id: int,
) -> dict[str, Any] | None:
    """Restituisce una request dell'utente letta da ``GET /requests``, o None."""
    for request in list_user_requests(BaseTests(), client, headers):
        if request.get("id") == request_id:
            return request
    return None


def _wait_for_user_request(
    client: FlaskClient,
    user: AuthenticatedTestUser,
    request_id: int,
) -> dict[str, Any]:
    """Attende che i worker reali concludano una request dell'utente."""
    return wait_for_finished_request(
        lambda: _find_user_request(client, user.headers, request_id),
        description=f"request {request_id}",
    )


def _final_task_state(task_id: str) -> str | bool:
    """Restituisce lo stato Celery finale di un task, o False finche non e finale."""
    state = celery.get_instance().celery_app.AsyncResult(task_id).state
    return state if state in FINISHED_STATES else False


def test_data_request_is_extracted_by_real_worker(
    client: FlaskClient,
    real_worker_user: AuthenticatedTestUser,
) -> None:
    """Verifica che un worker reale estragga end to end una request di ``POST /data``.

    Il file prodotto deve poi essere scaricabile con ``GET /data/<filename>``.
    """
    # act
    _, submitted = _submit_one_run(client, real_worker_user, "real-worker-data")
    request = _wait_for_user_request(client, real_worker_user, submitted["request_id"])
    download_response = client.get(
        f"{API_URI}/data/{request.get('fileoutput')}",
        headers=real_worker_user.headers,
    )

    try:
        # assert
        assert request["status"] == "SUCCESS", request.get("error_message")
        # Il worker ha eseguito proprio il task accodato dall'endpoint.
        assert request["task_id"] == submitted["task_id"]
        # Il file sta nella cartella dell'utente temporaneo, non in opendata.
        assert request["opendata"] is False
        assert (real_worker_user.output_dir / request["fileoutput"]).is_file()
        assert download_response.status_code == 200
        assert len(download_response.data) == request["filesize"]
        assert request["fileoutput"] in download_response.headers["Content-Disposition"]
    finally:
        download_response.close()


def test_failed_data_request_notifies_owner_through_smtp_mock(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
) -> None:
    """Verifica che l'email di fallimento di ``data_extract`` arrivi al mock SMTP."""
    # arrange
    # Con un limite di 1 byte il worker rifiuta l'estrazione per quota: data_extract
    # segna FAILURE e invia sempre l'email di esito al proprietario.
    user = _create_real_worker_user(
        client,
        cleanup_registry,
        test_runtime,
        max_output_size=1,
    )

    # act
    request_name, submitted = _submit_one_run(client, user, "real-worker-failure")
    request = _wait_for_user_request(client, user, submitted["request_id"])
    notification = wait_for_mock_email(user.email)

    # assert
    assert request["status"] == "FAILURE"
    assert request["error_message"] == OUTPUT_SIZE_ERROR
    assert request["task_id"] == submitted["task_id"]
    assert "fileoutput" not in request
    assert not any(user.output_dir.glob("*"))
    # Il mock scrive l'email solo se il worker gira in modalita test: con l'SMTP
    # reale qui non ci sarebbe nulla.
    assert notification.recipients == [user.email]
    assert notification.subject == "MeteoHub: data extraction completed"
    assert request_name in notification.text
    assert "FAILURE" in notification.text
    assert OUTPUT_SIZE_ERROR in notification.text


def test_cleanup_timeout_revokes_queued_request_on_real_workers(
    client: FlaskClient,
    real_worker_user: AuthenticatedTestUser,
) -> None:
    """Verifica che un cleanup scaduto revochi il task prima di cancellare la request.

    Usa ``register_wait_for_user_requests`` con worker Celery reali.
    """
    # arrange
    base = BaseTests()
    db = sqlalchemy.get_instance()
    _, submitted = _submit_one_run(client, real_worker_user, "real-worker-revoke")
    # Con timeout=0 l'attesa scade subito. L'endpoint accoda il task con countdown=1,
    # quindi il cleanup lo trova ancora in coda, come con un worker lento.
    registry = CleanupRegistry()
    register_wait_for_user_requests(
        base,
        client,
        registry,
        real_worker_user,
        timeout=0,
    )

    # act
    with pytest.warns(RealWorkerCleanupWarning, match="Deleted 1 request"):
        registry.run()
    task_state = wait_until(
        lambda: _final_task_state(submitted["task_id"]),
        timeout=30,
        interval=1,
        message=f"Task {submitted['task_id']} did not reach a final state",
    )

    # assert
    # Il worker ha scartato il task revocato invece di eseguirlo.
    assert task_state == "REVOKED"
    assert db.Request.query.get(submitted["request_id"]) is None
    assert db.FileOutput.query.filter_by(user_id=real_worker_user.user_id).count() == 0
    assert not any(real_worker_user.output_dir.glob("*"))
