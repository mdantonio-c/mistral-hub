# EXTENSION TRACEABILITY - Prompt 06, endpoint admin datasets.
# Origine: questo modulo aggiunge copertura per
# projects/mistral/backend/endpoints/admin_datasets.py senza toccare test dataset legacy.
# Ambito: verifica create/list/update/delete, relazioni license/attribution, sort_index
# vuoto normalizzato a None, 404 su dataset mancante e conflict su vincoli unique.
# Finestra dati: nessun dato meteorologico reale viene usato; il dataset e un record di
# catalogo sintetico con arkimet_id uuid e senza file di runtime.
# Runtime fake: nessun fake; il test attraversa Flask, schema dinamiche e SQLAlchemy.
# Cleanup: dataset sintetici rimossi prima delle relative license/group/attribution.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/admin.

from __future__ import annotations

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tests.integration.admin.support_EXT import (
    ADMIN_DATASETS_ENDPOINT_EXT,
    ADMIN_MISSING_ID_EXT,
    admin_headers_EXT,
    create_attribution_via_api_EXT,
    create_license_group_via_api_EXT,
    create_license_via_api_EXT,
    create_dataset_via_api_EXT,
    dataset_payload_EXT,
    delete_admin_records_EXT,
    find_list_item_EXT,
    response_content_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_admin_dataset_create_list_update_delete_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Copre CRUD dataset, relazioni e sort_index vuoto -> None.

    Il test crea due coppie license/attribution per verificare sia la creazione sia il
    cambio relazione in PUT. Il payload di update invia `sort_index=""`, coprendo il
    pre_load DatasetInput.null_sort_index senza dipendere da dati reali.
    """
    # arrange - dipendenze relazionali valide, tutte sintetiche e con cleanup registrato.
    first_attribution_id = create_attribution_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    first_group_id = create_license_group_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    first_license_id = create_license_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry, first_group_id
    )
    second_attribution_id = create_attribution_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    second_group_id = create_license_group_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    second_license_id = create_license_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry, second_group_id
    )
    create_payload = dataset_payload_EXT(first_license_id, first_attribution_id)

    # act - creazione dataset via controller admin.
    dataset_id = create_dataset_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
        first_license_id,
        first_attribution_id,
        payload=create_payload,
    )

    # assert - il listing espone schema dataset e relazioni iniziali.
    list_response = client.get(ADMIN_DATASETS_ENDPOINT_EXT, headers=admin_headers_EXT)
    assert list_response.status_code == 200
    created_item = find_list_item_EXT(response_content_EXT(list_response), dataset_id)
    assert created_item["arkimet_id"] == create_payload["arkimet_id"]
    assert created_item["name"] == create_payload["name"]
    assert created_item["category"] == create_payload["category"]
    assert created_item["source"] == create_payload["source"]
    assert created_item["sort_index"] == create_payload["sort_index"]
    assert created_item["supports_variable_browsing"] is True
    assert str(created_item["license"]["id"]) == str(first_license_id)
    assert str(created_item["attribution"]["id"]) == str(first_attribution_id)

    # act - update campi descrittivi e relazioni, con sort_index volutamente vuoto.
    update_payload = dataset_payload_EXT(
        second_license_id,
        second_attribution_id,
        arkimet_id=create_payload["arkimet_id"],
        name=f"{create_payload['name']}_updated",
        description="Updated synthetic dataset EXT",
        sort_index="",
        supports_variable_browsing=False,
    )
    update_response = client.put(
        f"{ADMIN_DATASETS_ENDPOINT_EXT}/{dataset_id}",
        headers=admin_headers_EXT,
        json=update_payload,
    )

    # assert - update 204 e normalizzazione persistita nello schema list.
    assert update_response.status_code == 204
    refreshed_response = client.get(
        ADMIN_DATASETS_ENDPOINT_EXT,
        headers=admin_headers_EXT,
    )
    refreshed_item = find_list_item_EXT(
        response_content_EXT(refreshed_response), dataset_id
    )
    assert refreshed_item["name"] == update_payload["name"]
    assert refreshed_item["description"] == update_payload["description"]
    assert refreshed_item["sort_index"] is None
    assert refreshed_item["supports_variable_browsing"] is False
    assert str(refreshed_item["license"]["id"]) == str(second_license_id)
    assert str(refreshed_item["attribution"]["id"]) == str(second_attribution_id)

    # act/assert - delete via API e verifica DB diretta.
    delete_response = client.delete(
        f"{ADMIN_DATASETS_ENDPOINT_EXT}/{dataset_id}",
        headers=admin_headers_EXT,
    )
    assert delete_response.status_code == 204
    assert sqlalchemy.get_instance().Datasets.query.get(dataset_id) is None


def test_admin_dataset_duplicate_unique_fields_return_conflict_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica 409 su duplicato dataset dove esistono vincoli unique reali.

    A differenza di license group e license, i dataset hanno arkimet_id e name unici da
    migration. Il test crea un record e reinvia lo stesso payload, aspettandosi Conflict.
    """
    # arrange - dipendenze valide e primo dataset creato via API.
    attribution_id = create_attribution_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    group_license_id = create_license_group_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    license_id = create_license_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry, group_license_id
    )
    payload = dataset_payload_EXT(license_id, attribution_id)
    first_dataset_id = create_dataset_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
        license_id,
        attribution_id,
        payload=payload,
    )

    # act - seconda create con gli stessi arkimet_id/name unici.
    duplicate_response = client.post(
        ADMIN_DATASETS_ENDPOINT_EXT,
        headers=admin_headers_EXT,
        json=payload,
    )

    # assert - il record originale resta il solo persistito e il controller espone 409.
    assert duplicate_response.status_code == 409
    db = sqlalchemy.get_instance()
    assert db.Datasets.query.get(first_dataset_id) is not None
    assert db.Datasets.query.filter_by(arkimet_id=payload["arkimet_id"]).count() == 1


def test_admin_dataset_missing_update_delete_return_404_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica NotFound per update/delete di dataset inesistente.

    License e attribution valide servono solo a superare la schema dinamica del PUT;
    l'id path resta mancante e deve attivare il controllo NotFound del controller.
    """
    # arrange - dipendenze valide e id dataset assente.
    db = sqlalchemy.get_instance()
    assert db.Datasets.query.get(ADMIN_MISSING_ID_EXT) is None
    attribution_id = create_attribution_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    group_license_id = create_license_group_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry
    )
    license_id = create_license_via_api_EXT(
        client, admin_headers_EXT, cleanup_registry, group_license_id
    )
    payload = dataset_payload_EXT(license_id, attribution_id)

    # act - update e delete sul dataset mancante.
    update_response = client.put(
        f"{ADMIN_DATASETS_ENDPOINT_EXT}/{ADMIN_MISSING_ID_EXT}",
        headers=admin_headers_EXT,
        json=payload,
    )
    delete_response = client.delete(
        f"{ADMIN_DATASETS_ENDPOINT_EXT}/{ADMIN_MISSING_ID_EXT}",
        headers=admin_headers_EXT,
    )

    # assert - entrambi i rami devono restituire 404.
    assert update_response.status_code == 404
    assert delete_response.status_code == 404