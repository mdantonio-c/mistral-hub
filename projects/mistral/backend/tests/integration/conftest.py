"""Shared integration fixtures for API scenarios under the modularized suite.

These fixtures provide a small authenticated baseline that many subtrees can
reuse: standard auth headers, a temporary access-key owner with a fresh key, and
the perimeter that confines the global request-cleanup task. Keeping them here
prevents every integration area from duplicating the same bootstrap code.
"""

from pathlib import Path
from typing import Any

import pytest
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from mistral.tests.helpers.task_perimeter import (
    RequestsCleanupPerimeter,
    confine_requests_cleanup,
)
from mistral.tests.integration.access_key.support import ACCESS_KEY_ENDPOINT


@pytest.fixture
def auth_headers(client: FlaskClient):
    """Log in the default test user and return reusable authenticated headers."""
    # Prepariamo la fixture suite di test: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    base = BaseTests()
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    headers, _ = base.do_login(client, None, None)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return headers


def _revoke_access_key(client: FlaskClient, headers: Any) -> None:
    """Revoke the owner's key, if any, before the owner itself is deleted."""
    response = client.delete(ACCESS_KEY_ENDPOINT, headers=headers)
    assert response.status_code in (204, 404)


@pytest.fixture
def access_key_owner(client: FlaskClient, cleanup_registry) -> AuthenticatedTestUser:
    """Create the temporary user that owns the access keys issued by a test.

    Creating a key revokes the previous key of the logged user. A throwaway owner
    keeps these writes away from the configured default account.
    """
    base = BaseTests()
    user = create_authenticated_test_user(base, client)
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    # Registrata dopo l'utente, la revoca gira prima della sua cancellazione:
    # la FK di AccessKey verso User non ammette NULL.
    cleanup_registry.add(lambda: _revoke_access_key(client, user.headers))
    return user


@pytest.fixture
def fresh_access_key(client: FlaskClient, access_key_owner: AuthenticatedTestUser):
    """Create a fresh key for ``access_key_owner`` and return headers and key.

    Tests that need both a logged-in user and a newly issued key can depend on
    this fixture instead of manually calling the access-key creation endpoint.
    BasicAuth scenarios pair the key with ``access_key_owner.email``.
    """
    # Prepariamo la fixture suite di test: crea lo stato riusabile e lascia al test solo
    # la verifica del comportamento.
    resp = client.post(ACCESS_KEY_ENDPOINT, headers=access_key_owner.headers)
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert resp.status_code == 200
    data = resp.json
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert "key" in data
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return access_key_owner.headers, data["key"]


@pytest.fixture
def requests_cleanup_perimeter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> RequestsCleanupPerimeter:
    """Confine ``automatic_cleanup`` to the rows and files registered by the test.

    Tests must call ``allow(...)`` with the users and requests they created; the
    orphan-file scan only sees ``download_root``, a temporary directory.
    """
    return confine_requests_cleanup(monkeypatch, tmp_path / "downloads")