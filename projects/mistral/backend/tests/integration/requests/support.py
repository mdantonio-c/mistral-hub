"""Request-domain support helpers kept local to pending-request integration tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from faker import Faker
from restapi.env import Env


grace_period_days = Env.get_int("GRACE_PERIOD", 2)
GRACE_PERIOD = timedelta(days=grace_period_days)


def create_pending_delete_requests(faker: Faker, db: Any, user_id: int) -> tuple[int, int]:
    """Seed one deletable request and one still-protected request for a user."""
    # Costruiamo lo stato controllato richiesto dal test, usando gli stessi canali che
    # il backend espone in produzione quando possibile.
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
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(deletable_request)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(undeletable_request)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.commit()

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return deletable_request.id, undeletable_request.id


def delete_request_rows(db: Any, *request_ids: int) -> None:
    """Delete seeded request rows from the database if they are still present."""
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    for request_id in request_ids:
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        request = db.Request.query.get(request_id)
        # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
        # succedere quando lo stato non e quello ideale.
        if request is not None:
            # Persistiamo la modifica nel database di test, altrimenti le chiamate
            # successive non vedrebbero lo scenario preparato.
            db.session.delete(request)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.commit()