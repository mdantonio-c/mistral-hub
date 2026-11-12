"""Test di integrazione sulla vista anonima del catalogo dataset.

Il modulo copre lo scenario pubblico piu semplice di GET /api/datasets e
GET /api/datasets/<dataset_name> (endpoints/datasets.py): un utente non
autenticato deve poter elencare i dataset pubblici e leggere i dettagli di un
dataset pubblico noto, mentre un identificativo sconosciuto deve dare ``404``.
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
    """Verifica il comportamento base degli endpoint del catalogo dataset senza login.

    Il test controlla tre aspetti indipendenti:

    1. ``GET /datasets`` funziona senza autenticazione,
    2. un dataset pubblico presente nel catalogo si puo leggere direttamente,
    3. un identificativo di dataset sconosciuto produce ``404``.
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
    list_response = client.get(f"{API_URI}/datasets")
    dataset_response = client.get(
        f"{API_URI}/datasets/{public_dataset.arkimet_id}"
    )
    missing_response = client.get(f"{API_URI}/datasets/{faker.pystr()}")

    # assert
    assert list_response.status_code == 200
    assert isinstance(list_response.json, list)
    assert any(
        dataset["id"] == public_dataset.arkimet_id
        and dataset["is_public"] is True
        for dataset in list_response.json
    )
    assert dataset_response.status_code == 200
    assert isinstance(dataset_response.json, dict)
    assert missing_response.status_code == 404