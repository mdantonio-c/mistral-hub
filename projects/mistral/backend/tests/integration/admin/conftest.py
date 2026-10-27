"""Fixture locali ai test degli endpoint metadata admin."""

from __future__ import annotations

import pytest
from restapi.tests import BaseTests, FlaskClient


@pytest.fixture
def admin_headers_EXT(client: FlaskClient) -> dict[str, str]:
    """Restituisce gli header dell'admin di default con scope per singolo test."""
    headers, _ = BaseTests().do_login(client, None, None)
    assert headers is not None
    return headers
