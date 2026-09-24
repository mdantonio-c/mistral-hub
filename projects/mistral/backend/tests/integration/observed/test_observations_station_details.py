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
    # Prepariamo lo scenario osservazioni con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        only_stations=True,
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert isinstance(content, dict)
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert response.status_code == 200
    stations = content.get("data")
    assert isinstance(stations, list)
    assert stations, f"No stations returned for the {observed_case.db_type} case"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert all(isinstance(station, dict) for station in stations)
    assert all(station.get("prod") == [] for station in stations)


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_station_details_returns_success_for_known_station(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that `stationDetails` succeeds for a station discovered from a valid query."""
    # arrange
    # Prepariamo lo scenario osservazioni con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
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
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response, content = fetch_observations(
        client,
        observed_case.headers,
        endpoint,
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 200
    assert isinstance(content, dict)
    stations = content.get("data")
    assert isinstance(stations, list)
    assert stations, f"No station details returned for the {observed_case.db_type} case"
    assert len(stations) == 1

    station = stations[0]
    assert isinstance(station, dict)
    station_metadata = station.get("stat")
    assert isinstance(station_metadata, dict)
    assert station_metadata.get("net") == observed_case.params.network
    assert station_metadata.get("lat") == pytest.approx(station_lat)
    assert station_metadata.get("lon") == pytest.approx(station_lon)

    products = station.get("prod")
    assert isinstance(products, list)
    assert products, f"No products returned for the {observed_case.db_type} station"
    for product in products:
        assert isinstance(product, dict)
        assert {"var", "lev", "trange", "val"} <= product.keys()
        assert isinstance(product["val"], list)
        assert product["val"]


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_station_details_with_unknown_network_returns_not_found(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that station details still enforce network validity checks."""
    # arrange
    # Prepariamo lo scenario osservazioni con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
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
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 404


@pytest.mark.parametrize("case_fixture", ALL_CASES)
def test_station_details_without_coordinates_returns_bad_request(
    request,
    client: FlaskClient,
    case_fixture: str,
) -> None:
    """Verify that station details reject requests that omit station coordinates."""
    # arrange
    # Prepariamo lo scenario osservazioni con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
    observed_case = request.getfixturevalue(case_fixture)
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
        station_details=True,
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response, _ = fetch_observations(client, observed_case.headers, endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 400