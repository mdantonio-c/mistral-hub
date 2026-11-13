"""Configurazione pytest valida per tutti i test del backend MeteoHub."""

import os

import pytest
from flask import Flask
from restapi.connectors.sqlalchemy import catch_db_exceptions
from restapi.server import create_app
from sqlalchemy.engine import Connection

from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.real_workers import (
    NO_SMTP_MOCK_REASON,
    workers_use_smtp_mock,
)
from mistral.tests.helpers.runtime import TestRuntime

PRODUCTION_GUARD_MESSAGE = (
    "The MeteoHub test suite creates, changes and deletes users, requests and files: "
    "it cannot run on a production stack (APP_MODE=production). "
    "Use a dedicated stack started with `rapydo --testing`."
)

# restapi avvolge questi metodi di classe con `catch_db_exceptions` a ogni
# inizializzazione del connettore SQLAlchemy, cioe a ogni `create_app`.
_WRAPPED_CONNECTION_METHODS = ("execute", "_execute_context")
# Tutti i wrapper creati da `catch_db_exceptions` condividono lo stesso codice.
_RESTAPI_DB_WRAPPER_CODE = catch_db_exceptions(lambda: None).__code__


def pytest_configure(config):
    """Ferma la suite negli stack di produzione e registra i marker personalizzati.

    I marker (``integration``, ``deterministic``, ``async_real``,
    ``runtime_sensitive``) servono solo a selezionare o saltare gruppi di test.
    """
    # Il controllo avviene prima della raccolta dei test e di qualunque accesso al DB.
    if os.environ.get("APP_MODE") == "production":
        pytest.exit(PRODUCTION_GUARD_MESSAGE, returncode=pytest.ExitCode.USAGE_ERROR)
    config.addinivalue_line(
        "markers", "integration: marks tests as integration-level"
    )
    config.addinivalue_line(
        "markers",
        "deterministic: marks tests whose control flow stays deterministic within the test runtime",
    )
    config.addinivalue_line(
        "markers",
        "async_real: marks tests that wait for real async dispatch via beat, broker, or workers",
    )
    config.addinivalue_line(
        "markers",
        "runtime_sensitive: marks tests whose outcome depends on runtime data or infrastructure state",
    )


def pytest_collection_modifyitems(config, items):
    """Salta i test ``async_real`` quando i worker reali invierebbero email vere."""
    # I task di questi test girano sui worker reali, dove monkeypatch non arriva:
    # solo negli stack `rapydo --testing` i worker usano il mock SMTP.
    if workers_use_smtp_mock():
        return
    skip_real_workers = pytest.mark.skip(reason=NO_SMTP_MOCK_REASON)
    for item in items:
        if item.get_closest_marker("async_real"):
            item.add_marker(skip_real_workers)


def unwrap_connection_methods() -> None:
    """Toglie da ``Connection`` i wrapper di restapi lasciati dalle app precedenti."""
    for name in _WRAPPED_CONNECTION_METHODS:
        method = getattr(Connection, name)
        while getattr(method, "__code__", None) is _RESTAPI_DB_WRAPPER_CODE:
            method = method.__wrapped__
        setattr(Connection, name, method)


@pytest.fixture
def app() -> Flask:
    """Crea l'app Flask del test, come la fixture omonima di restapi.

    Ogni test ha la sua app e restapi avvolge di nuovo i metodi di ``Connection``:
    senza togliere prima i wrapper delle app precedenti la catena crescerebbe di un
    livello per test, fino a superare il limite di ricorsione dopo circa 300 test.
    """
    unwrap_connection_methods()
    return create_app()


@pytest.fixture(scope="session")
def test_runtime() -> TestRuntime:
    """Crea lo stato condiviso da tutti i test della sessione.

    Contiene la cache degli id dei dataset e permette di cambiare un attributo
    del backend solo per la durata di un test (vedi ``helpers/runtime.py``).
    """
    return TestRuntime()


@pytest.fixture
def cleanup_registry() -> CleanupRegistry:
    """Raccoglie le azioni di pulizia registrate dal test e le esegue alla fine.

    Le azioni (cancellazione di utenti, righe DB, file) girano in ordine inverso
    di registrazione, anche quando il test fallisce.
    """
    registry = CleanupRegistry()
    yield registry
    registry.run()
