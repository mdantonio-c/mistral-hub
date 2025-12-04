import base64

from mistral.tests.conftest import ACCESS_KEY_ENDPOINT
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
        # using admin user?
        email = "admin@nomail.org"

        # Wrong key
        headers = make_basic_auth(email, "WRONG-KEY")
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)
        assert resp.status_code == 401

    def test_04_valid_access_key(self, client: FlaskClient, fresh_access_key):
        headers_auth, valid_key = fresh_access_key
        # using admin user?
        email = "admin@nomail.org"

        headers = make_basic_auth(email, valid_key)
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        assert resp.status_code == 200
        assert resp.json["status"] == "OK"
