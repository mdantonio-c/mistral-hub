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
    """Delete seeded request rows from the database if they are still present."""
    for request_id in request_ids:
        request = db.Request.query.get(request_id)
        if request is not None:
            db.session.delete(request)
    db.session.commit()