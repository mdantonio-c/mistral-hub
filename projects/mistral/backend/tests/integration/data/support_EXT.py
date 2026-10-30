# EXTENSION TRACEABILITY - Prompt 02, dominio integration/data.
# Origine: questo modulo e stato introdotto solo per i nuovi test *_EXT del contratto
# HTTP di POST /data e GET /data/<filename>; non modifica il test legacy
# test_data_endpoint_auth.py e non sposta fixture in conftest.py.
# Ambito: prepara utenti temporanei, dataset sintetici, request/fileoutput sintetici e
# fake locali per Celery/RabbitMQ, cosi i test restano confinati al backend di test e
# non avviano worker reali o estrazioni meteorologiche pesanti.
# Finestra dati: non usa finestre meteo reali; le date nei payload sono sintetiche e
# servono soltanto a esercitare la validazione schema e la queue_sorting deterministica.
# Runtime fake: Celery registra send_task e restituisce id/status controllati; RabbitMQ
# espone solo queue_exists; Arkimet e le funzioni quota sono monkeypatchate nei test.
# Cleanup: ogni record DB, associazione many-to-many, file fisico e utente temporaneo
# viene registrato nel cleanup_registry o rimosso da helper dedicati.
# Baseline non toccata: il modulo supporta solo file *_EXT e non altera fixture globali,
# moduli legacy o dati runtime persistenti della suite.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from celery import states
from mistral.endpoints import DOWNLOAD_DIR
from mistral.models.sqlalchemy import DatasetCategories
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

DEFAULT_BOUNDING = (
    "POLYGON ((10.0000000000000000 44.0000000000000000, "
    "11.0000000000000000 44.0000000000000000, "
    "11.0000000000000000 45.0000000000000000, "
    "10.0000000000000000 45.0000000000000000, "
    "10.0000000000000000 44.0000000000000000))"
)


@dataclass(frozen=True)
class DataEndpointDataset:
    """Record minimo per riferire un dataset sintetico nei test data endpoint.

    I test devono usare l'arkimet_id nel payload HTTP, ma il cleanup e le
    autorizzazioni lavorano sui record relazionali. Tenere entrambi i valori in un
    oggetto esplicito rende chiaro quale identificatore viene usato in ciascun punto.
    """

    id: int
    arkimet_id: str
    name: str
    category: str
    fileformat: str


@dataclass(frozen=True)
class FakeTaskResult:
    """Risultato Celery sintetico con i soli attributi letti dall'endpoint.

    Data.post copia id e status sul record Request subito dopo send_task. Questo
    oggetto espone esattamente quel contratto senza parlare con broker o worker reali.
    """

    id: str
    status: str


class RecordingCelery:
    """Fake del connettore Celery che registra le submission senza eseguirle.

    L'endpoint chiama celery.get_instance().celery_app.send_task(...). Il fake mantiene
    la stessa forma pubblica, accumula le chiamate in sent_tasks e restituisce sempre
    un risultato controllato, cosi il test puo verificare nome task, argomenti, queue e
    routing_key senza avviare worker reali.
    """

    def __init__(self, *, task_id: str = "task-data-endpoint-ext") -> None:
        # Memorizziamo nello stato del fake le chiamate che il test dovra ispezionare.
        self.sent_tasks: list[dict[str, Any]] = []
        self.celery_app = _RecordingCeleryApp(self.sent_tasks, task_id=task_id)


class _RecordingCeleryApp:
    """Facade minima di celery_app usata dal fake RecordingCelery."""

    def __init__(self, sent_tasks: list[dict[str, Any]], *, task_id: str) -> None:
        # Conserviamo lo stato condiviso con il wrapper esterno per rendere visibili
        # al test le submission prodotte dall'endpoint.
        self.sent_tasks = sent_tasks
        self.task_id = task_id

    def send_task(
        self,
        name: str,
        args: tuple[Any, ...] | list[Any] | None = None,
        **kwargs: Any,
    ) -> FakeTaskResult:
        """Registra una submission Celery e restituisce un AsyncResult sintetico."""
        # Intercettiamo l'invio del task per controllare quale lavoro asincrono sarebbe
        # stato richiesto dal backend, senza mandarlo al broker reale.
        self.sent_tasks.append({"name": name, "args": args, "kwargs": kwargs})
        # Restituiamo un risultato compatibile con gli attributi letti da Data.post.
        return FakeTaskResult(id=self.task_id, status=states.PENDING)


class FakeRabbit:
    """Fake RabbitMQ mirato al solo controllo queue_exists dell'endpoint push.

    Il contratto push di POST /data non richiede pubblicazioni AMQP: prima della
    submission l'endpoint verifica soltanto se la queue dell'utente esiste. Il fake
    rende quel risultato deterministico e ispezionabile.
    """

    def __init__(self, *, exists: bool) -> None:
        # Salviamo l'esito configurato e le queue verificate, cosi il test puo
        # distinguere il ramo positivo da quello negativo.
        self.exists = exists
        self.checked_queues: list[str] = []

    def queue_exists(self, queue_name: str) -> bool:
        """Restituisce l'esito configurato registrando la queue controllata."""
        # Registriamo l'input osservabile del ramo push prima di restituire il valore
        # sintetico scelto dal test.
        self.checked_queues.append(queue_name)
        return self.exists


def create_data_endpoint_user(
    client: FlaskClient,
    cleanup_registry,
    dataset_ids: list[int] | None = None,
    *,
    allowed_postprocessing: bool = False,
    amqp_queue: str | None = None,
    disk_quota: int = 1073741824,
    max_output_size: int = 1073741824,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo con permessi espliciti per il dominio data.

    Il helper passa dall'API di creazione utente come il resto della suite, poi registra
    cleanup HTTP e filesystem. Le autorizzazioni dataset sono espresse come id numerici
    per rispettare il formato accettato dagli endpoint admin esistenti.
    """
    # Costruiamo permessi chiusi e leggibili: l'utente vede i dataset pubblici, puo
    # essere associato a dataset privati sintetici e non ottiene postprocessing salvo
    # quando il singolo scenario lo richiede.
    permissions: dict[str, Any] = {
        "disk_quota": disk_quota,
        "max_output_size": max_output_size,
        "allowed_postprocessing": allowed_postprocessing,
        "open_dataset": True,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids or []]),
    }

    base = BaseTests()
    # Creiamo e autentichiamo l'utente temporaneo, evitando dipendenze da account
    # preesistenti nella base dati runtime.
    user = create_authenticated_test_user(base, client, permissions)
    db = sqlalchemy.get_instance()
    db_user = db.User.query.get(user.user_id)
    # Aggiorniamo sempre il campo sul record relazionale reale: l'endpoint admin usa
    # faker/schema per riempire campi facoltativi e potrebbe generare una queue casuale.
    # Per il contratto push del dominio data dobbiamo invece distinguere in modo
    # deterministico tra queue assente, queue presente ma inesistente e queue valida.
    assert db_user is not None
    db_user.amqp_queue = amqp_queue
    db.session.add(db_user)
    db.session.commit()
    # Registriamo subito la pulizia dell'utente e della relativa area output.
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


def create_synthetic_dataset(
    db,
    cleanup_registry,
    *,
    category: DatasetCategories = DatasetCategories.FOR,
    fileformat: str = "grib",
    is_public: bool = True,
    group_name: str | None = None,
    prefix: str = "data_ext",
) -> DataEndpointDataset:
    """Crea dataset/licenza/attribution sintetici e registra cleanup completo.

    I test del POST /data devono controllare formato, categoria e gruppo licenza senza
    dipendere da cataloghi reali. Questo helper produce un catalogo minimo isolato e lo
    rimuove in teardown insieme ai link utente eventualmente creati.
    """
    # Recuperiamo o creiamo un'attribution locale, cosi il dataset rispetta i vincoli
    # relazionali anche in ambienti di test con catalogo ridotto.
    attribution = db.Attribution.query.first()
    created_attribution_id = None
    if attribution is None:
        attribution = db.Attribution(
            name=f"attr_{uuid4().hex[:10]}",
            descr="Synthetic attribution for data endpoint EXT tests",
            url="https://example.invalid/data-ext-attribution",
        )
        db.session.add(attribution)
        db.session.flush()
        created_attribution_id = attribution.id

    token = uuid4().hex[:12]
    dataset_name = f"{prefix}_{token}"
    license_group = db.GroupLicense(
        name=group_name or f"{dataset_name}_group",
        descr=f"Synthetic license group for {dataset_name}",
        is_public=is_public,
    )
    db.session.add(license_group)
    db.session.flush()

    license_entry = db.License(
        name=f"{dataset_name}_license",
        descr=f"Synthetic license for {dataset_name}",
        group_license_id=license_group.id,
    )
    db.session.add(license_entry)
    db.session.flush()

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Synthetic dataset for {dataset_name}",
        source="arkimet",
        license_id=license_entry.id,
        attribution_id=attribution.id,
        category=category,
        fileformat=fileformat,
        bounding=DEFAULT_BOUNDING,
        supports_variable_browsing=False,
    )
    db.session.add(dataset)
    db.session.commit()

    # Registriamo la rimozione del bundle relazionale appena il record esiste.
    cleanup_registry.add(
        lambda: delete_dataset_bundle(
            db,
            dataset_id=dataset.id,
            license_id=license_entry.id,
            group_license_id=license_group.id,
            attribution_id=created_attribution_id,
        )
    )
    return DataEndpointDataset(
        id=dataset.id,
        arkimet_id=dataset.arkimet_id,
        name=dataset.name,
        category=category.name,
        fileformat=fileformat,
    )


def build_data_payload(
    dataset_names: list[str],
    *,
    request_name: str | None = None,
    reftime_from: str = "2020-01-01T00:00:00Z",
    reftime_to: str = "2020-01-01T01:00:00Z",
    **overrides: Any,
) -> dict[str, Any]:
    """Costruisce il body JSON comune a POST /data per scenari sintetici.

    Il payload include una reftime valida e filtri vuoti per attraversare schema,
    validazioni endpoint e creazione request senza chiamare Arkimet o DBALLE reali.
    Gli override consentono ai test di inserire solo il campo specifico dello scenario.
    """
    # Manteniamo il body minimo ma completo: request_name e dataset_names sono sempre
    # richiesti, mentre reftime sintetica rende deterministica la queue_sorting.
    payload: dict[str, Any] = {
        "request_name": request_name or f"data-ext-{uuid4().hex[:10]}",
        "dataset_names": dataset_names,
        "reftime": {"from": reftime_from, "to": reftime_to},
        "filters": {},
    }
    payload.update(overrides)
    return payload


def patch_data_endpoint_runtime(
    monkeypatch,
    data_endpoint_module,
    *,
    dataset_format: str | None = "grib",
    dataset_category: str = "FOR",
    celery_fake: RecordingCelery | None = None,
    rabbit_fake: FakeRabbit | None = None,
) -> RecordingCelery:
    """Applica fake runtime locali al modulo mistral.endpoints.data.

    L'endpoint importa arki, celery e rabbitmq come oggetti di modulo; monkeypatcharli
    qui mantiene il fake confinato al singolo test e garantisce cleanup automatico del
    fixture monkeypatch.
    """
    # Il fake Arkimet decide formato, categoria e ammissibilita filtri senza accedere a
    # configurazioni o dataset meteo reali.
    monkeypatch.setattr(
        data_endpoint_module.arki,
        "get_datasets_format",
        lambda dataset_names: dataset_format,
    )
    monkeypatch.setattr(
        data_endpoint_module.arki,
        "get_datasets_category",
        lambda dataset_names: dataset_category,
    )
    monkeypatch.setattr(
        data_endpoint_module.arki,
        "is_filter_allowed",
        lambda filter_name: True,
    )

    celery_to_use = celery_fake or RecordingCelery()
    monkeypatch.setattr(
        data_endpoint_module.celery,
        "get_instance",
        lambda: celery_to_use,
    )
    if rabbit_fake is not None:
        monkeypatch.setattr(
            data_endpoint_module.rabbitmq,
            "get_instance",
            lambda: rabbit_fake,
        )
    return celery_to_use


def create_file_download_record(
    db,
    cleanup_registry,
    user: AuthenticatedTestUser,
    *,
    content: str | None = "owned-output-content",
) -> str:
    """Crea request, FileOutput e opzionalmente file fisico per GET /data/<filename>.

    Il download endpoint controlla prima il record DB, poi ownership e infine il file
    sul filesystem. Questo helper prepara quei tre livelli in modo esplicito; passando
    content=None si lascia apposta il record DB senza file per il ramo 404.
    """
    # Inseriamo una request sintetica di successo associata all'utente temporaneo, cosi
    # il FileOutput ha un request_id valido e non dipende da task reali.
    request = db.Request(
        user_id=user.user_id,
        name=f"download-ext-{uuid4().hex[:10]}",
        args={"datasets": [], "reftime": {}, "filters": {}},
        status=states.SUCCESS,
        opendata=False,
    )
    db.session.add(request)
    db.session.commit()

    filename = f"{uuid4().hex}.grib"
    file_output = db.FileOutput(
        user_id=user.user_id,
        request_id=request.id,
        filename=filename,
        size=len(content.encode("utf-8")) if content is not None else 0,
    )
    db.session.add(file_output)
    db.session.commit()

    output_path = Path(DOWNLOAD_DIR, user.uuid, "outputs", filename)
    if content is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        cleanup_registry.add_path(output_path.parent)

    cleanup_registry.add(lambda: delete_request_row(db, request.id))
    return filename


def latest_request_for_user(db, user_id: int):
    """Restituisce la request piu recente dell'utente temporaneo sotto test.

    I test POST /data usano questo helper dopo la risposta HTTP per collegare il
    response body agli effetti persistiti dal repository layer.
    """
    # Leggiamo dal DB l'ultimo effetto prodotto dall'endpoint, ordinando per id per
    # evitare dipendenze dalla risoluzione temporale della submission_date.
    return (
        db.Request.query.filter_by(user_id=user_id)
        .order_by(db.Request.id.desc())
        .first()
    )


def delete_request_row(db, request_id: int) -> None:
    """Rimuove una request sintetica e il relativo FileOutput se sono ancora presenti."""
    # Rimuoviamo lo stato creato dal test senza assumere che il caso di errore sia
    # arrivato fino alla creazione completa di tutte le righe.
    request = db.Request.query.get(request_id)
    if request is None:
        return
    db.session.delete(request)
    db.session.commit()


def delete_dataset_bundle(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_license_id: int,
    attribution_id: int | None,
) -> None:
    """Rimuove dataset sintetico, licenza, gruppo licenza e attribution eventuale."""
    # Stacchiamo prima le associazioni utente-dataset, altrimenti la rimozione del
    # dataset puo lasciare righe many-to-many residue o fallire per vincoli DB.
    dataset = db.Datasets.query.get(dataset_id)
    if dataset is not None:
        for user in dataset.users.all():
            dataset.users.remove(user)
        db.session.delete(dataset)

    license_entry = db.License.query.get(license_id)
    if license_entry is not None:
        db.session.delete(license_entry)

    group_license = db.GroupLicense.query.get(group_license_id)
    if group_license is not None:
        db.session.delete(group_license)

    if attribution_id is not None:
        attribution = db.Attribution.query.get(attribution_id)
        if attribution is not None:
            db.session.delete(attribution)

    db.session.commit()


def delete_requests_for_user(db, user_id: int) -> None:
    """Rimuove tutte le request create per l'utente temporaneo del test."""
    # Alcuni scenari di errore non creano request, mentre il ramo happy path ne crea una;
    # il cleanup idempotente consente di registrare sempre la stessa azione.
    for request in db.Request.query.filter_by(user_id=user_id).all():
        db.session.delete(request)
    db.session.commit()