"""Test di integrazione sulle regole di autorizzazione e visibilita dei dataset.

Esercitano GET /api/datasets e GET /api/datasets/<dataset_name>
(endpoints/datasets.py) con utenti che hanno permessi diversi su dataset pubblici
e privati.
"""

import json
from typing import Any

import pytest
from faker import Faker
from mistral.tests.helpers.datasets import create_test_dataset
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
]


def _delete_user(client: FlaskClient, admin_headers: Any, user_uuid: Any) -> None:
    """Elimina un utente temporaneo durante il teardown (DELETE /api/admin/users).

    Si aspetta la risposta 204 dall'endpoint di amministrazione utenti di restapi.
    """
    response = client.delete(
        f"{API_URI}/admin/users/{user_uuid}",
        headers=admin_headers,
    )
    assert response.status_code == 204


def _create_test_user(
    client: FlaskClient,
    cleanup_registry,
    *,
    dataset_ids: tuple[int, ...] = (),
    open_dataset: bool,
) -> tuple[BaseTests, Any, Any, Any, dict[str, Any]]:
    """Crea un utente con permessi sui dataset e ne registra subito il cleanup.

    Usa l'API di amministrazione utenti di restapi per assegnare i permessi
    ``datasets`` (dataset privati concessi) e ``open_dataset`` (accesso ai dataset
    pubblici). Restituisce l'helper ``BaseTests``, l'uuid e gli header dell'utente,
    gli header admin e i permessi usati.
    """
    base = BaseTests()
    admin_headers, _ = base.do_login(client, None, None)
    permissions: dict[str, Any] = {
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids]),
        "open_dataset": open_dataset,
    }
    user_uuid, user_data = base.create_user(client, permissions)
    cleanup_registry.add(lambda: _delete_user(client, admin_headers, user_uuid))
    user_headers, _ = base.do_login(
        client,
        user_data.get("email"),
        user_data.get("password"),
    )
    return base, user_uuid, user_headers, admin_headers, permissions


def test_user_with_open_dataset_can_access_public_catalog(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un utente con ``open_dataset`` veda un dataset pubblico.

    Il dataset pubblico creato dal test compare in GET /api/datasets ed e
    leggibile con GET /api/datasets/<dataset_name>.
    """
    db = sqlalchemy.get_instance()
    public_dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=True,
        prefix="authorized_public_dataset",
    )
    base, _, user_headers, _, _ = _create_test_user(
        client,
        cleanup_registry,
        open_dataset=True,
    )

    list_response = client.get(f"{API_URI}/datasets", headers=user_headers)
    assert list_response.status_code == 200
    list_content = base.get_content(list_response)
    assert isinstance(list_content, list)
    assert any(
        dataset["id"] == public_dataset.arkimet_id
        and dataset["is_public"] is True
        for dataset in list_content
    )

    dataset_response = client.get(
        f"{API_URI}/datasets/{public_dataset.arkimet_id}",
        headers=user_headers,
    )

    assert dataset_response.status_code == 200
    assert isinstance(base.get_content(dataset_response), dict)


def test_private_dataset_visibility_requires_explicit_grant(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che sia visibile solo il dataset privato assegnato all'utente.

    GET /api/datasets/<dataset_name> risponde 200 per il dataset concesso e 404
    per un altro dataset privato non concesso.
    """
    db = sqlalchemy.get_instance()
    authorized_dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=False,
        prefix="authorized_private_dataset",
    )
    unauthorized_dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=False,
        prefix="unauthorized_private_dataset",
    )
    base, _, user_headers, _, _ = _create_test_user(
        client,
        cleanup_registry,
        dataset_ids=(authorized_dataset.id,),
        open_dataset=True,
    )

    unauthorized_response = client.get(
        f"{API_URI}/datasets/{unauthorized_dataset.arkimet_id}",
        headers=user_headers,
    )
    authorized_response = client.get(
        f"{API_URI}/datasets/{authorized_dataset.arkimet_id}",
        headers=user_headers,
    )

    assert unauthorized_response.status_code == 404
    assert authorized_response.status_code == 200
    authorized_content = base.get_content(authorized_response)
    assert isinstance(authorized_content, dict)
    assert authorized_content["is_public"] is False


def test_private_grant_survives_disabling_open_dataset(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che togliere ``open_dataset`` nasconda i pubblici ma non i privati.

    Dopo l'aggiornamento dell'utente con PUT /api/admin/users/<uuid>, il dataset
    pubblico risponde 404 mentre il dataset privato concesso resta leggibile.
    """
    db = sqlalchemy.get_instance()
    private_dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=False,
        prefix="persistent_private_dataset",
    )
    public_dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=True,
        prefix="toggle_public_dataset",
    )
    base, user_uuid, user_headers, admin_headers, permissions = _create_test_user(
        client,
        cleanup_registry,
        dataset_ids=(private_dataset.id,),
        open_dataset=True,
    )

    visible_public_response = client.get(
        f"{API_URI}/datasets/{public_dataset.arkimet_id}",
        headers=user_headers,
    )
    update_response = client.put(
        f"{API_URI}/admin/users/{user_uuid}",
        headers=admin_headers,
        json={
            "open_dataset": False,
            "datasets": permissions["datasets"],
        },
    )
    hidden_public_response = client.get(
        f"{API_URI}/datasets/{public_dataset.arkimet_id}",
        headers=user_headers,
    )
    still_authorized_response = client.get(
        f"{API_URI}/datasets/{private_dataset.arkimet_id}",
        headers=user_headers,
    )

    assert visible_public_response.status_code == 200
    assert update_response.status_code == 204
    assert hidden_public_response.status_code == 404
    assert still_authorized_response.status_code == 200
    private_content = base.get_content(still_authorized_response)
    assert isinstance(private_content, dict)
    assert private_content["is_public"] is False


def test_unknown_dataset_lookups_return_404(
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
) -> None:
    """Verifica che GET /api/datasets/<dataset_name> risponda 404 per nomi sconosciuti.

    Oltre a un nome casuale prova ``error`` e ``duplicates``, nomi che in Arkimet
    identificano dataset di servizio e che non devono comparire nel catalogo.
    """
    _, _, user_headers, _, _ = _create_test_user(
        client,
        cleanup_registry,
        open_dataset=True,
    )
    missing_dataset_names = (
        f"missing-{faker.uuid4()}",
        "error",
        "duplicates",
    )

    for dataset_name in missing_dataset_names:
        response = client.get(
            f"{API_URI}/datasets/{dataset_name}",
            headers=user_headers,
        )
        assert response.status_code == 404, dataset_name