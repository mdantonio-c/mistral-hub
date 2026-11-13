# Test di GET /observations: casi limite del controller (MapsObservations.get in
# endpoints/maps_observed.py). I filtri principali sono testati in
# test_observations_filters.py e test_observations_station_details.py.
# Ambito: copre limiti di intervallo (anche al bordo e appena oltre, GET e POST),
# conflict interval/timerange, daily, last, stationDetails senza/multi network, stazione
# senza dati (404), coordinate uguali a zero e allStationProducts=false.
# Finestra dati: i rami positivi usano agrmet DBALLE 2020-04-06 00:00-01:00; i limiti
# di durata usano date sintetiche solo per fallire prima dell'accesso ai dati reali.
# Runtime fake: BeDballe.LASTDAYS viene patchato solo per classificare la finestra
# storica 2020-04-06 come DBALLE recente durante il test. I test con la fixture
# `fake_dballe_access` sostituiscono l'accesso ai dati con un fake senza dati che
# registra le query ricevute.
# Cleanup: non vengono creati record persistenti, salvo eventuali risorse gestite dalle
# fixture globali.

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.observed_windows import (
    OBS_DBALLE_FROM,
    OBS_DBALLE_TO,
    OBSERVATIONS_ENDPOINT,
    OBSERVED_LICENSE_GROUP,
    OBSERVED_NETWORK,
    api_url,
    dballe_window_override,
    parse_response,
    require_dballe_product,
)
from restapi.services.cache import Cache
from restapi.tests import FlaskClient

from .support import extract_products


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]

DBALLE_QUERY = (
    f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};"
    f"network:{OBSERVED_NETWORK};license:{OBSERVED_LICENSE_GROUP}"
)


@pytest.fixture
def fake_dballe_access(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> SimpleNamespace:
    """Sostituisce l'accesso ai dati DB-All.e con un fake senza dati.

    Il fake classifica ogni intervallo come DBALLE e registra le chiamate: la scelta
    del database (``db_type``) e le query passate a ``get_maps_response`` (``maps``).
    """
    # Import dopo la creazione dell'app (fixture client): il decoratore cache
    # dell'endpoint richiede la cache di restapi gia inizializzata.
    from mistral.endpoints.maps_observed import MapsObservations

    calls = SimpleNamespace(db_type=[], maps=[])

    def fake_get_db_type(date_min, date_max):
        calls.db_type.append((date_min, date_max))
        return "dballe"

    def fake_get_maps_response(query, *args, **kwargs):
        calls.maps.append(
            {
                "query": dict(query or {}),
                "station": dict(kwargs.get("query_station_data") or {}),
            }
        )
        if kwargs.get("download"):
            return None, None, None, None
        return None

    monkeypatch.setattr(BeDballe, "get_db_type", staticmethod(fake_get_db_type))
    monkeypatch.setattr(
        BeDballe, "get_maps_response", staticmethod(fake_get_maps_response)
    )
    # Le GET sono in cache (Redis) anche tra esecuzioni diverse della suite: senza
    # invalidazione una richiesta anonima identica non arriverebbe al fake.
    Cache.invalidate(MapsObservations.get)
    return calls


def _require_dballe_product(client: FlaskClient, headers: Any, test_runtime) -> str:
    """Sceglie via /fields un prodotto reale agrmet nella finestra DBALLE 2020-04-06."""
    return require_dballe_product(client, headers, test_runtime, DBALLE_QUERY)


def _get_observations(client: FlaskClient, headers: Any | None = None, **params: Any):
    """Esegue GET /observations con parametri espliciti."""
    return client.get(api_url(OBSERVATIONS_ENDPOINT, **params), headers=headers)


def _require_station_coordinates(
    client: FlaskClient,
    headers: Any,
    test_runtime,
) -> tuple[float, float]:
    """Ricava lat/lon di una stazione reale dalla finestra agrmet DBALLE ammessa.

    Interroga GET /observations e salta il test se la finestra non ha stazioni.
    """
    # Usiamo una risposta observed reale per evitare coordinate hardcoded non portabili.
    product = _require_dballe_product(client, headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"
    with dballe_window_override(test_runtime):
        response = _get_observations(
            client,
            headers,
            q=query,
            networks=OBSERVED_NETWORK,
        )
    assert response.status_code == 200
    content = parse_response(response)
    if not content.get("data"):
        pytest.skip(
            "agrmet DBALLE 2020-04-06 00:00-01:00 returned no stations for "
            "stationDetails edge tests"
        )
    station = content["data"][0]["stat"]
    return station["lat"], station["lon"]


def test_observations_anonymous_interval_over_three_days_returns_unauthorized(
    client: FlaskClient,
) -> None:
    """Verifica il 401 di GET /observations per un anonimo oltre 3 giorni.

    Le date attraversano piu giorni solo per colpire il controllo MAX_REQ_DAYS, che
    avviene prima della selezione DBALLE/Arkimet e prima di qualsiasi query dati.
    """
    # arrange
    query = "reftime:>=2020-04-06 00:00,<=2020-04-10 00:00;license:CCBY_COMPLIANT"

    # act
    response = _get_observations(client, q=query)

    # assert
    assert response.status_code == 401


def test_observations_authenticated_interval_over_ten_days_returns_unauthorized(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 401 di GET /observations per un utente autenticato oltre 10 giorni.

    Il limite MAX_REQ_DAYS_AUTHENTICATED scatta prima dell'accesso ai dati reali.
    """
    # arrange
    query = "reftime:>=2020-04-06 00:00,<=2020-04-17 00:00;license:CCBY_COMPLIANT"

    # act
    response = _get_observations(client, auth_headers, q=query)

    # assert
    assert response.status_code == 401


def test_observations_interval_greater_than_timerange_returns_conflict(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 409 di GET /observations se interval e minore del timerange.

    Il timerange della query ha un intervallo di 2 ore, mentre interval vale 1.
    """
    # arrange
    query = (
        f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};"
        "timerange:1,7200,10800;license:CCBY_COMPLIANT"
    )

    # act
    response = _get_observations(client, auth_headers, q=query, interval=1)

    # assert
    assert response.status_code == 409


def test_observations_daily_returns_valid_payload_on_dballe_window(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica che GET /observations con daily=true risponda 200 con ``data``.

    Usa la finestra agrmet DBALLE 2020-04-06 00:00-01:00.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"

    # act
    with dballe_window_override(test_runtime):
        response = _get_observations(client, auth_headers, q=query, daily="true")

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert isinstance(content, dict)
    assert "data" in content


def test_observations_last_smoke_returns_valid_payload_on_dballe_window(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Smoke test di GET /observations con last=true sulla finestra DBALLE ammessa.

    Con una sola giornata DBALLE disponibile, il test protegge il ramo controller e non
    pretende un confronto storico piu robusto; ulteriori giorni consecutivi renderebbero
    possibile una verifica piu forte della restrizione ai dati recenti.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"

    # act
    with dballe_window_override(test_runtime):
        response = _get_observations(client, auth_headers, q=query, last="true")

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert isinstance(content, dict)
    assert "data" in content


def test_observations_station_details_without_networks_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 di GET /observations per stationDetails=true senza networks."""
    # arrange
    query = DBALLE_QUERY

    # act
    response = _get_observations(
        client,
        auth_headers,
        q=query,
        stationDetails="true",
        lat=44.0,
        lon=11.0,
    )

    # assert
    assert response.status_code == 400


def test_observations_station_details_with_multiple_networks_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 di GET /observations con stationDetails=true e piu network.

    Il rifiuto avviene anche se i network indicati sono validi.
    """
    # arrange
    lat, lon = _require_station_coordinates(client, auth_headers, test_runtime)
    duplicate_valid_networks = f"{OBSERVED_NETWORK} or {OBSERVED_NETWORK}"

    # act
    response = _get_observations(
        client,
        auth_headers,
        q=DBALLE_QUERY,
        networks=duplicate_valid_networks,
        stationDetails="true",
        lat=lat,
        lon=lon,
    )

    # assert
    assert response.status_code == 400


def test_observations_station_details_unknown_station_returns_not_found(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 404 di GET /observations con stationDetails su stazione inesistente.

    Regressione EDGE-001: il parser restituisce sempre ``{"descr", "data"}``, quindi il
    controllo sul risultato vuoto non scattava e la risposta era 200 con ``data`` vuota.
    Una stazione inesistente e una stazione esistente senza dati nell'intervallo hanno
    lo stesso esito: nessun dato, quindi 404.
    """
    # arrange
    # La finestra DBALLE deve avere dati: cosi il 404 dipende dalla stazione cercata.
    _require_dballe_product(client, auth_headers, test_runtime)

    # act
    with dballe_window_override(test_runtime):
        response = _get_observations(
            client,
            auth_headers,
            q=DBALLE_QUERY,
            networks=OBSERVED_NETWORK,
            stationDetails="true",
            ident="missing-station-ext",
        )

    # assert
    assert response.status_code == 404
    assert parse_response(response) == "Station data not found"


def test_observations_all_station_products_false_limits_station_details_products(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica che allStationProducts=false mantenga solo il prodotto richiesto.

    Il test chiama GET /observations con stationDetails=true su una stazione reale
    della finestra DBALLE 2020-04-06 e un prodotto scelto via /fields; se il runtime
    espone un payload senza prodotti, lo scenario non e significativo e viene saltato
    esplicitamente.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)
    lat, lon = _require_station_coordinates(client, auth_headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"

    # act
    with dballe_window_override(test_runtime):
        response = _get_observations(
            client,
            auth_headers,
            q=query,
            networks=OBSERVED_NETWORK,
            stationDetails="true",
            allStationProducts="false",
            lat=lat,
            lon=lon,
        )

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    products = extract_products(content)
    if not products:
        pytest.skip(
            "stationDetails payload for agrmet DBALLE 2020-04-06 has no products to "
            "assert allStationProducts=false"
        )
    assert products <= {product}


def test_observations_station_details_with_zero_coordinates_reaches_the_query(
    client: FlaskClient,
    auth_headers,
    fake_dballe_access: SimpleNamespace,
) -> None:
    """Verifica che lat=0 e lon=0 siano coordinate valide per stationDetails.

    Il fake non restituisce dati, quindi la risposta e il 404 "Station data not found"
    (stazione senza dati) e non il 400 per parametri mancanti.
    """
    # act
    response = _get_observations(
        client,
        auth_headers,
        q=DBALLE_QUERY,
        networks=OBSERVED_NETWORK,
        stationDetails="true",
        lat=0.0,
        lon=0.0,
    )

    # assert
    assert response.status_code == 404
    assert parse_response(response) == "Station data not found"
    assert len(fake_dballe_access.maps) == 1
    station = fake_dballe_access.maps[0]["station"]
    assert (station["lat"], station["lon"]) == (0.0, 0.0)


def test_observations_bbox_with_zero_coordinates_reaches_the_query(
    client: FlaskClient,
    auth_headers,
    fake_dballe_access: SimpleNamespace,
) -> None:
    """Verifica che una bbox completa con estremi a zero arrivi alla query.

    Senza stationDetails una mappa senza dati resta una risposta 200 con data vuota.
    """
    # act
    response = _get_observations(
        client,
        auth_headers,
        q=DBALLE_QUERY,
        lonmin=0.0,
        latmin=0.0,
        lonmax=20.0,
        latmax=50.0,
    )

    # assert
    assert response.status_code == 200
    assert parse_response(response)["data"] == []
    assert len(fake_dballe_access.maps) == 1
    query = fake_dballe_access.maps[0]["query"]
    bbox = {key: query[key] for key in ("lonmin", "latmin", "lonmax", "latmax")}
    assert bbox == {"lonmin": 0.0, "latmin": 0.0, "lonmax": 20.0, "latmax": 50.0}


@pytest.mark.parametrize("missing", ["lonmin", "latmin", "lonmax", "latmax"])
def test_observations_partial_bbox_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    fake_dballe_access: SimpleNamespace,
    missing: str,
) -> None:
    """Verifica il 400 per una bbox parziale, qualunque estremo manchi."""
    # arrange
    bbox = {"lonmin": 0.0, "latmin": 0.0, "lonmax": 20.0, "latmax": 50.0}
    del bbox[missing]

    # act
    response = _get_observations(client, auth_headers, q=DBALLE_QUERY, **bbox)

    # assert
    assert response.status_code == 400
    assert parse_response(response) == "Coordinates for bounding box are missing"
    assert fake_dballe_access.maps == []


def test_observations_post_zero_coordinates_reach_the_query(
    client: FlaskClient,
    auth_headers,
    fake_dballe_access: SimpleNamespace,
) -> None:
    """Verifica che il download accetti bbox e stazione con coordinate a zero.

    Con il fake non c'e nulla da estrarre e la risposta e una lista vuota.
    """
    # act
    bbox_response = client.post(
        api_url(
            OBSERVATIONS_ENDPOINT,
            q=DBALLE_QUERY,
            output_format="JSON",
            lonmin=0.0,
            latmin=0.0,
            lonmax=20.0,
            latmax=50.0,
        ),
        headers=auth_headers,
    )
    station_response = client.post(
        api_url(
            OBSERVATIONS_ENDPOINT,
            q=DBALLE_QUERY,
            output_format="JSON",
            networks=OBSERVED_NETWORK,
            singleStation="true",
            lat=0.0,
            lon=0.0,
        ),
        headers=auth_headers,
    )

    # assert
    assert bbox_response.status_code == 200
    assert station_response.status_code == 200
    assert len(fake_dballe_access.maps) == 2
    bbox_query = fake_dballe_access.maps[0]["query"]
    assert (bbox_query["lonmin"], bbox_query["latmin"]) == (0.0, 0.0)
    station = fake_dballe_access.maps[1]["station"]
    assert (station["lat"], station["lon"]) == (0.0, 0.0)


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    ("authenticated", "limit_days"),
    [(False, 3), (True, 10)],
    ids=["anonymous", "authenticated"],
)
@pytest.mark.parametrize(
    ("extra_minutes", "allowed"),
    [(0, True), (1, False)],
    ids=["exact-limit", "limit-plus-one-minute"],
)
def test_observations_interval_limit_counts_fractions_of_day(
    client: FlaskClient,
    auth_headers,
    fake_dballe_access: SimpleNamespace,
    method: str,
    authenticated: bool,
    limit_days: int,
    extra_minutes: int,
    allowed: bool,
) -> None:
    """Verifica il limite di durata di /observations al bordo e appena oltre.

    Il limite esatto (3 giorni anonimi, 10 autenticati) e consentito; un minuto in piu
    viene rifiutato con 401 prima di scegliere il database o leggere dati.
    """
    # arrange
    date_to = f"2020-04-{6 + limit_days:02d} 00:{extra_minutes:02d}"
    query = f"reftime:>=2020-04-06 00:00,<={date_to};license:{OBSERVED_LICENSE_GROUP}"
    headers = auth_headers if authenticated else None
    params = {"q": query}
    if method == "post":
        params["output_format"] = "JSON"

    # act
    send = client.get if method == "get" else client.post
    response = send(api_url(OBSERVATIONS_ENDPOINT, **params), headers=headers)

    # assert
    if allowed:
        assert response.status_code == 200
        assert len(fake_dballe_access.db_type) == 1
    else:
        assert response.status_code == 401
        assert parse_response(response) == f"maximum {limit_days} days can be requested"
        assert fake_dballe_access.db_type == []
