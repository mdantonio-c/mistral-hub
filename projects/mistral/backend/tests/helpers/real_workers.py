"""Helpers for ``async_real`` tests, whose tasks run on the real Celery workers.

Inside a worker ``monkeypatch`` has no effect: whatever the task does really
happens. These helpers keep such tests inside their own perimeter:

- run them only where the workers use the SMTP mock (``rapydo --testing``);
- poll the API until the workers close a request;
- make the cleanup wait for the workers before the API deletes the data of the
  test user, and stop the user's tasks first if the workers are too slow;
- read RedBeat only for the schedule created by the test;
- read the emails recorded by the SMTP mock.

Users whose extractions run on real workers must be created with
``create_data_ready_user``, which keeps every notification away from real
mailboxes.
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
    """One email recorded by the Rapydo SMTP mock instead of being sent."""

    recipients: list[str]
    subject: str
    text: str


class RealWorkerCleanupWarning(Warning):
    """The cleanup had to stop tasks of a test user on the real workers.

    It derives from ``Warning`` on purpose: in test mode ``create_app`` turns
    ``UserWarning`` into an error, which would interrupt the cleanup halfway.
    """


def workers_use_smtp_mock() -> bool:
    """Return True if the stack was started with ``rapydo --testing``.

    Only in that mode the real workers run with ``APP_MODE=test`` and replace
    SMTP with the Rapydo mock. The test process cannot read the environment of
    the workers, so it checks the variables that the same command sets in the
    backend container.
    """
    return all(
        os.environ.get(name) == value for name, value in TESTING_STACK_MARKERS.items()
    )


def read_periodic_task(schedule_id: int | str) -> Any:
    """Return the RedBeat entry of one schedule, or ``None`` if it does not exist.

    The lookup goes through the project's Celery connector and reads only the
    key of the given schedule.
    """
    return celery.get_instance().get_periodic_task(name=str(schedule_id))


def wait_for_finished_request(
    read_request: Callable[[], dict[str, Any] | None],
    *,
    description: str,
    timeout: float = 120,
    interval: float = 2,
) -> dict[str, Any]:
    """Poll until the request returned by ``read_request`` reaches a final state.

    ``read_request`` returns the request payload, or ``None`` while the request
    is not visible yet. The final payload is returned whatever its state, so the
    caller can assert on ``SUCCESS`` and show the worker error otherwise.
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
    """Return the email that the SMTP mock recorded for ``address``.

    The mock writes the last two sent emails in the logs folder, which the
    backend and the workers share. An email found here never left the stack.
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
    """Return the ids of the ``data_extract`` tasks of ``user_id`` held by a worker.

    Running, prefetched and countdown tasks are all included; the first argument
    of ``data_extract`` is the user id. ``None`` means that no worker replied, so
    nothing can be confirmed.
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
    """Stop the tasks of the test user and wait until the workers confirm it.

    Queued tasks are revoked, so the workers drop them; running ones are killed
    with SIGKILL, so they never reach the ``finally`` block of ``data_extract``,
    which writes the request and sends the notification. Only tasks of the test
    user are touched: those of its unfinished requests and the ``data_extract``
    tasks whose first argument is its id.

    If the workers do not confirm, the step fails: the cleanup stops and every
    row, file and account of the user stays in place, still consistent for a
    worker that completes the task later.
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
    """Make the cleanup wait for the workers before deleting the user's data.

    Register it after ``register_data_ready_user_cleanup``: the registry runs in
    LIFO order, so this step runs first. It waits until every request of the
    user is finished and no worker holds a ``data_extract`` task of the user.
    The API refuses to delete a pending request, and data deleted under a task
    would leave the worker writing on missing rows and folders.

    If the workers are too slow, ``stop_user_tasks`` stops the user's tasks and
    only then the unfinished requests of the user are deleted. If the workers
    do not confirm, the step fails and deletes nothing.
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
    db = sqlalchemy.get_instance()
    # populate_existing rilegge lo stato scritto dai worker in altri processi.
    requests = (
        db.Request.query.filter_by(user_id=user.user_id).populate_existing().all()
    )
    return [request for request in requests if request.status not in FINISHED_STATES]


def _delete_unfinished_requests(user: AuthenticatedTestUser) -> None:
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
