# EXTENSION TRACEABILITY - Prompt 02, contratto POST /data lato validazioni HTTP.
# Origine: questo modulo aggiunge solo casi *_EXT nel dominio integration/data e lascia
# invariati baseline, fixture globali e file legacy gia presenti.
# Ambito: copre dataset inesistente, formati misti, gruppi licenza diversi,
# output_format non valido a livello schema, output_format incompatibile con grib,
# postprocessor non autorizzato e only_reliable non supportato.
# Finestra dati: nessun dataset runtime reale viene usato come oracolo; tutti gli
# scenari sono guidati da record DB sintetici e fake sul modulo endpoint.
# Runtime fake: il modulo mistral.endpoints.data viene monkeypatchato solo dove il ramo
# sotto test richiede formato o categoria dataset, evitando chiamate Arkimet reali.
# Cleanup: dataset e utenti temporanei vengono registrati nel cleanup_registry; i rami
# coperti qui devono fallire prima di creare request persistite.
# Baseline non toccata: il modulo amplia il dominio senza modificare test_data_endpoint_auth.py.

"""Test di validazione per POST /data con dataset sintetici e fake strettamente locali."""

from __future__ import annotations

import mistral.endpoints.data as data_endpoint_module
import pytest
from mistral.models.sqlalchemy import DatasetCategories
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.integration.data.support_EXT import (
    build_data_payload,
    create_data_endpoint_user,
    create_synthetic_dataset,
    latest_request_for_user,
    patch_data_endpoint_runtime,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]

DATA_ENDPOINT = f"{API_URI}/data"


def test_post_data_returns_404_for_missing_dataset(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un dataset non autorizzato o inesistente produca 404 immediato.

    Il ramo protetto qui e il controllo di esistenza/visibilita ricavato da
    SqlApiDbManager.get_datasets: nessun fake Arkimet serve, perche il backend deve
    fermarsi prima di interrogare formato, categoria o queue.
    """
    # arrange
    # Creiamo solo un utente autenticato senza dataset sintetici collegati, cosi il nome
    # richiesto non puo comparire nel catalogo autorizzato restituito dal repository.
    db = sqlalchemy.get_instance()
    user = create_data_endpoint_user(client, cleanup_registry)
    payload = build_data_payload(["missing_dataset_ext"], request_name="missing-dataset")

    # act
    # La chiamata usa il percorso HTTP reale e lascia che sia l'endpoint a rilevare il
    # dataset assente prima di qualsiasi altra validazione applicativa.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Il contratto richiede 404 e l'assenza di request create, perche il ramo fallisce
    # prima di create_request_record.
    assert response.status_code == 404
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_returns_400_for_mixed_dataset_formats(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 400 per set di dataset con formati incompatibili tra loro.

    Il catalogo sintetico rende i dataset visibili all'utente, mentre il fake Arkimet
    restituisce `None` da get_datasets_format per rappresentare il caso di formati misti.
    Questo esercita il ramo BadRequest senza dipendere da cataloghi Arkimet reali.
    """
    # arrange
    # Creiamo due dataset distinti e autorizziamo l'utente a vederli entrambi, poi
    # forziamo il responso di Arkimet sul formato a `None` come segnatura del caso misto.
    db = sqlalchemy.get_instance()
    first_dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    second_dataset = create_synthetic_dataset(
        cleanup_registry=cleanup_registry,
        db=db,
        fileformat="bufr",
    )
    user = create_data_endpoint_user(
        client,
        cleanup_registry,
        dataset_ids=[first_dataset.id, second_dataset.id],
    )
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_format=None,
        dataset_category="FOR",
    )
    payload = build_data_payload(
        [first_dataset.arkimet_id, second_dataset.arkimet_id],
        request_name="mixed-formats",
    )

    # act
    # La submit deve attraversare il controllo catalogo e arrestarsi esattamente sul ramo
    # di formato misto esposto dal fake Arkimet.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # L'endpoint deve rifiutare il set con 400 senza creare effetti persistenti.
    assert response.status_code == 400
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_returns_400_for_different_license_groups(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 400 quando i dataset appartengono a gruppi licenza differenti.

    Ogni dataset sintetico viene creato con il proprio gruppo licenza dedicato. In questo
    modo il test usa il repository reale per il controllo licenze, limitandosi a fakeare
    il formato dataset per superare il ramo precedente.
    """
    # arrange
    # Prepariamo due dataset pubblici ma con gruppi licenza diversi, cosi il repository
    # reale puo restituire None da get_license_group senza dipendere da dati runtime.
    db = sqlalchemy.get_instance()
    first_dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    second_dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(
        client,
        cleanup_registry,
        dataset_ids=[first_dataset.id, second_dataset.id],
    )
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_format="grib",
        dataset_category="FOR",
    )
    payload = build_data_payload(
        [first_dataset.arkimet_id, second_dataset.arkimet_id],
        request_name="different-license-groups",
    )

    # act
    # Usiamo il flusso endpoint reale fino al controllo del gruppo licenza, che in questo
    # scenario deve essere il punto esatto di fallimento.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Il contratto richiede 400 e nessuna request persistita quando i gruppi licenza non
    # coincidono tra i dataset richiesti.
    assert response.status_code == 400
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_returns_400_for_invalid_output_format_schema(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il 400 di schema quando output_format non appartiene ai valori ammessi.

    Questo caso protegge la validazione Marshmallow dichiarata in DataExtraction prima che
    l'endpoint tocchi Arkimet o il repository applicativo. Per questo non servono fake di
    runtime oltre a un dataset sintetico valido nel payload.
    """
    # arrange
    # Prepariamo un dataset valido e un utente autenticato, poi inviamo un valore di
    # output_format non ammesso dalla schema validation (`csv`).
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    payload = build_data_payload(
        [dataset.arkimet_id],
        request_name="invalid-output-format-schema",
        output_format="csv",
    )

    # act
    # La chiamata passa dall'autenticazione ma deve fermarsi nella validazione schema.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Verifichiamo sia il codice HTTP sia l'esistenza di un payload errore che menzioni
    # output_format, mantenendo la verifica robusta rispetto al wrapper restapi.
    content = BaseTests().get_content(response)
    assert response.status_code == 400
    assert "output_format" in str(content)
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_returns_400_when_output_format_is_incompatible_with_grib(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 400 applicativo per output_format valido ma non compatibile con grib.

    Il valore `json` e ammesso dallo schema, quindi il test deve arrivare fino alla
    logica endpoint che vieta output_format espliciti per dataset forecast grib quando non
    e presente lo spare point interpolation.
    """
    # arrange
    # Prepariamo un dataset grib sintetico e fakeiamo formato/categoria per evitare che
    # il backend dipenda da metadata esterni legati al nome Arkimet del dataset.
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_format="grib",
        dataset_category="FOR",
    )
    payload = build_data_payload(
        [dataset.arkimet_id],
        request_name="incompatible-output-format",
        output_format="json",
    )

    # act
    # La submit attraversa schema e catalogo ma deve fermarsi sul controllo di
    # compatibilita applicativa fra formato dataset e formato di output richiesto.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Il backend deve respingere la richiesta con 400 e senza lasciare Request persistite.
    assert response.status_code == 400
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_returns_401_for_unauthorized_postprocessor_usage(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 401 quando l'utente prova a usare postprocessor senza permesso.

    Il payload usa un postprocessor semplice e valido a livello schema, cosi il test
    raggiunge il controllo repo.get_user_permissions e protegge il ramo Unauthorized
    senza dipendere da tool post-processing reali.
    """
    # arrange
    # L'utente viene creato senza allowed_postprocessing, mentre il dataset e reso valido
    # da fake Arkimet locali per superare i controlli precedenti al ramo autorizzativo.
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_format="grib",
        dataset_category="FOR",
    )
    payload = build_data_payload(
        [dataset.arkimet_id],
        request_name="unauthorized-postprocessor",
        postprocessors=[
            {
                "processor_type": "derived_variables",
                "variables": ["B12194"],
            }
        ],
    )

    # act
    # La submit usa un postprocessor sintatticamente valido per arrivare al solo controllo
    # di autorizzazione applicativa lato endpoint.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Il backend deve restituire 401 e fermarsi prima della creazione di qualsiasi request.
    assert response.status_code == 401
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_returns_400_when_only_reliable_is_not_supported(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 400 quando only_reliable viene chiesto su dataset non OBS.

    Il ramo da proteggere e puramente applicativo: l'opzione e lecita solo per OBS o per
    il dataset speciale multim-forecast. Un dataset forecast sintetico consente quindi di
    verificare il rifiuto senza dipendenze da dati meteo reali.
    """
    # arrange
    # Prepariamo un dataset forecast sintetico, lo rendiamo valido via fake Arkimet e
    # attiviamo only_reliable nel payload per colpire esattamente il controllo endpoint.
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(
        cleanup_registry=cleanup_registry,
        db=db,
        category=DatasetCategories.FOR,
        fileformat="grib",
    )
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_format="grib",
        dataset_category="FOR",
    )
    payload = build_data_payload(
        [dataset.arkimet_id],
        request_name="only-reliable-unsupported",
        only_reliable=True,
    )

    # act
    # La chiamata usa il percorso reale dell'endpoint e deve fallire esattamente sul ramo
    # che limita only_reliable ai dataset supportati.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Il backend deve rifiutare il parametro con 400 senza creare una request persistita.
    assert response.status_code == 400
    assert latest_request_for_user(db, user.user_id) is None