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
# Cleanup: gli utenti temporanei e le modifiche controllate alla licenza agrmet vengono
# registrati nel cleanup_registry; non vengono creati file persistenti dalla suite.
# Baseline non toccata: tutti gli helper nuovi sono locali al file e nessun conftest.py
# o support.py legacy viene modificato.

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.auth import (
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]

OBSERVED_ENDPOINT = f"{API_URI}/observations"
FIELDS_ENDPOINT = f"{API_URI}/fields"
OBSERVED_DATASET_NAME = "agrmet"
OBSERVED_NETWORK = "agrmet"
OBSERVED_LICENSE_GROUP = "CCBY_COMPLIANT"
OBSERVED_MISMATCH_LICENSE_GROUP = "CCBY-SA_COMPLIANT"
OBS_DBALLE_FROM = "2020-04-06 00:00"
OBS_DBALLE_TO = "2020-04-06 01:00"
OBS_ARKIMET_FROM = "2020-03-31 00:00"
OBS_ARKIMET_TO = "2020-04-01 23:59"

DBALLE_QUERY = (
    f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};license:{OBSERVED_LICENSE_GROUP}"
)
ARCHIVE_QUERY = (
    f"reftime:>={OBS_ARKIMET_FROM},<={OBS_ARKIMET_TO};"
    f"license:{OBSERVED_LICENSE_GROUP}"
)


def _url(endpoint: str, **params: Any) -> str:
    """Compone URL observed/fields preservando q, operatori reftime e booleani."""
    # Centralizziamo urlencode per evitare query string ambigue con `;`, `>=` e spazi.
    return f"{endpoint}?{urlencode(params)}"


def _parse_response(response) -> Any:
    """Converte una risposta restapi in payload Python quando non e uno stream file."""
    # BaseTests e lo stesso helper usato dai test baseline per leggere risposte JSON.
    return BaseTests().get_content(response)


def _dballe_window_override(test_runtime):
    """Forza BeDballe.get_db_type a trattare il 2020-04-06 come DBALLE recente.

    I dati reali rimangono quelli del runtime; l'override modifica solo la soglia mobile
    basata sulla data corrente, altrimenti una suite eseguita nel 2026 classificherebbe
    la finestra consentita come archivio.
    """
    # Posizioniamo il cutoff il giorno prima di agrmet 2020-04-06, come fa il discovery
    # observed esistente quando trova finestre DBALLE storiche.
    first_dballe_day = datetime(2020, 4, 6)
    last_archived_day = first_dballe_day - timedelta(days=1)
    lastdays = (datetime.now() - last_archived_day).days
    return test_runtime.override_attr(BeDballe, "LASTDAYS", lastdays)


def _require_agrmet_dataset(db):
    """Verifica che il catalogo reale esponga agrmet per le date consentite."""
    # Il prompt 03 non consente fallback ad altri dataset observed: se agrmet manca,
    # lo scenario non e verificabile nel runtime corrente.
    dataset = db.Datasets.query.filter_by(arkimet_id=OBSERVED_DATASET_NAME).first()
    if dataset is None:
        pytest.skip(
            "Dataset agrmet is not available for Prompt 03 observed windows: "
            "DBALLE 2020-04-06 and Arkimet 2020-03-31/2020-04-01"
        )
    return dataset


def _create_observed_user(
    client: FlaskClient,
    cleanup_registry,
    *,
    allowed_obs_archive: bool = False,
):
    """Crea un utente temporaneo associato ad agrmet e con archive flag controllato."""
    # L'associazione esplicita ad agrmet rende il test stabile anche se il catalogo
    # locale rende il dataset privato, mentre allowed_obs_archive resta scelto dal test.
    db = sqlalchemy.get_instance()
    dataset = _require_agrmet_dataset(db)
    base = BaseTests()
    user = create_authenticated_test_user(
        base,
        client,
        {
            "open_dataset": True,
            "allowed_obs_archive": allowed_obs_archive,
            "datasets": json.dumps([str(dataset.id)]),
        },
    )
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


def _create_observed_user_without_dataset_grant(
    client: FlaskClient,
    cleanup_registry,
):
    """Crea un utente temporaneo senza grant agrmet per i dinieghi controllati.

    Questo helper serve ai test che rendono agrmet temporaneamente privato: associare il
    dataset all'utente trasformerebbe lo scenario in positivo e nasconderebbe il ramo 401.
    """
    # Manteniamo open_dataset=True per non cambiare altri aspetti del profilo; il diniego
    # deve dipendere solo dall'assenza del grant esplicito al dataset privato agrmet.
    base = BaseTests()
    user = create_authenticated_test_user(
        base,
        client,
        {
            "open_dataset": True,
            "allowed_obs_archive": False,
            "datasets": json.dumps([]),
        },
    )
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


def _require_dballe_product(client: FlaskClient, headers: Any, test_runtime) -> str:
    """Ricava un prodotto agrmet disponibile nella finestra DBALLE 2020-04-06.

    Il download positivo deve usare dati reali a costo zero; questo probe su /fields
    evita di inventare un codice prodotto e produce uno skip esplicito se la finestra
    ammessa non e inizializzata nel runtime.
    """
    # Interroghiamo /fields nella stessa finestra DBALLE che usera il POST download.
    query = f"{DBALLE_QUERY};network:{OBSERVED_NETWORK}"
    with _dballe_window_override(test_runtime):
        response = client.get(_url(FIELDS_ENDPOINT, q=query), headers=headers)
    if response.status_code != 200:
        pytest.skip(
            "agrmet DBALLE 2020-04-06 00:00-01:00 is not exposed by /fields "
            f"in this runtime, status={response.status_code}"
        )
    content = _parse_response(response)
    summarystats = content["items"].get("summarystats", {})
    products = content["items"].get("product") or []
    if summarystats.get("c", 0) <= 0 or not products:
        pytest.skip(
            "agrmet DBALLE 2020-04-06 00:00-01:00 exposes no products for "
            "Prompt 03 observed download tests"
        )
    return products[0]["code"]


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
    return client.post(_url(OBSERVED_ENDPOINT, **params), headers=headers)


def _temporarily_make_agrmet_private(db, cleanup_registry) -> None:
    """Costruisce un diniego controllato per il ramo network non autorizzato.

    Invece di dipendere da una restrizione locale, il test sposta temporaneamente agrmet
    su un gruppo privato e ripristina la licenza originale in cleanup.
    """
    # Salviamo la licenza reale prima di creare gruppo/licenza privati temporanei.
    dataset = _require_agrmet_dataset(db)
    original_license_id = dataset.license_id
    group_name = f"observed_ext_private_{uuid4().hex[:10]}"
    private_group = db.GroupLicense(
        name=group_name,
        descr="Private group for observed POST EXT authorization denial",
        is_public=False,
        dballe_dsn="DBALLE",
    )
    db.session.add(private_group)
    db.session.flush()
    private_license = db.License(
        name=f"{group_name}_license",
        descr="Private license for observed POST EXT authorization denial",
        group_license_id=private_group.id,
    )
    db.session.add(private_license)
    db.session.flush()
    dataset.license_id = private_license.id
    db.session.add(dataset)
    db.session.commit()

    def _restore_license() -> None:
        # Ripristiniamo agrmet prima di cancellare i record sintetici, cosi il catalogo
        # reale torna consistente anche se l'asserzione del test fallisce.
        current_dataset = db.Datasets.query.get(dataset.id)
        if current_dataset is not None:
            current_dataset.license_id = original_license_id
            db.session.add(current_dataset)
            db.session.flush()
        current_license = db.License.query.get(private_license.id)
        if current_license is not None:
            db.session.delete(current_license)
            db.session.flush()
        current_group = db.GroupLicense.query.get(private_group.id)
        if current_group is not None:
            db.session.delete(current_group)
        db.session.commit()

    cleanup_registry.add(_restore_license)


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
    with _dballe_window_override(test_runtime):
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
    with _dballe_window_override(test_runtime):
        response = _post_observations(
            client,
            auth_headers,
            q=_download_query(product),
            networks=OBSERVED_NETWORK,
            output_format="BUFR",
        )

    # assert
    assert response.status_code == 200
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
    with _dballe_window_override(test_runtime):
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
) -> None:
    """Costruisce un 401 portabile spostando temporaneamente agrmet su licenza privata.

    Il diniego non dipende dallo stato locale del dataset: il test crea la restrizione,
    usa un utente senza grant specifico e lascia al cleanup il ripristino della licenza.
    """
    # arrange
    db = sqlalchemy.get_instance()
    _temporarily_make_agrmet_private(db, cleanup_registry)
    user = _create_observed_user_without_dataset_grant(client, cleanup_registry)

    # act
    response = _post_observations(
        client,
        user.headers,
        q=DBALLE_QUERY,
        networks=OBSERVED_NETWORK,
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
    user = _create_observed_user(client, cleanup_registry, allowed_obs_archive=False)

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
