"""Test deterministici del cleanup usato dai test con worker reali.

``register_wait_for_user_requests`` non deve mai cancellare dati sotto un task che
un worker potrebbe ancora eseguire. Qui il controllo Celery del modulo helper e
sostituito da un fake che fa la parte dei worker, cosi i rami di attesa e di
timeout girano senza worker reali; righe request, utenti e chiamate API sono reali.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import mistral.tests.helpers.real_workers as real_workers
import pytest
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.real_workers import (
    RealWorkerCleanupWarning,
    register_wait_for_user_requests,
)
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class FakeWorkers:
    """Fake del controllo Celery che simula i worker.

    Trattiene i task mostrati da ``inspect`` e registra le ``revoke`` ricevute. Le
    opzioni simulano worker che ignorano la revoke, che non rispondono o che finiscono
    i task da soli dopo ``finish_after`` ispezioni.
    """

    def __init__(
        self,
        held_tasks: list[dict[str, Any]],
        *,
        obey_revoke: bool = True,
        reply: bool = True,
        finish_after: int | None = None,
    ) -> None:
        self.held_tasks = list(held_tasks)
        self.obey_revoke = obey_revoke
        self.reply = reply
        self.finish_after = finish_after
        self.revokes: list[tuple[list[str], bool, str | None]] = []
        self.inspections = 0

    def revoke(self, task_ids, terminate=False, signal=None) -> None:
        self.revokes.append((list(task_ids), terminate, signal))
        if self.obey_revoke:
            self.held_tasks = [
                task for task in self.held_tasks if task["id"] not in task_ids
            ]

    def inspect(self, timeout=None) -> SimpleNamespace:
        self.inspections += 1
        if self.finish_after is not None and self.inspections > self.finish_after:
            # I worker hanno finito i task da soli.
            self.held_tasks = []
        # Senza risposta dei worker, Celery restituisce None.
        active = {"celery@fake": list(self.held_tasks)} if self.reply else None
        empty = {"celery@fake": []} if self.reply else None
        return SimpleNamespace(
            active=lambda: active,
            reserved=lambda: empty,
            scheduled=lambda: empty,
        )


def _install(monkeypatch: pytest.MonkeyPatch, workers: FakeWorkers) -> None:
    """Fa parlare il modulo helper ``real_workers`` con i worker fake."""
    # Sostituiamo solo il nome usato dall'helper, non il connettore condiviso.
    monkeypatch.setattr(
        real_workers,
        "celery",
        SimpleNamespace(
            get_instance=lambda: SimpleNamespace(
                celery_app=SimpleNamespace(control=workers)
            )
        ),
    )


def _data_extract_task(user_id: int) -> dict[str, Any]:
    """Restituisce un task ``data_extract`` nel formato di Celery inspect.

    Come nel task reale, il primo argomento e l'id dell'utente.
    """
    return {"id": f"fake-{uuid4().hex}", "name": "data_extract", "args": [user_id]}


def _temporary_user(client: FlaskClient, cleanup_registry) -> AuthenticatedTestUser:
    """Crea e autentica un utente temporaneo via API e ne registra il cleanup."""
    base = BaseTests()
    user = create_authenticated_test_user(base, client)
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


def _pending_request(cleanup_registry, user: AuthenticatedTestUser) -> tuple[int, str]:
    """Inserisce una request PENDING di ``user`` con un task_id fittizio.

    Usa ``SqlApiDbManager.create_request_record``; il cleanup la rimuove se c'e ancora.
    """
    db = sqlalchemy.get_instance()
    request = SqlApiDbManager.create_request_record(
        db,
        user.user_id,
        f"cleanup-timeout-{uuid4().hex[:8]}",
        {"datasets": ["lm5"]},
    )
    request.status = "PENDING"
    request.task_id = f"fake-{uuid4().hex}"
    db.session.commit()
    request_id, task_id = request.id, request.task_id

    def delete_request_row() -> None:
        row = db.Request.query.filter_by(id=request_id).first()
        if row is not None:
            db.session.delete(row)
            db.session.commit()

    # Registrata dopo l'utente, la riga sparisce prima che l'utente venga cancellato.
    cleanup_registry.add(delete_request_row)
    return request_id, task_id


def _request_status(request_id: int) -> str | None:
    """Rilegge dal DB lo stato della request, o None se e stata cancellata."""
    db = sqlalchemy.get_instance()
    row = db.Request.query.filter_by(id=request_id).populate_existing().first()
    return None if row is None else row.status


def test_cleanup_waits_while_workers_hold_a_task_of_the_user(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica che il cleanup attenda un task in coda che non ha ancora una request."""
    # arrange
    base = BaseTests()
    user = _temporary_user(client, cleanup_registry)
    # Come il primo task di una schedule: in coda in un worker, ancora senza request.
    workers = FakeWorkers([_data_extract_task(user.user_id)], finish_after=2)
    _install(monkeypatch, workers)
    registry = CleanupRegistry()
    register_wait_for_user_requests(
        base, client, registry, user, timeout=10, interval=0
    )

    # act
    registry.run()

    # assert
    assert workers.inspections == 3
    assert workers.revokes == []


def test_cleanup_timeout_stops_only_the_user_tasks_before_deleting_its_requests(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica che al timeout il cleanup revochi solo i task dell'utente.

    Solo dopo le revoche cancella le request dell'utente; quelle di altri restano.
    """
    # arrange
    base = BaseTests()
    owner = _temporary_user(client, cleanup_registry)
    other = _temporary_user(client, cleanup_registry)
    owner_request_id, owner_queued_id = _pending_request(cleanup_registry, owner)
    other_request_id, _ = _pending_request(cleanup_registry, other)
    owner_running = _data_extract_task(owner.user_id)
    other_running = _data_extract_task(other.user_id)
    workers = FakeWorkers([owner_running, other_running])
    _install(monkeypatch, workers)
    registry = CleanupRegistry()
    register_wait_for_user_requests(
        base, client, registry, owner, timeout=0, interval=0
    )

    # act
    with pytest.warns(RealWorkerCleanupWarning, match="Deleted 1 request"):
        registry.run()

    # assert
    # Prima il task della request ancora in coda, poi quello trovato nei worker.
    assert workers.revokes == [
        ([owner_queued_id], True, "SIGKILL"),
        ([owner_running["id"]], True, "SIGKILL"),
    ]
    assert workers.held_tasks == [other_running]
    assert _request_status(owner_request_id) is None
    assert _request_status(other_request_id) == "PENDING"


@pytest.mark.parametrize(
    "workers_behaviour",
    [{"obey_revoke": False}, {"reply": False}],
    ids=["task_not_stopped", "no_worker_replies"],
)
def test_cleanup_timeout_deletes_nothing_without_worker_confirmation(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
    workers_behaviour: dict[str, bool],
) -> None:
    """Verifica che senza conferma dei worker il cleanup fallisca e tenga le request."""
    # arrange
    base = BaseTests()
    user = _temporary_user(client, cleanup_registry)
    request_id, _ = _pending_request(cleanup_registry, user)
    workers = FakeWorkers([_data_extract_task(user.user_id)], **workers_behaviour)
    _install(monkeypatch, workers)
    registry = CleanupRegistry()
    register_wait_for_user_requests(
        base,
        client,
        registry,
        user,
        timeout=0,
        interval=0.05,
        stop_timeout=0.2,
    )

    # act
    with pytest.raises(AssertionError, match="left in place"):
        registry.run()

    # assert
    assert _request_status(request_id) == "PENDING"
