"""Test di integrazione sul ciclo di vita delle access key utente.

Il modulo verifica il comportamento visibile all'utente degli endpoint
/api/access-key e /api/access-key/validate (endpoints/access_key.py): creazione,
lettura, rigenerazione, gestione della scadenza e chiavi senza scadenza. Ogni
chiave appartiene all'utente temporaneo ``access_key_owner``.
"""

from datetime import timedelta

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from .support import (
    ACCESS_KEY_ENDPOINT,
    ACCESS_KEY_VALIDATE_ENDPOINT,
)
from mistral.tests.helpers.auth import AuthenticatedTestUser, make_basic_auth


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAccessKeyAPI:
    """Raggruppa gli scenari su creazione, lettura, rigenerazione e scadenza."""

    def test_01_get_access_key_unauthenticated(self, client: FlaskClient):
        """Verifica che GET /api/access-key risponda 401 a chi non e autenticato.

        E il controllo di autorizzazione piu esterno dell'area access key: prima
        dei dettagli sul ciclo di vita, il test dimostra che l'endpoint richiede
        una sessione utente autenticata.
        """
        resp = client.get(ACCESS_KEY_ENDPOINT)
        assert resp.status_code == 401

    def test_02_get_existing_access_key(self, client: FlaskClient, fresh_access_key):
        """Verifica che ``GET /access-key`` restituisca la chiave gia emessa all'utente.

        Il test crea prima una chiave nuova tramite la fixture e poi controlla che
        una lettura successiva restituisca esattamente lo stesso token, non uno
        nuovo o un payload vuoto.
        """
        headers, token = fresh_access_key
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=headers)
        assert resp.status_code == 200
        assert resp.json["key"] == token

    def test_03_regenerate_access_key(self, client: FlaskClient, fresh_access_key):
        """Verifica che rigenerare la chiave (POST /api/access-key) cambi il token.

        Non basta che il ``POST`` vada a buon fine: l'utente deve ottenere una
        access key diversa e le letture successive devono restituire il nuovo
        valore. La prima chiave e creata dalla fixture, quindi lo scenario non
        dipende da chiavi lasciate da test precedenti.
        """

        # arrange
        headers, old_token = fresh_access_key

        # act
        resp = client.post(ACCESS_KEY_ENDPOINT, headers=headers)
        new_token = resp.json["key"]

        # assert
        assert new_token != old_token
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=headers)
        assert resp.json["key"] == new_token

    def test_04_create_access_key_without_expiration(
        self, client: FlaskClient, access_key_owner: AuthenticatedTestUser
    ):
        """Verifica che POST /api/access-key accetti una chiave senza scadenza.

        Alcuni client hanno bisogno di credenziali di lunga durata per
        l'automazione. Lo scenario controlla che ``lifetime_seconds=None`` venga
        restituito come ``expiration=None`` nella risposta.
        """

        # act
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=access_key_owner.headers,
            json={"lifetime_seconds": None},
        )

        # assert
        assert resp.status_code == 200
        assert resp.json["expiration"] is None

    def test_06_validate_expired_access_key(
        self,
        client: FlaskClient,
        access_key_owner: AuthenticatedTestUser,
        fresh_access_key_with_expiration,
    ):
        """Verifica che una chiave prima valida diventi inutilizzabile dopo la scadenza.

        Il test sposta nel passato la scadenza della chiave direttamente nel
        database e poi dimostra che GET /api/access-key/validate la rifiuta con lo
        stesso ``401`` usato per qualsiasi altra credenziale non valida. Cambia
        solo la chiave dell'utente temporaneo.
        """

        # arrange
        _, token = fresh_access_key_with_expiration
        db = sqlalchemy.get_instance()
        user = db.User.query.get(access_key_owner.user_id)
        assert user is not None
        # La chiave dura 3600 secondi: togliendo un'ora la scadenza cade nel passato.
        user.access_key.expiration = user.access_key.expiration - timedelta(
            seconds=3600
        )
        db.session.commit()
        headers = make_basic_auth(user.email, token)

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 401