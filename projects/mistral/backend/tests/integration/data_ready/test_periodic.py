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
"""

from datetime import timedelta

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    create_schedule_request_record,
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


def _create_two_day_periodic_schedule(
    client: FlaskClient,
    data_ready_base,
    data_ready_user,
) -> tuple[str, object, str]:
    """Crea una schedule periodica di due giorni e ne rimuove la prima richiesta.

    Creare una schedule con ``POST /api/schedules`` puo generare subito una prima
    richiesta. I test periodici devono controllare tutta la storia delle richieste,
    quindi l'helper cancella quella riga (``DELETE /api/requests/<id>``) e
    restituisce i dati della schedule che servono al chiamante per costruire uno
    scenario preciso sul tempo trascorso.
    """
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    ref_from = dataset_window.ref_from.replace(second=0, microsecond=1)
    ref_to = dataset_window.ref_to.replace(second=0, microsecond=1)
    date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.%f")
    date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.%f")
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
    return schedule_id, ref_from, date_from


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
    invia un nuovo evento ``POST /api/data/ready`` e controlla che la schedule esponga
    ora due richieste: quella inserita dal test piu quella appena generata dal task
    ``launch_all_on_data_ready_extractions``.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    trigger_rundate = dataset_window.ref_from.strftime("%Y%m%d%H")
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
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=trigger_rundate,
        schedule_ids=[schedule_id],
    )

    # assert
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
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=ref_from.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
    )

    # assert
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
    aspetta comunque che ``POST /api/data/ready`` accetti l'evento, ma il numero di
    richieste della schedule deve restare invariato.
    """
    # arrange
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
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=ref_from.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
    )

    # assert
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
    assert len(requests) == 1