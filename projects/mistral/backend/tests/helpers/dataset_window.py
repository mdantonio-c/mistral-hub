"""Helper che converte i metadati di ``/api/fields`` in valori temporali per i test.

Diversi test di integrazione hanno bisogno di una finestra temporale di riferimento
affidabile per un dataset prima di poter creare richieste o schedule. Invece di
duplicare la stessa logica di parsing in ogni modulo di test, questo helper chiede
``/api/fields`` per un dataset e converte le statistiche riassuntive restituite in
oggetti ``datetime`` Python, piu stringhe gia formattate da riusare nei payload API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient


@dataclass(frozen=True)
class DatasetWindow:
    """Vista strutturata delle informazioni temporali restituite da ``/api/fields``.

    ``ref_from`` e ``ref_to`` sono datetime Python, comodi per fare calcoli nei
    test. ``date_from`` e ``date_to`` sono gli stessi estremi gia formattati per il
    body delle richieste. ``ref_run`` conserva i metadati del run esattamente come
    restituiti dall'API, cosi i test possono riusare un filtro run valido.
    """

    ref_from: datetime
    ref_to: datetime
    ref_run: list[dict[str, Any]]
    date_from: str  # nel formato "%Y-%m-%dT%H:%M:%S.000Z"
    date_to: str  # nel formato "%Y-%m-%dT%H:%M:%S.000Z"


def fetch_dataset_window(
    client: FlaskClient,
    headers: Any,
    dataset_name: str,
    *,
    tz: Optional[timezone] = timezone.utc,
) -> DatasetWindow:
    """Chiama ``GET /api/fields`` per un dataset e normalizza il risultato per i test.

    L'helper esegue tre passi che servono a molti test:

    1. chiama ``/api/fields`` (endpoints/fields.py) per il dataset richiesto,
    2. salta lo scenario se quel dataset non e esposto nel runtime corrente,
    3. converte la risposta in un oggetto ``DatasetWindow``, piu facile da
       riusare nei payload delle schedule e nei confronti tra date.

    Cosi i test chiamanti restano concentrati sul comportamento invece che sul
    parsing a basso livello della risposta.
    """
    endpoint = f"{API_URI}/fields?datasets={dataset_name}"
    base = BaseTests()
    r = client.get(endpoint, headers=headers)
    if r.status_code == 404:
        pytest.skip(
            f"Dataset '{dataset_name}' is not available through /api/fields in this environment"
        )
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

    return DatasetWindow(
        ref_from=ref_from,
        ref_to=ref_to,
        ref_run=ref_run,
        date_from=date_from,
        date_to=date_to,
    )
