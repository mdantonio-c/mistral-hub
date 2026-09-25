"""Fixtures dedicated to the data-ready integration subtree.

These fixtures prepare the minimal environment required by data-ready tests:

- the list of datasets accepted by the on-data-ready logic,
- authenticated admin headers for triggering events,
- direct access to the SQLAlchemy connector,
- a temporary user allowed to create schedules on the selected dataset.
"""

from mistral.endpoints.schedules import SingleSchedule
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASETS,
    DATA_READY_DATASET_NAME,
    create_data_ready_user,
    register_data_ready_user_cleanup,
)


import pytest


@pytest.fixture
def data_ready_base(test_runtime):
    """Expose a ``BaseTests`` helper while overriding the allowed data-ready datasets.

    The production configuration may not enable exactly the datasets that the test
    subtree wants to exercise. This fixture patches the authoritative list only
    for the lifetime of the fixture, so the tests can operate against a stable
    dataset set without permanently changing global state.
    """
    # Prepariamo la fixture data-ready: crea lo stato riusabile e lascia al test solo la
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
def data_ready_admin_headers(client: FlaskClient, data_ready_base):
    """Return admin authentication headers using the same base helper as the subtree."""
    # Prepariamo la fixture data-ready: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    headers, _ = data_ready_base.do_login(client, None, None)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return headers


@pytest.fixture
def data_ready_db():
    """Expose the SQLAlchemy connector reused by data-ready setup helpers and assertions."""
    # Prepariamo la fixture data-ready: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    return sqlalchemy.get_instance()


@pytest.fixture
def data_ready_user(
    client: FlaskClient,
    cleanup_registry,
    data_ready_base,
    test_runtime,
):
    """Provision a temporary user that can create schedules on the test dataset.

    If the configured forecast dataset is not available in the current runtime,
    the fixture skips the dependent tests instead of failing them with a later and
    less readable lookup error.
    """
    # Prepariamo la fixture data-ready: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    try:
        # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
        # account preesistenti.
        user = create_data_ready_user(
            data_ready_base,
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
        data_ready_base,
        client,
        cleanup_registry,
        user,
    )
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return user