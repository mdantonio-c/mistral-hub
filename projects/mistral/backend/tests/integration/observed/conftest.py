"""Fixtures that expose one valid observed-data scenario for each supported backend mode."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.runtime import TestRuntime

from .support import ObservedCase, yield_observed_case


@pytest.fixture
def dballe_observed_case(
    client: FlaskClient,
    auth_headers,
    test_runtime: TestRuntime,
) -> Iterator[ObservedCase]:
    """Provide one observed scenario that reads from recent DBALLE data."""
    # Prepariamo la fixture osservazioni: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    yield from yield_observed_case(client, auth_headers, test_runtime, "dballe")


@pytest.fixture
def arkimet_observed_case(
    client: FlaskClient,
    auth_headers,
    test_runtime: TestRuntime,
) -> Iterator[ObservedCase]:
    """Provide one observed scenario that reads from archived Arkimet data."""
    # Prepariamo la fixture osservazioni: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    yield from yield_observed_case(client, auth_headers, test_runtime, "arkimet")


@pytest.fixture
def mixed_observed_case(
    client: FlaskClient,
    auth_headers,
    test_runtime: TestRuntime,
) -> Iterator[ObservedCase]:
    """Provide one observed scenario that spans both DBALLE and Arkimet data."""
    # Prepariamo la fixture osservazioni: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    yield from yield_observed_case(client, auth_headers, test_runtime, "mixed")