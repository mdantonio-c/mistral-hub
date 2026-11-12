"""Helper locali per i test di integrazione sulle richieste pendenti.

Inseriscono e rimuovono righe ``Request`` direttamente nel DB, per esercitare la regola
del grace period usata da ``DELETE /api/requests/<id>`` (endpoints/requests.py) e dal
task ``automatic_cleanup`` (tasks/requests_cleanup.py).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from faker import Faker
from restapi.env import Env


grace_period_days = Env.get_int("GRACE_PERIOD", 2)
GRACE_PERIOD = timedelta(days=grace_period_days)


def create_pending_delete_requests(faker: Faker, db: Any, user_id: int) -> tuple[int, int]:
    """Inserisce per un utente una richiesta cancellabile e una ancora protetta.

    La prima e piu vecchia del grace period, la seconda e ancora dentro la finestra
    controllata da ``SqlApiDbManager.check_request_is_pending_within_grace_period``.
    Restituisce gli id nell'ordine ``(cancellabile, protetta)``.
    """
    deletable_request_name = faker.pystr()
    undeletable_request_name = faker.pystr()

    forbidden_delete_time = datetime.now() - GRACE_PERIOD + timedelta(days=1)
    allowed_delete_time = datetime.now() - GRACE_PERIOD - timedelta(days=1)

    deletable_request = db.Request(
        user_id=user_id,
        name=deletable_request_name,
        args={},
        submission_date=allowed_delete_time,
        status="STARTED",
    )
    undeletable_request = db.Request(
        user_id=user_id,
        name=undeletable_request_name,
        args={},
        submission_date=forbidden_delete_time,
        status="PENDING",
    )
    db.session.add(deletable_request)
    db.session.add(undeletable_request)
    db.session.commit()

    return deletable_request.id, undeletable_request.id


def delete_request_rows(db: Any, *request_ids: int) -> None:
    """Cancella dal DB (modello ``Request``) le righe inserite, se esistono ancora."""
    for request_id in request_ids:
        request = db.Request.query.get(request_id)
        if request is not None:
            db.session.delete(request)
    db.session.commit()