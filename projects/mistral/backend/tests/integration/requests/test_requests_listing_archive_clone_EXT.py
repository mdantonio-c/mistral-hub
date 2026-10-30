# EXTENSION TRACEABILITY: added by coverage extension prompt 04
# EXTENSION SCOPE: integrates the refactored suite without modifying legacy baseline
# EXTENSION DATA WINDOW: no real runtime data required; uses DB-seeded request rows
# EXTENSION RUNTIME: deterministic fake request rows; no async dependencies
# EXTENSION CLEANUP: request rows and temporary users cleaned via cleanup_registry
#
# This module extends the requests integration area with tests for:
# - GET /requests response shape and pagination
# - get_total=true returns 206 with total count
# - archived=true/false filtering
# - PUT /requests/<id> archive success
# - PUT /requests/<id> archive pending request forbidden
# - PUT /requests/<id> owner mismatch
# - GET /requests/<id>/clone success with dataset specs
# - GET /requests/<id>/clone missing request
# - GET /requests/<id>/clone foreign request
#
# The baseline already covers DELETE /requests/<id> thoroughly in
# test_delete_pending_request.py. This extension focuses on the remaining
# request-management surfaces.

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
# Local helper: seed a request row with controlled age and status
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
    """Seed one request row directly in the database for deterministic scenarios.

    The helper bypasses the endpoint creation path so tests can focus on the
    listing, archive, and clone contract without depending on extraction workers
    or real forecast runtime.
    """
    # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
    # quando l'endpoint POST richiederebbe troppo contesto esterno.
    submission_date = datetime.now() - timedelta(days=age_days)
    request_row = db.Request(
        user_id=user_id,
        name=faker.pystr(),
        args={"datasets": dataset_names or ["agrmet"]},
        submission_date=submission_date,
        status=status,
        archived=archived,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(request_row)
    db.session.commit()
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return request_row.id


def dataset_ids_for_user(db: Any, dataset_names: list[str]) -> str:
    """Return the JSON dataset-id list expected by the user creation endpoint.

    The clone endpoint enriches request args through the authenticated user's
    dataset visibility. This helper grants the temporary user explicit access to
    the datasets used by the seeded request so the test stays portable between a
    local setup with private forecast datasets and CI setups with looser defaults.
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
# Fixture: temporary authenticated user for request-listing scenarios
# =============================================================================


@pytest.fixture
def requests_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary authenticated user for request listing and archive tests."""
    # Prepariamo la fixture richieste utente: crea lo stato riusabile e lascia al test
    # solo la verifica del comportamento.
    base = BaseTests()
    db = sqlalchemy.get_instance()
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
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
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return user


# =============================================================================
# Tests: GET /requests - listing, pagination, and archived filter
# =============================================================================


class TestRequestsListing:
    """Verify the shape and filtering behavior of GET /requests."""

    def test_get_requests_returns_expected_shape(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests must return a list with standard request fields."""
        # arrange - seed one completed request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="SUCCESS",
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - list user requests
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests",
            headers=requests_user.headers,
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
        request_item = next((r for r in data if r["id"] == request_id), None)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
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
        """GET /requests?get_total=true must return 206 with total field."""
        # arrange - seed a few requests
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        request_ids = [
            seed_request_row(db, faker, requests_user.user_id, status="SUCCESS")
            for _ in range(3)
        ]
        for request_id in request_ids:
            # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
            # affidabile anche in caso di fallimento.
            cleanup_registry.add(lambda rid=request_id: delete_request_row(db, rid))

        # act - get total count
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests?get_total=true",
            headers=requests_user.headers,
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

    def test_archived_false_excludes_archived_requests(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests?archived=false must exclude archived requests from result."""
        # arrange - seed one active and one archived request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, active_id))
        cleanup_registry.add(lambda: delete_request_row(db, archived_id))

        # act - list non-archived requests
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests?archived=false",
            headers=requests_user.headers,
        )

        # assert - archived request is excluded
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        active_present = any(r["id"] == active_id for r in data)
        archived_present = any(r["id"] == archived_id for r in data)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert active_present
        assert not archived_present

    def test_archived_true_returns_only_archived_requests(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests?archived=true must return only archived requests."""
        # arrange - seed one active and one archived request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, active_id))
        cleanup_registry.add(lambda: delete_request_row(db, archived_id))

        # act - list archived requests
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests?archived=true",
            headers=requests_user.headers,
        )

        # assert - only archived request is returned
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        active_present = any(r["id"] == active_id for r in data)
        archived_present = any(r["id"] == archived_id for r in data)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert not active_present
        assert archived_present


# =============================================================================
# Tests: PUT /requests/<id> - archive operation
# =============================================================================


class TestRequestsArchive:
    """Verify the archive operation for completed requests."""

    def test_archive_success_for_old_completed_request(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """PUT /requests/<id> must archive a completed request outside grace period."""
        # arrange - seed one old completed request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="SUCCESS",
            age_days=grace_period_days + 1,
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - archive the request
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.put(
            f"{API_URI}/requests/{request_id}",
            headers=requests_user.headers,
        )

        # assert - archive success
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        request_row = db.Request.query.get(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert request_row.archived is True

    def test_archive_pending_request_forbidden(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """PUT /requests/<id> must reject archiving a pending request inside grace period."""
        # arrange - seed one recent pending request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="PENDING",
            age_days=0,
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - attempt to archive pending request
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.put(
            f"{API_URI}/requests/{request_id}",
            headers=requests_user.headers,
        )

        # assert - forbidden
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 403

    def test_archive_owner_mismatch_unauthorized(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """PUT /requests/<id> must reject archiving another user's request."""
        # arrange - seed request owned by a different user
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        base = BaseTests()
        # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
        # account preesistenti.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - attempt to archive with wrong user
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.put(
            f"{API_URI}/requests/{request_id}",
            headers=requests_user.headers,
        )

        # assert - unauthorized
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 401


# =============================================================================
# Tests: GET /requests/<id>/clone - clone request args with dataset specs
# =============================================================================


class TestRequestsClone:
    """Verify the clone endpoint returns request args with enriched dataset specs."""

    def test_clone_returns_args_with_dataset_specs(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests/<id>/clone must return args with expanded dataset specs."""
        # arrange - seed one completed request
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        request_id = seed_request_row(
            db,
            faker,
            requests_user.user_id,
            status="SUCCESS",
            dataset_names=["agrmet"],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - clone the request
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests/{request_id}/clone",
            headers=requests_user.headers,
        )

        # assert - args with dataset specs
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata
        # a buon fine prima di usare il payload.
        assert response.status_code == 200
        data = BaseTests().get_content(response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
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
        """GET /requests/<id>/clone must return 404 for nonexistent request."""
        # arrange - use a request id that does not exist
        missing_request_id = 999999

        # act - attempt to clone missing request
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests/{missing_request_id}/clone",
            headers=requests_user.headers,
        )

        # assert - not found
        # Verifichiamo che la risposta confermi l'assenza della risorsa prima di usare
        # il payload.
        assert response.status_code == 404

    def test_clone_foreign_request_unauthorized(
        self,
        client: FlaskClient,
        faker: Faker,
        requests_user: AuthenticatedTestUser,
        cleanup_registry,
    ):
        """GET /requests/<id>/clone must reject cloning another user's request."""
        # arrange - seed request owned by a different user
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        base = BaseTests()
        # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
        # account preesistenti.
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
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_request_row(db, request_id))

        # act - attempt to clone with wrong user
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.get(
            f"{API_URI}/requests/{request_id}/clone",
            headers=requests_user.headers,
        )

        # assert - unauthorized
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 401
