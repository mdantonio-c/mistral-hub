"""Fixture dedicate ai test di integrazione del sottoalbero data-ready.

Queste fixture preparano l'ambiente minimo richiesto dai test data-ready:

- la lista dei dataset accettati dalla logica on-data-ready,
- gli header di autenticazione admin per lanciare gli eventi,
- l'accesso diretto al connettore SQLAlchemy,
- un utente temporaneo abilitato a creare schedule sul dataset scelto,
- un trasporto Celery locale per l'endpoint delle schedule (niente broker, niente
  RedBeat).
"""

from types import SimpleNamespace

import mistral.endpoints.schedules as schedules_endpoint
from mistral.endpoints.schedules import SingleSchedule
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.helpers.celery_fakes import AcceptTasksWithoutRunningCelery
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASETS,
    DATA_READY_DATASET_NAME,
    create_data_ready_user,
    register_data_ready_user_cleanup,
)


import pytest


@pytest.fixture(autouse=True)
def schedules_endpoint_without_real_celery(monkeypatch):
    """Isola le chiamate a /schedules dei test data-ready dal broker reale e da RedBeat.

    Creare una schedule on-data-ready (``POST /api/schedules``) invia un primo
    ``data_extract`` al broker, e una schedule crontab o periodica scrive in RedBeat
    una entry che scatta ogni giorno. I test data-ready verificano la decisione del
    launcher, non quel trasporto: il fake e installato solo sui nomi usati dal modulo
    dell'endpoint (endpoints/schedules.py), quindi la logica dell'endpoint e le righe
    nel DB restano reali mentre nulla arriva ai worker Celery o a RedBeat.
    """
    schedules_celery = AcceptTasksWithoutRunningCelery("data_extract")
    monkeypatch.setattr(
        schedules_endpoint,
        "celery",
        SimpleNamespace(get_instance=lambda: schedules_celery),
    )
    for task_factory in (
        "create_periodic_task_with_routing",
        "create_crontab_task_with_routing",
    ):
        monkeypatch.setattr(
            schedules_endpoint,
            task_factory,
            lambda *args, **kwargs: None,
        )
    return schedules_celery


@pytest.fixture
def data_ready_base(test_runtime):
    """Fornisce un helper ``BaseTests`` forzando la lista dei dataset data-ready.

    La configurazione di produzione potrebbe non abilitare esattamente i dataset che
    questi test vogliono esercitare. La fixture sostituisce la lista autorevole
    (``SingleSchedule.ON_DATA_READY_DATASETS`` in endpoints/schedules.py) solo per la
    durata della fixture, cosi i test lavorano su un insieme di dataset stabile senza
    modificare in modo permanente lo stato globale.
    """
    base = BaseTests()
    with test_runtime.override_attr(
        SingleSchedule, "ON_DATA_READY_DATASETS", DATA_READY_DATASETS
    ):
        yield base


@pytest.fixture
def data_ready_admin_headers(client: FlaskClient, data_ready_base):
    """Restituisce gli header di autenticazione dell'admin di default.

    Usa lo stesso helper ``BaseTests`` del sottoalbero; servono per chiamare
    ``POST /api/data/ready`` (endpoints/data_ready.py), che richiede il ruolo
    operational.
    """
    headers, _ = data_ready_base.do_login(client, None, None)
    return headers


@pytest.fixture
def data_ready_db():
    """Espone il connettore SQLAlchemy del backend, usato da helper e asserzioni."""
    return sqlalchemy.get_instance()


@pytest.fixture
def data_ready_user(
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    test_runtime,
):
    """Crea un utente temporaneo che puo creare schedule sul dataset di test.

    L'utente nasce tramite l'API admin degli utenti di restapi e viene rimosso dal
    cleanup a fine test. Se il dataset di previsione configurato non e disponibile
    nel runtime corrente, la fixture salta i test dipendenti invece di farli fallire
    piu avanti con un errore di lookup meno leggibile.
    """
    try:
        user = create_data_ready_user(
            data_ready_base,
            client,
            test_runtime,
            [DATA_READY_DATASET_NAME],
        )
    except LookupError:
        pytest.skip(
            f"Dataset '{DATA_READY_DATASET_NAME}' is not available in this environment"
        )
    register_data_ready_user_cleanup(
        data_ready_base,
        client,
        cleanup_registry,
        user,
    )
    return user