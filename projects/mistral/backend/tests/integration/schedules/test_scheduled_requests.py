# Finestra dati: nessun dato runtime reale richiesto; usa righe scritte nel DB.
# Runtime: righe schedule/request finte e deterministiche; nessuna dipendenza asincrona.
# Cleanup: righe schedule/request e utenti temporanei rimossi tramite cleanup_registry.
#
# Questo modulo contiene i test di integrazione delle schedule per:
# - GET /schedules/<id>/requests?last=true senza request riuscite restituisce 404
# - GET /schedules/<id>/requests?last=false restituisce la lista delle request
# - GET /schedules/<id>/requests?get_total=true restituisce il conteggio totale
# - PATCH /schedules/<id> disabilita con successo una schedule periodica abilitata
# - PATCH /schedules/<id> su una schedule gia disabilitata restituisce conflitto
# - PATCH /schedules/<id> abilita una schedule disabilitata ricreando il task RedBeat
#   (finto)
# - PATCH /schedules/<id> su una schedule gia abilitata restituisce conflitto
# - DELETE /schedules/<id> rimuove la schedule dal DB e il task periodico (finto)
#
# test_schedule_opendata_bridge.py copre gia il flusso completo delle schedule
# data-ready. Questo modulo si concentra sull'endpoint delle request schedulate e
# sulle operazioni di patch/delete che modificano lo stato della schedule.

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.models.sqlalchemy import PeriodEnum
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


# =============================================================================
# Helper locali: inseriscono righe schedule e request con stato controllato
# =============================================================================


def seed_schedule_row(
    db: Any,
    faker: Faker,
    user_id: int,
    *,
    enabled: bool = True,
    on_data_ready: bool = False,
    period: str | None = None,
    every: int | None = None,
) -> int:
    """Inserisce una riga schedule direttamente nel database per scenari deterministici.

    Evita POST /schedules, che richiederebbe RedBeat e Celery reali.
    """
    schedule_row = db.Schedule(
        user_id=user_id,
        name=faker.pystr(),
        args={
            "datasets": ["agrmet"],
            "reftime": None,
            "filters": None,
            "postprocessors": None,
            "output_format": None,
            "only_reliable": False,
            "pushing_queue": None,
        },
        is_enabled=enabled,
        on_data_ready=on_data_ready,
        period=getattr(PeriodEnum, period) if period else None,
        every=every,
    )
    db.session.add(schedule_row)
    db.session.commit()
    return schedule_row.id


def seed_request_row(
    db: Any,
    faker: Faker,
    user_id: int,
    schedule_id: int,
    *,
    status: str = "SUCCESS",
) -> int:
    """Inserisce nel database una riga request collegata a una schedule."""
    request_row = db.Request(
        user_id=user_id,
        name=faker.pystr(),
        args={"datasets": ["agrmet"]},
        status=status,
        schedule_id=schedule_id,
    )
    db.session.add(request_row)
    db.session.commit()
    return request_row.id


def delete_schedule_row(db: Any, schedule_id: int) -> None:
    """Elimina dal database una riga schedule inserita dal test, se esiste ancora."""
    schedule = db.Schedule.query.get(schedule_id)
    if schedule is not None:
        db.session.delete(schedule)
        db.session.commit()


def delete_request_row(db: Any, request_id: int) -> None:
    """Elimina dal database una riga request inserita dal test, se esiste ancora."""
    request = db.Request.query.get(request_id)
    if request is not None:
        db.session.delete(request)
        db.session.commit()


# =============================================================================
# Fixture: utente autenticato temporaneo con permessi sulle schedule
# =============================================================================


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente autenticato temporaneo per i test sulle request schedulate.

    L'utente ha il permesso `allowed_schedule` e sostituisce, in questo modulo, la
    `schedules_user` del conftest; il cleanup e registrato in cleanup_registry.
    """
    base = BaseTests()
    user = create_authenticated_test_user(
        base,
        client,
        permissions={"allowed_schedule": True},
    )
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


# =============================================================================
# Test: GET /schedules/<id>/requests - elenco delle request schedulate
# =============================================================================


class TestScheduledRequests:
    """Verifica che GET /schedules/<id>/requests restituisca le request collegate.

    Esercita l'endpoint ScheduledRequests.get (endpoints/schedules.py).
    """

    def test_last_true_no_successful_request_returns_404(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id>/requests?last=true: 404 senza request riuscite."""
        # arrange - inserisce una schedule senza request riuscite
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(db, faker, schedules_user.user_id)
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - legge l'ultima request schedulata
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}/requests?last=true",
            headers=schedules_user.headers,
        )

        # assert - risorsa non trovata
        assert response.status_code == 404

    def test_last_false_returns_list_of_requests(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id>/requests?last=false: lista di tutte le request."""
        # arrange - inserisce una schedule con piu request
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(db, faker, schedules_user.user_id)
        request_ids = [
            seed_request_row(db, faker, schedules_user.user_id, schedule_id, status="SUCCESS")
            for _ in range(3)
        ]
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))
        for request_id in request_ids:
            cleanup_registry.add(lambda rid=request_id: delete_request_row(db, rid))

        # act - legge tutte le request schedulate
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}/requests?last=false",
            headers=schedules_user.headers,
        )

        # assert - lista delle request
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_total_returns_count(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id>/requests?get_total=true: conteggio totale."""
        # arrange - inserisce una schedule con alcune request
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(db, faker, schedules_user.user_id)
        request_ids = [
            seed_request_row(db, faker, schedules_user.user_id, schedule_id, status="SUCCESS")
            for _ in range(5)
        ]
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))
        for request_id in request_ids:
            cleanup_registry.add(lambda rid=request_id: delete_request_row(db, rid))

        # act - richiede il conteggio totale
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}/requests?get_total=true",
            headers=schedules_user.headers,
        )

        # assert - conteggio totale
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        assert "total" in data
        assert data["total"] >= 5


# =============================================================================
# Test: PATCH /schedules/<id> e DELETE /schedules/<id>
# =============================================================================


class TestSchedulePatchAndDelete:
    """Verifica che patch e delete modifichino correttamente lo stato della schedule.

    Esercita SingleSchedule.patch e SingleSchedule.delete con Celery finto.
    """

    def test_disable_enabled_periodic_schedule_success(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> (is_active=false) disabilita una schedule periodica."""
        # arrange - inserisce una schedule periodica abilitata
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            enabled=True,
            on_data_ready=False,
            period="days",
            every=1,
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Celery finto: la voce RedBeat della schedule esiste e si puo cancellare.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = {"name": str(schedule_id)}
        fake_celery.delete_periodic_task.return_value = True
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - disabilita la schedule
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": false}',
            content_type="application/json",
        )

        # assert - operazione riuscita
        assert response.status_code == 200
        schedule_row = db.Schedule.query.get(schedule_id)
        assert schedule_row.is_enabled is False

    def test_disable_already_disabled_schedule_conflict(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> (is_active=false) risponde 409 se gia disabilitata."""
        # arrange - inserisce una schedule periodica gia disabilitata
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            enabled=False,
            on_data_ready=False,
            period="days",
            every=1,
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Celery finto: nessuna voce RedBeat, cioe la schedule risulta gia disabilitata.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = None
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - tenta di disabilitare una schedule gia disabilitata
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": false}',
            content_type="application/json",
        )

        # assert - conflitto
        assert response.status_code == 409

    def test_enable_disabled_schedule_recreates_periodic_task(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> (is_active=true) abilita una schedule disabilitata."""
        # arrange - inserisce una schedule periodica disabilitata
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            enabled=False,
            on_data_ready=False,
            period="days",
            every=1,
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Celery finto: nessuna voce RedBeat, cioe la schedule risulta disabilitata.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = None
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # La ricreazione del task periodico e finta: la riattivazione non scrive in
        # RedBeat.
        fake_create_periodic_task = MagicMock()
        import mistral.endpoints.schedules as schedules_module
        monkeypatch.setattr(
            schedules_module,
            "create_periodic_task_with_routing",
            fake_create_periodic_task,
        )

        # act - abilita la schedule
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": true}',
            content_type="application/json",
        )

        # assert - operazione riuscita
        assert response.status_code == 200
        schedule_row = db.Schedule.query.get(schedule_id)
        assert schedule_row.is_enabled is True

    def test_enable_already_enabled_schedule_conflict(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> (is_active=true) risponde 409 se gia abilitata."""
        # arrange - inserisce una schedule periodica gia abilitata
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            enabled=True,
            on_data_ready=False,
            period="days",
            every=1,
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Celery finto: la voce RedBeat esiste, cioe la schedule risulta gia abilitata.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = {"name": str(schedule_id)}
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - tenta di abilitare una schedule gia abilitata
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": true}',
            content_type="application/json",
        )

        # assert - conflitto
        assert response.status_code == 409

    def test_delete_schedule_removes_db_and_periodic_task(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """DELETE /schedules/<id> rimuove la schedule dal DB e da Celery."""
        # arrange - inserisce una schedule
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            enabled=True,
            on_data_ready=False,
            period="days",
            every=1,
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Celery finto: la cancellazione della voce RedBeat riesce senza toccare Redis.
        fake_celery = MagicMock()
        fake_celery.delete_periodic_task.return_value = True
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - cancella la schedule
        response = client.delete(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
        )

        # assert - operazione riuscita
        assert response.status_code == 200
        schedule_row = db.Schedule.query.get(schedule_id)
        assert schedule_row is None
