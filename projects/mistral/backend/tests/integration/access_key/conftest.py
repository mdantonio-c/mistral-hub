"""Fixtures local to access-key scenarios that need slightly richer setup.

Most access-key tests can reuse the suite-wide authenticated headers and fresh key
fixtures. This module adds only the pieces that are specific to the access-key
domain, such as a key with an explicit expiration timestamp.
"""

import pytest
from restapi.tests import FlaskClient

from .support import ACCESS_KEY_ENDPOINT


@pytest.fixture
def fresh_access_key_with_expiration(client: FlaskClient, auth_headers):
    """Create an access key that expires after one hour.

    Tests that verify expiry behavior need a token whose lifetime is known and
    finite. This fixture creates exactly that kind of key and returns it together
    with the authenticated headers used to create it.
    """
    # Prepariamo la fixture access-key: crea lo stato riusabile e lascia al test solo la
    # verifica del comportamento.
    resp = client.post(
        ACCESS_KEY_ENDPOINT,
        headers=auth_headers,
        json={"lifetime_seconds": 3600},
    )
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert resp.status_code == 200
    data = resp.json
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert "key" in data
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert "expiration" in data and data["expiration"] is not None
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return auth_headers, data["key"]