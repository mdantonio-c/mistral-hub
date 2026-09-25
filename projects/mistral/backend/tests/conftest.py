"""Suite-wide pytest configuration shared by the whole backend test tree."""

import pytest

from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.runtime import TestRuntime


def pytest_configure(config):
    """Register custom markers used across the modularized integration suite."""
    # Entriamo nel blocco operativo della configurazione di test, mantenendo esplicito quale
    # stato viene letto o prodotto.
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


@pytest.fixture(scope="session")
def test_runtime() -> TestRuntime:
    """Create the session-scoped runtime cache reused by multiple test domains."""
    # Prepariamo la fixture suite di test: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    return TestRuntime()


@pytest.fixture
def cleanup_registry() -> CleanupRegistry:
    """Collect teardown callbacks and paths that each test wants cleaned up."""
    # Prepariamo la fixture suite di test: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    registry = CleanupRegistry()
    # Cediamo la fixture al test; quando il test termina, il codice sotto il yield
    # eseguira il teardown.
    yield registry
    registry.run()
