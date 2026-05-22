"""Suite-wide pytest configuration shared by the whole backend test tree."""

import pytest

from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.runtime import TestContext, TestRuntime


def pytest_configure(config):
    """Register custom markers used across the modularized integration suite."""
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
    return TestRuntime()


@pytest.fixture
def test_ctx(test_runtime: TestRuntime) -> TestContext:
    """Provide a per-test mutable context and run its cleanup at teardown."""
    ctx = test_runtime.new_context()
    yield ctx
    ctx.cleanup()


@pytest.fixture
def cleanup_registry() -> CleanupRegistry:
    """Collect teardown callbacks and paths that each test wants cleaned up."""
    registry = CleanupRegistry()
    yield registry
    registry.run()
