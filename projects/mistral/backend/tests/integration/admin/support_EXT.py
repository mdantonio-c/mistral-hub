# EXTENSION TRACEABILITY - Prompt 06, supporto locale per il dominio admin.
# Origine: questo modulo e stato aggiunto per evitare duplicazione fra i nuovi test
# *_EXT degli endpoint metadata admin. La baseline legacy non viene rinominata ne
# modificata: i test nuovi importano questo supporto in modo esplicito.
# Ambito: prepara payload HTTP per attributions, license groups, licenses e datasets,
# effettua login admin locale tramite BaseTests().do_login(client, None, None), e
# registra cleanup DB per ogni record sintetico creato dal singolo test.
# Finestra dati: nessun dataset meteorologico reale viene usato. I dataset creati qui
# sono righe sintetiche di catalogo, con nomi uuid e senza file Arkimet/DBALLE reali.
# Runtime fake: non servono worker, broker, filesystem meteo o monkeypatch; i test
# attraversano solo API Flask e database SQLAlchemy deterministici.
# Cleanup: i record vengono rimossi in ordine dataset -> license -> license group ->
# attribution, rimuovendo anche eventuali associazioni many-to-many user/dataset.
# Baseline non toccata: il modulo e un nuovo artefatto *_EXT.py confinato alla cartella
# integration/admin e non introduce fixture globali o conftest.py locali.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import pytest
from mistral.endpoints import DOWNLOAD_DIR
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


ADMIN_ATTRIBUTIONS_ENDPOINT_EXT = f"{API_URI}/admin/attributions"
ADMIN_LICENSE_GROUPS_ENDPOINT_EXT = f"{API_URI}/admin/licensegroups"
ADMIN_LICENSES_ENDPOINT_EXT = f"{API_URI}/admin/licenses"
ADMIN_DATASETS_ENDPOINT_EXT = f"{API_URI}/admin/datasets"

ADMIN_MISSING_ID_EXT = 987654321


@dataclass(frozen=True)
class AdminDatasetBundle_EXT:
    """Identificatori del bundle metadata sintetico creato via API admin.

    I test spesso devono creare attribution, group license, license e dataset insieme
    per verificare le serializzazioni annidate. Tenere gli id e i nomi in un record
    immutabile rende esplicito quale relazione verra poi controllata e quale cleanup e
    gia stato registrato dal helper.
    """

    attribution_id: int
    group_license_id: int
    license_id: int
    dataset_id: int
    dataset_arkimet_id: str
    dataset_name: str


@pytest.fixture
def admin_headers_EXT(client: FlaskClient) -> dict[str, str]:
    """Restituisce header admin usando il login standard richiesto dal prompt.

    La fixture resta locale al support importato dai file admin *_EXT: non viene messa
    in un conftest.py perche il riuso e limitato al dominio admin e non giustifica una
    nuova visibilita pytest di cartella.
    """
    # Prepariamo un login admin reale, usando esattamente il percorso BaseTests indicato
    # dal prompt per non introdurre account o ruoli alternativi nella suite.
    headers, _ = BaseTests().do_login(client, None, None)
    assert headers is not None
    return headers


def unique_admin_token_EXT(prefix: str) -> str:
    """Genera un token leggibile e unico per nomi metadata sintetici.

    Gli endpoint admin non devono dipendere dallo stato iniziale del catalogo runtime:
    usare uuid corti evita collisioni con dati preesistenti e rende il cleanup mirato.
    """
    # Manteniamo il prefisso nel valore per rendere chiara l'origine del record quando
    # un fallimento lascia tracce diagnostiche nel database di test.
    return f"{prefix}_{uuid4().hex[:12]}"


def attribution_payload_EXT(
    *,
    name: str | None = None,
    descr: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Costruisce il payload AttributionInput dell'endpoint admin attributions.

    Il payload usa campi minimi obbligatori e un URL valido opzionale. I test possono
    passare `url=""` per coprire il pre_load che normalizza la stringa vuota a None.
    """
    token = unique_admin_token_EXT("admin_attr_ext")
    return {
        "name": name or token,
        "descr": descr or f"Synthetic attribution for {token}",
        "url": url if url is not None else f"https://example.com/{token}",
    }


def license_group_payload_EXT(
    *,
    name: str | None = None,
    descr: str | None = None,
    is_public: bool = False,
    dballe_dsn: str | None = "DBALLE_EXT",
) -> dict[str, Any]:
    """Costruisce il payload LicGroupInput dell'endpoint admin licensegroups.

    Il gruppo licenza sintetico esplicita sempre is_public e dballe_dsn per proteggere
    il contratto di serializzazione dei campi usati poi da autorizzazioni e observed.
    """
    token = unique_admin_token_EXT("admin_lgroup_ext")
    return {
        "name": name or token,
        "descr": descr or f"Synthetic license group for {token}",
        "is_public": is_public,
        "dballe_dsn": dballe_dsn,
    }


def license_payload_EXT(
    group_license_id: int,
    *,
    name: str | None = None,
    descr: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Costruisce il payload dinamico dell'endpoint admin licenses.

    Il campo group_license e inviato come stringa per rispettare la OneOf costruita dal
    controller a partire dagli id presenti nel database.
    """
    token = unique_admin_token_EXT("admin_license_ext")
    return {
        "name": name or token,
        "descr": descr or f"Synthetic license for {token}",
        "url": url if url is not None else f"https://example.com/{token}",
        "group_license": str(group_license_id),
    }


def dataset_payload_EXT(
    license_id: int,
    attribution_id: int,
    *,
    arkimet_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    category: str = "FOR",
    source: str = "arkimet",
    fileformat: str = "grib",
    bounding: str = "POLYGON ((10 44, 11 44, 11 45, 10 45, 10 44))",
    sort_index: int | str | None = 10,
    supports_variable_browsing: bool = True,
) -> dict[str, Any]:
    """Costruisce il payload dinamico dell'endpoint admin datasets.

    Il dataset e solo catalografico: non punta a una finestra dati reale e serve a
    verificare CRUD, relazioni licenza/attribution e normalizzazione di sort_index.
    """
    token = unique_admin_token_EXT("admin_dataset_ext")
    dataset_name = name or token
    return {
        "arkimet_id": arkimet_id or dataset_name,
        "name": dataset_name,
        "description": description or f"Synthetic dataset for {dataset_name}",
        "category": category,
        "source": source,
        "fileformat": fileformat,
        "bounding": bounding,
        "sort_index": sort_index,
        "supports_variable_browsing": supports_variable_browsing,
        "license": str(license_id),
        "attribution": str(attribution_id),
    }


def response_content_EXT(response) -> Any:
    """Decodifica il body usando lo stesso helper BaseTests della suite.

    Centralizzare la decodifica evita differenze fra response.json e wrapper restapi
    quando un endpoint restituisce un valore scalare come id numerico.
    """
    # BaseTests.get_content e il parser gia usato dalla suite per scalari, liste e dict.
    return BaseTests().get_content(response)


def created_id_from_response_EXT(response) -> int:
    """Estrae l'id scalare restituito dagli endpoint admin POST.

    Gli endpoint Prompt 06 ritornano direttamente l'id creato con status 200, non un
    documento JSON annidato. Questo helper rende quell'assunzione visibile nei test.
    """
    content = response_content_EXT(response)
    assert isinstance(content, (int, str))
    return int(content)


def find_list_item_EXT(items: Iterable[dict[str, Any]], item_id: int) -> dict[str, Any]:
    """Trova un record serializzato confrontando id numerici e stringa.

    Gli schema admin dichiarano spesso id come Str anche quando il modello SQLAlchemy e
    Integer; il confronto normalizzato impedisce assert fragili sulla sola conversione.
    """
    for item in items:
        if str(item.get("id")) == str(item_id):
            return item
    raise AssertionError(f"Admin item {item_id} not found in response {items!r}")


def create_regular_user_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo senza ruolo admin per controlli di autorizzazione.

    Il test admin-required deve distinguere fra anonimo e utente autenticato ma non
    autorizzato. L'utente viene cancellato via admin API e la sua directory /data viene
    registrata subito nel cleanup_registry.
    """
    base = BaseTests()
    user = create_authenticated_test_user(base, client, {"open_dataset": True})
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=Path(DOWNLOAD_DIR, user.uuid),
    )
    return user


def create_attribution_via_api_EXT(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
    *,
    payload: dict[str, Any] | None = None,
) -> int:
    """Crea una attribution via endpoint admin e registra cleanup DB idempotente.

    Il helper attraversa il vero controller per preparare dipendenze di altri test, ma
    lascia al test chiamante il controllo esplicito degli assert quando lo scenario e il
    CRUD della attribution stessa.
    """
    request_payload = payload or attribution_payload_EXT()
    response = client.post(
        ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
        headers=admin_headers,
        json=request_payload,
    )
    assert response.status_code == 200
    attribution_id = created_id_from_response_EXT(response)
    db = sqlalchemy.get_instance()
    cleanup_registry.add(
        lambda attribution_id=attribution_id: delete_admin_records_EXT(
            db, attribution_ids=[attribution_id]
        )
    )
    return attribution_id


def create_license_group_via_api_EXT(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
    *,
    payload: dict[str, Any] | None = None,
) -> int:
    """Crea un group license via endpoint admin e registra cleanup DB.

    Il cleanup diretto evita che un fallimento successivo lasci gruppi sintetici che
    altererebbero le scelte dinamiche degli schema admin licenses/datasets.
    """
    request_payload = payload or license_group_payload_EXT()
    response = client.post(
        ADMIN_LICENSE_GROUPS_ENDPOINT_EXT,
        headers=admin_headers,
        json=request_payload,
    )
    assert response.status_code == 200
    group_license_id = created_id_from_response_EXT(response)
    db = sqlalchemy.get_instance()
    cleanup_registry.add(
        lambda group_license_id=group_license_id: delete_admin_records_EXT(
            db, group_license_ids=[group_license_id]
        )
    )
    return group_license_id


def create_license_via_api_EXT(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
    group_license_id: int,
    *,
    payload: dict[str, Any] | None = None,
) -> int:
    """Crea una license via endpoint admin e registra cleanup DB.

    La licenza e sempre collegata a un gruppo gia creato dal test, cosi i rami happy
    path non dipendono dal catalogo runtime iniziale.
    """
    request_payload = payload or license_payload_EXT(group_license_id)
    response = client.post(
        ADMIN_LICENSES_ENDPOINT_EXT,
        headers=admin_headers,
        json=request_payload,
    )
    assert response.status_code == 200
    license_id = created_id_from_response_EXT(response)
    db = sqlalchemy.get_instance()
    cleanup_registry.add(
        lambda license_id=license_id: delete_admin_records_EXT(
            db, license_ids=[license_id]
        )
    )
    return license_id


def create_dataset_via_api_EXT(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
    license_id: int,
    attribution_id: int,
    *,
    payload: dict[str, Any] | None = None,
) -> int:
    """Crea un dataset catalografico via endpoint admin e registra cleanup DB.

    Il record e sintetico e non punta a file reali: il suo unico scopo e verificare il
    contratto API/DB deterministico del catalogo admin.
    """
    request_payload = payload or dataset_payload_EXT(license_id, attribution_id)
    response = client.post(
        ADMIN_DATASETS_ENDPOINT_EXT,
        headers=admin_headers,
        json=request_payload,
    )
    assert response.status_code == 200
    dataset_id = created_id_from_response_EXT(response)
    db = sqlalchemy.get_instance()
    cleanup_registry.add(
        lambda dataset_id=dataset_id: delete_admin_records_EXT(
            db, dataset_ids=[dataset_id]
        )
    )
    return dataset_id


def create_dataset_bundle_via_api_EXT(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
) -> AdminDatasetBundle_EXT:
    """Crea attribution, group license, license e dataset via API admin.

    Il bundle e usato dai test di listing annidato. Ogni singolo record registra il suo
    cleanup appena creato; poiche il dataset viene creato per ultimo, il teardown LIFO
    elimina prima il dataset e poi le dipendenze relazionali.
    """
    attribution_id = create_attribution_via_api_EXT(
        client, admin_headers, cleanup_registry
    )
    group_license_id = create_license_group_via_api_EXT(
        client, admin_headers, cleanup_registry
    )
    license_id = create_license_via_api_EXT(
        client, admin_headers, cleanup_registry, group_license_id
    )
    dataset_payload = dataset_payload_EXT(license_id, attribution_id)
    dataset_id = create_dataset_via_api_EXT(
        client,
        admin_headers,
        cleanup_registry,
        license_id,
        attribution_id,
        payload=dataset_payload,
    )
    return AdminDatasetBundle_EXT(
        attribution_id=attribution_id,
        group_license_id=group_license_id,
        license_id=license_id,
        dataset_id=dataset_id,
        dataset_arkimet_id=str(dataset_payload["arkimet_id"]),
        dataset_name=str(dataset_payload["name"]),
    )


def delete_admin_records_EXT(
    db,
    *,
    dataset_ids: Iterable[int] = (),
    license_ids: Iterable[int] = (),
    group_license_ids: Iterable[int] = (),
    attribution_ids: Iterable[int] = (),
) -> None:
    """Rimuove record admin sintetici nell'ordine relazionale corretto.

    Il cleanup e difensivo e idempotente: se il test ha gia cancellato il record via API
    o se una creazione e fallita a meta, vengono rimossi solo gli oggetti ancora presenti.
    """
    # Ripuliamo prima i dataset per liberare FK verso license e attribution e per
    # svuotare eventuali associazioni many-to-many con utenti temporanei.
    for dataset_id in dataset_ids:
        dataset = db.Datasets.query.get(dataset_id)
        if dataset is not None:
            for user in dataset.users.all():
                dataset.users.remove(user)
            db.session.delete(dataset)
            db.session.flush()

    # Le license dipendono dal group license; vanno quindi rimosse prima del gruppo.
    for license_id in license_ids:
        license_entry = db.License.query.get(license_id)
        if license_entry is not None:
            db.session.delete(license_entry)
            db.session.flush()

    # I gruppi e le attribution non hanno piu dipendenze se il chiamante ha passato gli
    # id corretti; in caso contrario il flush evidenziera una relazione non ripulita.
    for group_license_id in group_license_ids:
        group_license = db.GroupLicense.query.get(group_license_id)
        if group_license is not None:
            db.session.delete(group_license)
            db.session.flush()

    for attribution_id in attribution_ids:
        attribution = db.Attribution.query.get(attribution_id)
        if attribution is not None:
            db.session.delete(attribution)
            db.session.flush()

    db.session.commit()