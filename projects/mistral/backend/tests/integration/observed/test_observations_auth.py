"""Integration tests for early validation failures on the observed-data endpoint.

This module focuses on requests that should fail before any meaningful observed
data lookup happens because required inputs are incomplete or malformed.
"""

import pytest
from restapi.tests import API_URI, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_observations_without_complete_reftime_returns_bad_request(
    client: FlaskClient,
) -> None:
    """Verify that the endpoint rejects queries missing one side of the reftime range."""
    # arrange
    endpoint = f"{API_URI}/observations?q=license:CCBY_COMPLIANT"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 400


def test_observations_without_license_returns_bad_request(
    client: FlaskClient,
) -> None:
    """Verify that the endpoint rejects observed queries without a license clause."""
    # arrange
    endpoint = f"{API_URI}/observations"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 400