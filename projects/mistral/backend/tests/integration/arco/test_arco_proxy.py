"""Integration tests for the authenticated ARCO proxy endpoint.

These scenarios verify the proxy behavior seen by API clients, including access
control and propagation of success or not-found responses.
"""

from unittest.mock import MagicMock

import pytest

from mistral.tests.helpers.auth import make_basic_auth
from restapi.services.authentication import BaseAuthentication
from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_arco_proxy_requires_authentication(client: FlaskClient) -> None:
    """Verify that the ARCO proxy enforces authentication before proxying data.

    The proxy ultimately serves remote Zarr content, but the access decision has
    to happen at the Meteo-Hub boundary first. This test protects that outer
    security contract.
    """
    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup")

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 401


def test_arco_proxy_returns_zgroup_for_authorized_user(
    client: FlaskClient,
    fresh_access_key,
    monkeypatch,
) -> None:
    """Verify that a user authenticated with an access key can read proxied Zarr metadata."""
    # arrange
    # Prepariamo lo scenario catalogo ARCO con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
    _, valid_key = fresh_access_key
    email = BaseAuthentication.default_user
    mock_s3 = MagicMock()
    mock_s3.client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b'{"zarr_format": 2}')
    }
    # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
    # test resta deterministico.
    monkeypatch.setattr("mistral.connectors.s3.get_instance", lambda: mock_s3)
    headers = make_basic_auth(email, valid_key)

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup", headers=headers)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert b"zarr_format" in response.data