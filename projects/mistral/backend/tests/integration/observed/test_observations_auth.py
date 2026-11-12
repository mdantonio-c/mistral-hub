"""Test di integrazione sugli errori di validazione precoce di GET /api/observations.

Il modulo verifica le richieste che devono fallire prima di qualsiasi lettura dei
dati osservati, perche mancano input obbligatori o sono incompleti.
"""

import pytest
from restapi.tests import API_URI, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_observations_without_complete_reftime_returns_bad_request(
    client: FlaskClient,
) -> None:
    """Verifica che una query senza reftime completo riceva 400.

    Esercita GET /api/observations (MapsObservations.get, ramo "Reftime is missing").
    """
    # arrange
    endpoint = f"{API_URI}/observations?q=license:CCBY_COMPLIANT"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 400


def test_observations_without_license_returns_bad_request(
    client: FlaskClient,
) -> None:
    """Verifica che una query senza clausola license riceva 400.

    Esercita GET /api/observations (MapsObservations.get, controllo del gruppo licenza).
    """
    # arrange
    endpoint = f"{API_URI}/observations"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 400