"""Test di integrazione del controllo crontab nelle schedule on-data-ready.

Verificano che il task ``launch_all_on_data_ready_extractions``
(tasks/on_data_ready_extractions.py), avviato da ``POST /api/data/ready``, scarti le
schedule il cui crontab non coincide con la data del run notificato. Tutti i campi
giorno/mese presenti devono coincidere e ``day_of_week`` segue la convenzione del
crontab Celery usato da RedBeat per le altre schedule (0 = domenica, 1 = lunedi).
"""

import pytest
from restapi.tests import FlaskClient

from mistral.tests.helpers.schedules import build_crontab_schedule
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    list_schedule_requests,
    trigger_data_ready_inline,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window

pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_data_ready_skips_schedule_when_full_crontab_does_not_match(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Verifica che un crontab completo non coincidente non generi richieste.

    Il crontab indica il 30 novembre, mentre il run notificato con
    ``POST /api/data/ready`` e del 19 ottobre 2021: il task
    ``launch_all_on_data_ready_extractions`` deve scartare la schedule.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    schedule_body = build_crontab_schedule(
        request_name="test_full_crontab_mismatch",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        minute=59,
        hour=23,
        day_of_week=6,
        day_of_month=30,
        month_of_year=11,
        on_data_ready=True,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate="2021101900",
        schedule_ids=[schedule_id],
    )

    # assert
    assert response.status_code == 202
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )


def test_data_ready_skips_schedule_when_partial_crontab_does_not_match(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
) -> None:
    """Verifica che anche un crontab parziale non coincidente non generi richieste.

    Il crontab indica solo giorno della settimana e mese: il giorno della settimana
    coincide (2 = martedi, come il run del 19 ottobre 2021) ma il mese no, quindi il
    task ``launch_all_on_data_ready_extractions`` deve scartare la schedule.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    schedule_body = build_crontab_schedule(
        request_name="test_partial_crontab_mismatch",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        minute=59,
        hour=23,
        day_of_week=2,
        month_of_year=11,
        on_data_ready=True,
        opendata=True,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate="2021101900",
        schedule_ids=[schedule_id],
    )

    # assert
    assert response.status_code == 202
    assert not list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )


@pytest.mark.parametrize(
    ("crontab", "rundate", "expected_requests"),
    [
        ({"day_of_week": 2}, "2021101900", 1),
        ({"day_of_week": 1}, "2021101900", 0),
        ({"day_of_week": 0}, "2021101700", 1),
        ({"day_of_month": 31}, "2021103100", 1),
        ({"day_of_month": 20}, "2021101900", 0),
        ({"month_of_year": 10}, "2021101900", 1),
        ({"month_of_year": 11}, "2021101900", 0),
        ({"day_of_week": 2, "month_of_year": 10}, "2021101900", 1),
        (
            {"day_of_week": 3, "day_of_month": 19, "month_of_year": 10},
            "2021101900",
            0,
        ),
    ],
    ids=[
        "tuesday-matches",
        "monday-does-not-match-tuesday",
        "sunday-matches",
        "day-31-matches",
        "only-day-of-month-mismatch",
        "only-month-matches",
        "only-month-mismatch",
        "weekday-and-month-match",
        "all-fields-weekday-mismatch",
    ],
)
def test_data_ready_crontab_applies_every_field(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    data_ready_base,
    data_ready_admin_headers,
    data_ready_db,
    data_ready_user,
    crontab: dict[str, int],
    rundate: str,
    expected_requests: int,
) -> None:
    """Verifica il filtro crontab del launcher campo per campo.

    Il 17 ottobre 2021 e domenica, il 19 martedi, il 31 domenica.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client, data_ready_user.headers, DATA_READY_DATASET_NAME
    )
    schedule_body = build_crontab_schedule(
        request_name="test_crontab_fields",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[DATA_READY_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        minute=0,
        hour=0,
        on_data_ready=True,
        opendata=True,
        **crontab,
    )
    schedule_id = create_schedule(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_body,
    )

    # act
    response = trigger_data_ready_inline(
        monkeypatch,
        client,
        data_ready_admin_headers,
        data_ready_db,
        model=DATA_READY_DATASET_NAME,
        rundate=rundate,
        schedule_ids=[schedule_id],
    )

    # assert
    assert response.status_code == 202
    requests = list_schedule_requests(
        data_ready_base,
        client,
        data_ready_user.headers,
        schedule_id,
    )
    assert len(requests) == expected_requests
