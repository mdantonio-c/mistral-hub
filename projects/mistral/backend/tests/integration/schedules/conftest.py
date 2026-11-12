"""Fixture condivise dai test delle schedule (eventi data-ready e bridge opendata)."""

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
    """Abilita i dataset data-ready per tutti i test della cartella schedules.

    Sovrascrive temporaneamente `SingleSchedule.ON_DATA_READY_DATASETS`
    (POST /schedules in endpoints/schedules.py) e lo ripristina a fine test:
    senza questo override il backend rifiuta le schedule on-data-ready.
    """
    base = BaseTests()
    with test_runtime.override_attr(
        SingleSchedule, "ON_DATA_READY_DATASETS", DATA_READY_DATASETS
    ):
        yield base


@pytest.fixture
def schedules_admin_headers(client: FlaskClient, schedules_base):
    """Restituisce gli header dell'admin di default.

    Servono per inviare gli eventi data-ready (POST /data/ready, riservato agli admin).
    """
    headers, _ = schedules_base.do_login(client, None, None)
    return headers


@pytest.fixture
def schedules_user(
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    test_runtime,
):
    """Crea un utente abilitato alle schedule sul dataset forecast usato dal bridge.

    Usa `create_data_ready_user` (tests/helpers/data_ready.py), registra il cleanup
    dell'utente e salta il test se il dataset non e disponibile nell'ambiente.
    """
    try:
        user = create_data_ready_user(
            schedules_base,
            client,
            test_runtime,
            [DATA_READY_DATASET_NAME],
        )
    except LookupError:
        pytest.skip(
            f"Dataset '{DATA_READY_DATASET_NAME}' is not available in this environment"
        )
    register_data_ready_user_cleanup(
        schedules_base,
        client,
        cleanup_registry,
        user,
    )
    return user