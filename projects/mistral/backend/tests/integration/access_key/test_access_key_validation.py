"""Integration tests for the access-key validation endpoint.

These scenarios check which combinations of email and access key are accepted or
rejected when credentials are presented through HTTP Basic authentication.
"""

import pytest
from restapi.services.authentication import BaseAuthentication
from restapi.tests import FlaskClient

from .support import (
    ACCESS_KEY_ENDPOINT,
    ACCESS_KEY_VALIDATE_ENDPOINT,
)
from mistral.tests.helpers.auth import make_basic_auth


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAccessKeyValidationAPI:
    """Group scenarios that verify which credentials the validation endpoint accepts."""

    def test_01_missing_credentials(self, client: FlaskClient):
        """Reject a validation request that does not carry any credentials."""
        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 401

    def test_02_invalid_email(self, client: FlaskClient):
        """Reject a validation request when the user email does not exist."""
        # arrange
        # Prepariamo lo scenario access-key con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        headers = make_basic_auth("nonexistent@example.com", "whatever")

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 401

    def test_03_invalid_access_key(self, client: FlaskClient, fresh_access_key):
        """Reject a validation request when the presented key does not match the user."""
        # arrange
        # Prepariamo lo scenario access-key con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        _, _ = fresh_access_key
        email = BaseAuthentication.default_user
        headers = make_basic_auth(email, "WRONG-KEY")

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 401

    def test_04_valid_access_key(self, client: FlaskClient, fresh_access_key):
        """Accept a validation request when email and access key match."""
        # arrange
        # Prepariamo lo scenario access-key con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        _, valid_key = fresh_access_key
        email = BaseAuthentication.default_user
        headers = make_basic_auth(email, valid_key)

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 200
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert resp.json["status"] == "OK"

    def test_05_validate_access_key_without_expiration(
        self, client: FlaskClient, auth_headers
    ):
        """Verify that a key created without expiration remains acceptable.

        This complements the creation-side test by checking the user-facing
        behavior of the validation endpoint, not just the shape of the creation
        response.
        """

        # arrange
        # Prepariamo lo scenario access-key con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=auth_headers,
            json={"lifetime_seconds": None},
        )
        token = resp.json["key"]
        email = BaseAuthentication.default_user
        headers = make_basic_auth(email, token)

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 200
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert resp.json["status"] == "OK"