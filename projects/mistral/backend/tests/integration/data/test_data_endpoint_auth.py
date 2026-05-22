"""Integration tests for authentication on the extraction data endpoint."""

import pytest

from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_data_endpoint_requires_authentication(client: FlaskClient) -> None:
    """Verify that posting to the data endpoint without credentials returns 401."""
    # act
    response = client.post(f"{API_URI}/data")

    # assert
    assert response.status_code == 401