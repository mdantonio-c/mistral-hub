# EXTENSION TRACEABILITY: questo modulo di supporto e stato aggiunto dal prompt 07
# dell'estensione copertura backend. Esiste solo per i nuovi test task *_EXT e non
# modifica la baseline legacy, gli helper globali o il codice applicativo.
# EXTENSION SCOPE: centralizza piccoli seed DB e fake SMTP/Rabbit/Celery usati dai
# test su requests_cleanup e data_extraction. I fake riproducono soltanto i metodi
# osservati dai task, cosi la verifica resta sui side effect di quota, cleanup e
# notification invece che sull'infrastruttura esterna.
# EXTENSION DATA WINDOW: nessun dataset meteorologico reale viene letto o richiesto.
# Le date usate dai chiamanti sono sintetiche e servono solo a rendere vecchi o
# recenti record e file controllati dalla suite.
# EXTENSION RUNTIME: non vengono aperte connessioni SMTP, RabbitMQ, Celery worker o
# tool meteo. Il DB e quello di test Rapydo perche i rami da coprire persistono
# request, schedule e fileoutput; tutti i servizi esterni sono fake locali.
# EXTENSION CLEANUP: i helper registrano utenti e directory nel cleanup_registry e
# offrono funzioni idempotenti per rimuovere request, schedule e fileoutput creati
# dai test. I path fisici vivono sotto la directory dell'utente temporaneo o sotto
# tmp_path, mai in aree runtime non controllate.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from mistral.models.sqlalchemy import PeriodEnum
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient


@dataclass
class SentEmailEXT:
    """Payload email catturato dal fake SMTP dei test task.

    Il task reale passa corpo HTML, subject, destinatario e body plain separatamente.
    Raggrupparli in una dataclass rende gli assert piu espliciti e mantiene il fake
    lontano da qualunque implementazione SMTP reale.
    """

    body: str
    subject: str
    recipient: str
    plain_body: str | None


class RetryThenSuccessSmtpFactoryEXT:
    """Fake SMTP che fallisce un numero controllato di send e poi accetta il payload.

    `notify_by_email` crea un nuovo client SMTP per ogni retry. Questo factory espone
    lo stesso punto di ingresso `get_instance`, registra kwargs e invii, e consente al
    test di verificare il retry senza sleep reale e senza server SMTP.
    """

    def __init__(self, *, failures_before_success: int = 1) -> None:
        # Memorizziamo il comportamento sintetico e gli effetti osservabili che il test
        # ispezionera dopo la chiamata a notify_by_email.
        self.failures_before_success = failures_before_success
        self.send_attempts = 0
        self.get_instance_calls: list[dict[str, Any]] = []
        self.sent_messages: list[SentEmailEXT] = []

    def get_instance_EXT(self, **kwargs: Any) -> "RetryThenSuccessSmtpClientEXT":
        """Restituisce un context manager SMTP fake per un singolo retry.

        Il nome con suffisso EXT rende chiaro che questo metodo e introdotto solo dalla
        suite estesa. Il chiamante lo monkeypatcha su `smtp.get_instance`, quindi la
        firma accetta kwargs generici come il connettore reale.
        """
        # Registriamo i parametri di connessione richiesti dal task; non li usiamo per
        # collegarci a servizi reali, ma proteggono il contratto di retry esistente.
        self.get_instance_calls.append(kwargs)
        return RetryThenSuccessSmtpClientEXT(self)


class RetryThenSuccessSmtpClientEXT:
    """Context manager minimale restituito dal factory SMTP EXT.

    Il client implementa solo `send`, `__enter__` e `__exit__`, cioe il sottoinsieme
    realmente usato dal task. Ogni altro comportamento SMTP resta fuori dallo scope.
    """

    def __init__(self, factory: RetryThenSuccessSmtpFactoryEXT) -> None:
        # Conserviamo un riferimento al factory per aggiornare contatori e messaggi
        # condivisi fra piu retry.
        self.factory = factory

    def __enter__(self) -> "RetryThenSuccessSmtpClientEXT":
        """Apre il context manager senza side effect esterni."""
        # Non esiste nessuna connessione reale da aprire: il valore osservabile e solo
        # il client fake restituito al blocco `with` del task.
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Chiude il context manager lasciando propagare eventuali eccezioni."""
        # Restituire False mantiene la semantica del context manager reale: se il test
        # configura un errore non gestito, l'eccezione rimane visibile.
        return False

    def send(
        self,
        body: str,
        subject: str,
        recipient: str,
        *,
        plain_body: str | None = None,
    ) -> None:
        """Registra l'email o simula un fallimento iniziale controllato."""
        # Incrementiamo il contatore prima di decidere se fallire, cosi il test puo
        # dimostrare quanti invii sono stati tentati dal ciclo retry.
        self.factory.send_attempts += 1
        if self.factory.send_attempts <= self.factory.failures_before_success:
            raise RuntimeError("synthetic smtp failure for EXT retry test")
        self.factory.sent_messages.append(
            SentEmailEXT(
                body=body,
                subject=subject,
                recipient=recipient,
                plain_body=plain_body,
            )
        )


class RecordingRabbitFactoryEXT:
    """Fake RabbitMQ che registra un singolo payload JSON senza usare il broker.

    `notify_by_amqp_queue` apre un context manager, invia JSON su una routing key e
    chiama `disconnect`. Questo fake conserva quei tre segnali osservabili per gli
    assert, evitando qualunque side effect verso RabbitMQ reale.
    """

    def __init__(self) -> None:
        # La stessa connessione fake e sufficiente per i test deterministici del task.
        self.connection = RecordingRabbitConnectionEXT()

    def get_instance_EXT(self) -> "RecordingRabbitConnectionEXT":
        """Restituisce la connessione fake usata dal monkeypatch di rabbitmq."""
        # Non apriamo socket o canali reali; consegniamo solo l'oggetto su cui il task
        # chiamera send_json e disconnect.
        return self.connection


class RecordingRabbitConnectionEXT:
    """Context manager RabbitMQ minimale con payload e routing key registrati."""

    def __init__(self) -> None:
        # Gli invii vengono accumulati per consentire assert precisi sul contenuto AMQP.
        self.sent_messages: list[dict[str, Any]] = []
        self.disconnected = False

    def __enter__(self) -> "RecordingRabbitConnectionEXT":
        """Apre il context manager senza contattare RabbitMQ reale."""
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Chiude il context manager lasciando propagare eventuali eccezioni."""
        return False

    def send_json(self, payload: dict[str, Any], *, routing_key: str) -> None:
        """Registra il payload JSON che sarebbe stato pubblicato sul broker."""
        # Copiamo il dict per evitare che modifiche successive del test alterino il
        # payload effettivamente prodotto dal task.
        self.sent_messages.append(
            {
                "payload": dict(payload),
                "routing_key": routing_key,
            }
        )

    def disconnect(self) -> None:
        """Registra la chiusura esplicita richiesta dal task."""
        # Il connettore reale chiude la connessione; qui rendiamo osservabile soltanto
        # il fatto che il task abbia invocato quel ramo.
        self.disconnected = True


class RecordingPeriodicTaskDeletionEXT:
    """Fake callable per CeleryExt.delete_periodic_task.

    I test quota devono verificare che una schedule periodica venga disabilitata e che
    il relativo periodic task venga rimosso. Questo callable registra nome e argomenti
    senza toccare RedBeat o worker Celery reali.
    """

    def __init__(self, *, return_value: bool = True) -> None:
        # Conserviamo il valore di ritorno configurabile e la cronologia chiamate.
        self.return_value = return_value
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> bool:
        """Registra la richiesta di cancellazione periodica e restituisce l'esito fake."""
        # Il task passa `name=str(schedule_id)`: registrarlo esplicitamente permette al
        # test di collegare il side effect Celery alla schedule DB corretta.
        self.calls.append({"args": args, "kwargs": kwargs})
        return self.return_value


def create_task_test_user_EXT(
    client: FlaskClient,
    cleanup_registry,
    *,
    requests_expiration_days: int | None = 180,
    requests_expiration_delete: bool = False,
    disk_quota: int = 1073741824,
    max_output_size: int | None = 1073741824,
    notify_on_successful_request: bool = True,
    allowed_schedule: bool = True,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo con impostazioni task controllate.

    Passiamo dall'API di creazione utente per restare allineati alla suite, poi
    normalizziamo direttamente i campi usati dai task. Il cleanup standard rimuove
    utente e directory output, mentre i test aggiungono cleanup specifici per request
    e schedule creati dopo l'utente.
    """
    # Prepariamo un utente reale del DB di test; nessun scenario dipende da account
    # seedati o da configurazioni locali non portabili.
    base = BaseTests()
    user = create_authenticated_test_user(
        base,
        client,
        permissions={"allowed_schedule": allowed_schedule, "open_dataset": True},
    )
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )

    db = sqlalchemy.get_instance()
    db_user = db.User.query.get(user.user_id)
    assert db_user is not None
    db_user.requests_expiration_days = requests_expiration_days
    db_user.requests_expiration_delete = requests_expiration_delete
    db_user.disk_quota = disk_quota
    db_user.max_output_size = max_output_size
    db_user.notify_on_successful_request = notify_on_successful_request
    db.session.add(db_user)
    db.session.commit()
    return user


def seed_request_EXT(
    db: Any,
    user_id: int,
    *,
    name: str | None = None,
    args: dict[str, Any] | None = None,
    status: str = "SUCCESS",
    submission_date: dt.datetime | None = None,
    end_date: dt.datetime | None = None,
    schedule_id: int | None = None,
    archived: bool = False,
    opendata: bool = False,
) -> int:
    """Inserisce una request sintetica per esercitare cleanup o duplicate data-ready.

    Il seed diretto evita endpoint e worker non pertinenti: i test vogliono controllare
    come i task reagiscono a righe gia presenti, non rieseguire il flusso di submit.
    """
    # Creiamo argomenti minimi ma realistici, includendo sempre reftime e dataset per i
    # rami che confrontano richieste schedulate precedenti.
    request = db.Request(
        user_id=user_id,
        name=name or f"task-ext-{uuid4().hex[:10]}",
        args=args
        or {
            "datasets": ["synthetic-task-ext"],
            "reftime": None,
            "filters": None,
        },
        status=status,
        submission_date=submission_date or dt.datetime.utcnow(),
        end_date=end_date,
        schedule_id=schedule_id,
        archived=archived,
        opendata=opendata,
    )
    db.session.add(request)
    db.session.commit()
    return request.id


def seed_fileoutput_EXT(
    db: Any,
    cleanup_registry,
    user: AuthenticatedTestUser,
    request_id: int,
    *,
    filename: str | None = None,
    content: str = "synthetic task output EXT",
) -> tuple[int, Path]:
    """Crea FileOutput e file fisico nella directory output dell'utente temporaneo.

    `automatic_cleanup` attraversa sia DB sia filesystem. Questo helper collega i due
    livelli con un filename unico e registra cleanup idempotente per il path utente.
    """
    # Scriviamo il file sotto DOWNLOAD_DIR/<uuid>/outputs, cioe lo stesso punto in cui
    # il task reale lo cercherebbe, ma confinato all'utente temporaneo del test.
    user.output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_registry.add_path(user.output_dir.parent)
    output_filename = filename or f"{uuid4().hex}.grib"
    output_path = user.output_dir / output_filename
    output_path.write_text(content, encoding="utf-8")

    fileoutput = db.FileOutput(
        user_id=user.user_id,
        request_id=request_id,
        filename=output_filename,
        size=len(content.encode("utf-8")),
    )
    db.session.add(fileoutput)
    db.session.commit()
    return fileoutput.id, output_path


def seed_schedule_EXT(
    db: Any,
    user_id: int,
    *,
    name: str | None = None,
    enabled: bool = True,
    on_data_ready: bool = False,
) -> int:
    """Inserisce una schedule minimale per rami quota e duplicate data-ready.

    La schedule non viene registrata in RedBeat: per questi test e sufficiente la riga
    DB letta da data_extract/check_user_quota, mentre la cancellazione periodica viene
    verificata con fake esplicito.
    """
    # Manteniamo gli args coerenti con il formato prodotto dagli endpoint schedule, ma
    # senza dipendere da dataset reali o creazione HTTP della schedule.
    schedule = db.Schedule(
        user_id=user_id,
        name=name or f"schedule-task-ext-{uuid4().hex[:10]}",
        args={
            "datasets": ["synthetic-task-ext"],
            "reftime": None,
            "filters": None,
            "postprocessors": None,
            "output_format": None,
            "only_reliable": False,
            "pushing_queue": None,
        },
        is_crontab=False,
        period=PeriodEnum.days,
        every=1,
        time_delta=dt.timedelta(hours=1),
        on_data_ready=on_data_ready,
        is_enabled=enabled,
        opendata=False,
    )
    db.session.add(schedule)
    db.session.commit()
    return schedule.id


def delete_schedule_EXT(db: Any, schedule_id: int) -> None:
    """Rimuove una schedule sintetica se il test non l'ha gia eliminata."""
    # Il cleanup e idempotente per non fallire quando il ramo sotto test cancella o
    # modifica lo stato prima del teardown.
    schedule = db.Schedule.query.get(schedule_id)
    if schedule is not None:
        db.session.delete(schedule)
        db.session.commit()


def delete_requests_for_user_EXT(db: Any, user_id: int) -> None:
    """Rimuove request e fileoutput creati per un utente temporaneo dei task EXT."""
    # Cancelliamo prima i FileOutput rimasti, poi le Request, cosi il teardown resta
    # stabile anche quando il task ha gia rimosso parte dello stato.
    for fileoutput in db.FileOutput.query.filter_by(user_id=user_id).all():
        db.session.delete(fileoutput)
    for request in db.Request.query.filter_by(user_id=user_id).all():
        db.session.delete(request)
    db.session.commit()


def touch_mtime_EXT(path: Path, when: dt.datetime) -> None:
    """Imposta l'mtime di un file sintetico per i rami orphan cleanup.

    Il task decide se cancellare un file guardando `stat().st_mtime`; questo helper
    rende esplicita la data scelta dal test e non legge alcun dato runtime esterno.
    """
    # Convertiamo il datetime naive nel timestamp locale atteso da os.utime attraverso
    # il metodo standard della libreria Path/stat usato dal task.
    timestamp = when.timestamp()
    path.touch(exist_ok=True)
    path.write_text(path.name, encoding="utf-8")
    import os

    os.utime(path, (timestamp, timestamp))