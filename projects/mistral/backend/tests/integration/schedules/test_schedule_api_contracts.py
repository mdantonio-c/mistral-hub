# Finestra dati: nessun dato runtime reale richiesto; usa righe schedule scritte nel DB.
# Runtime: righe schedule finte e deterministiche; nessuna dipendenza asincrona.
# Cleanup: righe schedule e utenti temporanei rimossi tramite cleanup_registry.
#
# Questo modulo contiene i test di integrazione delle schedule per:
# - GET /schedules restituisce una lista con la struttura attesa
# - GET /schedules?get_total=true restituisce 206 con il conteggio totale
# - GET /schedules/<id> restituisce il dettaglio della schedule
# - GET /schedules/<id> nega l'accesso se la schedule e di un altro utente
#
# test_schedule_opendata_bridge.py copre gia il flusso completo di creazione della
# schedule e di data-ready. Questo modulo si concentra sui contratti API di base
# esposti dal listing e dalla lettura per id.

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
# Helper locale: inserisce una riga schedule con argomenti controllati
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
    """Inserisce una riga schedule direttamente nel database per scenari deterministici.

    L'helper evita il percorso di creazione dell'endpoint (POST /schedules), cosi i
    test si concentrano sul contratto di listing e lettura per id senza dipendere da
    RedBeat o da un'infrastruttura Celery reale.
    """
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
    db.session.add(schedule_row)
    db.session.commit()
    return schedule_row.id


def delete_schedule_row(db: Any, schedule_id: int) -> None:
    """Elimina dal database una riga schedule inserita dal test, se esiste ancora."""
    schedule = db.Schedule.query.get(schedule_id)
    if schedule is not None:
        db.session.delete(schedule)
        db.session.commit()


# =============================================================================
# Fixture: utente autenticato temporaneo con permessi sulle schedule
# =============================================================================


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente autenticato temporaneo per i test CRUD sulle schedule.

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
# Test: GET /schedules - listing e paginazione
# =============================================================================


class TestSchedulesListing:
    """Verifica struttura e paginazione di GET /schedules (Schedules.get)."""

    def test_get_schedules_returns_expected_shape(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules restituisce una lista con i campi standard della schedule."""
        # arrange - inserisce una schedule
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            dataset_names=["agrmet"],
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - elenca le schedule dell'utente
        response = client.get(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
        )

        # assert - struttura della risposta
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        assert isinstance(data, list)
        assert len(data) >= 1
        schedule_item = next((s for s in data if s["id"] == schedule_id), None)
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
        """GET /schedules?get_total=true deve rispondere 206 con il campo total."""
        # arrange - inserisce alcune schedule
        db = sqlalchemy.get_instance()
        schedule_ids = [
            seed_schedule_row(db, faker, schedules_user.user_id, dataset_names=["agrmet"])
            for _ in range(3)
        ]
        for schedule_id in schedule_ids:
            cleanup_registry.add(lambda sid=schedule_id: delete_schedule_row(db, sid))

        # act - richiede il conteggio totale
        response = client.get(
            f"{API_URI}/schedules?get_total=true",
            headers=schedules_user.headers,
        )

        # assert - 206 con il totale
        assert response.status_code == 206
        data = BaseTests().get_content(response)
        assert "total" in data
        assert data["total"] >= 3


# =============================================================================
# Test: GET /schedules/<id> - lettura della schedule per id
# =============================================================================


class TestScheduleGetById:
    """Verifica la lettura per id con GET /schedules/<id> (SingleSchedule.get)."""

    def test_get_schedule_by_id_returns_details(
        self,
        client: FlaskClient,
        faker: Faker,
        schedules_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /schedules/<id> deve restituire il dettaglio della schedule."""
        # arrange - inserisce una schedule
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_row(
            db,
            faker,
            schedules_user.user_id,
            dataset_names=["agrmet"],
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - legge la schedule per id
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
        )

        # assert - dettaglio della schedule
        assert response.status_code == 200
        data = BaseTests().get_content(response)
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
        """GET /schedules/<id> risponde 403 se la schedule e di un altro utente."""
        # arrange - inserisce una schedule di un altro utente
        db = sqlalchemy.get_instance()
        base = BaseTests()
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
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # act - tenta la lettura con l'utente sbagliato
        response = client.get(
            f"{API_URI}/schedules/{schedule_id}",
            headers=schedules_user.headers,
        )

        # assert - accesso negato
        assert response.status_code == 403
