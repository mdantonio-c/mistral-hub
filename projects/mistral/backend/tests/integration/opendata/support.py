"""Opendata support helpers local to the opendata integration area.

The opendata tests create temporary datasets, users, synthetic request rows, and
fake downloadable files. This module centralizes that setup so the test files can
talk about authorization, listing, and download behavior without manually
building every supporting record each time.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4
from zipfile import ZipFile

import pytest
from mistral.endpoints import OPENDATA_DIR
from mistral.models.sqlalchemy import DatasetCategories
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

DEFAULT_BOUNDING = (
    "POLYGON ((-17.5374014843514558 25.8214118125177627, "
    "-29.6618577019240988 49.1185603319763260, "
    "-18.1123487722656762 52.2082915170863942, "
    "-5.2841914142956252 54.2586288297216370, "
    "8.3858281354571460 55.0739215029660087, "
    "22.1519686504923001 54.5643432849449539, "
    "35.2289961673372574 52.7869189178025664, "
    "47.0956192803686022 49.9188746081732049, "
    "47.1122744703592744 49.8885465483880779, "
    "35.6138690063754808 26.3910672255853775, "
    "-17.5374014843514558 25.8214118125177627))"
)


@dataclass(frozen=True)
class TestDataset:
    """Small record exposing both numeric and arkimet identifiers for one dataset."""

    id: int
    arkimet_id: str


@dataclass(frozen=True)
class OpendataSeedSpec:
    """Declarative description of one fake opendata package to seed in a test."""

    reftime: datetime
    content: str
    run: str | None = None
    archived: bool = False
    submission_date: datetime | None = None


@dataclass(frozen=True)
class FakeOpendataResult:
    """Metadata describing one seeded opendata request row and file on disk."""

    request_id: int
    filename: str
    content: str
    reftime: datetime
    run: str | None


def create_opendata_user(
    client: FlaskClient,
    dataset_ids: list[int] | None = None,
    *,
    allow_schedule: bool = False,
) -> AuthenticatedTestUser:
    """Create a temporary user for opendata tests, optionally pre-authorized.

    The fixture can grant access to specific datasets and, when needed, also allow
    schedule-related operations so the same helper can serve both public and
    private opendata scenarios.
    """
    permissions: dict[str, Any] = {
        "disk_quota": 1073741824,
        "max_output_size": 1073741824,
        "allowed_postprocessing": True,
        "open_dataset": True,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids or []]),
    }
    if allow_schedule:
        permissions["allowed_schedule"] = True

    return create_authenticated_test_user(BaseTests(), client, permissions)


def register_user_cleanup(
    client: FlaskClient,
    cleanup_registry,
    user: AuthenticatedTestUser,
) -> None:
    """Register the standard filesystem and user cleanup for an opendata scenario."""
    register_test_user_cleanup(
        BaseTests(),
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )


def create_test_dataset(
    db,
    cleanup_registry,
    *,
    is_public: bool,
    prefix: str = "opendata",
) -> TestDataset:
    """Create a temporary dataset together with its license records and cleanup.

    Opendata tests often need a dataset whose visibility they fully control. This
    helper creates a dedicated dataset plus its attribution and license structure
    so the test scenario stays isolated from unrelated catalog data.
    """
    attribution = db.Attribution.query.first()
    if attribution is None:
        pytest.skip("At least one attribution is required to create test datasets")

    token = uuid4().hex[:12]
    dataset_name = f"{prefix}_{token}"

    group_license = db.GroupLicense(
        name=f"{dataset_name}_group",
        descr=f"Temporary license group for {dataset_name}",
        is_public=is_public,
    )
    db.session.add(group_license)
    db.session.flush()

    license_entry = db.License(
        name=f"{dataset_name}_license",
        descr=f"Temporary license for {dataset_name}",
        group_license_id=group_license.id,
    )
    db.session.add(license_entry)
    db.session.flush()

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Temporary dataset for {dataset_name}",
        category=DatasetCategories.OBS,
        fileformat="bufr",
        license_id=license_entry.id,
        attribution_id=attribution.id,
        bounding=DEFAULT_BOUNDING,
    )
    db.session.add(dataset)
    db.session.commit()

    cleanup_registry.add(
        lambda: _delete_dataset_bundle(
            db,
            dataset_id=dataset.id,
            license_id=license_entry.id,
            group_license_id=group_license.id,
        )
    )

    return TestDataset(id=dataset.id, arkimet_id=dataset.arkimet_id)


def authorize_user_for_dataset(db, user_uuid: str, dataset_id: int) -> None:
    """Grant one existing user access to one existing dataset if not already linked."""
    user = db.User.query.filter_by(uuid=user_uuid).first()
    dataset = db.Datasets.query.get(dataset_id)
    assert user is not None
    assert dataset is not None

    if all(authorized_dataset.id != dataset_id for authorized_dataset in user.datasets):
        user.datasets.append(dataset)
        db.session.add(user)
        db.session.commit()


def create_fake_opendata_result(
    db,
    cleanup_registry,
    request_owner_id: int,
    dataset_id: str,
    reftime: datetime,
    file_content: str,
    *,
    run: str | None = None,
    archived: bool = False,
    submission_date: datetime | None = None,
) -> FakeOpendataResult:
    """Create a successful opendata request row together with its output file on disk."""
    request = db.Request(
        user_id=request_owner_id,
        name=f"opendata_{uuid4().hex}",
        args=_build_opendata_args(dataset_id, reftime, run),
        status="SUCCESS",
        opendata=True,
        archived=archived,
        submission_date=submission_date or datetime.utcnow(),
    )
    db.session.add(request)
    db.session.commit()

    filename = f"{uuid4().hex}.grib"
    output_path = Path(OPENDATA_DIR, filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(file_content, encoding="utf-8")

    file_output = db.FileOutput(
        user_id=request_owner_id,
        filename=filename,
        size=len(file_content.encode("utf-8")),
        request_id=request.id,
    )
    db.session.add(file_output)
    db.session.commit()

    cleanup_registry.add(lambda: _delete_request_row(db, request.id))
    cleanup_registry.add(lambda: _delete_file(output_path))

    return FakeOpendataResult(
        request_id=request.id,
        filename=filename,
        content=file_content,
        reftime=reftime,
        run=run,
    )


def seed_opendata_results(
    db,
    cleanup_registry,
    request_owner_id: int,
    dataset_id: str,
    seeds: Sequence[OpendataSeedSpec],
) -> list[FakeOpendataResult]:
    """Create several fake opendata results from a compact list of seed specifications."""
    return [
        create_fake_opendata_result(
            db,
            cleanup_registry,
            request_owner_id,
            dataset_id,
            seed.reftime,
            seed.content,
            run=seed.run,
            archived=seed.archived,
            submission_date=seed.submission_date,
        )
        for seed in seeds
    ]


def create_private_opendata_env(client: FlaskClient, cleanup_registry):
    """Create a private dataset, a request owner, and one seeded opendata result."""
    db = sqlalchemy.get_instance()
    dataset = create_test_dataset(db, cleanup_registry, is_public=False)
    user = create_opendata_user(client)
    register_user_cleanup(client, cleanup_registry, user)
    result = create_fake_opendata_result(
        db,
        cleanup_registry,
        user.user_id,
        dataset.arkimet_id,
        datetime(2020, 1, 1, 0, 0),
        "private-opendata-content",
        run="00:00",
    )
    return db, dataset, user, result


def create_listing_env(client: FlaskClient, cleanup_registry):
    """Create one public dataset and two seeded listing entries with different filters."""
    db = sqlalchemy.get_instance()
    dataset = create_test_dataset(db, cleanup_registry, is_public=True)
    request_owner = create_opendata_user(client)
    register_user_cleanup(client, cleanup_registry, request_owner)
    seeded_results = seed_opendata_results(
        db,
        cleanup_registry,
        request_owner.user_id,
        dataset.arkimet_id,
        [
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 1, 0, 0),
                run="00:00",
                content="listing-run-00",
            ),
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 2, 0, 0),
                run="12:00",
                content="listing-run-12",
            ),
        ],
    )
    return dataset, seeded_results


def create_download_env(client: FlaskClient, cleanup_registry):
    """Create one public dataset and three seeded opendata files for download scenarios."""
    db = sqlalchemy.get_instance()
    dataset = create_test_dataset(db, cleanup_registry, is_public=True)
    request_owner = create_opendata_user(client)
    register_user_cleanup(client, cleanup_registry, request_owner)
    seeded_results = seed_opendata_results(
        db,
        cleanup_registry,
        request_owner.user_id,
        dataset.arkimet_id,
        [
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 1, 0, 0),
                run="00:00",
                content="download-20200101-run-00",
            ),
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 1, 0, 0),
                run="12:00",
                content="download-20200101-run-12",
            ),
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 2, 0, 0),
                run="00:00",
                content="download-20200102-run-00",
            ),
        ],
    )
    return dataset, seeded_results


def zip_filenames(response) -> list[str]:
    """Extract and sort filenames contained in a zip download response."""
    archive_data = io.BytesIO(response.get_data())
    with ZipFile(archive_data, "r") as archive:
        return sorted(archive.namelist())


def _build_opendata_args(
    dataset_id: str,
    reftime: datetime,
    run: str | None,
) -> dict[str, Any]:
    """Build the request args payload stored in synthetic opendata request rows."""
    reftime_value = reftime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return {
        "filters": {"run": _build_run_filter(run)} if run else None,
        "reftime": {"from": reftime_value, "to": reftime_value},
        "datasets": [dataset_id],
    }


def _build_run_filter(run: str) -> list[dict[str, Any]]:
    """Convert an HH:MM run string into the stored MINUTE filter structure."""
    hours, minutes = [int(part) for part in run.split(":", maxsplit=1)]
    total_minutes = (hours * 60) + minutes
    return [
        {
            "desc": f"MINUTE({run})",
            "style": "MINUTE",
            "value": total_minutes,
            "active": True,
        }
    ]


def _delete_dataset_bundle(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_license_id: int,
) -> None:
    """Remove a temporary dataset together with its license and group-license records."""
    dataset = db.Datasets.query.get(dataset_id)
    if dataset is not None:
        for user in dataset.users.all():
            dataset.users.remove(user)
        db.session.delete(dataset)

    license_entry = db.License.query.get(license_id)
    if license_entry is not None:
        db.session.delete(license_entry)

    group_license = db.GroupLicense.query.get(group_license_id)
    if group_license is not None:
        db.session.delete(group_license)

    db.session.commit()


def _delete_request_row(db, request_id: int) -> None:
    """Delete a synthetic request row if it still exists in the test database."""
    request = db.Request.query.get(request_id)
    if request is None:
        return

    db.session.delete(request)
    db.session.commit()


def _delete_file(path: Path) -> None:
    """Delete a generated opendata file from disk if the path still exists."""
    if path.exists():
        path.unlink()