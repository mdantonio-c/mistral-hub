"""Test di integrazione delle schedule periodiche attivate da ``/data/ready``.

Questi test mescolano di proposito logica applicativa reale e una piccola
infrastruttura di fake:

- la chiamata HTTP a ``/data/ready`` e reale,
- la logica di decisione delle schedule periodiche e reale
  (``launch_all_on_data_ready_extractions`` in tasks/on_data_ready_extractions.py),
- il trasporto Celery e sostituito da fake in-process,
- il costoso worker di estrazione e sostituito da una scrittura sintetica nel DB.

Si ottengono cosi test deterministici sulle regole di scheduling, senza dipendere
dai tempi dei worker esterni ne dagli effetti di una vera estrazione dati.

Le richieste precedenti inserite dai test hanno la forma di quelle reali (``datasets``
lista, ``reftime`` dict from/to) e date senza microsecondi, come quelle prodotte da
``isoformat()``. Ogni scenario sceglie esplicitamente se il reftime precedente e
uguale (duplicato) o diverso da quello dell'evento.
"""

from datetime import datetime, timedelta

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.celery_fakes import InlineDataReadyExtractionCelery
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    create_schedule_request_record,
    data_ready_reftime,
    delete_request,
    list_schedule_requests,
    trigger_data_ready_inline,
    wait_for_schedule_requests,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window
from mistral.tests.helpers.schedules import build_periodic_schedule

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def _create_periodic_schedule(
    client: FlaskClient,
    data_ready_base,
    data_ready_user,
    *,
    every: int,
    request_name: str = "test_periodic_days",
) -> tuple[str, datetime]:
    """Crea una schedule periodica di ``every`` giorni e ne rimuove le richieste.

    Creare una schedule con ``POST /api/schedules`` puo generare subito una prima
    richiesta. I test periodici devono controllare tutta la storia delle richieste,
    quindi l'helper cancella quella riga (``DELETE /api/requests/<id>``) e
    restituisce l'id della schedule e l'inizio della finestra dati, che il chiamante
    usa per costruire uno scenario preciso sul tempo trascorso.
    """
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    schedule_body = build_periodic_schedule(
        request_name=request_name,
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        every=every,
        period="days",
        on_data_ready=True,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )
    for request in list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    ):
        delete_request(client, data_ready_user.headers, request["id"])
    return schedule_id, dataset_window.ref_from


def _run_date(ref_from: datetime) -> datetime:
    """Restituisce il rundate (ora intera, senza fuso) che il launcher riceve."""
    return datetime.strptime(ref_from.strftime("%Y%m%d%H"), "%Y%m%d%H")


def test_data_ready_creates_request_when_daily_period_has_elapsed(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Una schedule giornaliera deve creare una seconda richiesta dopo un giorno esatto.

    Il test inserisce nel DB una richiesta precedente riuscita datata un giorno prima,
    per il run del giorno prima, invia un nuovo evento ``POST /api/data/ready`` e
    controlla che il launcher ``launch_all_on_data_ready_extractions`` invii un solo
    task e che la schedule esponga ora due richieste. La data della richiesta
    precedente non ha microsecondi, come accade con ``isoformat()``.
    """
    # arrange
    schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=1,
        request_name="test_daily_period_elapsed",
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_daily_period_elapsed",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date - timedelta(days=1)),
        schedule_id=schedule_id,
        submission_date=ref_from - timedelta(days=1),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=run_date.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
        extraction_celery=extraction_celery,
    )

    # assert
    assert response.status_code == 202
    assert len(extraction_celery.sent_tasks) == 1
    requests = wait_for_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
        expected_count=2,
        timeout=5,
        interval=1,
    )
    assert len(requests) == 2


def test_data_ready_creates_request_when_two_day_period_has_elapsed(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Una schedule ogni due giorni deve ripartire solo dopo due giorni interi.

    Il test crea una richiesta precedente riuscita di due giorni prima e poi invia un
    evento data-ready corrispondente (``POST /api/data/ready``). Il task
    ``launch_all_on_data_ready_extractions`` deve generare una nuova riga, perche
    l'intervallo della schedule e stato rispettato del tutto.
    """
    # arrange
    schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=2,
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_days_older_than_period",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date - timedelta(days=2)),
        schedule_id=schedule_id,
        submission_date=ref_from - timedelta(days=2),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=run_date.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
        extraction_celery=extraction_celery,
    )

    # assert
    assert response.status_code == 202
    assert len(extraction_celery.sent_tasks) == 1
    requests = wait_for_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
        expected_count=2,
        timeout=5,
        interval=1,
    )
    assert len(requests) == 2


def test_data_ready_skips_request_before_two_day_period_elapses(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Una schedule ogni due giorni non deve ripartire dopo un solo giorno.

    Qui la richiesta inserita ha solo un giorno, quindi la regola periodica di
    ``launch_all_on_data_ready_extractions`` non e ancora soddisfatta. Il test si
    aspetta comunque che ``POST /api/data/ready`` accetti l'evento, ma il launcher
    non deve inviare task e il numero di richieste della schedule resta invariato.
    """
    # arrange
    schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=2,
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_days_before_period",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date - timedelta(days=1)),
        schedule_id=schedule_id,
        submission_date=ref_from - timedelta(days=1),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=run_date.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
        extraction_celery=extraction_celery,
    )

    # assert
    assert response.status_code == 202
    assert extraction_celery.sent_tasks == []
    requests = wait_for_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
        expected_count=1,
        timeout=5,
        interval=1,
    )
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("every", "days_since_last_request"),
    [(1, 3), (2, 3)],
    ids=["daily-two-missed-events", "two-days-one-missed-event"],
)
def test_data_ready_recovers_after_missed_event(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
    every: int,
    days_since_last_request: int,
) -> None:
    """Un evento previsto e mancato non blocca la schedule periodica.

    L'ultima richiesta riuscita e piu vecchia del periodo: l'evento atteso non e
    arrivato (o non ha prodotto una richiesta riuscita). Il launcher deve ripartire
    con il primo evento successivo alla data prevista, invece di aspettare una data
    che non tornera piu.
    """
    # arrange
    schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=every,
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_missed_event",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date - timedelta(days=days_since_last_request)),
        schedule_id=schedule_id,
        submission_date=ref_from - timedelta(days=days_since_last_request),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=run_date.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
        extraction_celery=extraction_celery,
    )

    # assert
    assert response.status_code == 202
    assert len(extraction_celery.sent_tasks) == 1
    requests = list_schedule_requests(
        data_ready_base, client, data_ready_user.headers, schedule_id
    )
    assert len(requests) == 2


def test_data_ready_repeated_event_creates_a_single_request(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """La stessa notifica ripetuta non crea estrazioni duplicate.

    Dopo il primo evento la schedule ha una nuova richiesta riuscita: alla seconda
    notifica dello stesso run il periodo non e trascorso e il launcher non invia
    altri task.
    """
    # arrange
    schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=1,
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_repeated_event",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date - timedelta(days=1)),
        schedule_id=schedule_id,
        submission_date=ref_from - timedelta(days=1),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    for _ in range(2):
        response = trigger_data_ready_inline(
            monkeypatch,
            client,
            data_ready_admin_headers,
            data_ready_db,
            model=DATA_READY_DATASET_NAME,
            rundate=run_date.strftime("%Y%m%d%H"),
            schedule_ids=[schedule_id],
            extraction_celery=extraction_celery,
        )
        assert response.status_code == 202

    # assert
    assert len(extraction_celery.sent_tasks) == 1
    requests = list_schedule_requests(
        data_ready_base, client, data_ready_user.headers, schedule_id
    )
    assert len(requests) == 2


def test_data_ready_does_not_duplicate_extraction_with_same_reftime(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Un invio con lo stesso reftime dell'ultima richiesta riuscita non crea righe.

    Il periodo e trascorso, quindi il launcher invia il task; ma l'ultima richiesta
    riuscita ha gia estratto lo stesso reftime e, come nel worker reale
    (``data_extract``), l'estrazione duplicata non produce una nuova riga.
    """
    # arrange
    schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=1,
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_periodic_same_reftime",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date),
        schedule_id=schedule_id,
        submission_date=ref_from - timedelta(days=1),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=run_date.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
        extraction_celery=extraction_celery,
    )

    # assert
    assert response.status_code == 202
    assert len(extraction_celery.sent_tasks) == 1
    sent_reftime = extraction_celery.sent_tasks[0]["args"][2]
    assert sent_reftime == data_ready_reftime(run_date)
    requests = list_schedule_requests(
        data_ready_base, client, data_ready_user.headers, schedule_id
    )
    assert len(requests) == 1


def test_data_ready_creation_date_without_microseconds_does_not_stop_launcher(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Una schedule creata in un istante senza microsecondi non blocca le altre.

    La prima schedule non ha richieste: il launcher usa la sua data di creazione,
    serializzata con ``isoformat()`` senza frazione. Deve essere saltata senza
    errori (il periodo non e trascorso) e la seconda schedule deve partire.
    """
    # arrange
    first_schedule_id, ref_from = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=1,
        request_name="test_creation_without_microseconds",
    )
    first_schedule = data_ready_db.Schedule.query.get(int(first_schedule_id))
    first_schedule.submission_date = first_schedule.submission_date.replace(
        microsecond=0
    )
    data_ready_db.session.commit()
    second_schedule_id, _ = _create_periodic_schedule(
        client,
        data_ready_base,
        data_ready_user,
        every=1,
        request_name="test_following_schedule",
    )
    run_date = _run_date(ref_from)
    create_schedule_request_record(
        data_ready_db,
        data_ready_user.user_id,
        "test_following_schedule",
        datasets=[DATA_READY_DATASET_NAME],
        reftime=data_ready_reftime(run_date - timedelta(days=1)),
        schedule_id=second_schedule_id,
        submission_date=ref_from - timedelta(days=1),
        status="SUCCESS",
    )
    extraction_celery = InlineDataReadyExtractionCelery(data_ready_db)

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=run_date.strftime("%Y%m%d%H"),
        schedule_ids=[first_schedule_id, second_schedule_id],
        extraction_celery=extraction_celery,
    )

    # assert
    assert response.status_code == 202
    sent_schedule_ids = [task["args"][9] for task in extraction_celery.sent_tasks]
    assert sent_schedule_ids == [int(second_schedule_id)]
    assert not list_schedule_requests(
        data_ready_base, client, data_ready_user.headers, first_schedule_id
    )
