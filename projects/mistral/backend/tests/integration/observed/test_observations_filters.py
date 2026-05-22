"""Integration tests for reftime, network, spatial, and product filters on observations."""

from uuid import uuid4

import pytest
from restapi.tests import FlaskClient

from .support import (
    ALL_CASES,
    ARCHIVE_CASES,
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
    """Verify that a valid reftime range returns data containing the discovered products."""
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
    """Verify that archived queries cannot specify only the upper reftime bound."""
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
    """Verify that recent queries cannot specify only the lower reftime bound."""
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
    """Verify that filtering by one discovered network keeps the expected products visible."""
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
    """Verify that an unknown observed network produces a 404 response."""
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
    """Verify that a valid bounding box still returns data for the expected products."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        lonmin=6.7499,
        lonmax=18.4802,
        latmin=36.6199,
        latmax=47.1153,
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
    """Verify that a bounding box outside the available station area returns no data."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        lonmin=36.6199,
        lonmax=47.1153,
        latmin=6.7499,
        latmax=18.4802,
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
    """Verify that filtering by one product excludes the secondary discovered product."""
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
    """Verify that an unknown product code yields an empty but successful response."""
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
    """Verify that combined reftime, network, bbox, and product filters stay mutually consistent."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    require_secondary_product(observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(
            observed_case.params,
            product=observed_case.params.product_1,
        ),
        networks=observed_case.params.network,
        lonmin=6.7499,
        lonmax=18.4802,
        latmin=36.6199,
        latmax=47.1153,
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