import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

ACCESS_KEY_ENDPOINT = f"{API_URI}/access-key"


@pytest.fixture
def auth_headers(client: FlaskClient):
    """Log in with 'default' user only once for the entire test session."""
    base = BaseTests()
    headers, _ = base.do_login(client, None, None)
    return headers


@pytest.fixture
def fresh_access_key(client: FlaskClient, auth_headers):
    """Create access key for each test."""
    resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json
    assert "key" in data
    return auth_headers, data["key"]


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
