# EXTENSION TRACEABILITY - Prompt 03, dominio integration/observed POST download.
# Origine: questo modulo aggiunge copertura a MapsObservations.post senza modificare i
# test GET baseline in test_observations_filters.py e test_observations_station_details.py.
# Ambito: copre download JSON/BUFR, validazioni schema/controller, mismatch licenza,
# network inesistente/non autorizzato, singleStation e archive authorization.
# Finestra dati: i success path usano solo agrmet DBALLE 2020-04-06 00:00-01:00; i
# rami archived usano solo agrmet Arkimet 2020-03-31/2020-04-01. Le date fuori da
# queste finestre non sono usate come oracolo dati reali.
# Runtime fake: nessun fake per i download positivi; BeDballe.LASTDAYS e temporaneamente
# patchato solo per classificare la finestra DBALLE storica come recente nel runtime di
# test, seguendo il pattern observed gia presente.
# Cleanup: gli utenti temporanei e il dataset privato sintetico vengono registrati nel
# cleanup_registry; il catalogo reale (agrmet compreso) viene solo letto e non vengono
# creati file persistenti dalla suite.
# Baseline non toccata: tutti gli helper nuovi sono locali al file e nessun conftest.py
# o support.py legacy viene modificato.

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from mistral.tests.helpers.auth import create_dataset_test_user
from mistral.tests.helpers.datasets import create_private_test_network
from mistral.tests.helpers.observed_windows import (
    OBS_ARKIMET_FROM,
    OBS_ARKIMET_TO,
    OBS_DBALLE_FROM,
    OBS_DBALLE_TO,
    OBSERVATIONS_ENDPOINT,
    OBSERVED_LICENSE_GROUP,
    OBSERVED_MISMATCH_LICENSE_GROUP,
    OBSERVED_NETWORK,
    api_url,
    dballe_window_override,
    require_dballe_product,
    require_observed_dataset_user,
)
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]

DBALLE_QUERY = (
    f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};license:{OBSERVED_LICENSE_GROUP}"
)
ARCHIVE_QUERY = (
    f"reftime:>={OBS_ARKIMET_FROM},<={OBS_ARKIMET_TO};"
    f"license:{OBSERVED_LICENSE_GROUP}"
)


def _require_dballe_product(client: FlaskClient, headers: Any, test_runtime) -> str:
    """Ricava via /fields un prodotto agrmet reale della finestra DBALLE 2020-04-06."""
    return require_dballe_product(
        client,
        headers,
        test_runtime,
        f"{DBALLE_QUERY};network:{OBSERVED_NETWORK}",
    )


def _download_query(product: str | None = None, *, license_group: str = OBSERVED_LICENSE_GROUP) -> str:
    """Costruisce la q del POST download sulla finestra DBALLE consentita."""
    # Il prodotto viene inserito solo dopo il probe /fields, cosi il test resta aderente
    # ai dati reali presenti nella finestra agrmet 2020-04-06.
    query = f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};license:{license_group}"
    if product is not None:
        query = f"{query};product:{product}"
    return query


def _post_observations(client: FlaskClient, headers: Any | None = None, **params: Any):
    """Esegue POST /observations con parametri query, come fa il controller reale."""
    # MapsObservations.post legge tutto dalla query string, non dal body JSON.
    return client.post(api_url(OBSERVATIONS_ENDPOINT, **params), headers=headers)


def test_observed_post_download_json_returns_stream_for_dballe_window(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il download JSON su agrmet DBALLE 2020-04-06 00:00-01:00.

    Il test usa prima /fields per scegliere un prodotto reale della finestra consentita,
    poi attraversa MapsObservations.post e controlla il mime type JSON dello stream.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)

    # act
    with dballe_window_override(test_runtime):
        response = _post_observations(
            client,
            auth_headers,
            q=_download_query(product),
            networks=OBSERVED_NETWORK,
            output_format="JSON",
        )

    # assert
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.data
    # Il downloader DBALLE emette newline-delimited JSON: ogni riga e un documento
    # valido, ma lo stream completo non e un singolo array JSON.
    decoded_rows = [
        json.loads(row)
        for row in response.data.decode("utf-8").splitlines()
        if row.strip()
    ]
    assert decoded_rows


def test_observed_post_download_bufr_returns_octet_stream_for_dballe_window(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il download BUFR su agrmet DBALLE 2020-04-06 00:00-01:00.

    La stessa finestra del caso JSON viene usata per coprire il secondo formato ammesso
    dallo schema ObservationsDownloader senza duplicare logica di discovery.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)

    # act
    with dballe_window_override(test_runtime):
        response = _post_observations(
            client,
            auth_headers,
            q=_download_query(product),
            networks=OBSERVED_NETWORK,
            output_format="BUFR",
        )

    # assert
    assert response.status_code == 200
    # verifica che la response sia in formato octet-stream ovvero un flusso di byte generico
    assert response.mimetype == "application/octet-stream"
    assert response.data


def test_observed_post_reliability_check_smoke_uses_dballe_window(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Esegue uno smoke positivo reliabilityCheck=true sulla finestra DBALLE ammessa.

    Il contratto qui e che il flag attraversi il controller e il download senza errore;
    il contenuto QC dipende dagli attributi presenti nei dati agrmet 2020-04-06.
    """
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)

    # act
    with dballe_window_override(test_runtime):
        response = _post_observations(
            client,
            auth_headers,
            q=_download_query(product),
            networks=OBSERVED_NETWORK,
            output_format="JSON",
            reliabilityCheck="true",
        )

    # assert
    assert response.status_code == 200
    assert response.mimetype == "application/json"


def test_observed_post_invalid_output_format_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 schema per output_format non ammesso prima del runtime DBALLE."""
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=_download_query(product),
        networks=OBSERVED_NETWORK,
        output_format="CSV",
    )

    # assert
    assert response.status_code == 400


def test_observed_post_incomplete_bbox_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 controller per bounding box incompleta su query valida."""
    # arrange
    product = _require_dballe_product(client, auth_headers, test_runtime)

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=_download_query(product),
        networks=OBSERVED_NETWORK,
        output_format="JSON",
        lonmin=10.0,
    )

    # assert
    assert response.status_code == 400


def test_observed_post_missing_license_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 quando q non contiene license, senza interrogare dati reali."""
    # arrange
    query_without_license = f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO}"

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=query_without_license,
        networks=OBSERVED_NETWORK,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 400


def test_observed_post_unknown_license_group_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 per gruppo licenza inesistente nella finestra DBALLE ammessa."""
    # arrange
    query = _download_query(license_group=f"missing_license_{uuid4().hex}")

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=query,
        networks=OBSERVED_NETWORK,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 400


def test_observed_post_mismatch_network_license_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 quando agrmet viene richiesto con gruppo licenza non coerente."""
    # arrange
    query = _download_query(license_group=OBSERVED_MISMATCH_LICENSE_GROUP)

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=query,
        networks=OBSERVED_NETWORK,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 400


def test_observed_post_unknown_network_returns_not_found(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 404 per network non presente nella configurazione Arkimet."""
    # arrange
    missing_network = f"missing_network_{uuid4().hex}"

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=DBALLE_QUERY,
        networks=missing_network,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 404


def test_observed_post_private_network_returns_unauthorized_without_local_oracle(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Costruisce un 401 portabile con una rete privata sintetica.

    Il diniego non dipende dallo stato locale del dataset e non modifica agrmet: il test
    crea un dataset privato sintetico raggiungibile da una rete sintetica e usa un
    utente senza grant specifico.
    """
    # arrange
    db = sqlalchemy.get_instance()
    private_network = create_private_test_network(
        db,
        cleanup_registry,
        monkeypatch,
        prefix="observed_ext_private",
    )
    # Nessun grant dataset: associare il dataset privato renderebbe positivo lo scenario.
    user = create_dataset_test_user(client, cleanup_registry)

    # act
    response = _post_observations(
        client,
        user.headers,
        q=DBALLE_QUERY,
        networks=private_network,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 401


def test_observed_post_single_station_without_networks_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 quando singleStation=true non dichiara networks."""
    # arrange
    query = DBALLE_QUERY

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=query,
        output_format="JSON",
        singleStation="true",
    )

    # assert
    assert response.status_code == 400


def test_observed_post_single_station_with_multiple_networks_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 quando singleStation riceve piu network, anche se validi."""
    # arrange
    duplicate_valid_networks = f"{OBSERVED_NETWORK} or {OBSERVED_NETWORK}"

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=DBALLE_QUERY,
        networks=duplicate_valid_networks,
        output_format="JSON",
        singleStation="true",
        lat=44.0,
        lon=11.0,
    )

    # assert
    assert response.status_code == 400


def test_observed_post_single_station_without_station_identity_returns_bad_request(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 400 quando singleStation non riceve coordinate ne ident."""
    # arrange
    query = DBALLE_QUERY

    # act
    response = _post_observations(
        client,
        auth_headers,
        q=query,
        networks=OBSERVED_NETWORK,
        output_format="JSON",
        singleStation="true",
    )

    # assert
    assert response.status_code == 400


def test_observed_post_archived_window_rejects_anonymous_user(
    client: FlaskClient,
) -> None:
    """Verifica il 401 anonimo su agrmet Arkimet 2020-03-31/2020-04-01."""
    # arrange
    query = ARCHIVE_QUERY

    # act
    response = _post_observations(
        client,
        None,
        q=query,
        networks=OBSERVED_NETWORK,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 401


def test_observed_post_archived_window_rejects_user_without_archive_permission(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il 401 archive per utente senza allowed_obs_archive su finestra ammessa."""
    # arrange
    user = require_observed_dataset_user(client, cleanup_registry, allowed_obs_archive=False)

    # act
    response = _post_observations(
        client,
        user.headers,
        q=ARCHIVE_QUERY,
        networks=OBSERVED_NETWORK,
        output_format="JSON",
    )

    # assert
    assert response.status_code == 401
