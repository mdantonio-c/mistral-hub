"""Fixture locali ai test degli endpoint metadata admin."""

from __future__ import annotations

import pytest
from restapi.tests import BaseTests, FlaskClient


@pytest.fixture
def admin_headers(client: FlaskClient) -> dict[str, str]:
    """Restituisce gli header dell'admin di default con scope per singolo test.

    Esegue un login reale con `BaseTests.do_login` (POST /auth/login di restapi);
    gli header servono ai test degli endpoint /api/admin/* di questo dominio.
    """
    headers, _ = BaseTests().do_login(client, None, None)
    assert headers is not None
    return headers
