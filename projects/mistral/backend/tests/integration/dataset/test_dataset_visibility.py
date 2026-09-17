"""Integration tests for the anonymous view of the dataset catalog.

This module focuses on the simplest public scenario: a user who is not logged
in should still be able to list public datasets and read the details of a known
public dataset, while unknown dataset identifiers must still return ``404``.
"""

import pytest
from faker import Faker
from mistral.tests.helpers.datasets import create_test_dataset

from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
]


def test_dataset_endpoints_expose_public_catalog_without_login(
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
) -> None:
    """Verify the basic anonymous contract for the dataset catalog endpoints.

    The test checks three independent expectations:

    1. ``GET /datasets`` works without authentication,
    2. one public dataset returned by the catalog can be fetched directly,
    3. an unknown dataset identifier still produces ``404``.
    """
    # arrange
    db = sqlalchemy.get_instance()
    public_dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=True,
        prefix="anonymous_public_dataset",
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    list_response = client.get(f"{API_URI}/datasets")
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    dataset_response = client.get(
        f"{API_URI}/datasets/{public_dataset.arkimet_id}"
    )
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    missing_response = client.get(f"{API_URI}/datasets/{faker.pystr()}")

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert list_response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert isinstance(list_response.json, list)
    assert any(
        dataset["id"] == public_dataset.arkimet_id
        and dataset["is_public"] is True
        for dataset in list_response.json
    )
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert dataset_response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert isinstance(dataset_response.json, dict)
    # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
    # visibile prima di usare il payload.
    assert missing_response.status_code == 404