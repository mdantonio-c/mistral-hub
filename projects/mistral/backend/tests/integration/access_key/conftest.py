"""Fixture locali per gli scenari access key che richiedono un setup piu ricco.

La maggior parte dei test access key puo riusare le fixture comuni della suite
``access_key_owner`` e ``fresh_access_key``. Questo modulo aggiunge solo cio che e
specifico del dominio access key, ad esempio una chiave con una scadenza esplicita.
"""

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.auth import AuthenticatedTestUser

from .support import ACCESS_KEY_ENDPOINT


@pytest.fixture
def fresh_access_key_with_expiration(
    client: FlaskClient, access_key_owner: AuthenticatedTestUser
):
    """Crea una access key che scade dopo un'ora (POST /api/access-key).

    I test sul comportamento della scadenza hanno bisogno di un token con durata
    nota e finita. La fixture crea una chiave di questo tipo per l'utente
    temporaneo ``access_key_owner`` e la restituisce insieme agli header del
    proprietario.
    """
    resp = client.post(
        ACCESS_KEY_ENDPOINT,
        headers=access_key_owner.headers,
        json={"lifetime_seconds": 3600},
    )
    assert resp.status_code == 200
    data = resp.json
    assert "key" in data
    assert "expiration" in data and data["expiration"] is not None
    return access_key_owner.headers, data["key"]