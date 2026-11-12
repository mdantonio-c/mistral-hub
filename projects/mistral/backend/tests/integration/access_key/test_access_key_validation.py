"""Test di integrazione dell'endpoint di validazione delle access key.

Gli scenari verificano quali combinazioni di email e access key vengono accettate
o rifiutate da GET /api/access-key/validate (endpoints/access_key.py) quando le
credenziali arrivano tramite autenticazione HTTP Basic. Le chiavi sono emesse per
l'utente temporaneo ``access_key_owner``, mai per l'account predefinito.
"""

import pytest
from restapi.tests import FlaskClient

from .support import (
    ACCESS_KEY_ENDPOINT,
    ACCESS_KEY_VALIDATE_ENDPOINT,
)
from mistral.tests.helpers.auth import AuthenticatedTestUser, make_basic_auth


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAccessKeyValidationAPI:
    """Raggruppa gli scenari su quali credenziali accetta l'endpoint di validazione."""

    def test_01_missing_credentials(self, client: FlaskClient):
        """Verifica che GET /api/access-key/validate risponda 401 senza credenziali."""
        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT)

        # assert
        assert resp.status_code == 401

    def test_02_invalid_email(self, client: FlaskClient):
        """Verifica che la validazione risponda 401 se l'email non esiste."""
        # arrange
        headers = make_basic_auth("nonexistent@example.com", "whatever")

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 401

    def test_03_invalid_access_key(
        self,
        client: FlaskClient,
        access_key_owner: AuthenticatedTestUser,
        fresh_access_key,
    ):
        """Verifica che la validazione risponda 401 se la chiave non e dell'utente."""
        # arrange
        _, _ = fresh_access_key
        email = access_key_owner.email
        headers = make_basic_auth(email, "WRONG-KEY")

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 401

    def test_04_valid_access_key(
        self,
        client: FlaskClient,
        access_key_owner: AuthenticatedTestUser,
        fresh_access_key,
    ):
        """Verifica che la validazione risponda 200 se email e chiave corrispondono."""
        # arrange
        _, valid_key = fresh_access_key
        email = access_key_owner.email
        headers = make_basic_auth(email, valid_key)

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 200
        assert resp.json["status"] == "OK"

    def test_05_validate_access_key_without_expiration(
        self, client: FlaskClient, access_key_owner: AuthenticatedTestUser
    ):
        """Verifica che una chiave creata senza scadenza venga accettata.

        Completa il test sulla creazione (test_access_key_api.py) controllando il
        comportamento di GET /api/access-key/validate, non solo la forma della
        risposta di POST /api/access-key.
        """

        # arrange
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=access_key_owner.headers,
            json={"lifetime_seconds": None},
        )
        token = resp.json["key"]
        email = access_key_owner.email
        headers = make_basic_auth(email, token)

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 200
        assert resp.json["status"] == "OK"