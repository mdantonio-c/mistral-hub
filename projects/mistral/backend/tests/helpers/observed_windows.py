"""Fixed observed-data windows and request helpers shared by /fields and /observations tests.

The EXT suites for ``/fields`` and ``/observations`` rely on the same real runtime
slices: agrmet DBALLE 2020-04-06 00:00-01:00 and agrmet Arkimet 2020-03-31/2020-04-01.
This module keeps those constants, the ``BeDballe.LASTDAYS`` override that makes the
historical DBALLE slice look recent, and the small request/response helpers in one place.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import pytest
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.auth import AuthenticatedTestUser, create_dataset_test_user
from mistral.tests.helpers.datasets import require_dataset
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


FIELDS_ENDPOINT = f"{API_URI}/fields"
OBSERVATIONS_ENDPOINT = f"{API_URI}/observations"

OBSERVED_DATASET_NAME = "agrmet"
OBSERVED_NETWORK = "agrmet"
OBSERVED_LICENSE_GROUP = "CCBY_COMPLIANT"
OBSERVED_MISMATCH_LICENSE_GROUP = "CCBY-SA_COMPLIANT"

OBS_DBALLE_FIRST_DAY = datetime(2020, 4, 6)
OBS_DBALLE_FROM = "2020-04-06 00:00"
OBS_DBALLE_TO = "2020-04-06 01:00"
OBS_ARKIMET_FROM = "2020-03-31 00:00"
OBS_ARKIMET_TO = "2020-04-01 23:59"


def api_url(endpoint: str, **params: Any) -> str:
    """Build an endpoint URL letting urlencode escape `;`, `>=`, `<=` and spaces in q."""
    return f"{endpoint}?{urlencode(params)}"


def parse_response(response) -> Any:
    """Decode a restapi/flask response payload for assertions."""
    return BaseTests().get_content(response)


def lastdays_for_dballe_window(first_dballe_day: datetime) -> int:
    """Return the BeDballe.LASTDAYS value whose cutoff falls the day before the window.

    ``BeDballe.get_db_type`` uses a threshold relative to today, so historical DBALLE
    slices would otherwise be classified as archived.
    """
    last_archived_day = first_dballe_day - timedelta(days=1)
    return (datetime.now() - last_archived_day).days


def dballe_window_override(test_runtime, first_dballe_day: datetime = OBS_DBALLE_FIRST_DAY):
    """Context manager that classifies the given DBALLE day as recent for one test."""
    return test_runtime.override_attr(
        BeDballe,
        "LASTDAYS",
        lastdays_for_dballe_window(first_dballe_day),
    )


def require_observed_dataset_user(
    client: FlaskClient,
    cleanup_registry,
    *,
    allowed_obs_archive: bool = False,
) -> AuthenticatedTestUser:
    """Create a user explicitly granted agrmet, skipping when agrmet is not in the catalog.

    The explicit grant keeps the scenario portable even when the local catalog makes
    agrmet private; ``allowed_obs_archive`` is chosen by the test.
    """
    db = sqlalchemy.get_instance()
    dataset = require_dataset(db, OBSERVED_DATASET_NAME)
    return create_dataset_test_user(
        client,
        cleanup_registry,
        [dataset.id],
        allowed_obs_archive=allowed_obs_archive,
    )


def require_dballe_product(
    client: FlaskClient,
    headers: Any,
    test_runtime,
    query: str,
) -> str:
    """Return the first real product exposed by /fields for a DBALLE window query, or skip.

    ``query`` must target the agrmet DBALLE window and include network and license.
    """
    with dballe_window_override(test_runtime):
        response = client.get(api_url(FIELDS_ENDPOINT, q=query), headers=headers)
    if response.status_code != 200:
        pytest.skip(
            f"agrmet DBALLE {OBS_DBALLE_FROM}-{OBS_DBALLE_TO} is not exposed by "
            f"/fields in this runtime, status={response.status_code}"
        )
    content = parse_response(response)
    summarystats = content["items"].get("summarystats", {})
    products = content["items"].get("product") or []
    if summarystats.get("c", 0) <= 0 or not products:
        pytest.skip(
            f"agrmet DBALLE {OBS_DBALLE_FROM}-{OBS_DBALLE_TO} exposes no products "
            "in this runtime"
        )
    return products[0]["code"]
