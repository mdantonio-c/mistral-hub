"""Integration tests for the anonymous view of the dataset catalog.

This module focuses on the simplest public scenario: a user who is not logged
in should still be able to list public datasets and read the details of a known
public dataset, while unknown dataset identifiers must still return ``404``.
"""

import pytest
from faker import Faker
from mistral.tests.helpers.datasets import first_public_dataset_id

from restapi.tests import API_URI, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


PUBLIC_DATASET_NAME = "lm5"  # "ICON_2I_SURFACE_PRESSURE_LEVELS"


def test_dataset_endpoints_expose_public_catalog_without_login(
    client: FlaskClient,
    faker: Faker,
) -> None:
    """Verify the basic anonymous contract for the dataset catalog endpoints.

    The test checks three independent expectations:

    1. ``GET /datasets`` works without authentication,
    2. one public dataset returned by the catalog can be fetched directly,
    3. an unknown dataset identifier still produces ``404``.
    """
    # act
    list_response = client.get(f"{API_URI}/datasets")
    public_dataset_id = first_public_dataset_id(list_response.json or [])
    dataset_response = client.get(f"{API_URI}/datasets/{public_dataset_id}")
    missing_response = client.get(f"{API_URI}/datasets/{faker.pystr()}")

    # assert
    assert list_response.status_code == 200
    assert isinstance(list_response.json, list)
    assert dataset_response.status_code == 200
    assert isinstance(dataset_response.json, dict)
    assert missing_response.status_code == 404