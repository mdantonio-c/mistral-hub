"""Helper per i test ``async_real``, i cui task girano sui worker Celery reali.

Dentro un worker ``monkeypatch`` non ha effetto: tutto quello che il task fa
avviene davvero. Questi helper tengono tali test dentro il loro perimetro:

- li eseguono solo dove i worker usano il mock SMTP (``rapydo --testing``);
- interrogano l'API finche i worker chiudono una richiesta;
- fanno si che il cleanup attenda i worker prima che l'API cancelli i dati
  dell'utente di test, e fermano prima i task dell'utente se i worker sono
  troppo lenti;
- leggono RedBeat solo per la schedule creata dal test;
- leggono le email registrate dal mock SMTP.

Gli utenti le cui estrazioni girano sui worker reali vanno creati con
``create_data_ready_user``, che tiene ogni notifica lontana da caselle di posta
reali.
"""

from __future__ import annotations

import email
import json
import os
import warnings
from dataclasses import dataclass
from typing import Any, Callable

from celery import states
from mistral.tests.helpers.auth import AuthenticatedTestUser
from mistral.tests.helpers.data_ready import list_user_requests
from mistral.tests.helpers.polling import wait_until
from restapi.connectors import celery, sqlalchemy
from restapi.tests import BaseTests, FlaskClient
from restapi.utilities.logs import LOGS_FOLDER

FINISHED_STATES = frozenset(states.READY_STATES)

# `rapydo --testing` (senza --production) mette APP_MODE=test in tutti i container,
# worker compresi, e queste tre variabili nel container backend. Nel processo dei
# test APP_MODE vale sempre "test" (lo forza `restapi tests`) e non distingue lo
# stack; queste variabili invece si.
TESTING_STACK_MARKERS = {
    "PYTHONMALLOC": "debug",
    "PYTHONASYNCIODEBUG": "1",
    "PYTHONFAULTHANDLER": "1",
}
NO_SMTP_MOCK_REASON = (
    "async_real: the real workers use the SMTP mock only on stacks started with "
    "`rapydo --testing`; on this stack a failed extraction would send real emails"
)
# Il mock SMTP di Rapydo conserva le ultime due email inviate in questi file.
SMTP_MOCK_FILES = ("mock.mail.lastsent.json", "mock.mail.prevsent.json")


@dataclass(frozen=True)
class MockEmail:
    """Un'email registrata dal mock SMTP di Rapydo invece di essere inviata."""

    recipients: list[str]
    subject: str
    text: str


class RealWorkerCleanupWarning(Warning):
    """Il cleanup ha dovuto fermare task di un utente di test sui worker reali.

    Deriva da ``Warning`` di proposito: in modalita test ``create_app`` trasforma
    ``UserWarning`` in errore, e questo interromperebbe il cleanup a meta.
    """


def workers_use_smtp_mock() -> bool:
    """Restituisce True se lo stack e stato avviato con ``rapydo --testing``.

    Solo in quella modalita i worker reali girano con ``APP_MODE=test`` e
    sostituiscono SMTP con il mock di Rapydo. Il processo dei test non puo leggere
    l'ambiente dei worker, quindi controlla le variabili che lo stesso comando
    imposta nel container backend.
    """
    return all(
        os.environ.get(name) == value for name, value in TESTING_STACK_MARKERS.items()
    )


def read_periodic_task(schedule_id: int | str) -> Any:
    """Restituisce la voce RedBeat di una schedule, o ``None`` se non esiste.

    La lettura passa dal connettore Celery del progetto
    (``celery.get_instance().get_periodic_task``) e legge solo la chiave della
    schedule indicata.
    """
    return celery.get_instance().get_periodic_task(name=str(schedule_id))


def wait_for_finished_request(
    read_request: Callable[[], dict[str, Any] | None],
    *,
    description: str,
    timeout: float = 120,
    interval: float = 2,
) -> dict[str, Any]:
    """Attende che la richiesta letta da ``read_request`` arrivi a uno stato finale.

    ``read_request`` restituisce il payload della richiesta, oppure ``None`` finche
    la richiesta non e ancora visibile. Il payload finale viene restituito qualunque
    sia lo stato, cosi il chiamante puo verificare ``SUCCESS`` e altrimenti mostrare
    l'errore del worker.
    """

    def finished_request() -> dict[str, Any] | bool:
        request = read_request()
        if request is None or request.get("status") not in FINISHED_STATES:
            return False
        return request

    return wait_until(
        finished_request,
        timeout=timeout,
        interval=interval,
        message=f"Real workers did not finish {description} within {timeout} seconds",
    )


def wait_for_mock_email(
    address: str,
    *,
    timeout: float = 30,
    interval: float = 1,
) -> MockEmail:
    """Restituisce l'email che il mock SMTP ha registrato per ``address``.

    Il mock scrive le ultime due email inviate nella cartella dei log, condivisa da
    backend e worker. Un'email trovata qui non e mai uscita dallo stack.
    """

    def recorded_email() -> MockEmail | bool:
        for filename in SMTP_MOCK_FILES:
            try:
                sent = json.loads(LOGS_FOLDER.joinpath(filename).read_text())
            except (OSError, ValueError):
                # Il mock sposta lastsent in prevsent prima di riscriverlo.
                continue
            if address not in sent.get("cc", []):
                continue
            message = email.message_from_string(sent["msg"])
            # notify_by_email invia testo e HTML: il testo e la prima parte.
            part = message.get_payload()[0] if message.is_multipart() else message
            return MockEmail(
                recipients=sent["cc"],
                subject=message["Subject"],
                text=part.get_payload(decode=True).decode("utf-8"),
            )
        return False

    return wait_until(
        recorded_email,
        timeout=timeout,
        interval=interval,
        message=f"The SMTP mock recorded no email for {address}",
    )


def held_user_tasks(user_id: int) -> set[str] | None:
    """Restituisce gli id dei task ``data_extract`` di ``user_id`` tenuti da un worker.

    Sono inclusi i task in esecuzione, quelli gia prelevati e quelli in attesa del
    countdown; il primo argomento di ``data_extract`` e l'id utente. ``None``
    significa che nessun worker ha risposto, quindi non si puo confermare nulla.
    """
    inspector = celery.get_instance().celery_app.control.inspect(timeout=1)
    replies = (inspector.active(), inspector.reserved(), inspector.scheduled())
    if any(reply is None for reply in replies):
        return None
    task_ids = set()
    for reply in replies:
        for tasks in reply.values():
            for task in tasks:
                # scheduled() incapsula i dati del task sotto "request".
                info = task.get("request", task)
                args = info.get("args") or []
                if info.get("name") == "data_extract" and args and args[0] == user_id:
                    task_ids.add(info["id"])
    return task_ids


def stop_user_tasks(
    user: AuthenticatedTestUser,
    *,
    timeout: float = 30,
    interval: float = 3,
) -> None:
    """Ferma i task dell'utente di test e attende che i worker lo confermino.

    I task in coda vengono revocati, quindi i worker li scartano; quelli in
    esecuzione vengono uccisi con SIGKILL, cosi non arrivano mai al blocco
    ``finally`` di ``data_extract``, che scrive la richiesta e invia la notifica.
    Vengono toccati solo i task dell'utente di test: quelli delle sue richieste
    non terminate e i task ``data_extract`` il cui primo argomento e il suo id.

    Se i worker non confermano, il passo fallisce: il cleanup si ferma e ogni riga,
    file e account dell'utente resta al suo posto, ancora coerente per un worker
    che completi il task piu tardi.
    """
    control = celery.get_instance().celery_app.control
    # Un task ancora nel broker non compare nelle risposte dei worker: si revoca
    # subito per id, e i worker lo scarteranno appena lo ricevono.
    known_ids = sorted(
        request.task_id for request in _unfinished_requests(user) if request.task_id
    )
    if known_ids:
        control.revoke(known_ids, terminate=True, signal="SIGKILL")

    def no_user_task_left() -> bool:
        held = held_user_tasks(user.user_id)
        if held:
            control.revoke(sorted(held), terminate=True, signal="SIGKILL")
        return held == set()

    wait_until(
        no_user_task_left,
        timeout=timeout,
        interval=interval,
        message=(
            f"The workers did not confirm that the tasks of test user {user.uuid} "
            "stopped: its requests, files and account are left in place"
        ),
    )


def register_wait_for_user_requests(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    user: AuthenticatedTestUser,
    *,
    timeout: float = 120,
    interval: float = 3,
    stop_timeout: float = 30,
) -> None:
    """Fa si che il cleanup attenda i worker prima di cancellare i dati dell'utente.

    Va registrato dopo ``register_data_ready_user_cleanup``: il registro esegue in
    ordine LIFO, quindi questo passo viene eseguito per primo. Attende che ogni
    richiesta dell'utente sia terminata e che nessun worker tenga un task
    ``data_extract`` dell'utente. L'API rifiuta di cancellare una richiesta in
    corso, e dati cancellati sotto un task lascerebbero il worker a scrivere su
    righe e cartelle mancanti.

    Se i worker sono troppo lenti, ``stop_user_tasks`` ferma i task dell'utente e
    solo dopo vengono cancellate le sue richieste non terminate. Se i worker non
    confermano, il passo fallisce e non cancella nulla.
    """

    def user_tasks_finished() -> bool:
        requests = list_user_requests(base, client, user.headers)
        if any(request.get("status") not in FINISHED_STATES for request in requests):
            return False
        # Il primo task di una schedule non ha ancora una request finche un worker
        # non lo avvia: va cercato direttamente nei worker.
        return held_user_tasks(user.user_id) == set()

    def wait_for_workers() -> None:
        try:
            wait_until(
                user_tasks_finished,
                timeout=timeout,
                interval=interval,
                message=f"Tasks of test user {user.uuid} still running",
            )
        except AssertionError:
            stop_user_tasks(user, timeout=stop_timeout, interval=interval)
            _delete_unfinished_requests(user)

    cleanup_registry.add(wait_for_workers)


def _unfinished_requests(user: AuthenticatedTestUser) -> list[Any]:
    """Restituisce le richieste dell'utente non ancora in uno stato finale (DB)."""
    db = sqlalchemy.get_instance()
    # populate_existing rilegge lo stato scritto dai worker in altri processi.
    requests = (
        db.Request.query.filter_by(user_id=user.user_id).populate_existing().all()
    )
    return [request for request in requests if request.status not in FINISHED_STATES]


def _delete_unfinished_requests(user: AuthenticatedTestUser) -> None:
    """Cancella con l'ORM le richieste non terminate e lo segnala con un warning."""
    db = sqlalchemy.get_instance()
    unfinished = _unfinished_requests(user)
    if not unfinished:
        return
    for request in unfinished:
        db.session.delete(request)
    db.session.commit()
    warnings.warn(
        f"Deleted {len(unfinished)} request(s) of test user {user.uuid} after "
        "stopping their tasks on the real workers",
        RealWorkerCleanupWarning,
        stacklevel=2,
    )
