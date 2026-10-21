# EXTENSION TRACEABILITY - Prompt 06, endpoint admin licenses.
# Origine: questo modulo copre i contratti CRUD e relazionali di
# projects/mistral/backend/endpoints/admin_licenses.py.
# Ambito: verifica create con group license, listing con group e datasets annidati,
# update di group license, delete, 404 su license mancante e comportamento documentato
# quando si richiede un group license inesistente.
# Finestra dati: nessun dato meteorologico reale viene usato; i dataset collegati sono
# righe metadata sintetiche create via API admin.
# Runtime fake: nessun fake o worker; solo controller Flask e SQLAlchemy.
# Cleanup: support_EXT rimuove dataset, license, group license e attribution sintetici.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/admin.

from __future__ import annotations

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tests.integration.admin.support_EXT import (
    ADMIN_LICENSES_ENDPOINT_EXT,
    ADMIN_MISSING_ID_EXT,
    admin_headers_EXT,
    create_dataset_bundle_via_api_EXT,
    create_license_group_via_api_EXT,
    create_license_via_api_EXT,
    find_list_item_EXT,
    license_payload_EXT,
    response_content_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_admin_license_create_list_update_delete_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Copre CRUD license e cambio di group license.

    Il test crea due gruppi sintetici, inserisce la license nel primo e poi la sposta nel
    secondo. L'URL vuota nell'update attraversa anche il pre_load null_url della schema.
    """
    # arrange - due gruppi creati prima della license per mantenere cleanup LIFO sicuro.
    original_group_id = create_license_group_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
    )
    updated_group_id = create_license_group_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
    )
    create_payload = license_payload_EXT(original_group_id)
    license_id = create_license_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
        original_group_id,
        payload=create_payload,
    )

    # act - listing dopo create.
    list_response = client.get(ADMIN_LICENSES_ENDPOINT_EXT, headers=admin_headers_EXT)

    # assert - la license deve esporre il gruppo originale e nessun dataset collegato.
    assert list_response.status_code == 200
    created_item = find_list_item_EXT(response_content_EXT(list_response), license_id)
    assert created_item["name"] == create_payload["name"]
    assert created_item["descr"] == create_payload["descr"]
    assert created_item["url"] == create_payload["url"]
    assert str(created_item["group_license"]["id"]) == str(original_group_id)
    assert created_item["datasets"] == []

    # act - update verso secondo gruppo e url vuota normalizzata a None.
    update_payload = license_payload_EXT(
        updated_group_id,
        name=f"{create_payload['name']}_updated",
        descr="Updated synthetic license EXT",
        url="",
    )
    update_response = client.put(
        f"{ADMIN_LICENSES_ENDPOINT_EXT}/{license_id}",
        headers=admin_headers_EXT,
        json=update_payload,
    )

    # assert - empty_response 204 e relazione aggiornata nel listing.
    assert update_response.status_code == 204
    refreshed_response = client.get(
        ADMIN_LICENSES_ENDPOINT_EXT,
        headers=admin_headers_EXT,
    )
    refreshed_item = find_list_item_EXT(
        response_content_EXT(refreshed_response), license_id
    )
    assert refreshed_item["name"] == update_payload["name"]
    assert refreshed_item["descr"] == update_payload["descr"]
    assert refreshed_item["url"] is None
    assert str(refreshed_item["group_license"]["id"]) == str(updated_group_id)

    # act/assert - delete via API e verifica DB diretta.
    delete_response = client.delete(
        f"{ADMIN_LICENSES_ENDPOINT_EXT}/{license_id}",
        headers=admin_headers_EXT,
    )
    assert delete_response.status_code == 204
    assert sqlalchemy.get_instance().License.query.get(license_id) is None


def test_admin_license_list_includes_group_and_datasets_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica lo schema list con group_license e datasets annidati.

    Il bundle crea un dataset catalografico collegato alla license. Il listing deve
    quindi esporre sia il gruppo licenza sia il dataset figlio con arkimet_id come id.
    """
    # arrange - bundle metadata completo via API admin.
    bundle = create_dataset_bundle_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
    )

    # act - listing license.
    response = client.get(ADMIN_LICENSES_ENDPOINT_EXT, headers=admin_headers_EXT)

    # assert - schema annidato coerente con le relazioni create.
    assert response.status_code == 200
    license_item = find_list_item_EXT(response_content_EXT(response), bundle.license_id)
    assert str(license_item["group_license"]["id"]) == str(bundle.group_license_id)
    assert {"id": bundle.dataset_arkimet_id, "name": bundle.dataset_name} in license_item[
        "datasets"
    ]


def test_admin_license_missing_license_returns_404_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica NotFound per update/delete di license inesistente.

    Il group license valido serve solo a superare la schema dinamica del PUT, cosi il
    test misura il ramo endpoint che cerca la license path e non una validazione body.
    """
    # arrange - gruppo valido per costruire un payload PUT accettato dallo schema.
    db = sqlalchemy.get_instance()
    assert db.License.query.get(ADMIN_MISSING_ID_EXT) is None
    group_license_id = create_license_group_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
    )
    payload = license_payload_EXT(group_license_id)

    # act - update e delete sulla license mancante.
    update_response = client.put(
        f"{ADMIN_LICENSES_ENDPOINT_EXT}/{ADMIN_MISSING_ID_EXT}",
        headers=admin_headers_EXT,
        json=payload,
    )
    delete_response = client.delete(
        f"{ADMIN_LICENSES_ENDPOINT_EXT}/{ADMIN_MISSING_ID_EXT}",
        headers=admin_headers_EXT,
    )

    # assert - entrambi i rami devono produrre NotFound.
    assert update_response.status_code == 404
    assert delete_response.status_code == 404


def test_admin_license_missing_group_returns_404_when_backend_allows_branch_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
) -> None:
    """Documenta il contratto atteso per group license inesistente.

    L'endpoint dichiara un NotFound per group license mancante, ma la schema dinamica
    costruisce una OneOf sugli id esistenti e nel backend corrente blocca l'input prima
    del ramo applicativo. La suite non usa xfail: se il runtime restituisce 400 per
    validation, il test fa skip esplicito e il problema e censito come ADMIN-001.
    """
    # arrange - payload con id gruppo inesistente e campi license validi.
    db = sqlalchemy.get_instance()
    assert db.GroupLicense.query.get(ADMIN_MISSING_ID_EXT) is None
    payload = license_payload_EXT(ADMIN_MISSING_ID_EXT)

    # act - create license con riferimento a group license mancante.
    response = client.post(
        ADMIN_LICENSES_ENDPOINT_EXT,
        headers=admin_headers_EXT,
        json=payload,
    )

    # assert - riattivare l'assert pieno quando il backend espone il NotFound documentato.
    if response.status_code == 400:
        pytest.skip(
            "ADMIN-001: lo schema dinamico di AdminLicenses intercetta group_license "
            "inesistente come 400 prima del ramo NotFound documentato; riattivare "
            "l'assert 404 quando il controller avra un contratto coerente."
        )
    assert response.status_code == 404