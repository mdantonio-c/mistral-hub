# EXTENSION TRACEABILITY: added by coverage extension prompt 04
# EXTENSION SCOPE: integrates the refactored suite without modifying legacy baseline
# EXTENSION DATA WINDOW: no real runtime data required; uses DB-seeded schedule rows
# EXTENSION RUNTIME: deterministic fake schedule rows; no async dependencies
# EXTENSION CLEANUP: schedule rows and temporary users cleaned via cleanup_registry
#
# This module extends the schedules integration area with tests for:
# - GET /schedules list returns expected shape
# - GET /schedules?get_total=true returns 206 with total count
# - GET /schedules/<id> returns schedule details
# - GET /schedules/<id> owner mismatch forbidden
#
# The baseline test_schedule_opendata_bridge.py already covers the full schedule
# creation and data-ready flow. This extension focuses on the basic CRUD API
# contracts that listing and get-by-id expose.

from __future__ import annotations

from typing import Any

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
# Local helper: seed a schedule row with controlled args
# =============================================================================


def seed_schedule_row(
    db: Any,
    faker: Faker,
    user_id: int,
    *,
    dataset_names: list[str] | None = None,
    enabled: bool = True,
    on_data_ready: bool = True,
    opendata: bool = False,
) -> int:
    """Seed one schedule row directly in the database for deterministic scenarios.

    The helper bypasses the endpoint creation path so tests can focus on the
    listing and get-by-id contract without depending on RedBeat or real Celery
    infrastructure.
    """
    # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
    # quando l'endpoint POST richiederebbe troppo contesto esterno.
    schedule_row = db.Schedule(
        user_id=user_id,
        name=faker.pystr(),
        args={
            "datasets": dataset_names or ["agrmet"],
            "reftime": None,
            "filters": None,
            "postprocessors": None,
            "output_format": None,
            "only_reliable": False,
            "pushing_queue": None,
        },
        is_enabled=enabled,
        on_data_ready=on_data_ready,
        period=PeriodEnum.days,
        every=1,
        opendata=opendata,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(schedule_row)
    db.session.commit()
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return schedule_row.id


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


# =============================================================================
# Fixture: temporary authenticated user with schedule permissions
# =============================================================================


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary authenticated user for schedule CRUD tests."""
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
# Tests: GET /schedules - listing and pagination
# =============================================================================


class TestSchedulesListing:
    """Verify the shape and pagination behavior of GET /schedules."""

    def test_get_schedules_returns_expected_shape(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules must return a list with standard schedule fields."""
        # arrange - seed one schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            dataset_names=["agrmet"],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - list user schedules
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
        )

        # assert - response shape
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert isinstance(data, list)
        assert len(data) >= 1
        schedule_item = next((s for s in data if s["id"] == schedule_id), None)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert schedule_item is not None
        assert "id" in schedule_item
        assert "name" in schedule_item
        assert "args" in schedule_item
        assert "enabled" in schedule_item
        assert "on_data_ready" in schedule_item

    def test_get_total_returns_206_with_count(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules?get_total=true must return 206 with total field."""
        # arrange - seed a few schedules
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_ids = [
            seed_schedule_row(db, faker, schedules_user.user_id, dataset_names=["agrmet"])
            for _ in range(3)
        ]
        for schedule_id in schedule_ids:
            # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
            # affidabile anche in caso di fallimento.
            cleanup_registry.add(lambda sid=schedule_id: delete_schedule_row(db, sid))

        # act - get total count
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules?get_total=true",
            headers=schedules_user.headers,
        )

        # assert - 206 with total
        # Verifichiamo che la risposta confermi l'uso del codice parziale prima di
        # usare il payload.
        assert response.status_code == 206
        data = BaseTests().get_content(response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert "total" in data
        assert data["total"] >= 3


# =============================================================================
# Tests: GET /schedules/<id> - get schedule by id
# =============================================================================


class TestScheduleGetById:
    """Verify the get-by-id operation returns schedule details."""

    def test_get_schedule_by_id_returns_details(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id> must return the schedule details."""
        # arrange - seed one schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            dataset_names=["agrmet"],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - get schedule by id
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
        )

        # assert - schedule details
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert data["id"] == schedule_id
        assert "name" in data
        assert "args" in data
        assert "enabled" in data
        assert "on_data_ready" in data

    def test_get_schedule_owner_mismatch_forbidden(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id> must reject accessing another user's schedule."""
        # arrange - seed schedule owned by a different user
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        base = BaseTests()
        # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
        # account preesistenti.
        other_user = create_authenticated_test_user(
            base,
            client,
            permissions={"allowed_schedule": True},
        )
        register_test_user_cleanup(
            base,
            client,
            cleanup_registry,
            user_uuid=other_user.uuid,
            root_path=other_user.output_dir.parent,
        )

        schedule_id = seed_schedule_row(
            db,
            faker,
            other_user.user_id,
            dataset_names=["agrmet"],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - attempt to get with wrong user
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
        )

        # assert - forbidden
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 403
