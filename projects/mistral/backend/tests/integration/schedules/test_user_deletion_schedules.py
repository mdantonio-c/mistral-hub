"""Test della cancellazione di un utente che possiede schedule.

Esercitano ``DELETE /api/admin/users/<uuid>`` (restapi) e il listener del progetto
``delete_schedules_of_deleted_users`` (models/sqlalchemy.py): le schedule dell'utente
vengono cancellate insieme ai loro task periodici RedBeat, come fa
``DELETE /api/schedules/<id>``. Le request dell'utente restano, come prima, con
``user_id`` e ``schedule_id`` a NULL.
"""

from __future__ import annotations

from types import SimpleNamespace

import mistral.models.sqlalchemy as models_module
import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.helpers.auth import create_authenticated_test_user, delete_test_user
from mistral.tests.integration.requests.support import delete_request_rows

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class _RecordingPeriodicTasks:
    """Fake del connettore Celery: registra le cancellazioni dei task periodici."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_periodic_task(self, name: str) -> bool:
        self.deleted.append(name)
        return True


def test_deleting_a_user_removes_its_schedules_and_periodic_tasks(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica che cancellando un utente spariscano le sue schedule e i task RedBeat.

    Celery e simulato solo sul nome importato dal modulo dei modelli: nessun task
    reale viene letto o cancellato.
    """
    # arrange
    base = BaseTests()
    db = sqlalchemy.get_instance()
    user = create_authenticated_test_user(base, client)
    cleanup_registry.add_path(user.output_dir.parent)

    def delete_user_if_present() -> None:
        if db.User.query.filter_by(uuid=user.uuid).first() is not None:
            delete_test_user(base, client, user.uuid)

    cleanup_registry.add(delete_user_if_present)
    schedule = db.Schedule(
        user_id=user.user_id,
        name="user-deletion-ext",
        args={"datasets": ["synthetic-user-deletion-ext"]},
        is_crontab=False,
        is_enabled=True,
    )
    db.session.add(schedule)
    db.session.commit()
    schedule_id = schedule.id
    request = db.Request(
        user_id=user.user_id,
        name="user-deletion-ext",
        args={},
        status="SUCCESS",
        schedule_id=schedule_id,
    )
    db.session.add(request)
    db.session.commit()
    request_id = request.id
    cleanup_registry.add(lambda: delete_request_rows(db, request_id))
    periodic_tasks = _RecordingPeriodicTasks()
    monkeypatch.setattr(
        models_module,
        "celery",
        SimpleNamespace(get_instance=lambda: periodic_tasks),
    )
    admin_headers, _ = base.do_login(client, None, None)

    # act
    response = client.delete(
        f"{API_URI}/admin/users/{user.uuid}", headers=admin_headers
    )

    # assert
    assert response.status_code == 204
    db.session.expire_all()
    assert db.Schedule.query.get(schedule_id) is None
    assert periodic_tasks.deleted == [str(schedule_id)]
    kept_request = db.Request.query.get(request_id)
    assert kept_request is not None
    assert kept_request.user_id is None
    assert kept_request.schedule_id is None
