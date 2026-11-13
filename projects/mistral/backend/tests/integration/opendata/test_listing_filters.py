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


@pytest.mark.parametrize(
    ("q", "expected_message"),
    [
        ("run", "Invalid run filter in q: run"),
        ("runX", "Invalid run filter in q: runX"),
        (
            "reftime:>=2019-06-21,<=2019-06-22 00:00",
            "Invalid reftime in q: 2019-06-21 (expected YYYY-MM-DD HH:MM)",
        ),
        (
            "reftime:>=2019-02-30 00:00,<=2019-03-01 00:00",
            "Invalid reftime in q: 2019-02-30 00:00 (expected YYYY-MM-DD HH:MM)",
        ),
        (
            "reftime:>2019-06-21 00:00,<=2019-06-22 00:00",
            "Invalid reftime filter in q: >2019-06-21 00:00",
        ),
        (
            "reftime:>=2019-06-21 00:00",
            "Invalid reftime filter in q: both bounds are required",
        ),
    ],
    ids=[
        "run-without-colon",
        "unknown-run-prefix",
        "reftime-without-time",
        "reftime-unexisting-date",
        "reftime-unknown-comparison",
        "reftime-single-bound",
    ],
)
def test_listing_malformed_q_returns_400_with_clear_message(
    client: FlaskClient,
    cleanup_registry,
    q: str,
    expected_message: str,
) -> None:
    """Verifica che un parametro ``q`` malformato dia un 400 con messaggio chiaro.

    Prima gli stessi input sollevavano IndexError/ValueError/KeyError, che restapi
    trasforma in un 400 generico con il solo nome dell'eccezione.
    """
    # arrange
    dataset, _ = create_listing_env(client, cleanup_registry)
    endpoint = f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"

    # act
    response = client.get(endpoint, query_string={"q": q})

    # assert
    assert response.status_code == 400
    assert BaseTests().get_content(response) == expected_message


def test_listing_filters_by_documented_query_with_spaces(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica la query documentata nel codice, con spazio dopo ``reftime:``.

    Esercita GET /api/datasets/<id>/opendata con
    ``q=reftime: >=...,<=...;run:MINUTE,00:00``.
    """
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    query = "reftime: >=2020-01-01 00:00,<=2020-01-02 23:59;run:MINUTE,00:00"
    endpoint = f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"

    # act
    response = client.get(endpoint, query_string={"q": query})

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert [item["filename"] for item in content] == [seeded_results[0].filename]
