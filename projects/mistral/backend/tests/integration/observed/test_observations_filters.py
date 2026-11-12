"""Test di integrazione sui filtri di GET /observations.

Coprono i filtri per reftime, network, area geografica (bounding box) e prodotto.
"""

from uuid import uuid4

import pytest
from restapi.tests import FlaskClient

from .support import (
    ALL_CASES,
    ARCHIVE_CASES,
    ITALY_BOUNDING_BOX,
    RECENT_CASES,
    build_observations_endpoint,
    build_reftime_query,
    extract_products,
    fetch_observations,
    require_secondary_product,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_reftime_range_returns_matching_products(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che GET /observations con reftime valido contenga i prodotti attesi."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    products = extract_products(content)
    assert observed_case.params.product_1 in products
    assert observed_case.params.product_2 in products


@pytest.mark.parametrize("case_fixture", ARCHIVE_CASES)
def test_reftime_with_only_date_to_returns_bad_request(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica il 400 di GET /observations se manca l'estremo iniziale del reftime.

    Scenari con dati archiviati: la query indica solo la data finale.
    """
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params, include_from=False),
    )

    # act
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    assert response.status_code == 400


@pytest.mark.parametrize("case_fixture", RECENT_CASES)
def test_reftime_with_only_date_from_returns_bad_request(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica il 400 di GET /observations se manca l'estremo finale del reftime.

    Scenari con dati recenti: la query indica solo la data iniziale.
    """
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params, include_to=False),
    )

    # act
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    assert response.status_code == 400


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_network_filter_returns_matching_products(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che il filtro networks di GET /observations tenga i prodotti attesi."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    products = extract_products(content)
    assert observed_case.params.product_1 in products
    assert observed_case.params.product_2 in products


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_unknown_network_returns_not_found(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che GET /observations risponda 404 per un network sconosciuto."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=f"missing_{uuid4().hex}",
    )

    # act
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    assert response.status_code == 404


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_bounding_box_filter_returns_matching_products(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che GET /observations con bounding box valida dia i prodotti attesi."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        **ITALY_BOUNDING_BOX,
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    products = extract_products(content)
    assert observed_case.params.product_1 in products
    assert observed_case.params.product_2 in products


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_outside_bounding_box_returns_empty_data(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che GET /observations su una bounding box senza stazioni dia data vuoto.

    La bounding box si ottiene scambiando latitudini e longitudini di
    ITALY_BOUNDING_BOX, cosi cade fuori dall'area delle stazioni.
    """
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        lonmin=ITALY_BOUNDING_BOX["latmin"],
        lonmax=ITALY_BOUNDING_BOX["latmax"],
        latmin=ITALY_BOUNDING_BOX["lonmin"],
        latmax=ITALY_BOUNDING_BOX["lonmax"],
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    assert content["data"] == []


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_product_filter_returns_only_requested_product(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che il filtro product di GET /observations escluda l'altro prodotto."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(
            observed_case.params,
            product=observed_case.params.product_1,
        ),
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    products = extract_products(content)
    assert observed_case.params.product_1 in products
    assert observed_case.params.product_2 not in products


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_unknown_product_returns_empty_data(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che GET /observations con prodotto sconosciuto dia 200 e data vuoto."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params, product="B11111"),
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    assert content["data"] == []


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_combined_filters_return_only_requested_product(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verifica che i filtri combinati di GET /observations restino coerenti tra loro.

    Reftime, network, bounding box e prodotto insieme restituiscono solo il prodotto
    richiesto.
    """
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(
            observed_case.params,
            product=observed_case.params.product_1,
        ),
        networks=observed_case.params.network,
        **ITALY_BOUNDING_BOX,
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert isinstance(content, dict)
    assert response.status_code == 200
    products = extract_products(content)
    assert observed_case.params.product_1 in products
    assert observed_case.params.product_2 not in products