# Test CRUD dell'endpoint admin /api/admin/datasets
# (projects/mistral/backend/endpoints/admin_datasets.py).
# Ambito: verifica create/list/update/delete, relazioni license/attribution, sort_index
# vuoto normalizzato a None, 404 su dataset mancante e conflict su vincoli unique,
# NotFound del controller per license/attribution inesistenti e status 204 di PUT/DELETE
# dichiarati nella specifica OpenAPI.
# Finestra dati: nessun dato meteorologico reale viene usato; il dataset e un record di
# catalogo sintetico con arkimet_id uuid e senza file di runtime.
# Runtime fake: nessun fake; il test attraversa Flask, schema dinamiche e SQLAlchemy.
# Cleanup: dataset sintetici rimossi prima delle relative license/group/attribution.

from __future__ import annotations

import inspect

import pytest
from mistral.endpoints.admin_datasets import AdminDatasets
from restapi.connectors import sqlalchemy
from restapi.exceptions import NotFound
from restapi.tests import API_URI, FlaskClient

from mistral.tests.integration.admin.support import (
    ADMIN_DATASETS_ENDPOINT,
    ADMIN_MISSING_ID,
    create_attribution_via_api,
    create_license_group_via_api,
    create_license_via_api,
    create_dataset_via_api,
    dataset_payload,
    delete_admin_records,
    find_list_item,
    response_content,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_admin_dataset_create_list_update_delete(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
) -> None:
    """Copre CRUD dataset, relazioni e sort_index vuoto -> None.

    Il test crea due coppie license/attribution per verificare sia la creazione sia il
    cambio relazione in PUT. Il payload di update invia `sort_index=""`, coprendo il
    pre_load DatasetInput.null_sort_index senza dipendere da dati reali.
    Endpoint esercitati: GET/POST /api/admin/datasets e PUT/DELETE
    /api/admin/datasets/<id>.
    """
    # arrange - dipendenze relazionali valide, tutte sintetiche e con cleanup registrato.
    first_attribution_id = create_attribution_via_api(
        client, admin_headers, cleanup_registry
    )
    first_group_id = create_license_group_via_api(
        client, admin_headers, cleanup_registry
    )
    first_license_id = create_license_via_api(
        client, admin_headers, cleanup_registry, first_group_id
    )
    second_attribution_id = create_attribution_via_api(
        client, admin_headers, cleanup_registry
    )
    second_group_id = create_license_group_via_api(
        client, admin_headers, cleanup_registry
    )
    second_license_id = create_license_via_api(
        client, admin_headers, cleanup_registry, second_group_id
    )
    create_payload = dataset_payload(first_license_id, first_attribution_id)

    # act - creazione dataset via controller admin.
    dataset_id = create_dataset_via_api(
        client,
        admin_headers,
        cleanup_registry,
        first_license_id,
        first_attribution_id,
        payload=create_payload,
    )

    # assert - il listing espone schema dataset e relazioni iniziali.
    list_response = client.get(ADMIN_DATASETS_ENDPOINT, headers=admin_headers)
    assert list_response.status_code == 200
    created_item = find_list_item(response_content(list_response), dataset_id)
    assert created_item["arkimet_id"] == create_payload["arkimet_id"]
    assert created_item["name"] == create_payload["name"]
    assert created_item["category"] == create_payload["category"]
    assert created_item["source"] == create_payload["source"]
    assert created_item["sort_index"] == create_payload["sort_index"]
    assert created_item["supports_variable_browsing"] is True
    assert str(created_item["license"]["id"]) == str(first_license_id)
    assert str(created_item["attribution"]["id"]) == str(first_attribution_id)

    # act - update campi descrittivi e relazioni, con sort_index volutamente vuoto.
    update_payload = dataset_payload(
        second_license_id,
        second_attribution_id,
        arkimet_id=create_payload["arkimet_id"],
        name=f"{create_payload['name']}_updated",
        description="Updated synthetic dataset EXT",
        sort_index="",
        supports_variable_browsing=False,
    )
    update_response = client.put(
        f"{ADMIN_DATASETS_ENDPOINT}/{dataset_id}",
        headers=admin_headers,
        json=update_payload,
    )

    # assert - update 204 e normalizzazione persistita nello schema list.
    assert update_response.status_code == 204
    refreshed_response = client.get(
        ADMIN_DATASETS_ENDPOINT,
        headers=admin_headers,
    )
    refreshed_item = find_list_item(
        response_content(refreshed_response), dataset_id
    )
    assert refreshed_item["name"] == update_payload["name"]
    assert refreshed_item["description"] == update_payload["description"]
    assert refreshed_item["sort_index"] is None
    assert refreshed_item["supports_variable_browsing"] is False
    assert str(refreshed_item["license"]["id"]) == str(second_license_id)
    assert str(refreshed_item["attribution"]["id"]) == str(second_attribution_id)

    # act/assert - delete via API e verifica DB diretta.
    delete_response = client.delete(
        f"{ADMIN_DATASETS_ENDPOINT}/{dataset_id}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 204
    assert sqlalchemy.get_instance().Datasets.query.get(dataset_id) is None


def test_admin_dataset_duplicate_unique_fields_return_conflict(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica 409 su duplicato dataset dove esistono vincoli unique reali.

    A differenza di license group e license, i dataset hanno arkimet_id e name unici da
    migration. Il test crea un record e reinvia lo stesso payload, aspettandosi Conflict.
    Endpoint esercitato: POST /api/admin/datasets.
    """
    # arrange - dipendenze valide e primo dataset creato via API.
    attribution_id = create_attribution_via_api(
        client, admin_headers, cleanup_registry
    )
    group_license_id = create_license_group_via_api(
        client, admin_headers, cleanup_registry
    )
    license_id = create_license_via_api(
        client, admin_headers, cleanup_registry, group_license_id
    )
    payload = dataset_payload(license_id, attribution_id)
    first_dataset_id = create_dataset_via_api(
        client,
        admin_headers,
        cleanup_registry,
        license_id,
        attribution_id,
        payload=payload,
    )

    # act - seconda create con gli stessi arkimet_id/name unici.
    duplicate_response = client.post(
        ADMIN_DATASETS_ENDPOINT,
        headers=admin_headers,
        json=payload,
    )

    # assert - il record originale resta il solo persistito e il controller espone 409.
    assert duplicate_response.status_code == 409
    db = sqlalchemy.get_instance()
    assert db.Datasets.query.get(first_dataset_id) is not None
    assert db.Datasets.query.filter_by(arkimet_id=payload["arkimet_id"]).count() == 1


def test_admin_dataset_missing_update_delete_return_404(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica NotFound per update/delete di dataset inesistente.

    License e attribution valide servono solo a superare la schema dinamica del PUT;
    l'id path resta mancante e deve attivare il controllo NotFound del controller.
    Endpoint esercitati: PUT e DELETE /api/admin/datasets/<id>.
    """
    # arrange - dipendenze valide e id dataset assente.
    db = sqlalchemy.get_instance()
    assert db.Datasets.query.get(ADMIN_MISSING_ID) is None
    attribution_id = create_attribution_via_api(
        client, admin_headers, cleanup_registry
    )
    group_license_id = create_license_group_via_api(
        client, admin_headers, cleanup_registry
    )
    license_id = create_license_via_api(
        client, admin_headers, cleanup_registry, group_license_id
    )
    payload = dataset_payload(license_id, attribution_id)

    # act - update e delete sul dataset mancante.
    update_response = client.put(
        f"{ADMIN_DATASETS_ENDPOINT}/{ADMIN_MISSING_ID}",
        headers=admin_headers,
        json=payload,
    )
    delete_response = client.delete(
        f"{ADMIN_DATASETS_ENDPOINT}/{ADMIN_MISSING_ID}",
        headers=admin_headers,
    )

    # assert - entrambi i rami devono restituire 404.
    assert update_response.status_code == 404
    assert delete_response.status_code == 404


def _delete_datasets_by_arkimet_id(db, arkimet_id: str) -> None:
    """Rimuove i dataset sintetici con l'arkimet_id indicato (cleanup idempotente)."""
    db.session.rollback()
    for dataset in db.Datasets.query.filter_by(arkimet_id=arkimet_id).all():
        db.session.delete(dataset)
    db.session.commit()


@pytest.mark.parametrize("missing", ["license", "attribution"])
def test_admin_dataset_controller_missing_reference_returns_not_found(
    client: FlaskClient,
    admin_headers: dict[str, str],
    cleanup_registry,
    missing: str,
) -> None:
    """Verifica il ramo NotFound del controller per license o attribution inesistenti.

    Via HTTP la OneOf rifiuta prima gli id inesistenti: il controller viene quindi
    chiamato direttamente, senza decoratori. Il dataset appena creato deve essere
    rimosso, senza lasciare righe parziali.
    Metodo esercitato: AdminDatasets.post.
    """
    # arrange
    attribution_id = create_attribution_via_api(
        client, admin_headers, cleanup_registry
    )
    group_license_id = create_license_group_via_api(
        client, admin_headers, cleanup_registry
    )
    license_id = create_license_via_api(
        client, admin_headers, cleanup_registry, group_license_id
    )
    if missing == "license":
        payload = dataset_payload(ADMIN_MISSING_ID, attribution_id)
    else:
        payload = dataset_payload(license_id, ADMIN_MISSING_ID)
    db = sqlalchemy.get_instance()
    cleanup_registry.add(
        lambda: _delete_datasets_by_arkimet_id(db, payload["arkimet_id"])
    )
    post = inspect.unwrap(AdminDatasets.post)

    # act / assert
    with pytest.raises(NotFound):
        post(AdminDatasets(), None, **payload)
    assert db.Datasets.query.filter_by(arkimet_id=payload["arkimet_id"]).count() == 0


def test_admin_dataset_openapi_declares_204_for_update_and_delete(
    client: FlaskClient,
    admin_headers: dict[str, str],
) -> None:
    """Verifica che la specifica OpenAPI dichiari 204, lo status reale di PUT/DELETE."""
    # act
    response = client.get(f"{API_URI}/specs", headers=admin_headers)

    # assert
    assert response.status_code == 200
    path = response_content(response)["paths"]["/api/admin/datasets/{dataset_id}"]
    for method in ("put", "delete"):
        assert "204" in path[method]["responses"]
        assert "200" not in path[method]["responses"]
