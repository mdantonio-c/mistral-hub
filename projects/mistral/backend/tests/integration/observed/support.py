"""Observed-data support helpers local to the observed integration area.

Observed scenarios are more environment-dependent than most other test domains:
they depend on DBALLE availability, archived data windows, networks, products,
and license-group rules. This module centralizes the logic that discovers one
usable observed slice from the current runtime and exposes it in a reusable form
for the actual tests.
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
from mistral.tests.helpers.runtime import TestRuntime
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient
from restapi.utilities.logs import log


@dataclass(frozen=True)
class ObservedQueryParams:
    """Small immutable bundle describing one valid observed query slice.

    These values are exactly what the observed tests need to build requests that
    should succeed: a date window, a network code, and up to two product codes.
    """

    date_from: str
    date_to: str
    network: str
    product_1: str
    product_2: str | None


@dataclass(frozen=True)
class ObservedCase:
    """Complete observed test scenario combining auth, backend type, and query data.

    Tests parameterized over ``dballe``, ``arkimet``, and ``mixed`` receive one of
    these objects so they can focus on API expectations instead of discovery.
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


def _prioritized_observed_datasets(dataset_names: list[str]) -> list[str]:
    """Return observed datasets with the known rich ``agrmet`` runtime first.

    The legacy observed tests naturally discovered ``agrmet`` because they walked
    the available runtime and accepted the first window with useful data. The
    refactored suite keeps that dynamic behavior, but tries ``agrmet`` first so
    environments that carry the same seed data get a stable two-product case.
    """
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    return sorted(
        dataset_names,
        key=lambda dataset_name: (
            PREFERRED_OBSERVED_NETWORK
            not in arki.get_observed_dataset_params(dataset_name),
            dataset_name,
        ),
    )


def _prioritized_networks(dataset_name: str) -> list[str]:
    """Return networks for one observed dataset, preferring ``agrmet`` when present."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    return sorted(
        arki.get_observed_dataset_params(dataset_name),
        key=lambda network: (network != PREFERRED_OBSERVED_NETWORK, network),
    )


def _dballe_network_window(transaction, network: str) -> tuple[datetime, datetime] | None:
    """Return the widest DBALLE window currently present for one observed network.

    The previous refactored discovery used only the latest one-hour slice. That
    made the test sensitive to whichever product happened to be latest. The old
    as-is test instead allowed broader windows, so this helper restores that
    spirit by spanning the complete DBALLE slice available for the network.
    """
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    date_from_dt = None
    date_to_dt = None

    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    for row in transaction.query_data({"rep_memo": network}):
        row_datetime = datetime(
            row["year"],
            row["month"],
            row["day"],
            row["hour"],
            row["min"],
        )
        # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
        # succedere quando lo stato non e quello ideale.
        if date_from_dt is None or row_datetime < date_from_dt:
            date_from_dt = row_datetime
        # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
        # succedere quando lo stato non e quello ideale.
        if date_to_dt is None or row_datetime > date_to_dt:
            date_to_dt = row_datetime

    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if date_from_dt is None or date_to_dt is None:
        # Non c'e un risultato da consegnare al chiamante: il segnale utile e
        # l'effetto gia prodotto o l'assenza esplicita di dati.
        return None

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return date_from_dt, date_to_dt + timedelta(hours=1)


def _summary_datetime(summary_value: list[int]) -> datetime:
    """Convert a DBALLE/Arkimet summary timestamp list into a ``datetime``."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    return datetime(
        summary_value[0],
        summary_value[1],
        summary_value[2],
        summary_value[3],
        summary_value[4],
    )


def _arkimet_dataset_window(dataset_name: str) -> tuple[datetime, datetime] | None:
    """Return the full archived Arkimet summary window for one observed dataset."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    arki_summary = arki.load_summary(datasets=[dataset_name])
    summary_stats = arki_summary["items"]["summarystats"]
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if "b" not in summary_stats or "e" not in summary_stats:
        # Non c'e un risultato da consegnare al chiamante: il segnale utile e
        # l'effetto gia prodotto o l'assenza esplicita di dati.
        return None
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return _summary_datetime(summary_stats["b"]), _summary_datetime(summary_stats["e"])


def _lastdays_override_for_dballe_window(date_from_dt: datetime) -> int:
    """Place the DBALLE/Arkimet cutoff just before the discovered DBALLE slice."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    today = datetime.now()
    last_dballe_date = date_from_dt - timedelta(days=1)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return (today - last_dballe_date).days


def yield_observed_case(
    client: FlaskClient,
    headers: Any,
    test_runtime: TestRuntime,
    db_type: str,
):
    """Yield one reusable observed scenario and apply any required DBALLE override.

    Some observed scenarios need a temporary ``BeDballe.LASTDAYS`` override so the
    API can see the same time window that the discovery step found. This helper
    wraps that override and yields a ready-to-use ``ObservedCase``.
    """
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    params, lastdays_override = discover_observed_params(
        client,
        headers,
        db_type,
        test_runtime=test_runtime,
    )
    runtime_override = nullcontext()
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if lastdays_override is not None:
        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato,
        # cosi il test resta deterministico.
        runtime_override = test_runtime.override_attr(
            BeDballe,
            "LASTDAYS",
            lastdays_override,
        )

    with runtime_override:
        # Cediamo la fixture al test; quando il test termina, il codice sotto il yield
        # eseguira il teardown.
        yield ObservedCase(db_type=db_type, headers=headers, params=params)


def discover_observed_params(
    client: FlaskClient,
    headers: Any,
    db_type: str,
    *,
    test_runtime: TestRuntime | None = None,
) -> tuple[ObservedQueryParams, int | None]:
    """Probe the current runtime until one observed dataset yields usable filters.

    The discovery process walks through candidate observed datasets exposed by the
    runtime and tries to derive one concrete query window that the API can answer
    for the requested backend type:

    - ``dballe`` for recent observed data,
    - ``arkimet`` for archived observed data,
    - ``mixed`` for a dataset that spans both worlds.

    The function returns the discovered query parameters plus any ``LASTDAYS``
    override needed to make DBALLE expose the same recent slice during the test.
    """
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    base = BaseTests()
    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
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

    # Scorriamo gli elementi restituiti dal backend per trovare solo quelli rilevanti
    # per questo scenario.
    for dataset_name in observed_datasets:
        arkimet_window = None
        if db_type in {"arkimet", "mixed"}:
            arkimet_window = _arkimet_dataset_window(dataset_name)

        dballe_windows = {}
        if db_type in {"dballe", "mixed"}:
            # Controlliamo il contratto specifico dello scenario, non soltanto che il
            # codice sia arrivato fin qui senza eccezioni.
            assert db_dballe is not None
            with db_dballe.transaction() as transaction:
                # Scorriamo gli elementi restituiti dal backend per trovare solo quelli
                # rilevanti per questo scenario.
                for network in _prioritized_networks(dataset_name):
                    dballe_window = _dballe_network_window(transaction, network)
                    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa
                    # deve succedere quando lo stato non e quello ideale.
                    if dballe_window is not None:
                        dballe_windows[network] = dballe_window

        # Scorriamo gli elementi restituiti dal backend per trovare solo quelli
        # rilevanti per questo scenario.
        for network in _prioritized_networks(dataset_name):
            date_from_dt = None
            date_to_dt = None
            lastdays_override = None

            if db_type == "dballe":
                dballe_window = dballe_windows.get(network)
                # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
                # succedere quando lo stato non e quello ideale.
                if dballe_window is None:
                    continue
                date_from_dt, date_to_dt = dballe_window
                lastdays_override = _lastdays_override_for_dballe_window(date_from_dt)

            elif db_type == "arkimet":
                # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
                # succedere quando lo stato non e quello ideale.
                if arkimet_window is None:
                    continue
                date_from_dt, date_to_dt = arkimet_window

            else:
                dballe_window = dballe_windows.get(network)
                # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
                # succedere quando lo stato non e quello ideale.
                if dballe_window is None or arkimet_window is None:
                    continue
                date_from_dt = arkimet_window[0]
                date_to_dt = dballe_window[1]
                lastdays_override = _lastdays_override_for_dballe_window(
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
            # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
            # succedere quando lo stato non e quello ideale.
            if test_runtime is not None and lastdays_override is not None:
                # Sostituiamo temporaneamente la dipendenza esterna con un fake
                # controllato, cosi il test resta deterministico.
                runtime_override = test_runtime.override_attr(
                    BeDballe,
                    "LASTDAYS",
                    lastdays_override,
                )

            with runtime_override:
                # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi
                # routing, autorizzazione e serializzazione vengono verificati insieme.
                response = client.get(
                    f"{API_URI}/fields"
                    f"?q={build_reftime_query(params)}"
                    f"&datasets={dataset_name}&SummaryStats=false",
                    headers=headers,
                )

            if response.status_code != 200:
                continue

            response_data = base.get_content(response)
            # Controlliamo il contratto specifico dello scenario, non soltanto che il
            # codice sia arrivato fin qui senza eccezioni.
            assert isinstance(response_data, dict)
            # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
            # succedere quando lo stato non e quello ideale.
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

            # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
            # direttamente nelle asserzioni.
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
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(
            "No usable recent observed dataset is available for dballe in the current runtime"
        )

    if db_type == "arkimet":
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(
            "No usable archived observed dataset is available for arkimet in the current runtime"
        )

    if db_type == "mixed":
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
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
    """Build the semicolon-separated observed query string used by fields and observations."""
    # Componiamo il payload in un solo punto, cosi i test possono concentrarsi sulla
    # regola di business invece che sulla forma JSON.
    bounds: list[str] = []
    if include_from:
        bounds.append(f">={params.date_from}")
    if include_to:
        bounds.append(f"<={params.date_to}")

    query_parts: list[str] = []
    if bounds:
        query_parts.append(f"reftime:{','.join(bounds)}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if product is not None:
        query_parts.append(f"product:{product}")
    query_parts.append("license:CCBY_COMPLIANT")
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
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
    """Assemble an observations endpoint URL from query, network, and spatial options."""
    # Componiamo il payload in un solo punto, cosi i test possono concentrarsi sulla
    # regola di business invece che sulla forma JSON.
    params = [f"q={query}"]

    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if networks is not None:
        params.append(f"networks={networks}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if lonmin is not None:
        params.append(f"lonmin={lonmin}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if lonmax is not None:
        params.append(f"lonmax={lonmax}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if latmin is not None:
        params.append(f"latmin={latmin}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if latmax is not None:
        params.append(f"latmax={latmax}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if lat is not None:
        params.append(f"lat={lat}")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if lon is not None:
        params.append(f"lon={lon}")
    if only_stations:
        params.append("onlyStations=true")
    if station_details:
        params.append("stationDetails=true")

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return f"{API_URI}/observations?{'&'.join(params)}"


def fetch_observations(
    client: FlaskClient,
    headers: Any,
    endpoint: str,
) -> tuple[Any, Any]:
    """Call one observations URL and return both the response object and parsed payload."""
    # Interroghiamo il backend e normalizziamo la risposta in una struttura semplice da
    # usare nelle asserzioni.
    response = client.get(endpoint, headers=headers)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return response, BaseTests().get_content(response)


def extract_products(content: dict[str, Any]) -> set[str]:
    """Collect all product codes present in the nested observations response payload."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    products = set()
    # Scorriamo gli elementi restituiti dal backend per trovare solo quelli rilevanti
    # per questo scenario.
    for station in content.get("data", []):
        # Scorriamo gli elementi restituiti dal backend per trovare solo quelli
        # rilevanti per questo scenario.
        for entry in station.get("prod", []):
            product = entry.get("var")
            # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
            # succedere quando lo stato non e quello ideale.
            if product is not None:
                products.add(product)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return products


def extract_station_coordinates(content: dict[str, Any]) -> tuple[float, float]:
    """Read latitude and longitude from the first station returned by observations."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    station = content["data"][0]["stat"]
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return station["lat"], station["lon"]


def fetch_station_sample(client: FlaskClient, observed_case: ObservedCase) -> tuple[float, float]:
    """Fetch one successful observations response and extract a known station location from it."""
    # Interroghiamo il backend e normalizziamo la risposta in una struttura semplice da
    # usare nelle asserzioni.
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
    )
    response, content = fetch_observations(client, observed_case.headers, endpoint)
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert isinstance(content, dict)
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return extract_station_coordinates(content)


def require_secondary_product(observed_case: ObservedCase) -> None:
    """Skip tests that specifically require two observed products when only one is exposed."""
    # Entriamo nel blocco operativo dell'helper osservazioni, mantenendo esplicito quale
    # stato viene letto o prodotto.
    if observed_case.params.product_2 is None:
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(
            f"Observed case '{observed_case.db_type}' exposes only one product in this environment"
        )