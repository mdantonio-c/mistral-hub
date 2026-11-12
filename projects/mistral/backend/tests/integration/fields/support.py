# EXTENSION TRACEABILITY - Prompt 03, dominio integration/fields.
# Origine: questo modulo supporta solo i nuovi test di estensione per l'endpoint /fields e
# nasce per non modificare la suite baseline osservazioni gia rifattorizzata.
# Ambito: centralizza URL, finestre dati ammesse, utenti temporanei, dataset sintetici
# e cleanup per coprire il ramo OBS/map, il ramo OBS/dataset e il ramo FOR/Arkimet.
# Finestra dati: OBS usa solo agrmet DBALLE 2020-04-06 00:00-01:00 e agrmet Arkimet
# 2020-03-31/2020-04-01; FOR usa solo lm5 2021-10-19 o lm2.2 2019-09-10.
# Runtime fake: i casi happy path interrogano il runtime reale sulle finestre sopra;
# i casi di validazione multi-dataset usano dataset DB sintetici e monkeypatch mirati
# solo per arrivare al ramo controller senza richiedere dati forecast aggiuntivi.
# Cleanup: ogni utente temporaneo, dataset sintetico, gruppo licenza e licenza creati
# dal supporto viene registrato nel cleanup_registry; i record reali del catalogo, come
# agrmet, vengono solo letti e mai modificati.
# Baseline non toccata: non vengono creati conftest.py, fixture globali o helper fuori
# dal dominio fields; la logica nuova resta confinata in file di estensione.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from mistral.models.sqlalchemy import DatasetCategories
from mistral.tests.helpers.auth import create_dataset_test_user
from mistral.tests.helpers.datasets import delete_test_dataset_bundle
from mistral.tests.helpers.observed_windows import (
    FIELDS_ENDPOINT,
    OBS_ARKIMET_FROM,
    OBS_ARKIMET_TO,
    OBS_DBALLE_FROM,
    OBS_DBALLE_TO,
    OBSERVED_LICENSE_GROUP,
    OBSERVED_NETWORK,
    api_url,
    parse_response,
)
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient


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
    """Costruisce un URL /fields con query string codificata da urlencode."""
    return api_url(FIELDS_ENDPOINT, **params)


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

    dataset_id = dataset.id
    license_id = license_entry.id
    group_license_id = group_license.id
    cleanup_registry.add(
        lambda: delete_test_dataset_bundle(
            db,
            dataset_id=dataset_id,
            license_id=license_id,
            group_license_id=group_license_id,
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
        user = create_dataset_test_user(client, cleanup_registry, [dataset.id])
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
