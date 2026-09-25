"""Integration tests for authentication on the extraction data endpoint."""

import pytest

from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_data_endpoint_requires_authentication(client: FlaskClient) -> None:
    """Verify that posting to the data endpoint without credentials returns 401."""
    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.post(f"{API_URI}/data")

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 401