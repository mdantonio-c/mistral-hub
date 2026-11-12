"""Configurazione pytest valida per tutti i test del backend MeteoHub."""

import pytest

from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.real_workers import (
    NO_SMTP_MOCK_REASON,
    workers_use_smtp_mock,
)
from mistral.tests.helpers.runtime import TestRuntime


def pytest_configure(config):
    """Registra i marker personalizzati usati per classificare i test.

    I marker (``integration``, ``deterministic``, ``async_real``,
    ``runtime_sensitive``) servono solo a selezionare o saltare gruppi di test.
    """
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
