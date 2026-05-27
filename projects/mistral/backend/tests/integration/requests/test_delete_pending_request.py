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
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
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
        # Prepariamo lo scenario richieste utente con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        db = sqlalchemy.get_instance()
        deletable_request_id, _ = pending_delete_requests

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        response = delete_pending_request(
            client,
            pending_request_user.headers,
            deletable_request_id,
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert response.status_code == 200
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        assert db.Request.query.get(deletable_request_id) is None

    def test_delete_request_within_grace_period_returns_403(
        self,
        client: FlaskClient,
        pending_request_user: AuthenticatedTestUser,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verify that fresh pending requests are still protected from manual deletion."""
        # arrange
        # Prepariamo lo scenario richieste utente con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        db = sqlalchemy.get_instance()
        _, undeletable_request_id = pending_delete_requests

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        response = delete_pending_request(
            client,
            pending_request_user.headers,
            undeletable_request_id,
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert response.status_code == 403
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        assert db.Request.query.get(undeletable_request_id) is not None

    def test_requests_cleanup_marks_stale_request_as_failure(
        self,
        app: Flask,
        pending_delete_requests: tuple[int, int],
    ) -> None:
        """Verify that automatic cleanup marks stale requests as failed but leaves fresh ones pending."""
        # arrange
        # Prepariamo lo scenario richieste utente con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        db = sqlalchemy.get_instance()
        deletable_request_id, undeletable_request_id = pending_delete_requests

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        self.send_task(app, "automatic_cleanup")

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        deletable_request = db.Request.query.get(deletable_request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert deletable_request is not None
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert deletable_request.status == "FAILURE"

        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        undeletable_request = db.Request.query.get(undeletable_request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert undeletable_request is not None
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert undeletable_request.status not in READY_STATES