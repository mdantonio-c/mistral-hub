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
    resp = client.post(
        ACCESS_KEY_ENDPOINT,
        headers=auth_headers,
        json={"lifetime_seconds": 3600},
    )
    assert resp.status_code == 200
    data = resp.json
    assert "key" in data
    assert "expiration" in data and data["expiration"] is not None
    return auth_headers, data["key"]