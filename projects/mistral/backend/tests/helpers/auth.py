"""Helper per autenticazione e utenti temporanei condivisi dalla suite di test.

Molti scenari di integrazione hanno bisogno di un utente usa e getta con permessi
noti e degli header HTTP necessari per chiamare l'API come quell'utente. Questo
modulo centralizza quel setup, cosi i singoli test dichiarano solo l'intento senza
gestire a mano creazione dell'utente, login, directory di output e teardown.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mistral.endpoints import DOWNLOAD_DIR
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


@dataclass(frozen=True)
class AuthenticatedTestUser:
    """Record immutabile che descrive un utente di test temporaneo autenticato.

    Raggruppa i valori che servono di solito ai test dopo la creazione dell'utente:
    l'UUID usato nei percorsi su filesystem, l'id numerico nel database, gli header
    HTTP autenticati, la directory di output attesa su disco e, se nota, l'email di
    login usata negli scenari BasicAuth.
    """

    uuid: str
    user_id: int
    headers: Any
    output_dir: Path
    email: str | None = None


def create_authenticated_test_user(
    base: BaseTests,
    client: FlaskClient,
    permissions: dict[str, Any] | None = None,
) -> AuthenticatedTestUser:
    """Crea un utente API temporaneo, esegue il login e ne restituisce i metadati.

    Accetta un dizionario opzionale di permessi con lo stesso formato dell'endpoint
    admin di creazione utenti (via ``BaseTests.create_user`` di restapi). Poi esegue
    il login con le credenziali generate e raccoglie il risultato in
    ``AuthenticatedTestUser``, cosi il chiamante riusa lo stesso oggetto per setup,
    asserzioni e cleanup.
    """
    db = sqlalchemy.get_instance()
    uuid, data = base.create_user(client, permissions or {})
    headers, _ = base.do_login(client, data.get("email"), data.get("password"))

    user = db.User.query.filter_by(uuid=uuid).first()
    assert user is not None

    return AuthenticatedTestUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
        email=data.get("email"),
    )


def delete_test_user(base: BaseTests, client: FlaskClient, user_uuid: str) -> None:
    """Cancella un utente temporaneo via API admin, con il login admin di default.

    Chiama ``DELETE {API_URI}/admin/users/<uuid>`` e si aspetta 204. Ai test di
    solito non interessa il body di questa operazione di cleanup: serve solo un modo
    affidabile per rimuovere gli utenti usa e getta alla fine dello scenario.
    """
    admin_headers, _ = base.do_login(client, None, None)
    response = client.delete(f"{API_URI}/admin/users/{user_uuid}", headers=admin_headers)
    assert response.status_code == 204


def register_test_user_cleanup(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    *,
    user_uuid: str,
    root_path: Path,
) -> None:
    """Registra le azioni di teardown standard per un utente di test temporaneo.

    Aggiunge al registro sia la rimozione dal filesystem della directory di lavoro
    dell'utente sia la cancellazione del record utente via API admin, cosi i test
    possono fallire senza lasciare stato residuo.
    """
    cleanup_registry.add_path(root_path)
    cleanup_registry.add(lambda: delete_test_user(base, client, user_uuid))


def create_dataset_test_user(
    client: FlaskClient,
    cleanup_registry,
    dataset_ids: list[int] | None = None,
    *,
    allowed_obs_archive: bool = False,
    open_dataset: bool = True,
) -> AuthenticatedTestUser:
    """Crea un utente con grant espliciti sui dataset e ne registra il teardown.

    ``dataset_ids`` elenca gli unici dataset concessi esplicitamente all'utente: una
    lista vuota produce un utente senza grant, utile per raggiungere i rami 401 dei
    dataset privati. ``allowed_obs_archive`` controlla l'accesso ai dati osservati
    archiviati. I permessi passano dall'API admin di creazione utenti.
    """
    permissions: dict[str, Any] = {
        "open_dataset": open_dataset,
        "allowed_obs_archive": allowed_obs_archive,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids or []]),
    }
    base = BaseTests()
    user = create_authenticated_test_user(base, client, permissions)
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


def make_basic_auth(email: str, access_key: str) -> dict[str, str]:
    """Costruisce l'header HTTP Basic usato dai test di validazione dell'access key.

    L'endpoint ``GET /api/access-key/validate`` (endpoints/access_key.py) si aspetta
    email dell'utente e access key codificate in un unico token Basic-auth. Questo
    helper tiene il dettaglio della codifica fuori dal corpo dei test.
    """
    token = base64.b64encode(f"{email}:{access_key}".encode()).decode()
    return {"Authorization": f"Basic {token}"}