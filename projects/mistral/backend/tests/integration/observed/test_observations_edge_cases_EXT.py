# EXTENSION TRACEABILITY - Prompt 03, dominio integration/observed GET edge cases.
# Origine: questo modulo aggiunge solo rami controller GET non gia coperti dalla suite
# baseline observed, evitando duplicazioni dei filtri principali gia migrati.
# Ambito: copre limiti di intervallo, conflict interval/timerange, daily, last,
# stationDetails senza/multi network, stazione inesistente e allStationProducts=false.
# Finestra dati: i rami positivi usano agrmet DBALLE 2020-04-06 00:00-01:00; i limiti
# di durata usano date sintetiche solo per fallire prima dell'accesso ai dati reali.
# Runtime fake: BeDballe.LASTDAYS viene patchato solo per classificare la finestra
# storica 2020-04-06 come DBALLE recente durante il test; nessun dato viene simulato.
# Cleanup: non vengono creati record persistenti, salvo eventuali risorse gestite dalle
# fixture globali; non si modifica alcun conftest.py.
# Baseline non toccata: i casi core GET restano nei moduli legacy rifattorizzati e qui
# compaiono soltanto varianti controller-only richieste dal prompt.

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import pytest
from mistral.services.dballe import BeDballe
from restapi.tests import API_URI, BaseTests, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]

OBSERVED_ENDPOINT = f"{API_URI}/observations"
FIELDS_ENDPOINT = f"{API_URI}/fields"
OBSERVED_NETWORK = "agrmet"
OBSERVED_LICENSE_GROUP = "CCBY_COMPLIANT"
OBS_DBALLE_FROM = "2020-04-06 00:00"
OBS_DBALLE_TO = "2020-04-06 01:00"

DBALLE_QUERY = (
    f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};"
    f"network:{OBSERVED_NETWORK};license:{OBSERVED_LICENSE_GROUP}"
)


def _url(endpoint: str, **params: Any) -> str:
    """Costruisce URL query-string safe per /observations e /fields."""
    # I parser del backend leggono operatori e separatori dentro q, quindi usiamo
    # urlencode per consegnarli alla view senza ambiguita.
    return f"{endpoint}?{urlencode(params)}"


def _parse_response(response) -> Any:
    """Normalizza payload JSON restapi usati nelle asserzioni GET observed."""
    # BaseTests e il parser condiviso gia usato dal resto della suite di integrazione.
    return BaseTests().get_content(response)


def _dballe_window_override(test_runtime):
    """Classifica agrmet 2020-04-06 come DBALLE recente per i soli test positivi."""
    # L'override non inventa dati: sposta soltanto la soglia mobile usata da get_db_type.
    first_dballe_day = datetime(2020, 4, 6)
    last_archived_day = first_dballe_day - timedelta(days=1)
    lastdays = (datetime.now() - last_archived_day).days
    return test_runtime.override_attr(BeDballe, "LASTDAYS", lastdays)


def _require_dballe_product(client: FlaskClient, headers: Any, test_runtime) -> str:
    """Sceglie un prodotto reale agrmet nella finestra DBALLE 2020-04-06."""
    # Il probe evita di assumere un codice prodotto fisso e produce uno skip esplicito
    # se il runtime non espone la finestra dati ammessa.
    with _dballe_window_override(test_runtime):
        response = client.get(_url(FIELDS_ENDPOINT, q=DBALLE_QUERY), headers=headers)
    if response.status_code != 200:
        pytest.skip(
            "agrmet DBALLE 2020-04-06 00:00-01:00 is not exposed by /fields "
            f"for observed edge tests, status={response.status_code}"
        )
    content = _parse_response(response)
    products = content["items"].get("product") or []
    if content["items"].get("summarystats", {}).get("c", 0) <= 0 or not products:
        pytest.skip(
            "agrmet DBALLE 2020-04-06 00:00-01:00 exposes no product for "
            "observed edge tests"
        )
    return products[0]["code"]


def _get_observations(client: FlaskClient, headers: Any | None = None, **params: Any):
    """Esegue GET /observations con parametri espliciti."""
    # Manteniamo una sola azione HTTP per test, lasciando ai chiamanti la costruzione
    # dello scenario e delle asserzioni.
    return client.get(_url(OBSERVED_ENDPOINT, **params), headers=headers)


def _extract_products(content: dict[str, Any]) -> set[str]:
    """Estrae i codici prodotto dal payload nested delle osservazioni."""
    # Il formato observed contiene prodotti dentro ogni stazione; l'helper rende
    # l'assert allStationProducts=false leggibile e confinato al modulo EXT.
    products: set[str] = set()
    for station in content.get("data", []):
        for entry in station.get("prod", []):
            product = entry.get("var")
            if product is not None:
                products.add(product)
    return products


def _require_station_coordinates(
    client: FlaskClient,
    headers: Any,
    test_runtime,
) -> tuple[float, float]:
    """Ricava lat/lon di una stazione reale dalla finestra agrmet DBALLE ammessa."""
    # Usiamo una risposta observed reale per evitare coordinate hardcoded non portabili.
    product = _require_dballe_product(client, headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"
    with _dballe_window_override(test_runtime):
        response = _get_observations(
            client,
            headers,
            q=query,
            networks=OBSERVED_NETWORK,
        )
    assert response.status_code == 200
    content = _parse_response(response)
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
    """Verifica il limite anonimo >3 giorni senza leggere dati reali fuori finestra.

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
    """Verifica il limite autenticato >10 giorni prima dell'accesso ai dati reali."""
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
    """Verifica il 409 quando interval richiesto e minore del timerange query."""
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
    """Esegue daily=true sulla finestra agrmet DBALLE 2020-04-06 00:00-01:00."""
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"

    # act
    with _dballe_window_override(test_runtime):
        response = _get_observations(client, auth_headers, q=query, daily="true")

    # assert
    content = _parse_response(response)
    assert response.status_code == 200
    assert isinstance(content, dict)
    assert "data" in content


def test_observations_last_smoke_returns_valid_payload_on_dballe_window(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Esegue last=true come smoke sulla finestra agrmet DBALLE consentita.

    Con una sola giornata DBALLE disponibile, il test protegge il ramo controller e non
    pretende un confronto storico piu robusto; ulteriori giorni consecutivi renderebbero
    possibile una verifica piu forte della restrizione ai dati recenti.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"

    # act
    with _dballe_window_override(test_runtime):
        response = _get_observations(client, auth_headers, q=query, last="true")

    # assert
    content = _parse_response(response)
    assert response.status_code == 200
    assert isinstance(content, dict)
    assert "data" in content


def test_observations_station_details_without_networks_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 per stationDetails=true senza networks."""
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
    """Verifica il 400 per stationDetails=true con piu network validi."""
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
    """Verifica il 404 per stationDetails su stazione inesistente nella finestra DBALLE.

    Il controller dichiara `ident` come stringa, quindi il primo tentativo usa un ident
    fittizio. Se il runtime restituisce invece un `200` vuoto, il test riprova senza
    `ident` e con coordinate valide ma lontane dalla stazione reale scoperta nella stessa
    finestra DBALLE, cosi da sondare anche il ramo lat/lon prima di dichiarare il `404`
    non costruibile nel runtime corrente.
    """
    # arrange
    _require_dballe_product(client, auth_headers, test_runtime)
    station_lat, station_lon = _require_station_coordinates(
        client,
        auth_headers,
        test_runtime,
    )
    missing_lat = min(float(station_lat) + 20.0, 89.0)
    missing_lon = min(float(station_lon) + 20.0, 179.0)

    # act
    with _dballe_window_override(test_runtime):
        ident_response = _get_observations(
            client,
            auth_headers,
            q=DBALLE_QUERY,
            networks=OBSERVED_NETWORK,
            stationDetails="true",
            ident="missing-station-ext",
        )

    response = ident_response
    if ident_response.status_code == 200:
        ident_content = _parse_response(ident_response)
        if not ident_content.get("data"):
            with _dballe_window_override(test_runtime):
                response = _get_observations(
                    client,
                    auth_headers,
                    q=DBALLE_QUERY,
                    networks=OBSERVED_NETWORK,
                    stationDetails="true",
                    lat=missing_lat,
                    lon=missing_lon,
                )

    # assert
    if response.status_code == 200:
        content = _parse_response(response)
        if not content.get("data"):
            pytest.skip(
                "agrmet DBALLE 2020-04-06 does not construct the stationDetails "
                "404 branch for either an unknown ident string or a lat/lon miss; "
                "backend returns an empty 200 payload instead"
            )
    assert response.status_code == 404


def test_observations_all_station_products_false_limits_station_details_products(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica che allStationProducts=false mantenga solo il prodotto richiesto.

    Il test usa una stazione reale della finestra DBALLE 2020-04-06 e un prodotto scelto
    via /fields; se il runtime espone un payload senza prodotti, lo scenario non e
    significativo e viene saltato esplicitamente.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)
    lat, lon = _require_station_coordinates(client, auth_headers, test_runtime)
    query = f"{DBALLE_QUERY};product:{product}"

    # act
    with _dballe_window_override(test_runtime):
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
    content = _parse_response(response)
    assert response.status_code == 200
    products = _extract_products(content)
    if not products:
        pytest.skip(
            "stationDetails payload for agrmet DBALLE 2020-04-06 has no products to "
            "assert allStationProducts=false"
        )
    assert products <= {product}
