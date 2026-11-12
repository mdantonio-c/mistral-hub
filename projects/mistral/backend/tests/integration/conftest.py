"""Fixture condivise dai test di integrazione delle API.

Forniscono una base autenticata minima riusabile da tutte le aree: header di
login dell'utente di default, un utente temporaneo proprietario di una access
key nuova e il perimetro che limita il task globale di pulizia delle richieste.
Tenerle qui evita di ripetere lo stesso setup in ogni area di ``integration/``.
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
    """Esegue il login con l'utente di default e restituisce gli header autenticati.

    L'account e condiviso da tutti i test che usano questa fixture: va usato solo
    per letture, non per creare o ruotare access key.
    """
    base = BaseTests()
    headers, _ = base.do_login(client, None, None)
    return headers


def _revoke_access_key(client: FlaskClient, headers: Any) -> None:
    """Revoca la access key del proprietario (``DELETE /access-key``), se esiste."""
    response = client.delete(ACCESS_KEY_ENDPOINT, headers=headers)
    assert response.status_code in (204, 404)


@pytest.fixture
def access_key_owner(client: FlaskClient, cleanup_registry) -> AuthenticatedTestUser:
    """Crea un utente temporaneo a cui intestare le access key create dal test.

    Creare una access key revoca quella precedente dell'utente loggato: usare un
    utente usa-e-getta evita di toccare l'account di default. A fine test la key
    viene revocata e l'utente cancellato.
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
    """Crea una access key nuova per ``access_key_owner`` con ``POST /access-key``.

    Restituisce la coppia ``(header, key)``. I test BasicAuth usano la key insieme
    a ``access_key_owner.email``.
    """
    resp = client.post(ACCESS_KEY_ENDPOINT, headers=access_key_owner.headers)
    assert resp.status_code == 200
    data = resp.json
    assert "key" in data
    return access_key_owner.headers, data["key"]


@pytest.fixture
def requests_cleanup_perimeter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> RequestsCleanupPerimeter:
    """Limita il task ``automatic_cleanup`` alle righe e ai file creati dal test.

    Il test deve chiamare ``allow(...)`` con gli utenti e le richieste che ha
    creato; la ricerca dei file orfani vede solo ``download_root``, una cartella
    temporanea. Cosi il task non tocca dati reali di altri utenti.
    """
    return confine_requests_cleanup(monkeypatch, tmp_path / "downloads")