"""Test di integrazione su cancellazione e cleanup automatico delle richieste pendenti.

Coprono ``DELETE /api/requests/<id>`` (endpoints/requests.py) con la regola del grace
period e il task Celery ``automatic_cleanup`` (tasks/requests_cleanup.py), che marca
come fallite le richieste rimaste ferme troppo a lungo.
"""

import pytest
from celery.states import READY_STATES
from flask import Flask
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.helpers.auth import AuthenticatedTestUser
from mistral.tests.helpers.task_perimeter import RequestsCleanupPerimeter


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def delete_pending_request(client: FlaskClient, headers, request_id: int):
    """Chiama ``DELETE /api/requests/<id>``, l'endpoint sotto test, per la richiesta."""
    return client.delete(f"{API_URI}/requests/{request_id}", headers=headers)


class TestDeletePendingRequests(BaseTests):
    """Scenari sulle regole di cancellazione delle richieste attorno al grace period."""

    def test_delete_request_before_grace_period_returns_200(
        self,
        client: FlaskClient,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verifica che una richiesta piu vecchia del grace period si possa cancellare.

        ``DELETE /api/requests/<id>`` risponde 200 e la riga sparisce dal DB.
        """
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
        """Verifica che una richiesta pendente recente non si possa cancellare.

        Dentro il grace period ``DELETE /api/requests/<id>`` risponde 403 e la riga
        resta nel DB.
        """
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
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
        requests_cleanup_perimeter: RequestsCleanupPerimeter,
    ) -> None:
        """Verifica che il cleanup automatico marchi come fallite le richieste ferme.

        Il task Celery ``automatic_cleanup`` mette in ``FAILURE`` la richiesta oltre il
        grace period e lascia pendente quella recente.
        """
        # arrange
        db = sqlalchemy.get_instance()
        deletable_request_id, undeletable_request_id = pending_delete_requests
        # Il task reale e globale: gli rendiamo visibili solo utente e request del test.
        requests_cleanup_perimeter.allow(
            user_ids=[pending_request_user.user_id],
            request_ids=pending_delete_requests,
        )

        # act
        self.send_task(app, "automatic_cleanup")

        # assert
        deletable_request = db.Request.query.get(deletable_request_id)
        assert deletable_request is not None
        assert deletable_request.status == "FAILURE"

        undeletable_request = db.Request.query.get(undeletable_request_id)
        assert undeletable_request is not None
        assert undeletable_request.status not in READY_STATES