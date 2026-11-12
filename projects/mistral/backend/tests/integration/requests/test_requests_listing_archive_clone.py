# Finestra dati: non servono dati runtime reali; usa righe di richiesta inserite nel DB.
# Runtime: righe di richiesta finte e deterministiche; nessuna dipendenza asincrona.
# Cleanup: righe di richiesta e utenti temporanei rimossi tramite cleanup_registry.
#
# Questo modulo copre, nell'area delle richieste (endpoints/requests.py):
# - forma della risposta e paginazione di GET /requests
# - get_total=true restituisce 206 con il conteggio totale
# - filtro archived=true/false
# - PUT /requests/<id>: archiviazione riuscita
# - PUT /requests/<id>: archiviazione vietata per una richiesta pendente
# - PUT /requests/<id>: richiesta di un altro utente
# - GET /requests/<id>/clone: clone riuscito con i dettagli dei dataset
# - GET /requests/<id>/clone: richiesta inesistente
# - GET /requests/<id>/clone: richiesta di un altro utente
#
# DELETE /requests/<id> e gia coperto in dettaglio da test_delete_pending_request.py;
# qui si coprono le altre operazioni di gestione delle richieste.

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import json

import pytest
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.env import Env
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


grace_period_days = Env.get_int("GRACE_PERIOD", 2)
GRACE_PERIOD = timedelta(days=grace_period_days)


# =============================================================================
# Helper locale: inserisce una riga di richiesta con eta e stato controllati
# =============================================================================


def seed_request_row(
    db: Any,
    faker: Faker,
    user_id: int,
    *,
    archived: bool = False,
    status: str = "SUCCESS",
    age_days: int = 0,
    dataset_names: list[str] | None = None,
) -> int:
    """Inserisce direttamente nel DB una riga di richiesta per scenari deterministici.

    L'helper salta il percorso di creazione tramite endpoint, cosi i test possono
    concentrarsi sul contratto di listing, archiviazione e clone di
    endpoints/requests.py senza dipendere dai worker di estrazione o da dati di
    previsione reali.
    """
    submission_date = datetime.now() - timedelta(days=age_days)
    request_row = db.Request(
        user_id=user_id,
        name=faker.pystr(),
        args={"datasets": dataset_names or ["agrmet"]},
        submission_date=submission_date,
        status=status,
        archived=archived,
    )
    db.session.add(request_row)
    db.session.commit()
    return request_row.id


def dataset_ids_for_user(db: Any, dataset_names: list[str]) -> str:
    """Restituisce la lista JSON di id dataset richiesta dalla creazione utenti.

    L'endpoint di clone (``GET /api/requests/<id>/clone``) arricchisce gli args
    della richiesta in base ai dataset visibili all'utente autenticato. L'helper
    concede all'utente temporaneo l'accesso esplicito ai dataset della richiesta
    inserita, cosi il test resta portabile tra un setup locale con dataset di
    previsione privati e setup di CI con default piu permissivi.
    """
    # Leggiamo i dataset dal DB applicativo gia inizializzato, senza usare file meteo
    # reali: qui serve solo l'anagrafica necessaria alla serializzazione del clone.
    dataset_ids: list[str] = []
    for dataset_name in dataset_names:
        dataset = db.Datasets.query.filter_by(arkimet_id=dataset_name).first()
        # Controlliamo subito la precondizione del runtime, cosi un dataset mancante
        # produce un errore leggibile invece di un clone vuoto e ambiguo.
        assert dataset is not None, f"Dataset {dataset_name} is required by this test"
        dataset_ids.append(str(dataset.id))
    # Restituiamo il formato usato dall'endpoint admin utenti.
    return json.dumps(dataset_ids)


def delete_request_row(db: Any, request_id: int) -> None:
    """Cancella dal DB (modello ``Request``) la riga inserita, se esiste ancora."""
    request = db.Request.query.get(request_id)
    if request is not None:
        db.session.delete(request)
        db.session.commit()


# =============================================================================
# Fixture: utente temporaneo autenticato per gli scenari sul listing delle richieste
# =============================================================================


@pytest.fixture
def requests_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo autenticato per i test di listing e archiviazione.

    L'utente nasce tramite l'API admin degli utenti di restapi, con accesso al
    dataset ``agrmet``; il cleanup a fine test rimuove utente e cartelle di output.
    """
    base = BaseTests()
    db = sqlalchemy.get_instance()
    user = create_authenticated_test_user(
        base,
        client,
        permissions={
            "open_dataset": True,
            "datasets": dataset_ids_for_user(db, ["agrmet"]),
        },
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
# Test: GET /requests - listing, paginazione e filtro archived
# =============================================================================


class TestRequestsListing:
    """Verifica forma e filtri della risposta di GET /requests."""

    def test_get_requests_returns_expected_shape(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests deve restituire una lista con i campi standard di richiesta."""
        # arrange - inserisce una richiesta completata
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="SUCCESS",
        )
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - elenca le richieste dell'utente
        response = client.get(
            f"{API_URI}/requests",
            headers=requests_user.headers,
        )

        # assert - forma della risposta
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        assert isinstance(data, list)
        assert len(data) >= 1
        request_item = next((r for r in data if r["id"] == request_id), None)
        assert request_item is not None
        assert "id" in request_item
        assert "name" in request_item
        assert "args" in request_item
        assert "submission_date" in request_item
        assert "status" in request_item
        assert "dataset_names" in request_item["args"]

    def test_get_total_returns_206_with_count(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests?get_total=true deve restituire 206 con il campo total."""
        # arrange - inserisce alcune richieste
        db = sqlalchemy.get_instance()
        request_ids = [
            seed_request_row(db, faker, requests_user.user_id, status="SUCCESS")
            for _ in range(3)
        ]
        for request_id in request_ids:
            cleanup_registry.add(lambda rid=request_id: delete_request_row(db, rid))

        # act - chiede il conteggio totale
        response = client.get(
            f"{API_URI}/requests?get_total=true",
            headers=requests_user.headers,
        )

        # assert - 206 con il campo total
        assert response.status_code == 206
        data = BaseTests().get_content(response)
        assert "total" in data
        assert data["total"] >= 3

    def test_archived_false_excludes_archived_requests(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests?archived=false deve escludere le richieste archiviate."""
        # arrange - inserisce una richiesta attiva e una archiviata
        db = sqlalchemy.get_instance()
        active_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            archived=False,
            status="SUCCESS",
        )
        archived_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            archived=True,
            status="SUCCESS",
        )
        cleanup_registry.add(lambda: delete_request_row(db, active_id))
        cleanup_registry.add(lambda: delete_request_row(db, archived_id))

        # act - elenca le richieste non archiviate
        response = client.get(
            f"{API_URI}/requests?archived=false",
            headers=requests_user.headers,
        )

        # assert - la richiesta archiviata e esclusa
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        active_present = any(r["id"] == active_id for r in data)
        archived_present = any(r["id"] == archived_id for r in data)
        assert active_present
        assert not archived_present

    def test_archived_true_returns_only_archived_requests(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests?archived=true deve restituire solo le richieste archiviate."""
        # arrange - inserisce una richiesta attiva e una archiviata
        db = sqlalchemy.get_instance()
        active_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            archived=False,
            status="SUCCESS",
        )
        archived_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            archived=True,
            status="SUCCESS",
        )
        cleanup_registry.add(lambda: delete_request_row(db, active_id))
        cleanup_registry.add(lambda: delete_request_row(db, archived_id))

        # act - elenca le richieste archiviate
        response = client.get(
            f"{API_URI}/requests?archived=true",
            headers=requests_user.headers,
        )

        # assert - torna solo la richiesta archiviata
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        active_present = any(r["id"] == active_id for r in data)
        archived_present = any(r["id"] == archived_id for r in data)
        assert not active_present
        assert archived_present


# =============================================================================
# Test: PUT /requests/<id> - archiviazione
# =============================================================================


class TestRequestsArchive:
    """Verifica l'archiviazione delle richieste completate con PUT /requests/<id>."""

    def test_archive_success_for_old_completed_request(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """PUT /requests/<id> deve archiviare una richiesta completata.

        La richiesta e piu vecchia del grace period; dopo la chiamata la riga nel DB
        ha ``archived`` a True.
        """
        # arrange - inserisce una richiesta completata vecchia
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="SUCCESS",
            age_days=grace_period_days + 1,
        )
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - archivia la richiesta
        response = client.put(
            f"{API_URI}/requests/{request_id}",
            headers=requests_user.headers,
        )

        # assert - archiviazione riuscita
        assert response.status_code == 200
        request_row = db.Request.query.get(request_id)
        assert request_row.archived is True

    def test_archive_pending_request_forbidden(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """PUT /requests/<id> deve rifiutare con 403 una richiesta pendente.

        La richiesta e appena stata creata, quindi e ancora dentro il grace period.
        """
        # arrange - inserisce una richiesta pendente recente
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="PENDING",
            age_days=0,
        )
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - prova ad archiviare la richiesta pendente
        response = client.put(
            f"{API_URI}/requests/{request_id}",
            headers=requests_user.headers,
        )

        # assert - accesso negato
        assert response.status_code == 403

    def test_archive_owner_mismatch_unauthorized(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """PUT /requests/<id> deve rifiutare con 401 la richiesta di un altro utente."""
        # arrange - inserisce una richiesta di un altro utente
        db = sqlalchemy.get_instance()
        base = BaseTests()
        other_user = create_authenticated_test_user(base, client)
        register_test_user_cleanup(
            base,
            client,
            cleanup_registry,
            user_uuid=other_user.uuid,
            root_path=other_user.output_dir.parent,
        )

        request_id = seed_request_row(
            db,
            faker,
            other_user.user_id,
            status="SUCCESS",
            age_days=grace_period_days + 1,
        )
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - prova ad archiviare con l'utente sbagliato
        response = client.put(
            f"{API_URI}/requests/{request_id}",
            headers=requests_user.headers,
        )

        # assert - non autorizzato
        assert response.status_code == 401


# =============================================================================
# Test: GET /requests/<id>/clone - clone degli args con i dettagli dei dataset
# =============================================================================


class TestRequestsClone:
    """Verifica che GET /requests/<id>/clone restituisca args e dettagli dei dataset."""

    def test_clone_returns_args_with_dataset_specs(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests/<id>/clone deve restituire gli args con i dataset espansi."""
        # arrange - inserisce una richiesta completata
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="SUCCESS",
            dataset_names=["agrmet"],
        )
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - clona la richiesta
        response = client.get(
            f"{API_URI}/requests/{request_id}/clone",
            headers=requests_user.headers,
        )

        # assert - args con i dettagli dei dataset
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        assert "datasets" in data
        assert isinstance(data["datasets"], list)
        assert len(data["datasets"]) >= 1
        dataset_entry = data["datasets"][0]
        assert "id" in dataset_entry
        assert "name" in dataset_entry

    def test_clone_missing_request_not_found(
        self,
        client: FlaskClient,
        requests_user: AuthenticatedTestUser,
    ):
        """GET /requests/<id>/clone deve restituire 404 se la richiesta non esiste."""
        # arrange - usa un id di richiesta inesistente
        missing_request_id = 999999

        # act - prova a clonare la richiesta inesistente
        response = client.get(
            f"{API_URI}/requests/{missing_request_id}/clone",
            headers=requests_user.headers,
        )

        # assert - richiesta non trovata
        assert response.status_code == 404

    def test_clone_foreign_request_unauthorized(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests/<id>/clone deve dare 401 sulla richiesta di un altro utente."""
        # arrange - inserisce una richiesta di un altro utente
        db = sqlalchemy.get_instance()
        base = BaseTests()
        other_user = create_authenticated_test_user(base, client)
        register_test_user_cleanup(
            base,
            client,
            cleanup_registry,
            user_uuid=other_user.uuid,
            root_path=other_user.output_dir.parent,
        )

        request_id = seed_request_row(
            db,
            faker,
            other_user.user_id,
            status="SUCCESS",
            dataset_names=["agrmet"],
        )
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - prova a clonare con l'utente sbagliato
        response = client.get(
            f"{API_URI}/requests/{request_id}/clone",
            headers=requests_user.headers,
        )

        # assert - non autorizzato
        assert response.status_code == 401
