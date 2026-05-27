"""Authentication and temporary-user helpers shared across the test suite.

Many integration scenarios need a throwaway user with known permissions, plus
the HTTP headers required to call the API as that user. This module centralizes
that setup so the individual tests can declare intent without manually dealing
with user creation, login, output directories, or teardown wiring.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mistral.endpoints import DOWNLOAD_DIR
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


@dataclass(frozen=True)
class AuthenticatedTestUser:
    """Small immutable record describing one temporary authenticated test user.

    The object groups together the values that tests commonly need after user
    creation: the UUID used by filesystem paths, the numeric database id, the
    authenticated HTTP headers, and the expected output directory on disk.
    """

    uuid: str
    user_id: int
    headers: Any
    output_dir: Path


def create_authenticated_test_user(
    base: BaseTests,
    client: FlaskClient,
    permissions: dict[str, Any] | None = None,
) -> AuthenticatedTestUser:
    """Create a temporary API user, log it in, and return the reusable metadata.

    The helper accepts an optional permissions dictionary exactly like the admin
    user-creation endpoint. It then logs in with the generated credentials and
    packages the result into ``AuthenticatedTestUser`` so callers can reuse the
    same object across setup, assertions, and cleanup.
    """
    # Costruiamo lo stato controllato richiesto dal test, usando gli stessi canali che
    # il backend espone in produzione quando possibile.
    db = sqlalchemy.get_instance()
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
    uuid, data = base.create_user(client, permissions or {})
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    headers, _ = base.do_login(client, data.get("email"), data.get("password"))

    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    user = db.User.query.filter_by(uuid=uuid).first()
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert user is not None

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return AuthenticatedTestUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
    )


def delete_test_user(base: BaseTests, client: FlaskClient, user_uuid: str) -> None:
    """Delete one temporary user through the admin API with default admin login.

    Tests rarely care about the response body of this cleanup operation; they
    only need a reliable way to remove throwaway users after the scenario.
    """
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    admin_headers, _ = base.do_login(client, None, None)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    response = client.delete(f"{API_URI}/admin/users/{user_uuid}", headers=admin_headers)
    # Verifichiamo che la risposta confermi la cancellazione senza body di risposta
    # prima di usare il payload.
    assert response.status_code == 204


def register_test_user_cleanup(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    *,
    user_uuid: str,
    root_path: Path,
) -> None:
    """Register the standard teardown actions for a temporary test user.

    This helper adds both filesystem cleanup for the user's working directory and
    admin-side deletion of the user record itself, so tests can fail safely
    without leaving residual state behind.
    """
    # Registriamo subito il cleanup: anche se il test fallisce a meta, le risorse
    # temporanee verranno rimosse.
    cleanup_registry.add_path(root_path)
    # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta affidabile
    # anche in caso di fallimento.
    cleanup_registry.add(lambda: delete_test_user(base, client, user_uuid))


def make_basic_auth(email: str, access_key: str) -> dict[str, str]:
    """Build the exact HTTP Basic header used by access-key validation tests.

    The validation endpoint expects the user email and access key encoded as a
    single Basic-auth token. This helper keeps that encoding detail out of the
    test bodies.
    """
    # Entriamo nel blocco operativo dell'helper condiviso, mantenendo esplicito
    # quale stato viene letto o prodotto.
    token = base64.b64encode(f"{email}:{access_key}".encode()).decode()
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return {"Authorization": f"Basic {token}"}