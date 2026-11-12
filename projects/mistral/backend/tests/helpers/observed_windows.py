"""Finestre di dati osservati e helper condivisi dai test di /fields e /observations.

I test di ``/fields`` e ``/observations`` si basano sulle stesse slice reali del
runtime: agrmet DBALLE 2020-04-06 00:00-01:00 e agrmet Arkimet 2020-03-31/2020-04-01.
Questo modulo tiene in un unico punto queste costanti, l'override di
``BeDballe.LASTDAYS`` che fa sembrare recente la slice DBALLE storica e i piccoli
helper per richieste e risposte.
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
    """Costruisce l'URL dell'endpoint con i parametri di query.

    ``urlencode`` fa l'escape di `;`, `>=`, `<=` e degli spazi nel parametro q.
    """
    return f"{endpoint}?{urlencode(params)}"


def parse_response(response) -> Any:
    """Decodifica il payload di una risposta restapi/Flask per le asserzioni."""
    return BaseTests().get_content(response)


def lastdays_for_dballe_window(first_dballe_day: datetime) -> int:
    """Calcola il BeDballe.LASTDAYS che pone il cutoff al giorno prima della finestra.

    ``BeDballe.get_db_type`` usa una soglia relativa a oggi, quindi altrimenti le
    slice DBALLE storiche verrebbero classificate come archiviate.
    """
    last_archived_day = first_dballe_day - timedelta(days=1)
    return (datetime.now() - last_archived_day).days


def dballe_window_override(test_runtime, first_dballe_day: datetime = OBS_DBALLE_FIRST_DAY):
    """Context manager che fa considerare recente il giorno DBALLE indicato.

    Vale solo dentro il blocco ``with`` del test: sovrascrive temporaneamente
    ``BeDballe.LASTDAYS`` tramite ``test_runtime.override_attr``.
    """
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
    """Crea un utente con grant esplicito su agrmet, o salta se agrmet manca.

    Il grant esplicito mantiene lo scenario portabile anche quando il catalogo locale
    rende agrmet privato; ``allowed_obs_archive`` viene scelto dal test.
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
    """Restituisce il primo prodotto reale esposto da /fields nella finestra DBALLE.

    Se ``GET /api/fields`` non risponde 200 o non espone prodotti, salta il test.
    ``query`` deve puntare alla finestra DBALLE di agrmet e includere rete e licenza.
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
