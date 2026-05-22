"""Integration tests for dataset authorization and visibility rules.

These tests build a small controlled scenario with temporary datasets and a
temporary user so they can verify how the API behaves with:

- public datasets,
- private datasets not assigned to the user,
- private datasets explicitly assigned to the user.
"""

import json
from typing import Any

from mistral.models.sqlalchemy import DatasetCategories
from mistral.tests.helpers.datasets import first_public_dataset_id
import pytest
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


PUBLIC_DATASET_NAME = "lm5"  # "ICON_2I_SURFACE_PRESSURE_LEVELS"


def _delete_dataset(db, dataset_id: int) -> None:
    """Delete one temporary dataset created by the test, including user links.

    The test may create datasets only for its own setup. Before removing the row
    it also detaches any many-to-many user associations so database cleanup is
    complete and predictable.
    """
    dataset = db.Datasets.query.get(dataset_id)
    if dataset is None:
        return

    for user in dataset.users.all():
        dataset.users.remove(user)

    db.session.delete(dataset)
    db.session.commit()


def _ensure_dataset_exists(db, cleanup_registry, dataset_name: str):
    """Return a usable dataset for the scenario, creating one if necessary.

    The authorization test needs a couple of concrete dataset rows with known
    names. If the environment already provides them, the test reuses them. If it
    does not, the helper creates temporary datasets and registers cleanup so the
    scenario remains self-contained.
    """
    dataset = db.Datasets.query.filter_by(name=dataset_name).first()
    if dataset is not None:
        return dataset

    license_entry = db.License.query.filter_by().first()
    attribution = db.Attribution.query.first()
    if license_entry is None or attribution is None:
        pytest.skip(
            "At least one license and one attribution are required to create test datasets"
        )

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Temporary dataset for {dataset_name}",
        category=DatasetCategories.OBS,
        fileformat="bufr",
        license_id=license_entry.id,
        attribution_id=attribution.id,
    )
    db.session.add(dataset)
    db.session.commit()
    cleanup_registry.add(lambda: _delete_dataset(db, dataset.id))

    return dataset


def test_dataset_endpoints_respect_user_authorizations(
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
) -> None:
    """Verify how dataset visibility changes with public access and explicit grants.

    The test prepares two private datasets, grants the user access to only one of
    them, and then checks that the API exposes exactly what that user should see.
    It also flips the user's ``open_dataset`` flag to confirm that explicit grants
    still work even after public-catalog access is disabled.
    """
    # arrange
    base = BaseTests()
    db = sqlalchemy.get_instance()
    dataset_to_auth = _ensure_dataset_exists(
        db,
        cleanup_registry,
        "sa_dataset_special",
    )
    unauth_dataset = _ensure_dataset_exists(
        db,
        cleanup_registry,
        "sa_dataset",
    )

    original_dataset_to_auth_license_id = dataset_to_auth.license_id
    original_unauth_dataset_license_id = unauth_dataset.license_id

    fake_private_group = db.GroupLicense(
        name="private_group",
        descr="mock private_group",
        is_public=False,
    )
    db.session.add(fake_private_group)
    db.session.flush()

    fake_private_license = db.License(
        name="private auth license",
        descr="mock private license",
        group_license_id=fake_private_group.id,
    )
    db.session.add(fake_private_license)
    db.session.flush()

    unauth_dataset.license_id = fake_private_license.id
    dataset_to_auth.license_id = fake_private_license.id
    db.session.add(unauth_dataset)
    db.session.add(dataset_to_auth)
    db.session.commit()

    permissions: dict[str, Any] = {
        "datasets": json.dumps([str(dataset_to_auth.id)]),
        "open_dataset": True,
    }
    user_uuid, user_data = base.create_user(client, permissions)
    user_headers, _ = base.do_login(
        client,
        user_data.get("email"),
        user_data.get("password"),
    )
    admin_headers, _ = base.do_login(client, None, None)

    try:
        # act
        list_response = client.get(f"{API_URI}/datasets", headers=user_headers)
        public_dataset_id = first_public_dataset_id(
            base.get_content(list_response) or []
        )
        public_dataset_response = client.get(
            f"{API_URI}/datasets/{public_dataset_id}",
            headers=user_headers,
        )
        missing_dataset_response = client.get(
            f"{API_URI}/datasets/{faker.pystr()}",
            headers=user_headers,
        )
        unauthorized_dataset_response = client.get(
            f"{API_URI}/datasets/sa_dataset",
            headers=user_headers,
        )
        authorized_dataset_response = client.get(
            f"{API_URI}/datasets/sa_dataset_special",
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
        hidden_public_dataset_response = client.get(
            f"{API_URI}/datasets/{public_dataset_id}",
            headers=user_headers,
        )
        still_authorized_dataset_response = client.get(
            f"{API_URI}/datasets/sa_dataset_special",
            headers=user_headers,
        )
        error_dataset_response = client.get(
            f"{API_URI}/datasets/error",
            headers=user_headers,
        )
        duplicates_dataset_response = client.get(
            f"{API_URI}/datasets/duplicates",
            headers=user_headers,
        )

        # assert
        assert list_response.status_code == 200
        assert isinstance(base.get_content(list_response), list)
        assert public_dataset_response.status_code == 200
        assert isinstance(base.get_content(public_dataset_response), dict)
        assert missing_dataset_response.status_code == 404
        assert unauthorized_dataset_response.status_code == 404

        assert authorized_dataset_response.status_code == 200
        authorized_content = base.get_content(authorized_dataset_response)
        assert isinstance(authorized_content, dict)
        assert authorized_content["is_public"] is False

        assert update_response.status_code == 204
        assert hidden_public_dataset_response.status_code == 404
        assert still_authorized_dataset_response.status_code == 200
        assert error_dataset_response.status_code == 404
        assert duplicates_dataset_response.status_code == 404
    finally:
        user_delete_response = client.delete(
            f"{API_URI}/admin/users/{user_uuid}",
            headers=admin_headers,
        )
        assert user_delete_response.status_code == 204

        current_license = db.License.query.filter_by().first()
        assert current_license is not None
        unauth_dataset.license_id = original_unauth_dataset_license_id or current_license.id
        dataset_to_auth.license_id = (
            original_dataset_to_auth_license_id or current_license.id
        )
        db.session.add(unauth_dataset)
        db.session.add(dataset_to_auth)
        db.session.flush()
        db.session.delete(fake_private_license)
        db.session.delete(fake_private_group)
        db.session.commit()