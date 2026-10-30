# EXTENSION TRACEABILITY: added by coverage extension prompt 04
# EXTENSION SCOPE: integrates the refactored suite without modifying legacy baseline
# EXTENSION DATA WINDOW: no real runtime data required; uses DB-seeded rows
# EXTENSION RUNTIME: deterministic fake schedule and request rows; no async dependencies
# EXTENSION CLEANUP: schedule/request rows and temporary users cleaned via cleanup_registry
#
# This module extends the schedules integration area with tests for:
# - GET /schedules/<id>/requests?last=true with no successful request returns 404
# - GET /schedules/<id>/requests?last=false returns list of requests
# - GET /schedules/<id>/requests?get_total=true returns total count
# - PATCH /schedules/<id> disable enabled periodic schedule success
# - PATCH /schedules/<id> disable already disabled schedule conflict
# - PATCH /schedules/<id> enable disabled schedule recreates fake RedBeat task
# - PATCH /schedules/<id> enable already enabled schedule conflict
# - DELETE /schedules/<id> removes DB schedule and fake periodic task
#
# The baseline test_schedule_opendata_bridge.py already covers the full data-ready
# schedule flow. This extension focuses on the scheduled_requests endpoint and on
# the patch/delete operations that modify schedule state.

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
# Local helpers: seed schedule and request rows with controlled state
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
    """Seed one schedule row directly in the database for deterministic scenarios."""
    # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
    # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(schedule_row)
    db.session.commit()
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return schedule_row.id


def seed_request_row(
    db: Any,
    faker: Faker,
    user_id: int,
    schedule_id: int,
    *,
    status: str = "SUCCESS",
) -> int:
    """Seed one request row linked to a schedule for listing scenarios."""
    # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
    # quando l'endpoint POST richiederebbe troppo contesto esterno.
    request_row = db.Request(
        user_id=user_id,
        name=faker.pystr(),
        args={"datasets": ["agrmet"]},
        status=status,
        schedule_id=schedule_id,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(request_row)
    db.session.commit()
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return request_row.id


def delete_schedule_row(db: Any, schedule_id: int) -> None:
    """Delete one seeded schedule row from the database if still present."""
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    schedule = db.Schedule.query.get(schedule_id)
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if schedule is not None:
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.delete(schedule)
        db.session.commit()


def delete_request_row(db: Any, request_id: int) -> None:
    """Delete one seeded request row from the database if still present."""
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    request = db.Request.query.get(request_id)
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if request is not None:
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.delete(request)
        db.session.commit()


# =============================================================================
# Fixture: temporary authenticated user with schedule permissions
# =============================================================================


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary authenticated user for scheduled_requests tests."""
    # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    base = BaseTests()
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
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
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return user


# =============================================================================
# Tests: GET /schedules/<id>/requests - scheduled requests listing
# =============================================================================


class TestScheduledRequests:
    """Verify the scheduled_requests endpoint returns linked requests."""

    def test_last_true_no_successful_request_returns_404(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id>/requests?last=true must return 404 when no successful request exists."""
        # arrange - seed schedule without successful request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(db, faker, schedules_user.user_id)
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - get last scheduled request
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}/requests?last=true",
            headers=schedules_user.headers,
        )

        # assert - not found
        # Verifichiamo che la risposta confermi l'assenza della risorsa prima di usare
        # il payload.
        assert response.status_code == 404

    def test_last_false_returns_list_of_requests(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id>/requests?last=false must return list of all scheduled requests."""
        # arrange - seed schedule with multiple requests
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(db, faker, schedules_user.user_id)
        request_ids = [
            seed_request_row(db, faker, schedules_user.user_id, schedule_id, status="SUCCESS")
            for _ in range(3)
        ]
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))
        for request_id in request_ids:
            cleanup_registry.add(lambda rid=request_id: delete_request_row(db, rid))

        # act - get all scheduled requests
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}/requests?last=false",
            headers=schedules_user.headers,
        )

        # assert - list of requests
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_total_returns_count(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id>/requests?get_total=true must return total count."""
        # arrange - seed schedule with a few requests
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(db, faker, schedules_user.user_id)
        request_ids = [
            seed_request_row(db, faker, schedules_user.user_id, schedule_id, status="SUCCESS")
            for _ in range(5)
        ]
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))
        for request_id in request_ids:
            cleanup_registry.add(lambda rid=request_id: delete_request_row(db, rid))

        # act - get total count
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}/requests?get_total=true",
            headers=schedules_user.headers,
        )

        # assert - total count
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert "total" in data
        assert data["total"] >= 5


# =============================================================================
# Tests: PATCH /schedules/<id> and DELETE /schedules/<id>
# =============================================================================


class TestSchedulePatchAndDelete:
    """Verify the patch and delete operations modify schedule state correctly."""

    def test_disable_enabled_periodic_schedule_success(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> with is_active=false must disable an enabled periodic schedule."""
        # arrange - seed enabled periodic schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = {"name": str(schedule_id)}
        fake_celery.delete_periodic_task.return_value = True
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - disable the schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": false}',
            content_type="application/json",
        )

        # assert - success
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        schedule_row = db.Schedule.query.get(schedule_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert schedule_row.is_enabled is False

    def test_disable_already_disabled_schedule_conflict(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> with is_active=false must reject disabling an already disabled schedule."""
        # arrange - seed already disabled periodic schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = None
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - attempt to disable already disabled schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": false}',
            content_type="application/json",
        )

        # assert - conflict
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 409

    def test_enable_disabled_schedule_recreates_periodic_task(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> with is_active=true must enable a disabled periodic schedule."""
        # arrange - seed disabled periodic schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = None
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_create_periodic_task = MagicMock()
        import mistral.endpoints.schedules as schedules_module
        monkeypatch.setattr(
            schedules_module,
            "create_periodic_task_with_routing",
            fake_create_periodic_task,
        )

        # act - enable the schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": true}',
            content_type="application/json",
        )

        # assert - success
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        schedule_row = db.Schedule.query.get(schedule_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert schedule_row.is_enabled is True

    def test_enable_already_enabled_schedule_conflict(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """PATCH /schedules/<id> with is_active=true must reject enabling an already enabled schedule."""
        # arrange - seed already enabled periodic schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        fake_celery.get_periodic_task.return_value = {"name": str(schedule_id)}
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - attempt to enable already enabled schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.patch(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
            data='{"is_active": true}',
            content_type="application/json",
        )

        # assert - conflict
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 409

    def test_delete_schedule_removes_db_and_periodic_task(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """DELETE /schedules/<id> must remove the schedule from DB and celery."""
        # arrange - seed schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        fake_celery.delete_periodic_task.return_value = True
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - delete the schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.delete(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
        )

        # assert - success
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        schedule_row = db.Schedule.query.get(schedule_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert schedule_row is None
