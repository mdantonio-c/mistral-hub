"""Fixtures shared by schedule integration tests that bridge data-ready events and opendata."""

import pytest
from mistral.endpoints.schedules import SingleSchedule
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    DATA_READY_DATASETS,
    create_data_ready_user,
    register_data_ready_user_cleanup,
)


@pytest.fixture
def schedules_base(test_runtime):
    """Override the enabled data-ready datasets for the whole schedules subtree."""
    # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    base = BaseTests()
    # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
    # test resta deterministico.
    with test_runtime.override_attr(
        SingleSchedule, "ON_DATA_READY_DATASETS", DATA_READY_DATASETS
    ):
        # Cediamo la fixture al test; quando il test termina, il codice sotto il yield
        # eseguira il teardown.
        yield base


@pytest.fixture
def schedules_admin_headers(client: FlaskClient, schedules_base):
    """Return admin authentication headers used to trigger data-ready events."""
    # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    headers, _ = schedules_base.do_login(client, None, None)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return headers


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    test_runtime,
):
    """Create a schedule-capable user for the forecast dataset used by bridge tests."""
    # Prepariamo la fixture schedules: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    try:
        # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
        # account preesistenti.
        user = create_data_ready_user(
            schedules_base,
            client,
            test_runtime,
            [DATA_READY_DATASET_NAME],
        )
    except LookupError:
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(
            f"Dataset '{DATA_READY_DATASET_NAME}' is not available in this environment"
        )
    register_data_ready_user_cleanup(
        schedules_base,
        client,
        cleanup_registry,
        user,
    )
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return user