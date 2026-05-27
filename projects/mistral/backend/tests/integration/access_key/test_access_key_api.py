"""Integration tests for the lifecycle of user access keys.

This module covers the user-visible contract around access keys: creation,
retrieval, regeneration, expiration handling, and behavior for keys with no
expiration timestamp.
"""

from datetime import timedelta

import pytest
from restapi.connectors import sqlalchemy
from restapi.services.authentication import BaseAuthentication
from restapi.tests import FlaskClient

from .support import (
    ACCESS_KEY_ENDPOINT,
    ACCESS_KEY_VALIDATE_ENDPOINT,
)
from mistral.tests.helpers.auth import make_basic_auth


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAccessKeyAPI:
    """Group scenarios that cover creation, retrieval, regeneration, and expiry."""

    def test_01_get_access_key_unauthenticated(self, client: FlaskClient):
        """Verify that the access-key endpoint never serves anonymous callers.

        This is the outer authorization contract for the whole access-key area:
        before testing key lifecycle details, the suite proves that the endpoint
        is bound to an authenticated user session.
        """
        # Prepariamo lo scenario access-key con il minimo stato necessario, cosi
        # l'asserzione finale misura un solo comportamento.
        resp = client.get(ACCESS_KEY_ENDPOINT)
        # Verifichiamo che la risposta richieda credenziali quando l'utente non e
        # autenticato prima di usare il payload.
        assert resp.status_code == 401

    def test_02_get_existing_access_key(self, client: FlaskClient, fresh_access_key):
        """Verify that ``GET /access-key`` returns the key already issued to the user.

        The test first creates a fresh key through the fixture and then checks
        that a subsequent read returns exactly that same token instead of a new
        one or an empty payload.
        """
        # Prepariamo lo scenario access-key con il minimo stato necessario, cosi
        # l'asserzione finale misura un solo comportamento.
        headers, token = fresh_access_key
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=headers)
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine
        # prima di usare il payload.
        assert resp.status_code == 200
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert resp.json["key"] == token

    def test_03_regenerate_access_key(self, client: FlaskClient, auth_headers):
        """Verify that regenerating a key invalidates the previous token value.

        The contract here is not just that ``POST`` succeeds, but that the user
        ends up with a different access key and that subsequent reads expose the
        newly generated value.
        """

        # arrange
        # Prepariamo lo scenario access-key con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        old_token = resp.json["key"]

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        new_token = resp.json["key"]

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert new_token != old_token
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert resp.json["key"] == new_token

    def test_04_create_access_key_without_expiration(
        self, client: FlaskClient, auth_headers
    ):
        """Verify that the API accepts a non-expiring key when asked explicitly.

        Some callers need long-lived automation credentials. This scenario makes
        that contract explicit by checking that ``lifetime_seconds=None`` is
        stored as ``expiration=None`` in the response.
        """

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=auth_headers,
            json={"lifetime_seconds": None},
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 200
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert resp.json["expiration"] is None

    def test_06_validate_expired_access_key(
        self, client: FlaskClient, fresh_access_key_with_expiration
    ):
        """Verify that a previously valid key becomes unusable after expiration.

        The test forces the issued key into the past at database level and then
        proves that the validation endpoint rejects it with the same ``401`` seen
        for any other invalid credential.
        """

        # arrange
        # Prepariamo lo scenario access-key con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        _, token = fresh_access_key_with_expiration
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        db = sqlalchemy.get_instance()
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        user = db.User.query.filter_by(email=BaseAuthentication.default_user).first()
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert user is not None
        user.access_key.expiration = user.access_key.expiration - timedelta(
            seconds=3600
        )
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.commit()
        headers = make_basic_auth(user.email, token)

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert resp.status_code == 401