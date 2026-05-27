"""Shared integration fixtures for API scenarios under the modularized suite.

These fixtures provide a small authenticated baseline that many subtrees can
reuse: standard auth headers and a freshly created access key. Keeping them here
prevents every integration area from duplicating the same bootstrap code.
"""

import pytest
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.integration.access_key.support import ACCESS_KEY_ENDPOINT


@pytest.fixture
def auth_headers(client: FlaskClient):
    """Log in the default test user and return reusable authenticated headers."""
    # Prepariamo la fixture suite di test: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    base = BaseTests()
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    headers, _ = base.do_login(client, None, None)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return headers


@pytest.fixture
def fresh_access_key(client: FlaskClient, auth_headers):
    """Create a fresh access key and return it together with the auth headers.

    Tests that need both a logged-in user and a newly issued key can depend on
    this fixture instead of manually calling the access-key creation endpoint.
    """
    # Prepariamo la fixture suite di test: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert resp.status_code == 200
    data = resp.json
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert "key" in data
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return auth_headers, data["key"]