# EXTENSION TRACEABILITY: added by coverage extension prompt 04
# EXTENSION SCOPE: integrates the refactored suite without modifying legacy baseline
# EXTENSION DATA WINDOW: no real runtime data required; validation is input-only
# EXTENSION RUNTIME: deterministic input validation; no async dependencies
# EXTENSION CLEANUP: temporary users cleaned via cleanup_registry
#
# This module extends the schedules integration area with tests for:
# - POST /schedules with no schedule setting returns 400
# - POST /schedules with period < 15 minutes returns 403
# - POST /schedules opendata as non-admin returns 403
# - POST /schedules opendata multidataset returns 400
# - POST /schedules opendata observed dataset returns 400
# - POST /schedules with postprocessor as non-authorized user returns 401
# - POST /schedules with push queue missing returns 403
# - POST /schedules with push queue nonexistent returns 403
#
# The baseline test_schedule_opendata_bridge.py already covers the happy path
# schedule creation flow. This extension focuses on the validation edge cases
# that prevent invalid schedule submissions.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.endpoints import DOWNLOAD_DIR
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def dataset_ids_for_user(db: Any, dataset_names: list[str]) -> str:
    """Return the JSON dataset-id list used to authorize temporary users.

    These validation tests intentionally exercise authorization-independent
    branches such as opendata role checks, multidataset validation, and observed
    dataset rejection. Granting the datasets explicitly prevents local private
    dataset rules for `lm5`/`lm2.2` from becoming the assertion oracle.
    """
    # Leggiamo solo metadata SQLAlchemy, non dati meteorologici reali. Le date nei
    # payload restano nelle finestre documentate quando nominano dataset forecast.
    dataset_ids: list[str] = []
    for dataset_name in dataset_names:
        dataset = db.Datasets.query.filter_by(arkimet_id=dataset_name).first()
        # Rendiamo esplicita la precondizione del runtime: questi dataset sono parte
        # dell'ambiente Meteo-Hub usato dalle altre suite runtime-sensitive.
        assert dataset is not None, f"Dataset {dataset_name} is required by this test"
        dataset_ids.append(str(dataset.id))
    return json.dumps(dataset_ids)


# =============================================================================
# Fixture: temporary authenticated user with schedule permissions
# =============================================================================


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary authenticated user for schedule validation tests."""
    # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    base = BaseTests()
    db = sqlalchemy.get_instance()
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
    user = create_authenticated_test_user(
        base,
        client,
        permissions={
            "allowed_schedule": True,
            "open_dataset": True,
            "datasets": dataset_ids_for_user(db, ["agrmet", "lm5", "lm2.2"]),
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


@pytest.fixture
def admin_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary admin user for opendata schedule tests."""
    # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    base = BaseTests()
    db = sqlalchemy.get_instance()
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
    uuid, created_user = base.create_user(
        client,
        {
            "allowed_schedule": True,
            "open_dataset": True,
            "datasets": dataset_ids_for_user(db, ["agrmet", "lm5", "lm2.2"]),
        },
        ["admin_root"],
    )
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    headers, _ = base.do_login(
        client, created_user.get("email"), created_user.get("password")
    )

    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    user = db.User.query.filter_by(uuid=uuid).first()
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert user is not None

    user_obj = AuthenticatedTestUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
    )

    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user_obj.uuid,
        root_path=user_obj.output_dir.parent,
    )
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return user_obj


# =============================================================================
# Tests: POST /schedules - validation edge cases
# =============================================================================


class TestScheduleValidation:
    """Verify the validation rules for schedule creation."""

    def test_no_schedule_setting_returns_400(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
    ):
        """POST /schedules must reject payload with no schedule setting."""
        # arrange - build payload without period-settings, crontab-settings, or on-data-ready
        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_no_setting",
            "reftime": {"from": "2021-01-01T00:00:00Z", "to": "2021-01-01T01:00:00Z"},
            "dataset_names": ["agrmet"],
        })

        # act - post schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.post(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - bad request
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 400

    def test_period_less_than_15_minutes_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
    ):
        """POST /schedules must reject period settings below 15 minutes."""
        # arrange - build payload with period < 15 minutes
        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_short_period",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 10, "period": "minutes"},
        })

        # act - post schedule
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.post(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - forbidden
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 403

    def test_opendata_as_non_admin_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
    ):
        """POST /schedules with opendata=true must reject non-admin users."""
        # arrange - build opendata schedule payload
        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_opendata_non_admin",
            "reftime": {"from": "2021-10-19T00:00:00Z", "to": "2021-10-19T01:00:00Z"},
            "dataset_names": ["lm5"],
            "period-settings": {"every": 1, "period": "days"},
            "opendata": True,
        })

        # act - post schedule as non-admin
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.post(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - forbidden
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 403

    def test_opendata_multidataset_returns_400(
        self,
        client: FlaskClient,
        admin_user: AuthenticatedTestUser,
    ):
        """POST /schedules with opendata=true must reject multiple datasets."""
        # arrange - build opendata schedule with multiple datasets
        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_opendata_multi",
            "reftime": {"from": "2021-10-19T00:00:00Z", "to": "2021-10-19T01:00:00Z"},
            "dataset_names": ["lm5", "lm2.2"],
            "period-settings": {"every": 1, "period": "days"},
            "opendata": True,
        })

        # act - post schedule as admin
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.post(
            f"{API_URI}/schedules",
            headers=admin_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - bad request
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 400

    def test_opendata_observed_dataset_returns_400(
        self,
        client: FlaskClient,
        admin_user: AuthenticatedTestUser,
    ):
        """POST /schedules with opendata=true must reject observed datasets."""
        # arrange - build opendata schedule with observed dataset
        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_opendata_obs",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 1, "period": "days"},
            "opendata": True,
        })

        # act - post schedule as admin
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.post(
            f"{API_URI}/schedules",
            headers=admin_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - bad request
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 400

    def test_postprocessor_unauthorized_returns_401(
        self,
        client: FlaskClient,
        cleanup_registry,
    ):
        """POST /schedules with postprocessor must reject unauthorized users."""
        # arrange - create user without postprocessing permission
        # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
        # verifica del comportamento.
        base = BaseTests()
        db = sqlalchemy.get_instance()
        # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
        # account preesistenti.
        user_no_postproc = create_authenticated_test_user(
            base,
            client,
            permissions={
                "allowed_schedule": True,
                "allowed_postprocessing": False,
                "open_dataset": True,
                "datasets": dataset_ids_for_user(db, ["agrmet"]),
            },
        )
        register_test_user_cleanup(
            base,
            client,
            cleanup_registry,
            user_uuid=user_no_postproc.uuid,
            root_path=user_no_postproc.output_dir.parent,
        )

        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_postproc_unauth",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 1, "period": "days"},
            "postprocessors": [
                {
                    "processor_type": "derived_variables",
                    "variables": ["B12194"],
                }
            ],
        })

        # act - post schedule with postprocessor
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        response = client.post(
            f"{API_URI}/schedules",
            headers=user_no_postproc.headers,
            data=body,
            content_type="application/json",
        )

        # assert - unauthorized
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 401

    def test_push_queue_missing_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """POST /schedules with push=true must reject users without amqp_queue."""
        # arrange - build schedule with push=true
        # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
        # verifica riguarda la logica e non dettagli casuali di input.
        body = json.dumps({
            "request_name": "test_push_missing",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 1, "period": "days"},
        })

        # act - post schedule with push query param
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        fake_rabbit = MagicMock()
        fake_rabbit.queue_exists.return_value = False
        from restapi.connectors import rabbitmq
        monkeypatch.setattr(rabbitmq, "get_instance", lambda: fake_rabbit)
        response = client.post(
            f"{API_URI}/schedules?push=true",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - forbidden
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 403

    def test_push_queue_nonexistent_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """POST /schedules with push=true must reject a configured but missing AMQP queue."""
        # arrange - set a queue name on the temporary user and fake Rabbit saying it
        # does not exist. This covers the same backend branch without contacting RabbitMQ.
        db = sqlalchemy.get_instance()
        user = db.User.query.get(schedules_user.user_id)
        user.amqp_queue = "missing.prompt04.ext"
        db.session.commit()
        body = json.dumps({
            "request_name": "test_push_nonexistent",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 1, "period": "days"},
        })
        fake_rabbit = MagicMock()
        fake_rabbit.queue_exists.return_value = False
        from restapi.connectors import rabbitmq
        monkeypatch.setattr(rabbitmq, "get_instance", lambda: fake_rabbit)

        # act - post schedule with push query param
        response = client.post(
            f"{API_URI}/schedules?push=true",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - forbidden
        # Verifichiamo che la risposta confermi il diniego esplicito prima di usare
        # il payload.
        assert response.status_code == 403
