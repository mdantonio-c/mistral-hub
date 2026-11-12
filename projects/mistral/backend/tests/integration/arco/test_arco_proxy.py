"""Test di integrazione dell'endpoint proxy ARCO autenticato.

Gli scenari verificano il comportamento del proxy visto dai client API, incluso il
controllo di accesso e la propagazione delle risposte di successo o di oggetto non
trovato.
"""

from unittest.mock import MagicMock

import pytest

from mistral.tests.helpers.auth import AuthenticatedTestUser, make_basic_auth
from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_arco_proxy_requires_authentication(client: FlaskClient) -> None:
    """Verifica che il proxy ARCO richieda l'autenticazione prima di servire dati.

    Il proxy GET /api/arco/<path> (ArcoResource.get) serve contenuti Zarr remoti, ma la
    decisione di accesso deve avvenire prima, al confine di Meteo-Hub. Il test protegge
    questo contratto di sicurezza esterno.
    """
    # act
    response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup")

    # assert
    assert response.status_code == 401


def test_arco_proxy_returns_zgroup_for_authorized_user(
    client: FlaskClient,
    access_key_owner: AuthenticatedTestUser,
    fresh_access_key,
    monkeypatch,
) -> None:
    """Verifica che un utente con access key valida legga i metadati Zarr dal proxy.

    Endpoint esercitato: GET /api/arco/<path> (ArcoResource.get) con BasicAuth
    email:access key; il connettore S3 e sostituito da un MagicMock.
    """
    # arrange
    _, valid_key = fresh_access_key
    email = access_key_owner.email
    mock_s3 = MagicMock()
    mock_s3.client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b'{"zarr_format": 2}')
    }
    monkeypatch.setattr("mistral.connectors.s3.get_instance", lambda: mock_s3)
    headers = make_basic_auth(email, valid_key)

    # act
    response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup", headers=headers)

    # assert
    assert response.status_code == 200
    assert b"zarr_format" in response.data