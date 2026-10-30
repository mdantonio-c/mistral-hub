# EXTENSION TRACEABILITY - Prompt 03, dominio integration/fields.
# Origine: questo modulo supporta solo i nuovi test *_EXT.py per l'endpoint /fields e
# nasce per non modificare la suite baseline osservazioni gia rifattorizzata.
# Ambito: centralizza URL, finestre dati ammesse, utenti temporanei, dataset sintetici
# e cleanup per coprire il ramo OBS/map, il ramo OBS/dataset e il ramo FOR/Arkimet.
# Finestra dati: OBS usa solo agrmet DBALLE 2020-04-06 00:00-01:00 e agrmet Arkimet
# 2020-03-31/2020-04-01; FOR usa solo lm5 2021-10-19 o lm2.2 2019-09-10.
# Runtime fake: i casi happy path interrogano il runtime reale sulle finestre sopra;
# i casi di validazione multi-dataset usano dataset DB sintetici e monkeypatch mirati
# solo per arrivare al ramo controller senza richiedere dati forecast aggiuntivi.
# Cleanup: ogni utente temporaneo, dataset sintetico, gruppo licenza e licenza creati
# dal supporto viene registrato nel cleanup_registry; i record reali letti non vengono
# modificati salvo nei test che ripristinano esplicitamente la licenza originale.
# Baseline non toccata: non vengono creati conftest.py, fixture globali o helper fuori
# dal dominio fields; la logica nuova resta confinata in file *_EXT.py.

from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from mistral.models.sqlalchemy import DatasetCategories
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


FIELDS_ENDPOINT = f"{API_URI}/fields"
OBSERVED_DATASET_NAME = "agrmet"
OBSERVED_NETWORK = "agrmet"
OBSERVED_LICENSE_GROUP = "CCBY_COMPLIANT"
OBSERVED_MISMATCH_LICENSE_GROUP = "CCBY-SA_COMPLIANT"

OBS_DBALLE_FROM = "2020-04-06 00:00"
OBS_DBALLE_TO = "2020-04-06 01:00"
OBS_ARKIMET_FROM = "2020-03-31 00:00"
OBS_ARKIMET_TO = "2020-04-01 23:59"

OBS_DBALLE_QUERY = (
    f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};"
    f"network:{OBSERVED_NETWORK};license:{OBSERVED_LICENSE_GROUP}"
)
OBS_DBALLE_QUERY_WITHOUT_LICENSE = (
    f"reftime:>={OBS_DBALLE_FROM},<={OBS_DBALLE_TO};network:{OBSERVED_NETWORK}"
)
OBS_ARCHIVE_QUERY = (
    f"reftime:>={OBS_ARKIMET_FROM},<={OBS_ARKIMET_TO};"
    f"network:{OBSERVED_NETWORK};license:{OBSERVED_LICENSE_GROUP}"
)

FORECAST_WINDOWS = (
    ("lm5", "2021-10-19 00:00", "2021-10-19 23:59"),
    ("lm2.2", "2019-09-10 00:00", "2019-09-10 23:59"),
)


@dataclass(frozen=True)
class FieldsSyntheticDataset:
    """Record minimo per dataset sintetici usati dai soli rami di validazione.

    I test /fields devono talvolta costruire set di dataset con categorie o gruppi
    licenza incompatibili. Farlo con record sintetici evita di cambiare cataloghi reali
    e rende esplicito quali identificatori servono all'URL e quali al cleanup.
    """

    id: int
    arkimet_id: str
    name: str
    category: DatasetCategories
    group_license_id: int
    license_id: int


@dataclass(frozen=True)
class ForecastFieldsCase:
    """Scenario forecast reale autorizzato su una sola finestra ammessa.

    Il caso contiene il dataset scelto fra lm5 e lm2.2, la query Arkimet limitata alla
    data consentita e gli header di un utente temporaneo esplicitamente autorizzato,
    cosi il test non dipende dalle differenze locale/CI sulle restrizioni dataset.
    """

    dataset_name: str
    query: str
    headers: Any
    content: dict[str, Any]


def fields_url(**params: Any) -> str:
    """Costruisce un URL /fields con query string codificata in modo leggibile.

    Il carattere `;` e gli operatori `>=`/`<=` sono significativi per il parser del
    backend, quindi lasciamo a urlencode il compito di trasportarli senza ambiguita.
    """
    # Componiamo l'URL in un solo punto per non duplicare dettagli di escaping nei test.
    return f"{FIELDS_ENDPOINT}?{urlencode(params)}"


def parse_response(response) -> Any:
    """Normalizza il payload restapi/flask in una struttura Python per le asserzioni."""
    # Il wrapper BaseTests conosce gia la forma delle risposte restapi usate dalla suite.
    return BaseTests().get_content(response)


def observed_dballe_override(test_runtime):
    """Forza DBALLE a classificare il 2020-04-06 come finestra recente del test.

    La fixture runtime contiene davvero i dati agrmet del 2020-04-06, ma il classifier
    BeDballe.get_db_type usa una soglia mobile basata sulla data corrente. Questo
    override riproduce la strategia gia usata dalla suite observed esistente e resta
    confinato al singolo test tramite il context manager del TestRuntime.
    """
    # Calcoliamo LASTDAYS facendo cadere il cutoff il giorno prima della finestra DBALLE
    # ammessa, in modo che 2020-04-06 00:00 sia trattato come dato recente.
    first_dballe_day = datetime(2020, 4, 6)
    last_archived_day = first_dballe_day - timedelta(days=1)
    lastdays = (datetime.now() - last_archived_day).days
    return test_runtime.override_attr(BeDballe, "LASTDAYS", lastdays)


def require_dataset(db, dataset_name: str):
    """Restituisce un dataset reale o salta con una motivazione legata alla finestra.

    Il prompt 03 consente solo agrmet, lm5 e lm2.2 per i rami runtime-realistic; quando
    uno di questi cataloghi manca, lo skip deve citarlo esplicitamente invece di cercare
    date o dataset alternativi.
    """
    # Leggiamo il catalogo reale per verificare che il runtime esponga il dataset chiave.
    dataset = db.Datasets.query.filter_by(arkimet_id=dataset_name).first()
    if dataset is None:
        pytest.skip(
            f"Dataset '{dataset_name}' is not available for Prompt 03 allowed windows"
        )
    return dataset


def create_fields_user(
    client: FlaskClient,
    cleanup_registry,
    dataset_ids: list[int] | None = None,
    *,
    allowed_obs_archive: bool = False,
    open_dataset: bool = True,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo con autorizzazioni dichiarate dal test.

    Per i forecast lm5/lm2.2 questo helper associa esplicitamente il dataset all'utente,
    cosi il caso positivo resta portabile tra il locale con restrizioni e la CI senza
    restrizioni. Per gli archive observed, il flag allowed_obs_archive viene scelto dal
    test per colpire il ramo 401 o il ramo positivo.
    """
    # Costruiamo il profilo tramite l'API admin della suite, mantenendo il cleanup nel
    # registry per eliminare utente e cartella output anche in caso di failure.
    permissions: dict[str, Any] = {
        "open_dataset": open_dataset,
        "allowed_obs_archive": allowed_obs_archive,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids or []]),
    }
    base = BaseTests()
    user = create_authenticated_test_user(base, client, permissions)
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


def create_fields_synthetic_dataset(
    db,
    cleanup_registry,
    *,
    arkimet_id: str | None = None,
    category: DatasetCategories = DatasetCategories.FOR,
    fileformat: str = "grib",
    group_name: str | None = None,
    is_public: bool = True,
    dballe_dsn: str | None = None,
) -> FieldsSyntheticDataset:
    """Crea un dataset sintetico minimo e registra cleanup relazionale completo.

    I rami multi-dataset di /fields falliscono prima del caricamento Arkimet reale. Il
    fake corretto, quindi, e un catalogo SQL minimo piu eventuale monkeypatch del solo
    calcolo categoria: dati meteo aggiuntivi non darebbero copertura migliore.
    """
    # Recuperiamo un'attribution reale quando esiste; se il runtime e minimale, ne
    # creiamo una temporanea e la marchiamo per cleanup.
    attribution = db.Attribution.query.first()
    created_attribution_id = None
    if attribution is None:
        attribution = db.Attribution(
            name=f"fields_ext_attr_{uuid4().hex[:8]}",
            descr="Synthetic attribution for fields EXT tests",
            url="https://example.invalid/fields-ext-attribution",
        )
        db.session.add(attribution)
        db.session.flush()
        created_attribution_id = attribution.id

    token = uuid4().hex[:10]
    dataset_name = arkimet_id or f"fields_ext_{token}"
    group_license = db.GroupLicense(
        name=group_name or f"fields_ext_group_{token}",
        descr=f"Synthetic license group for {dataset_name}",
        is_public=is_public,
        dballe_dsn=dballe_dsn,
    )
    db.session.add(group_license)
    db.session.flush()

    license_entry = db.License(
        name=f"fields_ext_license_{token}",
        descr=f"Synthetic license for {dataset_name}",
        group_license_id=group_license.id,
    )
    db.session.add(license_entry)
    db.session.flush()

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Synthetic dataset for fields EXT {dataset_name}",
        source="arkimet",
        license_id=license_entry.id,
        attribution_id=attribution.id,
        category=category,
        fileformat=fileformat,
        bounding="POLYGON ((10 44, 11 44, 11 45, 10 45, 10 44))",
        supports_variable_browsing=True,
    )
    db.session.add(dataset)
    db.session.commit()

    cleanup_registry.add(
        lambda: delete_fields_dataset_bundle(
            db,
            dataset_id=dataset.id,
            license_id=license_entry.id,
            group_license_id=group_license.id,
            attribution_id=created_attribution_id,
        )
    )
    return FieldsSyntheticDataset(
        id=dataset.id,
        arkimet_id=dataset.arkimet_id,
        name=dataset.name,
        category=category,
        group_license_id=group_license.id,
        license_id=license_entry.id,
    )


def get_or_create_multim_forecast_dataset(db, cleanup_registry) -> FieldsSyntheticDataset:
    """Garantisce un record DB `multim-forecast` per il ramo multi-dataset 400.

    L'endpoint verifica la presenza di `multim-forecast` nella lista dataset prima di
    chiamare Arkimet. Se il catalogo runtime non lo contiene, un record sintetico e
    sufficiente e viene rimosso in teardown.
    """
    # Usiamo il record reale se esiste, altrimenti prepariamo un sostituto DB-only.
    existing = db.Datasets.query.filter_by(arkimet_id="multim-forecast").first()
    if existing is not None:
        return FieldsSyntheticDataset(
            id=existing.id,
            arkimet_id=existing.arkimet_id,
            name=existing.name,
            category=existing.category,
            group_license_id=existing.dataset_license.group_license_id,
            license_id=existing.license_id,
        )
    return create_fields_synthetic_dataset(
        db,
        cleanup_registry,
        arkimet_id="multim-forecast",
        category=DatasetCategories.OBS,
        fileformat="bufr",
        dballe_dsn="DBALLE",
    )


def delete_fields_dataset_bundle(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_license_id: int,
    attribution_id: int | None,
) -> None:
    """Rimuove dataset sintetico, link utenti, licenza e gruppo licenza se presenti."""
    # Il cleanup e difensivo: se un test fallisce prima del commit completo, rimuove
    # solo cio che esiste ancora senza mascherare l'errore originale.
    dataset = db.Datasets.query.get(dataset_id)
    if dataset is not None:
        for user in dataset.users.all():
            dataset.users.remove(user)
        db.session.delete(dataset)
        db.session.flush()

    license_entry = db.License.query.get(license_id)
    if license_entry is not None:
        db.session.delete(license_entry)
        db.session.flush()

    group_license = db.GroupLicense.query.get(group_license_id)
    if group_license is not None:
        db.session.delete(group_license)
        db.session.flush()

    if attribution_id is not None:
        attribution = db.Attribution.query.get(attribution_id)
        if attribution is not None:
            db.session.delete(attribution)

    db.session.commit()


def create_private_observed_dataset_for_all_available_products(db, cleanup_registry) -> str:
    """Crea un gruppo licenza OBS privato per verificare il filtro autorizzativo.

    Il test allAvailableProducts usa dati reali agrmet per la query, ma ha bisogno di un
    gruppo privato non autorizzato come controllo negativo. Un dataset OBS sintetico e
    sufficiente per far comparire il gruppo fra quelli potenzialmente rilevanti.
    """
    # Il dballe_dsn punta a DBALLE solo per rendere il gruppo semanticamente OBS; il test
    # non interroga mai dati di questo dataset sintetico.
    dataset = create_fields_synthetic_dataset(
        db,
        cleanup_registry,
        category=DatasetCategories.OBS,
        fileformat="bufr",
        is_public=False,
        dballe_dsn="DBALLE",
    )
    group_license = db.GroupLicense.query.get(dataset.group_license_id)
    assert group_license is not None
    return group_license.name


def require_observed_dataset_user(
    client: FlaskClient,
    cleanup_registry,
    *,
    allowed_obs_archive: bool = False,
) -> AuthenticatedTestUser:
    """Crea un utente associato al dataset reale agrmet quando il runtime lo espone."""
    # Associamo agrmet in modo esplicito anche se oggi e pubblico: se in futuro il
    # runtime locale cambia restrizioni, il test resta portabile.
    db = sqlalchemy.get_instance()
    dataset = require_dataset(db, OBSERVED_DATASET_NAME)
    return create_fields_user(
        client,
        cleanup_registry,
        [dataset.id],
        allowed_obs_archive=allowed_obs_archive,
    )


def require_forecast_fields_case(
    client: FlaskClient,
    cleanup_registry,
) -> ForecastFieldsCase:
    """Trova lm5 o lm2.2 con dati nella sola finestra forecast ammessa.

    Il helper prova prima lm5 2021-10-19 e poi lm2.2 2019-09-10. Ogni probe usa un
    utente temporaneo autorizzato al dataset specifico, quindi l'esito non dipende dal
    fatto che la CI abbia restrizioni meno forti del locale dell'utente.
    """
    # Cerchiamo un solo caso forecast reale, mantenendo le finestre del prompt come
    # unica sorgente di verita e saltando esplicitamente se nessuna espone dati.
    db = sqlalchemy.get_instance()
    for dataset_name, date_from, date_to in FORECAST_WINDOWS:
        dataset = db.Datasets.query.filter_by(arkimet_id=dataset_name).first()
        if dataset is None:
            continue
        user = create_fields_user(client, cleanup_registry, [dataset.id])
        query = f"reftime:>={date_from},<={date_to}"
        response = client.get(
            fields_url(datasets=dataset_name, q=query),
            headers=user.headers,
        )
        if response.status_code == 404:
            continue
        assert response.status_code == 200
        content = parse_response(response)
        summarystats = content["items"]["summarystats"]
        if summarystats.get("c", 0) <= 0:
            continue
        return ForecastFieldsCase(
            dataset_name=dataset_name,
            query=query,
            headers=user.headers,
            content=content,
        )

    pytest.skip(
        "No forecast data found for Prompt 03 allowed windows: "
        "lm5 2021-10-19 or lm2.2 2019-09-10"
    )


def temporarily_make_observed_dataset_private(db, cleanup_registry) -> str:
    """Rende temporaneamente agrmet privato e registra il ripristino della licenza.

    Serve a costruire un 401 portabile per i controlli network authorization: non si
    usa la configurazione locale come oracolo, ma si crea il diniego in modo controllato
    e si ripristina sempre la licenza reale in teardown.
    """
    # Salviamo la licenza originale prima di creare il gruppo privato, cosi il cleanup
    # puo riportare il catalogo runtime allo stato iniziale.
    dataset = require_dataset(db, OBSERVED_DATASET_NAME)
    original_license_id = dataset.license_id
    private_group_name = f"fields_ext_private_{uuid4().hex[:10]}"
    private_group = db.GroupLicense(
        name=private_group_name,
        descr="Private group for fields EXT authorization denial",
        is_public=False,
        dballe_dsn="DBALLE",
    )
    db.session.add(private_group)
    db.session.flush()
    private_license = db.License(
        name=f"{private_group_name}_license",
        descr="Private license for fields EXT authorization denial",
        group_license_id=private_group.id,
    )
    db.session.add(private_license)
    db.session.flush()
    dataset.license_id = private_license.id
    db.session.add(dataset)
    db.session.commit()

    def _restore_observed_dataset_license() -> None:
        # Ripristiniamo prima il dataset reale, poi rimuoviamo i record sintetici.
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

    cleanup_registry.add(_restore_observed_dataset_license)
    return private_group_name


def null_runtime_context():
    """Restituisce un context manager nullo per simmetria con override runtime opzionali."""
    # Piccolo helper per mantenere leggibili i test che scelgono a runtime se patchare.
    return nullcontext()
