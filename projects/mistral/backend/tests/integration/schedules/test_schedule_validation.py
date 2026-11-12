# Finestra dati: nessun dato runtime reale richiesto; si valida solo l'input.
# Runtime: validazione dell'input deterministica; l'endpoint delle schedule non arriva
# mai a Celery/RedBeat reali (forbid_real_schedule_dispatch fa fallire prima il test).
# Cleanup: utenti temporanei rimossi tramite cleanup_registry.
#
# Questo modulo contiene i test di integrazione delle schedule per:
# - POST /schedules senza impostazioni di schedule restituisce 400
# - POST /schedules con period inferiore a 15 minuti restituisce 403
# - POST /schedules opendata da utente non admin restituisce 403
# - POST /schedules opendata con piu dataset restituisce 400
# - POST /schedules opendata su dataset osservato restituisce 400
# - POST /schedules con postprocessor da utente non autorizzato restituisce 401
# - POST /schedules con push senza coda restituisce 403
# - POST /schedules con push su coda inesistente restituisce 403
#
# test_schedule_opendata_bridge.py copre gia il flusso di creazione della schedule
# nel caso di successo. Questo modulo si concentra sui casi limite di validazione
# che bloccano l'invio di schedule non valide.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import mistral.endpoints.schedules as schedules_endpoint
import orjson
import pytest
from restapi.connectors import sqlalchemy
from restapi.services.authentication import Role
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.endpoints import DOWNLOAD_DIR
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


@pytest.fixture(autouse=True)
def forbid_real_schedule_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fa fallire il test se POST /schedules supera la validazione.

    L'endpoint crea la riga Schedule, il task periodico RedBeat e l'eventuale primo
    data_extract solo dopo celery.get_instance(). Questi test si aspettano un rifiuto
    precedente: se la validazione non scatta, nulla deve arrivare al Celery reale.
    pytest.fail solleva un'eccezione non intercettata dal catch-all di restapi, quindi
    il bypass diventa un fallimento esplicito e non una risposta HTTP qualsiasi.
    """

    def fail_on_real_dispatch() -> None:
        pytest.fail(
            "POST /schedules ha superato la validazione e avrebbe creato una "
            "schedule reale con task Celery/RedBeat"
        )

    # Sostituiamo solo il nome usato dal modulo endpoint, non il connettore condiviso.
    monkeypatch.setattr(
        schedules_endpoint,
        "celery",
        SimpleNamespace(get_instance=fail_on_real_dispatch),
    )


def dataset_ids_for_user(db: Any, dataset_names: list[str]) -> str:
    """Restituisce la lista JSON di id dei dataset usata per autorizzare gli utenti.

    Questi test di validazione esercitano di proposito rami che non dipendono
    dalle autorizzazioni, come il controllo del ruolo per opendata, la validazione
    multidataset e il rifiuto dei dataset osservati. Concedere i dataset in modo
    esplicito evita che le regole locali sui dataset privati `lm5`/`lm2.2`
    decidano l'esito dell'asserzione.
    """
    # Leggiamo solo gli id dei dataset dal DB, non dati meteorologici reali.
    dataset_ids: list[str] = []
    for dataset_name in dataset_names:
        dataset = db.Datasets.query.filter_by(arkimet_id=dataset_name).first()
        # Rendiamo esplicita la precondizione del runtime: questi dataset sono parte
        # dell'ambiente Meteo-Hub usato dalle altre suite runtime-sensitive.
        assert dataset is not None, f"Dataset {dataset_name} is required by this test"
        dataset_ids.append(str(dataset.id))
    return json.dumps(dataset_ids)


# =============================================================================
# Fixture: utente autenticato temporaneo con permessi sulle schedule
# =============================================================================


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente autenticato temporaneo per i test di validazione delle schedule.

    Utente non admin (solo Role.USER) con `allowed_schedule`, `open_dataset` e i
    dataset agrmet, lm5 e lm2.2; sostituisce, in questo modulo, la `schedules_user`
    del conftest.
    """
    base = BaseTests()
    db = sqlalchemy.get_instance()
    # Il ruolo e fissato a Role.USER: senza, BaseTests.create_user ne sceglie uno a
    # caso (anche admin_root) e il gate opendata diventa instabile.
    user = create_authenticated_test_user(
        base,
        client,
        permissions={
            "allowed_schedule": True,
            "open_dataset": True,
            "datasets": dataset_ids_for_user(db, ["agrmet", "lm5", "lm2.2"]),
            "roles": orjson.dumps([Role.USER.value]).decode("UTF8"),
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


@pytest.fixture
def admin_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente admin temporaneo (ruolo admin_root) per i test opendata.

    Serve a superare il controllo sul ruolo di POST /schedules con opendata=true e
    raggiungere le validazioni successive; il cleanup e registrato in cleanup_registry.
    """
    base = BaseTests()
    db = sqlalchemy.get_instance()
    uuid, created_user = base.create_user(
        client,
        {
            "allowed_schedule": True,
            "open_dataset": True,
            "datasets": dataset_ids_for_user(db, ["agrmet", "lm5", "lm2.2"]),
        },
        ["admin_root"],
    )
    headers, _ = base.do_login(
        client, created_user.get("email"), created_user.get("password")
    )

    user = db.User.query.filter_by(uuid=uuid).first()
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
    return user_obj


# =============================================================================
# Test: POST /schedules - casi limite di validazione
# =============================================================================


class TestScheduleValidation:
    """Verifica le regole di validazione nella creazione delle schedule.

    Esercita POST /schedules (schema ScheduledDataExtraction e SingleSchedule.post).
    """

    def test_no_schedule_setting_returns_400(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
    ):
        """POST /schedules risponde 400 se mancano le impostazioni di schedule."""
        # arrange - payload senza period-settings, crontab-settings o on-data-ready
        body = json.dumps({
            "request_name": "test_no_setting",
            "reftime": {"from": "2021-01-01T00:00:00Z", "to": "2021-01-01T01:00:00Z"},
            "dataset_names": ["agrmet"],
        })

        # act - invia la schedule
        response = client.post(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - richiesta non valida
        assert response.status_code == 400

    def test_period_less_than_15_minutes_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
    ):
        """POST /schedules risponde 403 se il period e inferiore a 15 minuti."""
        # arrange - payload con period inferiore a 15 minuti
        body = json.dumps({
            "request_name": "test_short_period",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 10, "period": "minutes"},
        })

        # act - invia la schedule
        response = client.post(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - accesso negato
        assert response.status_code == 403

    def test_opendata_as_non_admin_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
    ):
        """POST /schedules con opendata=true risponde 403 agli utenti non admin."""
        # arrange - l'utente temporaneo deve essere un utente semplice, altrimenti il
        # 403 atteso dipenderebbe dal ruolo scelto da BaseTests.create_user.
        db = sqlalchemy.get_instance()
        persisted_user = db.User.query.get(schedules_user.user_id)
        assert [role.name for role in persisted_user.roles] == [Role.USER.value]

        # arrange - payload di una schedule opendata
        body = json.dumps({
            "request_name": "test_opendata_non_admin",
            "reftime": {"from": "2021-10-19T00:00:00Z", "to": "2021-10-19T01:00:00Z"},
            "dataset_names": ["lm5"],
            "period-settings": {"every": 1, "period": "days"},
            "opendata": True,
        })

        # act - invia la schedule come utente non admin
        response = client.post(
            f"{API_URI}/schedules",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - accesso negato
        assert response.status_code == 403

    def test_opendata_multidataset_returns_400(
        self,
        client: FlaskClient,
        admin_user: AuthenticatedTestUser,
    ):
        """POST /schedules con opendata=true risponde 400 se c'e piu di un dataset."""
        # arrange - schedule opendata con piu dataset
        body = json.dumps({
            "request_name": "test_opendata_multi",
            "reftime": {"from": "2021-10-19T00:00:00Z", "to": "2021-10-19T01:00:00Z"},
            "dataset_names": ["lm5", "lm2.2"],
            "period-settings": {"every": 1, "period": "days"},
            "opendata": True,
        })

        # act - invia la schedule come admin
        response = client.post(
            f"{API_URI}/schedules",
            headers=admin_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - 400 dal ramo multidataset, non dal controllo precedente sul gruppo
        # di licenza che risponde anch'esso 400.
        assert response.status_code == 400
        assert (
            BaseTests().get_content(response)
            == "Multi dataset for opendata schedules is not supported"
        )

    def test_opendata_observed_dataset_returns_400(
        self,
        client: FlaskClient,
        admin_user: AuthenticatedTestUser,
    ):
        """POST /schedules con opendata=true risponde 400 sui dataset osservati."""
        # arrange - schedule opendata su un dataset osservato
        body = json.dumps({
            "request_name": "test_opendata_obs",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 1, "period": "days"},
            "opendata": True,
        })

        # act - invia la schedule come admin
        response = client.post(
            f"{API_URI}/schedules",
            headers=admin_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - richiesta non valida
        assert response.status_code == 400

    def test_postprocessor_unauthorized_returns_401(
        self,
        client: FlaskClient,
        cleanup_registry,
    ):
        """POST /schedules con postprocessor risponde 401 all'utente non autorizzato."""
        # arrange - utente senza permesso di postprocessing
        base = BaseTests()
        db = sqlalchemy.get_instance()
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

        # act - invia la schedule con un postprocessor
        response = client.post(
            f"{API_URI}/schedules",
            headers=user_no_postproc.headers,
            data=body,
            content_type="application/json",
        )

        # assert - non autorizzato
        assert response.status_code == 401

    def test_push_queue_missing_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """POST /schedules con push=true risponde 403 se l'utente non ha amqp_queue."""
        # arrange - schedule da inviare con push=true
        body = json.dumps({
            "request_name": "test_push_missing",
            "reftime": {"from": "2020-04-06T00:00:00Z", "to": "2020-04-06T01:00:00Z"},
            "dataset_names": ["agrmet"],
            "period-settings": {"every": 1, "period": "days"},
        })

        # act - invia la schedule con il parametro push
        # RabbitMQ finto: la coda dell'utente (qui non configurata) risulta inesistente.
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

        # assert - accesso negato
        assert response.status_code == 403

    def test_push_queue_nonexistent_returns_403(
        self,
        client: FlaskClient,
        schedules_user: AuthenticatedTestUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """POST /schedules con push=true risponde 403 se la coda AMQP non esiste."""
        # arrange - assegna un nome di coda all'utente temporaneo e usa un RabbitMQ
        # finto che la dichiara inesistente: si copre il ramo del backend senza
        # contattare RabbitMQ.
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

        # act - invia la schedule con il parametro push
        response = client.post(
            f"{API_URI}/schedules?push=true",
            headers=schedules_user.headers,
            data=body,
            content_type="application/json",
        )

        # assert - accesso negato
        assert response.status_code == 403
