"""Helpers for isolated dataset records used by integration tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from mistral.models.sqlalchemy import DatasetCategories
from mistral.services.arkimet import BeArkimet


def require_dataset(db, dataset_name: str):
    """Return a real catalog dataset by name or arkimet_id, or skip when missing."""
    dataset = db.Datasets.query.filter(
        (db.Datasets.name == dataset_name) | (db.Datasets.arkimet_id == dataset_name)
    ).first()
    if dataset is None:
        pytest.skip(f"Dataset '{dataset_name}' is not available in this environment")
    return dataset


def delete_test_dataset_bundle(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_license_id: int,
    attribution_id: int | None,
) -> None:
    """Remove a synthetic dataset and all of its supporting records.

    Cleanup is defensive: rows already gone are skipped, so a half-built setup does not
    mask the original failure. Pass ``attribution_id=None`` when the dataset reuses a
    real attribution that must be preserved.
    """
    db.session.rollback()
    dataset = db.Datasets.query.get(dataset_id)
    if dataset is not None:
        for user in dataset.users.all():
            dataset.users.remove(user)
        db.session.delete(dataset)
        db.session.flush()

    license_entry = db.License.query.get(license_id)
    if license_entry is not None:
        db.session.delete(license_entry)
        db.session.flush()

    group_license = db.GroupLicense.query.get(group_license_id)
    if group_license is not None:
        db.session.delete(group_license)
        db.session.flush()

    if attribution_id is not None:
        attribution = db.Attribution.query.get(attribution_id)
        if attribution is not None:
            db.session.delete(attribution)
            db.session.flush()

    db.session.commit()
    assert db.Datasets.query.get(dataset_id) is None
    assert db.License.query.get(license_id) is None
    assert db.GroupLicense.query.get(group_license_id) is None
    if attribution_id is not None:
        assert db.Attribution.query.get(attribution_id) is None


def create_test_dataset(
    db,
    cleanup_registry,
    *,
    is_public: bool,
    prefix: str = "dataset_test",
):
    """Create an isolated dataset bundle and register its complete teardown."""
    dataset_name = f"{prefix}_{uuid4().hex[:12]}"
    group_license = db.GroupLicense(
        name=f"{dataset_name}_group",
        descr=f"Synthetic license group for {dataset_name}",
        is_public=is_public,
    )
    attribution = db.Attribution(
        name=f"{dataset_name}_attribution",
        descr=f"Synthetic attribution for {dataset_name}",
        url="https://example.invalid/dataset-test-attribution",
    )
    db.session.add(group_license)
    db.session.add(attribution)
    db.session.flush()

    license_entry = db.License(
        name=f"{dataset_name}_license",
        descr=f"Synthetic license for {dataset_name}",
        group_license_id=group_license.id,
    )
    db.session.add(license_entry)
    db.session.flush()

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Synthetic dataset for {dataset_name}",
        source="arkimet",
        license_id=license_entry.id,
        attribution_id=attribution.id,
        category=DatasetCategories.OBS,
        fileformat="bufr",
    )
    db.session.add(dataset)
    db.session.commit()
    dataset_id = dataset.id
    license_id = license_entry.id
    group_license_id = group_license.id
    attribution_id = attribution.id
    cleanup_registry.add(
        lambda: delete_test_dataset_bundle(
            db,
            dataset_id=dataset_id,
            license_id=license_id,
            group_license_id=group_license_id,
            attribution_id=attribution_id,
        )
    )
    return dataset


def create_private_test_network(
    db,
    cleanup_registry,
    monkeypatch,
    *,
    prefix: str = "private_network_test",
) -> str:
    """Create a private synthetic dataset reachable through a synthetic network.

    Only the synthetic network is routed to the private dataset; every other network
    keeps the real Arkimet mapping and dataset authorization stays real, so users
    without an explicit grant get a portable 401 without touching the real catalog.
    """
    dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=False,
        prefix=prefix,
    )
    dataset_name = dataset.arkimet_id
    network = f"{dataset_name}_net"
    real_from_network_to_dataset = BeArkimet.from_network_to_dataset

    def from_network_to_dataset(requested_network: str):
        if requested_network == network:
            return dataset_name
        return real_from_network_to_dataset(requested_network)

    monkeypatch.setattr(
        BeArkimet,
        "from_network_to_dataset",
        staticmethod(from_network_to_dataset),
    )
    return network