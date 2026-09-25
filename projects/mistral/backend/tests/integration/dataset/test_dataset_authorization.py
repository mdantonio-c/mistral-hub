"""Integration tests for dataset authorization and visibility rules."""

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
    """Delete one temporary API user during fixture teardown."""
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
    """Create an authenticated user and immediately register its teardown."""
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
    """An authorized user can list and read a controlled public dataset."""
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
    """Only the private dataset explicitly assigned to the user is visible."""
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
    """Disabling public access hides public data but preserves a private grant."""
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
    """Authenticated lookup returns 404 for each representative unknown name."""
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