"""Authentication and temporary-user helpers shared across the test suite.

Many integration scenarios need a throwaway user with known permissions, plus
the HTTP headers required to call the API as that user. This module centralizes
that setup so the individual tests can declare intent without manually dealing
with user creation, login, output directories, or teardown wiring.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mistral.endpoints import DOWNLOAD_DIR
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


@dataclass(frozen=True)
class AuthenticatedTestUser:
    """Small immutable record describing one temporary authenticated test user.

    The object groups together the values that tests commonly need after user
    creation: the UUID used by filesystem paths, the numeric database id, the
    authenticated HTTP headers, and the expected output directory on disk.
    """

    uuid: str
    user_id: int
    headers: Any
    output_dir: Path


def create_authenticated_test_user(
    base: BaseTests,
    client: FlaskClient,
    permissions: dict[str, Any] | None = None,
) -> AuthenticatedTestUser:
    """Create a temporary API user, log it in, and return the reusable metadata.

    The helper accepts an optional permissions dictionary exactly like the admin
    user-creation endpoint. It then logs in with the generated credentials and
    packages the result into ``AuthenticatedTestUser`` so callers can reuse the
    same object across setup, assertions, and cleanup.
    """
    db = sqlalchemy.get_instance()
    uuid, data = base.create_user(client, permissions or {})
    headers, _ = base.do_login(client, data.get("email"), data.get("password"))

    user = db.User.query.filter_by(uuid=uuid).first()
    assert user is not None

    return AuthenticatedTestUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
    )


def delete_test_user(base: BaseTests, client: FlaskClient, user_uuid: str) -> None:
    """Delete one temporary user through the admin API with default admin login.

    Tests rarely care about the response body of this cleanup operation; they
    only need a reliable way to remove throwaway users after the scenario.
    """
    admin_headers, _ = base.do_login(client, None, None)
    response = client.delete(f"{API_URI}/admin/users/{user_uuid}", headers=admin_headers)
    assert response.status_code == 204


def register_test_user_cleanup(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    *,
    user_uuid: str,
    root_path: Path,
) -> None:
    """Register the standard teardown actions for a temporary test user.

    This helper adds both filesystem cleanup for the user's working directory and
    admin-side deletion of the user record itself, so tests can fail safely
    without leaving residual state behind.
    """
    cleanup_registry.add_path(root_path)
    cleanup_registry.add(lambda: delete_test_user(base, client, user_uuid))


def make_basic_auth(email: str, access_key: str) -> dict[str, str]:
    """Build the exact HTTP Basic header used by access-key validation tests.

    The validation endpoint expects the user email and access key encoded as a
    single Basic-auth token. This helper keeps that encoding detail out of the
    test bodies.
    """
    token = base64.b64encode(f"{email}:{access_key}".encode()).decode()
    return {"Authorization": f"Basic {token}"}