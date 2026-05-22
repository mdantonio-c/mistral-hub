"""Integration tests for deleting pending requests and for automatic stale-request cleanup."""

import pytest
from celery.states import READY_STATES
from flask import Flask
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.helpers.auth import AuthenticatedTestUser


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def delete_pending_request(client: FlaskClient, headers, request_id: int):
    """Call the request-deletion endpoint for the provided request identifier."""
    return client.delete(f"{API_URI}/requests/{request_id}", headers=headers)


class TestDeletePendingRequests(BaseTests):
    """Group scenarios covering request deletion rules around the configured grace period."""

    def test_delete_request_before_grace_period_returns_200(
        self,
        client: FlaskClient,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verify that requests older than the grace period can be deleted manually."""
        # arrange
        db = sqlalchemy.get_instance()
        deletable_request_id, _ = pending_delete_requests

        # act
        response = delete_pending_request(
            client,
            pending_request_user.headers,
            deletable_request_id,
        )

        # assert
        assert response.status_code == 200
        assert db.Request.query.get(deletable_request_id) is None

    def test_delete_request_within_grace_period_returns_403(
        self,
        client: FlaskClient,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verify that fresh pending requests are still protected from manual deletion."""
        # arrange
        db = sqlalchemy.get_instance()
        _, undeletable_request_id = pending_delete_requests

        # act
        response = delete_pending_request(
            client,
            pending_request_user.headers,
            undeletable_request_id,
        )

        # assert
        assert response.status_code == 403
        assert db.Request.query.get(undeletable_request_id) is not None

    def test_requests_cleanup_marks_stale_request_as_failure(
        self,
        app: Flask,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verify that automatic cleanup marks stale requests as failed but leaves fresh ones pending."""
        # arrange
        db = sqlalchemy.get_instance()
        deletable_request_id, undeletable_request_id = pending_delete_requests

        # act
        self.send_task(app, "automatic_cleanup")

        # assert
        deletable_request = db.Request.query.get(deletable_request_id)
        assert deletable_request is not None
        assert deletable_request.status == "FAILURE"

        undeletable_request = db.Request.query.get(undeletable_request_id)
        assert undeletable_request is not None
        assert undeletable_request.status not in READY_STATES