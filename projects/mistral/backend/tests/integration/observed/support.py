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
    """Convert a DBALLE/Arkimet summary timestamp list into a ``datetime``."""
    return datetime(
        summary_value[0],
        summary_value[1],
        summary_value[2],
        summary_value[3],
        summary_value[4],
    )


def _arkimet_dataset_window(dataset_name: str) -> tuple[datetime, datetime] | None:
    """Return the full archived Arkimet summary window for one observed dataset."""
    arki_summary = arki.load_summary(datasets=[dataset_name])
    summary_stats = arki_summary["items"]["summarystats"]
    if "b" not in summary_stats or "e" not in summary_stats:
        return None
    return _summary_datetime(summary_stats["b"]), _summary_datetime(summary_stats["e"])


def _lastdays_override_for_dballe_window(date_from_dt: datetime) -> int:
    """Place the DBALLE/Arkimet cutoff just before the discovered DBALLE slice."""
    today = datetime.now()
    last_dballe_date = date_from_dt - timedelta(days=1)
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
                lastdays_override = _lastdays_override_for_dballe_window(date_from_dt)

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
    """Build the semicolon-separated observed query string used by fields and observations."""
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
    """Assemble an observations endpoint URL from query, network, and spatial options."""
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
    """Call one observations URL and return both the response object and parsed payload."""
    response = client.get(endpoint, headers=headers)
    return response, BaseTests().get_content(response)


def extract_products(content: dict[str, Any]) -> set[str]:
    """Collect all product codes present in the nested observations response payload."""
    products = set()
    for station in content.get("data", []):
        for entry in station.get("prod", []):
            product = entry.get("var")
            if product is not None:
                products.add(product)
    return products


def extract_station_coordinates(content: dict[str, Any]) -> tuple[float, float]:
    """Read latitude and longitude from the first station returned by observations."""
    station = content["data"][0]["stat"]
    return station["lat"], station["lon"]


def fetch_station_sample(client: FlaskClient, observed_case: ObservedCase) -> tuple[float, float]:
    """Fetch one successful observations response and extract a known station location from it."""
    endpoint = build_observations_endpoint(
        query=build_reftime_query(observed_case.params),
        networks=observed_case.params.network,
    )
    response, content = fetch_observations(client, observed_case.headers, endpoint)
    assert response.status_code == 200
    assert isinstance(content, dict)
    return extract_station_coordinates(content)


def require_secondary_product(observed_case: ObservedCase) -> None:
    """Skip tests that specifically require two observed products when only one is exposed."""
    if observed_case.params.product_2 is None:
        pytest.skip(
            f"Observed case '{observed_case.db_type}' exposes only one product in this environment"
        )