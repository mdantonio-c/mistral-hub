# Test CRUD dell'endpoint admin /api/admin/licensegroups
# (projects/mistral/backend/endpoints/admin_license_groups.py).
# Ambito: verifica create/list/update/delete, preservazione di is_public e dballe_dsn,
# listing delle license annidate e 404 su update/delete di gruppo mancante.
# Finestra dati: nessun dataset meteorologico reale viene usato; le license sono record
# metadata sintetici creati via API admin.
# Runtime fake: nessun fake richiesto, solo Flask test client e database SQLAlchemy.
# Cleanup: support registra cleanup di license e gruppi con ordine relazionale LIFO.

from __future__ import annotations

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tests.integration.admin.support import (
    ADMIN_LICENSE_GROUPS_ENDPOINT,
    ADMIN_MISSING_ID,
    create_license_group_via_api,
    create_license_via_api,
    find_list_item,
    license_group_payload,
    response_content,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_admin_license_group_create_list_update_delete(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
) -> None:
    """Copre il CRUD principale dei gruppi licenza admin.

    Il payload dichiara esplicitamente is_public e dballe_dsn per proteggere campi che
    influenzano autorizzazioni e observed; il test aggiorna entrambi prima di cancellare
    il record via endpoint. Endpoint esercitati: GET/POST /api/admin/licensegroups e
    PUT/DELETE /api/admin/licensegroups/<id>.
    """
    # arrange - creazione attraverso helper API con cleanup registrato immediatamente.
    create_payload = license_group_payload(is_public=False, dballe_dsn="DBALLE_EXT")
    group_license_id = create_license_group_via_api(
        client,
        admin_headers,
        cleanup_registry,
        payload=create_payload,
    )

    # act - listing dopo la creazione.
    list_response = client.get(
        ADMIN_LICENSE_GROUPS_ENDPOINT,
        headers=admin_headers,
    )

    # assert - il gruppo creato deve preservare i campi di autorizzazione OBS.
    assert list_response.status_code == 200
    created_item = find_list_item(
        response_content(list_response), group_license_id
    )
    assert created_item["name"] == create_payload["name"]
    assert created_item["descr"] == create_payload["descr"]
    assert created_item["is_public"] is False
    assert created_item["dballe_dsn"] == "DBALLE_EXT"
    assert created_item["license"] == []

    # act - aggiorna nome, descrizione, visibilita e dsn.
    update_payload = license_group_payload(
        name=f"{create_payload['name']}_updated",
        descr="Updated synthetic license group EXT",
        is_public=True,
        dballe_dsn="DBALLE_EXT_UPDATED",
    )
    update_response = client.put(
        f"{ADMIN_LICENSE_GROUPS_ENDPOINT}/{group_license_id}",
        headers=admin_headers,
        json=update_payload,
    )

    # assert - empty_response 204 e listing aggiornato.
    assert update_response.status_code == 204
    refreshed_response = client.get(
        ADMIN_LICENSE_GROUPS_ENDPOINT,
        headers=admin_headers,
    )
    refreshed_item = find_list_item(
        response_content(refreshed_response), group_license_id
    )
    assert refreshed_item["name"] == update_payload["name"]
    assert refreshed_item["descr"] == update_payload["descr"]
    assert refreshed_item["is_public"] is True
    assert refreshed_item["dballe_dsn"] == "DBALLE_EXT_UPDATED"

    # act/assert - delete via API e verifica che il record non resti nel DB.
    delete_response = client.delete(
        f"{ADMIN_LICENSE_GROUPS_ENDPOINT}/{group_license_id}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 204
    assert sqlalchemy.get_instance().GroupLicense.query.get(group_license_id) is None


def test_admin_license_group_list_includes_nested_licenses(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica che il listing gruppi includa le license figlie.

    Il gruppo e la license sono creati via API admin. Questo copre il loop su gl.license
    senza dipendere da gruppi o licenze inizializzate dal progetto.
    Endpoint esercitato: GET /api/admin/licensegroups.
    """
    # arrange - gruppo e license sintetici con cleanup automatico.
    group_license_id = create_license_group_via_api(
        client,
        admin_headers,
        cleanup_registry,
    )
    license_id = create_license_via_api(
        client,
        admin_headers,
        cleanup_registry,
        group_license_id,
    )

    # act - listing gruppi.
    response = client.get(
        ADMIN_LICENSE_GROUPS_ENDPOINT,
        headers=admin_headers,
    )

    # assert - almeno una license annidata deve corrispondere all'id appena creato.
    assert response.status_code == 200
    group_item = find_list_item(response_content(response), group_license_id)
    nested_license_ids = {str(item["id"]) for item in group_item["license"]}
    assert str(license_id) in nested_license_ids


def test_admin_license_group_missing_update_delete_return_404(
    client: FlaskClient,
    admin_headers: dict[str, str],
) -> None:
    """Verifica i rami NotFound per gruppo licenza inesistente.

    La suite non testa un duplicate conflict per questo modello perche modello e
    migration dichiarano l'indice name non unique; non esiste quindi un oracolo 409
    stabile senza cambiare il backend applicativo.
    Endpoint esercitati: PUT e DELETE /api/admin/licensegroups/<id>.
    """
    # arrange - id mancante verificato sul DB e payload valido per il ramo PUT.
    db = sqlalchemy.get_instance()
    assert db.GroupLicense.query.get(ADMIN_MISSING_ID) is None
    payload = license_group_payload(is_public=True, dballe_dsn="DBALLE_MISSING_EXT")

    # act - update e delete sullo stesso id inesistente.
    update_response = client.put(
        f"{ADMIN_LICENSE_GROUPS_ENDPOINT}/{ADMIN_MISSING_ID}",
        headers=admin_headers,
        json=payload,
    )
    delete_response = client.delete(
        f"{ADMIN_LICENSE_GROUPS_ENDPOINT}/{ADMIN_MISSING_ID}",
        headers=admin_headers,
    )

    # assert - il controller deve restituire 404 per entrambi i metodi.
    assert update_response.status_code == 404
    assert delete_response.status_code == 404