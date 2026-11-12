"""Fixture con uno scenario valido di dati osservati per ogni modalita backend."""

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
    """Fornisce uno scenario osservato che legge dati recenti da DBALLE.

    Lo scenario viene scoperto sui dati reali tramite GET /api/fields (vedi support.py).
    """
    yield from yield_observed_case(client, auth_headers, test_runtime, "dballe")


@pytest.fixture
def arkimet_observed_case(
    client: FlaskClient,
    auth_headers,
    test_runtime: TestRuntime,
) -> Iterator[ObservedCase]:
    """Fornisce uno scenario osservato che legge dati archiviati da Arkimet.

    Lo scenario viene scoperto sui dati reali tramite GET /api/fields (vedi support.py).
    """
    yield from yield_observed_case(client, auth_headers, test_runtime, "arkimet")


@pytest.fixture
def mixed_observed_case(
    client: FlaskClient,
    auth_headers,
    test_runtime: TestRuntime,
) -> Iterator[ObservedCase]:
    """Fornisce uno scenario osservato che copre sia dati DBALLE sia dati Arkimet.

    Lo scenario viene scoperto sui dati reali tramite GET /api/fields (vedi support.py).
    """
    yield from yield_observed_case(client, auth_headers, test_runtime, "mixed")