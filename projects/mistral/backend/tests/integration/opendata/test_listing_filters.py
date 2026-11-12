"""Test di integrazione sui filtri dell'elenco opendata di un dataset.

Esercitano GET /api/datasets/<id>/opendata (endpoints/opendata.py) con i filtri
``q=run:...`` e ``q=reftime:...``.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

from .support import create_listing_env


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_listing_unknown_dataset_returns_404(client: FlaskClient) -> None:
    """Verifica che l'elenco opendata di un dataset inesistente risponda 404.

    Esercita GET /api/datasets/<id>/opendata.
    """
    # arrange
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/datasets/{dataset_name}/opendata"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404


def test_listing_filters_by_run_returns_matching_package(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che il filtro sul run restituisca solo il pacchetto di quel run.

    Esercita GET /api/datasets/<id>/opendata con ``q=run:MINUTE,00:00``.
    """
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/datasets/{dataset.arkimet_id}/opendata?q=run:MINUTE,00:00"
    )

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert len(content) == 1
    assert content[0]["filename"] == seeded_results[0].filename


def test_listing_filters_by_reftime_returns_matching_package(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che una finestra di reftime restituisca solo il pacchetto interno.

    Esercita GET /api/datasets/<id>/opendata con ``q=reftime:>=...,<=...``.
    """
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    query_from = (seeded_results[0].reftime + timedelta(minutes=1)).strftime(
        "%Y-%m-%d %H:%M"
    )
    query_to = seeded_results[1].reftime.strftime("%Y-%m-%d %H:%M")
    endpoint = (
        f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
        f"?q=reftime:>={query_from},<={query_to}"
    )

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert len(content) == 1
    assert content[0]["filename"] == seeded_results[1].filename


def test_listing_filters_by_reftime_and_run_can_exclude_results(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che reftime e run combinati possano restituire un elenco vuoto.

    Esercita GET /api/datasets/<id>/opendata con filtri reftime e run insieme: la
    risposta e 200 con lista vuota, non 404.
    """
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    query_from = seeded_results[0].reftime.strftime("%Y-%m-%d %H:%M")
    query_to = (seeded_results[1].reftime - timedelta(minutes=1)).strftime(
        "%Y-%m-%d %H:%M"
    )
    endpoint = (
        f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
        f"?q=reftime:>={query_from},<={query_to};run:MINUTE,12:00"
    )

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert content == []