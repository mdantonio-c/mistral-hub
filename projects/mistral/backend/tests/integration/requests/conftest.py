"""Fixtures local to the pending-request integration area.

These fixtures prepare a temporary user and a pair of seeded requests with
different ages so the deletion tests can focus on grace-period behavior instead
of on raw request-row setup.
"""

import pytest
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from mistral.tests.integration.requests.support import (
    create_pending_delete_requests,
    delete_request_rows,
)


@pytest.fixture
def pending_request_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary authenticated user dedicated to pending-request tests."""
    base = BaseTests()
    user = create_authenticated_test_user(base, client)
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


@pytest.fixture
def pending_delete_requests(
    faker: Faker,
    pending_request_user: AuthenticatedTestUser,
    cleanup_registry,
) -> tuple[int, int]:
    """Seed one old request and one fresh request for deletion-rule scenarios.

    The deletion tests need two contrasting cases: one request old enough to be
    deletable and one still inside the protection window. This fixture creates and
    registers cleanup for both ids.
    """
    db = sqlalchemy.get_instance()
    deletable_request_id, undeletable_request_id = create_pending_delete_requests(
        faker,
        db,
        pending_request_user.user_id,
    )
    cleanup_registry.add(
        lambda: delete_request_rows(
            db,
            deletable_request_id,
            undeletable_request_id,
        )
    )
    return deletable_request_id, undeletable_request_id