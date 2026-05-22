"""Integration tests for station-only and station-details views of observed data."""

import pytest
from restapi.tests import FlaskClient

from .support import (
    ALL_CASES,
    build_observations_endpoint,
    build_reftime_query,
    fetch_station_sample,
    fetch_observations,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_only_stations_returns_entries_without_products(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that `onlyStations` suppresses product details in station listings."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        only_stations=True,
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
    assert content["data"][0]["prod"] == []


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_station_details_returns_success_for_known_station(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that `stationDetails` succeeds for a station discovered from a valid query."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    station_lat, station_lon = fetch_station_sample(client, observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
        lat=station_lat,
        lon=station_lon,
        station_details=True,
    )

    # act
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    assert response.status_code == 200
    assert content is not None


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_station_details_with_unknown_network_returns_not_found(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that station details still enforce network validity checks."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    station_lat, station_lon = fetch_station_sample(client, observed_case)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks="network_does_not_exist",
        lat=station_lat,
        lon=station_lon,
        station_details=True,
    )

    # act
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    assert response.status_code == 404


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_station_details_without_coordinates_returns_bad_request(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that station details reject requests that omit station coordinates."""
    # arrange
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
        station_details=True,
    )

    # act
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    assert response.status_code == 400