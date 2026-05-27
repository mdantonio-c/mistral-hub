"""Helpers that turn raw ``/api/fields`` metadata into test-friendly time values.

Several integration tests need a reliable reference window for a dataset before
they can create requests or schedules. Instead of duplicating the same parsing
logic in every test module, this helper asks ``/api/fields`` for one dataset and
converts the returned summary statistics into Python ``datetime`` objects plus
preformatted strings ready to be reused in API payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient


@dataclass(frozen=True)
class DatasetWindow:
    """Structured view of the time information returned by ``/api/fields``.

    ``ref_from`` and ``ref_to`` are Python datetimes useful for arithmetic in
    tests. ``date_from`` and ``date_to`` are the same boundaries already
    formatted for request bodies. ``ref_run`` preserves the run metadata exactly
    as returned by the API so tests can reuse one valid run filter.
    """

    ref_from: datetime
    ref_to: datetime
    ref_run: list[dict[str, Any]]
    date_from: str  # formatted as "%Y-%m-%dT%H:%M:%S.000Z"
    date_to: str  # formatted as "%Y-%m-%dT%H:%M:%S.000Z"


def fetch_dataset_window(
    client: FlaskClient,
    headers: Any,
    dataset_name: str,
    *,
    tz: Optional[timezone] = timezone.utc,
) -> DatasetWindow:
    """Fetch ``/api/fields`` for one dataset and normalize the result for tests.

    The helper performs three steps that many tests need:

    1. call ``/api/fields`` for the requested dataset,
    2. skip the scenario if that dataset is not exposed in the current runtime,
    3. convert the response into one ``DatasetWindow`` object that is easier to
       reuse in schedule payloads and date comparisons.

    This keeps the calling tests focused on behavior instead of on low-level
    response parsing.
    """
    # Interroghiamo il backend e normalizziamo la risposta in una struttura semplice da
    # usare nelle asserzioni.
    endpoint = f"{API_URI}/fields?datasets={dataset_name}"
    base = BaseTests()
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    r = client.get(endpoint, headers=headers)
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if r.status_code == 404:
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(
            f"Dataset '{dataset_name}' is not available through /api/fields in this environment"
        )
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert r.status_code == 200

    response = base.get_content(r)
    stats_b = response["items"]["summarystats"]["b"]
    stats_e = response["items"]["summarystats"]["e"]
    ref_run = response["items"]["run"]

    ref_from = datetime(
        stats_b[0], stats_b[1], stats_b[2], stats_b[3], stats_b[4], tzinfo=tz
    )
    ref_to = datetime(
        stats_e[0], stats_e[1], stats_e[2], stats_e[3], stats_e[4], tzinfo=tz
    )

    date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return DatasetWindow(
        ref_from=ref_from,
        ref_to=ref_to,
        ref_run=ref_run,
        date_from=date_from,
        date_to=date_to,
    )
