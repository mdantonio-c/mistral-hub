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
    base = BaseTests()
    headers, _ = base.do_login(client, None, None)
    return headers


@pytest.fixture
def fresh_access_key(client: FlaskClient, auth_headers):
    """Create a fresh access key and return it together with the auth headers.

    Tests that need both a logged-in user and a newly issued key can depend on
    this fixture instead of manually calling the access-key creation endpoint.
    """
    resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json
    assert "key" in data
    return auth_headers, data["key"]