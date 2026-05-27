"""Integration tests for periodic schedules driven by ``/data/ready`` events.

These tests deliberately mix real application logic with a small amount of test
double infrastructure:

- the HTTP call to ``/data/ready`` is real,
- the periodic-schedule decision logic is real,
- the Celery transport layer is replaced with in-process fakes,
- the expensive extraction worker is replaced with a synthetic DB write.

This gives deterministic tests for the scheduling rules without depending on the
timing of external workers or on full data extraction side effects.
"""

from datetime import datetime, timedelta

import pytest
from restapi.tests import FlaskClient

import mistral.endpoints.data_ready as data_ready_endpoint
import mistral.tasks.on_data_ready_extractions as on_data_ready_task
from mistral.tests.helpers.celery_fakes import (
    AcceptTasksWithoutRunningCelery,
    InlineDataReadyExtractionCelery,
)
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    create_schedule_request_record,
    delete_request,
    list_schedule_requests,
    trigger_data_ready_and_wait_accepted,
    wait_for_schedule_requests,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window
from mistral.tests.helpers.schedules import build_periodic_schedule

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def _trigger_data_ready_periodic_inline(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_admin_headers,
    data_ready_db,
    *,
    rundate: str,
):
    """Drive one data-ready event through the real code path, but fully in-process.

    The helper first calls the real ``/data/ready`` endpoint and intercepts only
    the Celery submission that would normally enqueue
    ``launch_all_on_data_ready_extractions`` on an external worker.

    It then runs ``launch_all_on_data_ready_extractions`` directly in the test
    process and again intercepts the nested ``data_extract`` submission, turning
    it into a synthetic request row in the database.

    In short: the business logic is real, but the asynchronous transport and the
    heavy extraction worker are replaced with local fakes.
    """
    # The HTTP endpoint is real; this fake only absorbs its Celery submission.
    monkeypatch.setattr(
        data_ready_endpoint.celery,
        "get_instance",
        lambda: AcceptTasksWithoutRunningCelery(
            "launch_all_on_data_ready_extractions"
        ),
    )
    response = trigger_data_ready_and_wait_accepted(
        client,
        data_ready_admin_headers,
        model=DATA_READY_DATASET_NAME,
        rundate=rundate,
    )
    # The scheduler logic is real; this fake turns data_extract into a DB row.
    monkeypatch.setattr(
        on_data_ready_task.celery,
        "get_instance",
        lambda: InlineDataReadyExtractionCelery(data_ready_db),
    )
    on_data_ready_task.launch_all_on_data_ready_extractions.run(
        DATA_READY_DATASET_NAME,
        datetime.strptime(rundate, "%Y%m%d%H"),
    )
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return response


def _create_two_day_periodic_schedule(
    client: FlaskClient,
    data_ready_base,
    data_ready_user,
) -> tuple[str, object, str]:
    """Create a reusable two-day schedule and remove the automatic first request.

    Creating a schedule can immediately generate an initial request row. The
    periodic tests need full control over the request history, so this helper
    removes that eager row and returns the schedule metadata the caller needs to
    build a precise scenario around elapsed time.
    """
    # Entriamo nel blocco operativo dell'helper data-ready, mantenendo esplicito quale
    # stato viene letto o prodotto.
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    ref_from = dataset_window.ref_from.replace(second=0, microsecond=1)
    ref_to = dataset_window.ref_to.replace(second=0, microsecond=1)
    date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.%f")
    date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.%f")
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
    schedule_body = build_periodic_schedule(
        request_name="test_periodic_days",
        date_from=date_from,
        date_to=date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        every=2,
        period="days",
        on_data_ready=True,
        opendata=True,
    )
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )
    # Scorriamo gli elementi restituiti dal backend per trovare solo quelli rilevanti
    # per questo scenario.
    for request in list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    ):
        delete_request(client, data_ready_user.headers, request["id"])
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return schedule_id, ref_from, date_from


def test_data_ready_creates_request_when_daily_period_has_elapsed(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """A one-day schedule must create a second request after exactly one elapsed day.

    The test seeds one successful previous request dated one day earlier, sends a
    new ``/data/ready`` event, and then checks that the schedule now exposes two
    request rows: the original seeded row plus the newly generated one.
    """
    # arrange
    # Prepariamo lo scenario data-ready con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    trigger_rundate = dataset_window.ref_from.strftime("%Y%m%d%H")
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
    schedule_body = build_periodic_schedule(
        request_name="test_daily_period_elapsed",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        every=1,
        period="days",
        on_data_ready=True,
        opendata=True,
    )
    # Prepariamo la schedule con parametri espliciti, rendendo chiara la condizione che
    # deve attivare o bloccare il backend.
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_daily_period_elapsed",
        dataset_name=DATA_READY_DATASET_NAME,
        reftime=dataset_window.date_from,
        schedule_id=schedule_id,
        submission_date=(dataset_window.ref_from + timedelta(days=-1)).replace(
            microsecond=1
        ),
        status="SUCCESS",
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = _trigger_data_ready_periodic_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        rundate=trigger_rundate,
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 202
    requests = wait_for_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
        expected_count=2,
        timeout=5,
        interval=1,
    )
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert len(requests) == 2


def test_data_ready_creates_request_when_two_day_period_has_elapsed(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """A two-day schedule must fire again only when two full days have passed.

    The test creates a previous successful request two days in the past and then
    submits a matching data-ready event. A new row should be generated because
    the schedule interval has been completely satisfied.
    """
    # arrange
    # Prepariamo lo scenario data-ready con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    schedule_id, ref_from, date_from = _create_two_day_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
    )
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_days_older_than_period",
        dataset_name=DATA_READY_DATASET_NAME,
        reftime=date_from,
        schedule_id=schedule_id,
        submission_date=(ref_from + timedelta(days=-2)),
        status="SUCCESS",
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = _trigger_data_ready_periodic_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        rundate=ref_from.strftime("%Y%m%d%H"),
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 202
    requests = wait_for_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
        expected_count=2,
        timeout=5,
        interval=1,
    )
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert len(requests) == 2


def test_data_ready_skips_request_before_two_day_period_elapses(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """A two-day schedule must not fire early after only one elapsed day.

    Here the seeded request is only one day old, so the periodic rule is not yet
    satisfied. The test still expects the endpoint to accept the event, but the
    schedule request count must remain unchanged.
    """
    # arrange
    # Prepariamo lo scenario data-ready con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    schedule_id, ref_from, date_from = _create_two_day_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
    )
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_days_before_period",
        dataset_name=DATA_READY_DATASET_NAME,
        reftime=date_from,
        schedule_id=schedule_id,
        submission_date=(ref_from + timedelta(days=-1)),
        status="SUCCESS",
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = _trigger_data_ready_periodic_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        rundate=ref_from.strftime("%Y%m%d%H"),
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 202
    requests = wait_for_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
        expected_count=1,
        timeout=5,
        interval=1,
    )
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert len(requests) == 1