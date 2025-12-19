import base64
from datetime import timedelta

from mistral.tests.conftest import ACCESS_KEY_ENDPOINT
from restapi.connectors import sqlalchemy
from restapi.services.authentication import BaseAuthentication
from restapi.tests import BaseTests, FlaskClient


class TestAccessKeyAPI(BaseTests):
    def test_01_get_access_key_unauthenticated(self, client: FlaskClient):
        """An unauthenticated user should receive 401"""
        resp = client.get(ACCESS_KEY_ENDPOINT)
        assert resp.status_code == 401

    def test_02_get_existing_access_key(self, client: FlaskClient, fresh_access_key):
        """Retrieve the newly created key"""
        headers, token = fresh_access_key
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=headers)
        assert resp.status_code == 200
        assert resp.json["key"] == token

    def test_03_regenerate_access_key(self, client: FlaskClient, auth_headers):
        """Regenerate a key: the token must change"""

        # get access key before regeneration
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        old_token = resp.json["key"]

        # regenerate a key
        resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        new_token = resp.json["key"]
        assert new_token != old_token

        # get access key after regeneration
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        assert resp.json["key"] == new_token

    def test_04_create_access_key_without_expiration(
        self, client: FlaskClient, auth_headers
    ):
        """Create an access key without expiration"""

        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=auth_headers,
            json={"lifetime_seconds": None},
        )
        assert resp.status_code == 200
        assert resp.json["expiration"] is None

    def test_06_validate_expired_access_key(
        self, client: FlaskClient, fresh_access_key_with_expiration
    ):
        """An expired key should return 401"""

        headers, token = fresh_access_key_with_expiration

        db = sqlalchemy.get_instance()
        user = db.User.query.filter_by(email=BaseAuthentication.default_user).first()
        # force expiration
        user.access_key.expiration = user.access_key.expiration - timedelta(
            seconds=3600
        )
        db.session.commit()

        headers = make_basic_auth(user.email, token)
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)
        assert resp.status_code == 401


def make_basic_auth(email: str, access_key: str) -> dict:
    token = base64.b64encode(f"{email}:{access_key}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


ACCESS_KEY_VALIDATE_ENDPOINT = f"{ACCESS_KEY_ENDPOINT}/validate"


class TestAccessKeyValidationAPI(BaseTests):
    def test_01_missing_credentials(self, client: FlaskClient):
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT)
        assert resp.status_code == 401

    def test_02_invalid_email(self, client: FlaskClient):
        headers = make_basic_auth("nonexistent@example.com", "whatever")
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)
        assert resp.status_code == 401

    def test_03_invalid_access_key(self, client: FlaskClient, fresh_access_key):
        headers_auth, valid_key = fresh_access_key
        email = BaseAuthentication.default_user

        # Wrong key
        headers = make_basic_auth(email, "WRONG-KEY")
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)
        assert resp.status_code == 401

    def test_04_valid_access_key(self, client: FlaskClient, fresh_access_key):
        headers_auth, valid_key = fresh_access_key
        email = BaseAuthentication.default_user

        headers = make_basic_auth(email, valid_key)
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        assert resp.status_code == 200
        assert resp.json["status"] == "OK"

    def test_05_validate_access_key_without_expiration(
        self, client: FlaskClient, auth_headers
    ):
        """A non-expiring access key must always be valid"""

        # create non-expiring key
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=auth_headers,
            json={"lifetime_seconds": None},
        )
        token = resp.json["key"]
        email = BaseAuthentication.default_user

        headers = make_basic_auth(email, token)
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        assert resp.status_code == 200
        assert resp.json["status"] == "OK"
