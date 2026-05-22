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
    base = BaseTests()
    with test_runtime.override_attr(
        SingleSchedule, "ON_DATA_READY_DATASETS", DATA_READY_DATASETS
    ):
        yield base


@pytest.fixture
def data_ready_admin_headers(client: FlaskClient, data_ready_base):
    """Return admin authentication headers using the same base helper as the subtree."""
    headers, _ = data_ready_base.do_login(client, None, None)
    return headers


@pytest.fixture
def data_ready_db():
    """Expose the SQLAlchemy connector reused by data-ready setup helpers and assertions."""
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