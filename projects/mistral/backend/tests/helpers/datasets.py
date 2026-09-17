"""Helpers for isolated dataset records used by integration tests."""

from __future__ import annotations

from uuid import uuid4

from mistral.models.sqlalchemy import DatasetCategories


def _delete_test_dataset_bundle(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_license_id: int,
    attribution_id: int,
) -> None:
    """Remove a synthetic dataset and all of its supporting records."""
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

    attribution = db.Attribution.query.get(attribution_id)
    if attribution is not None:
        db.session.delete(attribution)
        db.session.flush()

    db.session.commit()
    assert db.Datasets.query.get(dataset_id) is None
    assert db.License.query.get(license_id) is None
    assert db.GroupLicense.query.get(group_license_id) is None
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
        lambda: _delete_test_dataset_bundle(
            db,
            dataset_id=dataset_id,
            license_id=license_id,
            group_license_id=group_license_id,
            attribution_id=attribution_id,
        )
    )
    return dataset