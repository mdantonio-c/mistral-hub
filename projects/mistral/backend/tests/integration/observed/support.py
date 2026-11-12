"""Helper di supporto per i test di integrazione sui dati osservati.

Gli scenari osservati dipendono dall'ambiente piu degli altri domini di test:
servono DBALLE disponibile, finestre di dati archiviati, network, prodotti e
regole sui gruppi di licenza. Questo modulo raccoglie la logica che scopre nel
runtime corrente una porzione di dati osservati utilizzabile e la espone in forma
riusabile ai test.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import dballe
import pytest
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.observed_windows import lastdays_for_dballe_window
from mistral.tests.helpers.runtime import TestRuntime
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient
from restapi.utilities.logs import log


@dataclass(frozen=True)
class ObservedQueryParams:
    """Insieme immutabile di parametri che descrive una query osservata valida.

    Contiene cio che serve ai test per costruire richieste che devono riuscire:
    una finestra temporale, un codice network e fino a due codici prodotto.
    """

    date_from: str
    date_to: str
    network: str
    product_1: str
    product_2: str | None


@dataclass(frozen=True)
class ObservedCase:
    """Scenario osservato completo: header di autenticazione, tipo di backend e query.

    I test parametrizzati su ``dballe``, ``arkimet`` e ``mixed`` ricevono uno di
    questi oggetti e possono concentrarsi sulle attese dell'API invece che sulla
    scoperta dei dati.
    """

    db_type: str
    headers: Any
    params: ObservedQueryParams


ALL_CASES = [
    pytest.param("dballe_observed_case", id="dballe"),
    pytest.param("arkimet_observed_case", id="arkimet"),
    pytest.param("mixed_observed_case", id="mixed"),
]

RECENT_CASES = [
    pytest.param("dballe_observed_case", id="dballe"),
    pytest.param("mixed_observed_case", id="mixed"),
]

ARCHIVE_CASES = [
    pytest.param("arkimet_observed_case", id="arkimet"),
    pytest.param("mixed_observed_case", id="mixed"),
]

PREFERRED_OBSERVED_NETWORK = "agrmet"

ITALY_BOUNDING_BOX = {
    "lonmin": 6.7499,
    "lonmax": 18.4802,
    "latmin": 36.6199,
    "latmax": 47.1153,
}


def _prioritized_observed_datasets(dataset_names: list[str]) -> list[str]:
    """Restituisce i dataset osservati mettendo per primi quelli con network ``agrmet``.

    Usa BeArkimet.get_observed_dataset_params. La scoperta resta dinamica, ma prova
    prima ``agrmet`` cosi gli ambienti con gli stessi dati di seed ottengono un caso
    stabile con due prodotti.
    """
    return sorted(
        dataset_names,
        key=lambda dataset_name: (
            PREFERRED_OBSERVED_NETWORK
            not in arki.get_observed_dataset_params(dataset_name),
            dataset_name,
        ),
    )


def _prioritized_networks(dataset_name: str) -> list[str]:
    """Restituisce i network di un dataset osservato, con ``agrmet`` per primo.

    Usa BeArkimet.get_observed_dataset_params.
    """
    return sorted(
        arki.get_observed_dataset_params(dataset_name),
        key=lambda network: (network != PREFERRED_OBSERVED_NETWORK, network),
    )


def _dballe_network_window(transaction, network: str) -> tuple[datetime, datetime] | None:
    """Restituisce la finestra DBALLE piu ampia presente per un network osservato.

    Legge direttamente il database DBALLE e copre tutti i dati del network invece
    della sola ultima ora, cosi il test non dipende da quale prodotto e arrivato
    per ultimo. Restituisce None se il network non ha dati.
    """
    date_from_dt = None
    date_to_dt = None

    for row in transaction.query_data({"rep_memo": network}):
        row_datetime = datetime(
            row["year"],
            row["month"],
            row["day"],
            row["hour"],
            row["min"],
        )
        if date_from_dt is None or row_datetime < date_from_dt:
            date_from_dt = row_datetime
        if date_to_dt is None or row_datetime > date_to_dt:
            date_to_dt = row_datetime

    if date_from_dt is None or date_to_dt is None:
        return None

    return date_from_dt, date_to_dt + timedelta(hours=1)


def _summary_datetime(summary_value: list[int]) -> datetime:
    """Converte un timestamp di summary DBALLE/Arkimet (lista di interi) in datetime."""
    return datetime(
        summary_value[0],
        summary_value[1],
        summary_value[2],
        summary_value[3],
        summary_value[4],
    )


def _arkimet_dataset_window(dataset_name: str) -> tuple[datetime, datetime] | None:
    """Restituisce l'intera finestra archiviata Arkimet di un dataset osservato.

    Usa BeArkimet.load_summary; restituisce None se il summary non ha inizio e fine.
    """
    arki_summary = arki.load_summary(datasets=[dataset_name])
    summary_stats = arki_summary["items"]["summarystats"]
    if "b" not in summary_stats or "e" not in summary_stats:
        return None
    return _summary_datetime(summary_stats["b"]), _summary_datetime(summary_stats["e"])


def yield_observed_case(
    client: FlaskClient,
    headers: Any,
    test_runtime: TestRuntime,
    db_type: str,
):
    """Produce uno scenario osservato riusabile, con l'eventuale override DBALLE.

    Alcuni scenari richiedono di cambiare temporaneamente ``BeDballe.LASTDAYS``
    perche l'API veda la stessa finestra temporale trovata nella fase di scoperta.
    Questo helper applica l'override e cede un ``ObservedCase`` pronto all'uso.
    """
    params, lastdays_override = discover_observed_params(
        client,
        headers,
        db_type,
        test_runtime=test_runtime,
    )
    runtime_override = nullcontext()
    if lastdays_override is not None:
        runtime_override = test_runtime.override_attr(
            BeDballe,
            "LASTDAYS",
            lastdays_override,
        )

    with runtime_override:
        yield ObservedCase(db_type=db_type, headers=headers, params=params)


def discover_observed_params(
    client: FlaskClient,
    headers: Any,
    db_type: str,
    *,
    test_runtime: TestRuntime | None = None,
) -> tuple[ObservedQueryParams, int | None]:
    """Esplora il runtime finche un dataset osservato non fornisce filtri utilizzabili.

    La scoperta scorre i dataset osservati disponibili e cerca una finestra di query
    concreta a cui l'API GET /api/fields sappia rispondere per il tipo di backend
    richiesto:

    - ``dballe`` per i dati osservati recenti,
    - ``arkimet`` per i dati osservati archiviati,
    - ``mixed`` per un dataset che copre entrambi.

    Restituisce i parametri di query trovati e l'eventuale override di ``LASTDAYS``
    necessario perche DBALLE esponga la stessa finestra recente durante il test.
    Se nessun dataset e utilizzabile, il test viene saltato con ``pytest.skip``.
    """
    base = BaseTests()
    db = sqlalchemy.get_instance()
    observed_datasets = _prioritized_observed_datasets(arki.get_obs_datasets(None, None))

    db_dballe = None
    if db_type in {"dballe", "mixed"}:
        db_dballe = dballe.DB.connect(
            "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                engine=db.variables.get("dbtype"),
                user=db.variables.get("user"),
                pw=db.variables.get("password"),
                host=db.variables.get("host"),
                port=db.variables.get("port"),
            )
        )

    for dataset_name in observed_datasets:
        arkimet_window = None
        if db_type in {"arkimet", "mixed"}:
            arkimet_window = _arkimet_dataset_window(dataset_name)

        dballe_windows = {}
        if db_type in {"dballe", "mixed"}:
            assert db_dballe is not None
            with db_dballe.transaction() as transaction:
                for network in _prioritized_networks(dataset_name):
                    dballe_window = _dballe_network_window(transaction, network)
                    if dballe_window is not None:
                        dballe_windows[network] = dballe_window

        for network in _prioritized_networks(dataset_name):
            date_from_dt = None
            date_to_dt = None
            lastdays_override = None

            if db_type == "dballe":
                dballe_window = dballe_windows.get(network)
                if dballe_window is None:
                    continue
                date_from_dt, date_to_dt = dballe_window
                lastdays_override = lastdays_for_dballe_window(date_from_dt)

            elif db_type == "arkimet":
                if arkimet_window is None:
                    continue
                date_from_dt, date_to_dt = arkimet_window

            else:
                dballe_window = dballe_windows.get(network)
                if dballe_window is None or arkimet_window is None:
                    continue
                date_from_dt = arkimet_window[0]
                date_to_dt = dballe_window[1]
                lastdays_override = lastdays_for_dballe_window(
                    dballe_window[0]
                )

            params = ObservedQueryParams(
                date_from=date_from_dt.strftime("%Y-%m-%d %H:%M"),
                date_to=date_to_dt.strftime("%Y-%m-%d %H:%M"),
                network="",
                product_1="",
                product_2=None,
            )
            runtime_override = nullcontext()
            # L'override di LASTDAYS vale anche per la chiamata di prova, cosi
            # /fields vede la stessa finestra che vedra il test.
            if test_runtime is not None and lastdays_override is not None:
                runtime_override = test_runtime.override_attr(
                    BeDballe,
                    "LASTDAYS",
                    lastdays_override,
                )

            with runtime_override:
                response = client.get(
                    f"{API_URI}/fields"
                    f"?q={build_reftime_query(params)}"
                    f"&datasets={dataset_name}&SummaryStats=false",
                    headers=headers,
                )

            if response.status_code != 200:
                continue

            response_data = base.get_content(response)
            assert isinstance(response_data, dict)
            if not response_data["items"]:
                continue

            log.debug(
                "api fields db type {} dataset {} network {} : response data: {}",
                db_type,
                dataset_name,
                network,
                response_data,
            )

            products = response_data["items"]["product"]
            if len(products) < 2:
                log.debug(
                    "Skipping observed dataset {} network {} for {} because it exposes {} products",
                    dataset_name,
                    network,
                    db_type,
                    len(products),
                )
                continue

            return (
                ObservedQueryParams(
                    date_from=params.date_from,
                    date_to=params.date_to,
                    network=response_data["items"]["network"][0]["code"],
                    product_1=products[0]["code"],
                    product_2=products[1]["code"],
                ),
                lastdays_override,
            )

    if db_type == "dballe":
        pytest.skip(
            "No usable recent observed dataset is available for dballe in the current runtime"
        )

    if db_type == "arkimet":
        pytest.skip(
            "No usable archived observed dataset is available for arkimet in the current runtime"
        )

    if db_type == "mixed":
        pytest.skip(
            "No observed dataset spans both arkimet and dballe in the current runtime"
        )

    pytest.fail("No observed dataset returned usable fields for the selected db type")


def build_reftime_query(
    params: ObservedQueryParams,
    *,
    include_from: bool = True,
    include_to: bool = True,
    product: str | None = None,
) -> str:
    """Costruisce la stringa ``q`` (parti separate da ``;``) per le query osservate.

    La stessa stringa e usata da GET /api/fields e GET /api/observations; aggiunge
    sempre ``license:CCBY_COMPLIANT``.
    """
    bounds: list[str] = []
    if include_from:
        bounds.append(f">={params.date_from}")
    if include_to:
        bounds.append(f"<={params.date_to}")

    query_parts: list[str] = []
    if bounds:
        query_parts.append(f"reftime:{','.join(bounds)}")
    if product is not None:
        query_parts.append(f"product:{product}")
    query_parts.append("license:CCBY_COMPLIANT")
    return ";".join(query_parts)


def build_observations_endpoint(
    *,
    query: str,
    networks: str | None = None,
    lonmin: float | None = None,
    lonmax: float | None = None,
    latmin: float | None = None,
    latmax: float | None = None,
    lat: float | None = None,
    lon: float | None = None,
    only_stations: bool = False,
    station_details: bool = False,
) -> str:
    """Compone l'URL di GET /api/observations da query, network e opzioni spaziali."""
    params = [f"q={query}"]

    if networks is not None:
        params.append(f"networks={networks}")
    if lonmin is not None:
        params.append(f"lonmin={lonmin}")
    if lonmax is not None:
        params.append(f"lonmax={lonmax}")
    if latmin is not None:
        params.append(f"latmin={latmin}")
    if latmax is not None:
        params.append(f"latmax={latmax}")
    if lat is not None:
        params.append(f"lat={lat}")
    if lon is not None:
        params.append(f"lon={lon}")
    if only_stations:
        params.append("onlyStations=true")
    if station_details:
        params.append("stationDetails=true")

    return f"{API_URI}/observations?{'&'.join(params)}"


def fetch_observations(
    client: FlaskClient,
    headers: Any,
    endpoint: str,
) -> tuple[Any, Any]:
    """Chiama un URL di GET /api/observations e restituisce risposta e payload letto."""
    response = client.get(endpoint, headers=headers)
    return response, BaseTests().get_content(response)


def extract_products(content: dict[str, Any]) -> set[str]:
    """Raccoglie i codici prodotto presenti nel payload di GET /api/observations.

    I prodotti si trovano nel campo ``var`` di ogni elemento ``data[].prod[]``.
    """
    products = set()
    for station in content.get("data", []):
        for entry in station.get("prod", []):
            product = entry.get("var")
            if product is not None:
                products.add(product)
    return products


def extract_station_coordinates(content: dict[str, Any]) -> tuple[float, float]:
    """Legge latitudine e longitudine della prima stazione di GET /api/observations."""
    station = content["data"][0]["stat"]
    return station["lat"], station["lon"]


def fetch_station_sample(client: FlaskClient, observed_case: ObservedCase) -> tuple[float, float]:
    """Ottiene da GET /api/observations la posizione di una stazione reale.

    Esegue una query valida per lo scenario, controlla che risponda 200 e
    restituisce latitudine e longitudine della prima stazione.
    """
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
    )
    response, content = fetch_observations(client, observed_case.headers, endpoint)
    assert response.status_code == 200
    assert isinstance(content, dict)
    return extract_station_coordinates(content)


def require_secondary_product(observed_case: ObservedCase) -> None:
    """Salta il test se lo scenario osservato espone un solo prodotto invece di due."""
    if observed_case.params.product_2 is None:
        pytest.skip(
            f"Observed case '{observed_case.db_type}' exposes only one product in this environment"
        )