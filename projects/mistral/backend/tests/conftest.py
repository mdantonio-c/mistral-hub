import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

ACCESS_KEY_ENDPOINT = f"{API_URI}/access-key"


@pytest.fixture
def auth_headers(client: FlaskClient):
    base = BaseTests()
    headers, _ = base.do_login(client, None, None)
    return headers


@pytest.fixture
def fresh_access_key(client: FlaskClient, auth_headers):
    resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json
    assert "key" in data
    return auth_headers, data["key"]
