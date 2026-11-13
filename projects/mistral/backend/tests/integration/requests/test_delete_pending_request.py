"""Test di integrazione su cancellazione e cleanup automatico delle richieste pendenti.

Coprono ``DELETE /api/requests/<id>`` (endpoints/requests.py) con la regola del grace
period e il task Celery ``automatic_cleanup`` (tasks/requests_cleanup.py), che marca
come fallite le richieste rimaste ferme troppo a lungo.
"""

import datetime as dt
from types import SimpleNamespace

import mistral.services.sqlapi_db_manager as sqlapi_db_manager_module
import mistral.tasks.requests_cleanup as requests_cleanup_module
import pytest
from celery.states import READY_STATES
from flask import Flask
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.services.sqlapi_db_manager import SqlApiDbManager
from mistral.tests.helpers.auth import AuthenticatedTestUser
from mistral.tests.helpers.task_perimeter import RequestsCleanupPerimeter
from mistral.tests.integration.requests.support import delete_request_rows

# Istante UTC fisso; le date delle request sono salvate in UTC senza fuso.
FIXED_UTC_NOW = dt.datetime(2026, 1, 3, 12, 0)


def _clock_with_local_offset(hours: int) -> type:
    """Orologio fermo a FIXED_UTC_NOW per un processo con fuso UTC+``hours``."""
    offset = dt.timedelta(hours=hours)

    class _LocalClock(dt.datetime):
        @classmethod
        def utcnow(cls):
            return FIXED_UTC_NOW

        @classmethod
        def now(cls, tz=None):
            return FIXED_UTC_NOW + offset

        @classmethod
        def utcfromtimestamp(cls, timestamp):
            return dt.datetime.utcfromtimestamp(timestamp)

        @classmethod
        def fromtimestamp(cls, timestamp, tz=None):
            return dt.datetime.utcfromtimestamp(timestamp) + offset

    return _LocalClock


def _seed_pending_request(db, user_id: int, age: dt.timedelta) -> int:
    """Inserisce una request ancora in corso inviata ``age`` prima di FIXED_UTC_NOW."""
    request = db.Request(
        user_id=user_id,
        name=f"grace-period-utc-{age.total_seconds():.0f}",
        args={},
        submission_date=FIXED_UTC_NOW - age,
        status="STARTED",
    )
    db.session.add(request)
    db.session.commit()
    return request.id


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def delete_pending_request(client: FlaskClient, headers, request_id: int):
    """Chiama ``DELETE /api/requests/<id>``, l'endpoint sotto test, per la richiesta."""
    return client.delete(f"{API_URI}/requests/{request_id}", headers=headers)


class TestDeletePendingRequests(BaseTests):
    """Scenari sulle regole di cancellazione delle richieste attorno al grace period."""

    def test_delete_request_before_grace_period_returns_200(
        self,
        client: FlaskClient,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verifica che una richiesta piu vecchia del grace period si possa cancellare.

        ``DELETE /api/requests/<id>`` risponde 200 e la riga sparisce dal DB.
        """
        # arrange
        db = sqlalchemy.get_instance()
        deletable_request_id, _ = pending_delete_requests

        # act
        response = delete_pending_request(
            client,
            pending_request_user.headers,
            deletable_request_id,
        )

        # assert
        assert response.status_code == 200
        assert db.Request.query.get(deletable_request_id) is None

    def test_delete_request_within_grace_period_returns_403(
        self,
        client: FlaskClient,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verifica che una richiesta pendente recente non si possa cancellare.

        Dentro il grace period ``DELETE /api/requests/<id>`` risponde 403 e la riga
        resta nel DB.
        """
        # arrange
        db = sqlalchemy.get_instance()
        _, undeletable_request_id = pending_delete_requests

        # act
        response = delete_pending_request(
            client,
            pending_request_user.headers,
            undeletable_request_id,
        )

        # assert
        assert response.status_code == 403
        assert db.Request.query.get(undeletable_request_id) is not None

    def test_requests_cleanup_marks_stale_request_as_failure(
        self,
        app: Flask,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
        requests_cleanup_perimeter: RequestsCleanupPerimeter,
    ) -> None:
        """Verifica che il cleanup automatico marchi come fallite le richieste ferme.

        Il task Celery ``automatic_cleanup`` mette in ``FAILURE`` la richiesta oltre il
        grace period e lascia pendente quella recente.
        """
        # arrange
        db = sqlalchemy.get_instance()
        deletable_request_id, undeletable_request_id = pending_delete_requests
        # Il task reale e globale: gli rendiamo visibili solo utente e request del test.
        requests_cleanup_perimeter.allow(
            user_ids=[pending_request_user.user_id],
            request_ids=pending_delete_requests,
        )

        # act
        self.send_task(app, "automatic_cleanup")

        # assert
        deletable_request = db.Request.query.get(deletable_request_id)
        assert deletable_request is not None
        assert deletable_request.status == "FAILURE"

        undeletable_request = db.Request.query.get(undeletable_request_id)
        assert undeletable_request is not None
        assert undeletable_request.status not in READY_STATES


@pytest.mark.parametrize("utc_offset_hours", [2, -5], ids=["utc+02", "utc-05"])
def test_grace_period_is_computed_in_utc(
    pending_request_user: AuthenticatedTestUser,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
    utc_offset_hours: int,
) -> None:
    """Verifica che il grace period non dipenda dal fuso del processo.

    Una request un'ora piu giovane del grace period resta protetta, una piu vecchia
    di un'ora no, anche se l'ora locale del processo non e UTC.
    Metodo esercitato: SqlApiDbManager.check_request_is_pending_within_grace_period.
    """
    # arrange
    db = sqlalchemy.get_instance()
    grace_period = sqlapi_db_manager_module.GRACE_PERIOD
    protected_id = _seed_pending_request(
        db, pending_request_user.user_id, grace_period - dt.timedelta(hours=1)
    )
    expired_id = _seed_pending_request(
        db, pending_request_user.user_id, grace_period + dt.timedelta(hours=1)
    )
    cleanup_registry.add(lambda: delete_request_rows(db, protected_id, expired_id))
    monkeypatch.setattr(
        sqlapi_db_manager_module,
        "datetime",
        SimpleNamespace(
            datetime=_clock_with_local_offset(utc_offset_hours),
            timedelta=dt.timedelta,
        ),
    )

    # act
    protected = SqlApiDbManager.check_request_is_pending_within_grace_period(
        db, protected_id
    )
    expired = SqlApiDbManager.check_request_is_pending_within_grace_period(
        db, expired_id
    )

    # assert
    assert protected is True
    assert expired is False


@pytest.mark.parametrize("utc_offset_hours", [2, -5], ids=["utc+02", "utc-05"])
def test_requests_cleanup_grace_period_is_computed_in_utc(
    pending_request_user: AuthenticatedTestUser,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
    requests_cleanup_perimeter: RequestsCleanupPerimeter,
    utc_offset_hours: int,
) -> None:
    """Verifica che ``automatic_cleanup`` usi l'UTC per grace period ed end_date.

    Solo la request oltre il grace period diventa FAILURE, con end_date in UTC.
    """
    # arrange
    db = sqlalchemy.get_instance()
    grace_period = requests_cleanup_module.GRACE_PERIOD
    protected_id = _seed_pending_request(
        db, pending_request_user.user_id, grace_period - dt.timedelta(hours=1)
    )
    expired_id = _seed_pending_request(
        db, pending_request_user.user_id, grace_period + dt.timedelta(hours=1)
    )
    cleanup_registry.add(lambda: delete_request_rows(db, protected_id, expired_id))
    requests_cleanup_perimeter.allow(
        user_ids=[pending_request_user.user_id],
        request_ids=[protected_id, expired_id],
    )
    monkeypatch.setattr(
        requests_cleanup_module,
        "datetime",
        _clock_with_local_offset(utc_offset_hours),
    )

    # act
    requests_cleanup_module.automatic_cleanup.run()

    # assert
    db.session.expire_all()
    protected = db.Request.query.get(protected_id)
    expired = db.Request.query.get(expired_id)
    assert protected.status == "STARTED"
    assert protected.end_date is None
    assert expired.status == "FAILURE"
    assert expired.end_date == FIXED_UTC_NOW
