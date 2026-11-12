"""Test di integrazione dell'autenticazione su POST /data (endpoints/data.py)."""

import pytest

from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_data_endpoint_requires_authentication(client: FlaskClient) -> None:
    """Verifica che POST /data senza credenziali risponda 401 (Data.post)."""
    # act
    response = client.post(f"{API_URI}/data")

    # assert
    assert response.status_code == 401