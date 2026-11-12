"""Fixture locali dell'area di integrazione sulle richieste pendenti.

Queste fixture preparano un utente temporaneo e una coppia di richieste inserite nel
DB con eta diverse, cosi i test di cancellazione possono concentrarsi sul
comportamento del grace period invece che sulla preparazione delle righe.
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
    """Crea un utente temporaneo autenticato per i test sulle richieste pendenti.

    L'utente nasce tramite l'API admin degli utenti di restapi; il cleanup a fine
    test rimuove utente e cartelle di output.
    """
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
    """Inserisce una richiesta vecchia e una recente per gli scenari di cancellazione.

    I test su ``DELETE /api/requests/<id>`` e sul task ``automatic_cleanup`` hanno
    bisogno di due casi opposti: una richiesta abbastanza vecchia da essere
    cancellabile e una ancora dentro la finestra di protezione. La fixture crea
    entrambe e registra il cleanup dei due id.
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