"""Test di integrazione del ponte tra schedule data-ready e opendata.

Gli scenari verificano il passaggio completo da una request generata da una
schedule alla creazione di un pacchetto opendata, che poi si puo elencare e
scaricare.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

import mistral.endpoints.data_ready as data_ready_endpoint
import mistral.endpoints.schedules as schedules_endpoint
import mistral.tasks.on_data_ready_extractions as on_data_ready_task
from mistral.tests.helpers.celery_fakes import (
    AcceptTasksWithoutRunningCelery,
    InlineDataExtractCelery,
)
from mistral.tests.helpers.schedules import (
    build_crontab_schedule,
    build_on_data_ready_schedule,
)
from mistral.tests.helpers.data_ready import (
    DATA_READY_DATASET_NAME,
    create_schedule,
    delete_schedule,
    list_schedule_requests,
    register_schedule_cleanup,
    trigger_data_ready_and_wait_accepted,
    wait_for_schedule_requests,
)
from mistral.tests.helpers.dataset_window import fetch_dataset_window
from mistral.tests.helpers.polling import wait_until
from mistral.tests.helpers.real_workers import (
    read_periodic_task,
    register_wait_for_user_requests,
)
from mistral.tests.helpers.task_perimeter import confine_data_ready_schedules


pytestmark = [pytest.mark.integration, pytest.mark.runtime_sensitive]

BRIDGE_DATASET_NAME = DATA_READY_DATASET_NAME


class ScheduleRequestFailed(AssertionError):
    """Sollevata quando una request generata dalla schedule va in FAILURE."""

    pass


# =============================================================================
# Due percorsi di test: on-data-ready (inline) e crontab (RedBeat/Beat)
# =============================================================================
# Questo file verifica il ponte dalle schedule a opendata in due modi:
#
# 1. Percorso ON-DATA-READY (test_on_data_ready_schedule_publishes_opendata_package):
#    - Il test usa monkeypatch su Celery per intercettare i task prima del broker.
#    - L'endpoint /api/data/ready viene chiamato, il task e accettato localmente
#      e il data_extract annidato gira subito nello stesso processo.
#    - L'intero flusso e sincrono e deterministico dentro il test.
#    - Serve a verificare la logica dell'endpoint e l'estrazione immediata.
#
# 2. Percorso CRONTAB (test_crontab_schedule_publishes_opendata_package):
#    - Il test crea una vera voce di schedule in Redis tramite RedBeat (lo scheduler).
#    - Il container celerybeat in esecuzione legge quella voce da Redis.
#    - All'ora prevista celerybeat mette il task nel broker RabbitMQ.
#    - I worker Celery asincroni consumano il task ed eseguono l'estrazione.
#    - Il test fa polling sul risultato, aspettando sia beat sia i worker.
#    - Serve a verificare la persistenza reale della schedule e l'esecuzione asincrona.
#
# Il percorso on-data-ready e piu veloce e del tutto isolato; il percorso crontab
# usa l'infrastruttura reale (Redis, RabbitMQ, celerybeat, worker) ed e quindi un
# test di integrazione piu completo.
# =============================================================================


def _trigger_data_ready_schedule_inline(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    schedules_admin_headers,
    *,
    model: str,
    rundate: str,
    schedule_ids: list[str],
):
    """Porta una schedule data-ready fino a un'estrazione reale eseguita inline.

    Il test mantiene l'endpoint HTTP reale (POST /data/ready) e la logica reale di
    schedulazione data-ready, ma sostituisce due volte il trasporto Celery:

    - l'invio dall'endpoint viene accettato localmente invece di andare al broker,
    - il task annidato ``data_extract`` viene eseguito subito nello stesso processo.

    L'estrazione inline e reale, quindi il launcher e limitato a ``schedule_ids``:
    le schedule di altri utenti non arrivano mai a ``data_extract``.
    """
    monkeypatch.setattr(
        data_ready_endpoint.celery,
        "get_instance",
        lambda: AcceptTasksWithoutRunningCelery(
            "launch_all_on_data_ready_extractions"
        ),
    )
    response = trigger_data_ready_and_wait_accepted(
        client,
        schedules_admin_headers,
        model=model,
        rundate=rundate,
    )
    monkeypatch.setattr(
        on_data_ready_task.celery,
        "get_instance",
        lambda: InlineDataExtractCelery(),
    )
    confine_data_ready_schedules(monkeypatch, schedule_ids)
    on_data_ready_task.launch_all_on_data_ready_extractions.run(
        model,
        datetime.strptime(rundate, "%Y%m%d%H"),
    )
    return response


def _wait_for_successful_schedule_request(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
    *,
    timeout: float = 120,
    interval: float = 5,
    grace_timeout: float = 0,
) -> dict[str, Any]:
    """Fa polling su una schedule finche espone una request riuscita con un file reale.

    Legge le request con GET /schedules/<id>/requests. Il timeout normale copre la
    finestra di invio attesa. Una seconda finestra di tolleranza, opzionale, esiste
    solo per il percorso crontab con worker reali, dove celerybeat e i worker possono
    a volte mostrare la request oltre il limite nominale anche se il flusso alla
    fine riesce.
    """
    def successful_request():
        """Restituisce la request quando e riuscita con un nome di file concreto."""
        requests = list_schedule_requests(base, client, headers, schedule_id)
        if len(requests) != 1:
            return False

        request = requests[0]
        if request.get("status") == "FAILURE":
            raise ScheduleRequestFailed(
                request.get("error message")
                or f"Scheduled request {request['id']} failed"
            )

        if (
            request.get("status") == "SUCCESS"
            and request.get("fileoutput")
            and request.get("fileoutput") != "no file available"
        ):
            return request

        return False

    try:
        return wait_until(
            successful_request,
            timeout=timeout,
            interval=interval,
            message=(
                f"Expected schedule {schedule_id} to produce a successful opendata request"
            ),
        )
    except AssertionError:
        if grace_timeout <= 0:
            raise

    return wait_until(
        successful_request,
        timeout=grace_timeout,
        interval=interval,
        message=(
            "Expected schedule {schedule_id} to produce a successful opendata "
            "request even after the additional grace window"
        ).format(schedule_id=schedule_id),
    )


def _wait_for_listing_entry(
    client: FlaskClient,
    dataset_name: str,
    filename: str,
    headers: Any,
    *,
    query: str,
    timeout: float = 60,
    interval: float = 3,
) -> dict[str, Any]:
    """Fa polling sul listing opendata del dataset finche compare il file atteso.

    Usa GET /datasets/<dataset_name>/opendata con il filtro ``query``.
    """
    endpoint = f"{API_URI}/datasets/{dataset_name}/opendata?q={query}"
    base = BaseTests()

    def listed_package():
        """Restituisce il pacchetto quando il file atteso compare nel listing."""
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200
        content = base.get_content(response) or []
        for package in content:
            if package.get("filename") == filename:
                return package
        return False

    return wait_until(
        listed_package,
        timeout=timeout,
        interval=interval,
        message=(
            f"Expected opendata listing for dataset {dataset_name} to expose {filename}"
        ),
    )


def _next_crontab_run_time() -> datetime:
    """Restituisce il prossimo minuto sicuro per l'esecuzione reale di una crontab.

    Questo helper serve solo al percorso crontab (vedi la nota in cima al file).
    Se il test parte troppo vicino al cambio di minuto, schedulare il task per il
    minuto successivo puo entrare in competizione con la lettura di RedBeat e
    celerybeat. Un minuto in piu mantiene il test deterministico e resta comunque
    molto piu stretto di uno sleep fisso.
    """
    now = datetime.now()
    minutes_ahead = 2 if now.second >= 45 else 1
    return now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_ahead)


@pytest.mark.deterministic
def test_on_data_ready_schedule_publishes_opendata_package(
    monkeypatch: pytest.MonkeyPatch,
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    schedules_admin_headers,
    schedules_user,
) -> None:
    """Una schedule on-data-ready riuscita pubblica un pacchetto opendata scaricabile.

    Esercita POST /schedules, POST /data/ready, il task
    ``launch_all_on_data_ready_extractions``, il listing
    GET /datasets/<name>/opendata e il download GET /opendata/<file>.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client,
        schedules_user.headers,
        BRIDGE_DATASET_NAME,
    )
    schedule_body = build_on_data_ready_schedule(
        request_name="test_schedule_opendata_bridge",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[BRIDGE_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        opendata=True,
    )
    # POST /schedules on-data-ready invia subito un data_extract: il fake lo accetta
    # senza eseguirlo, cosi l'unica estrazione e quella lanciata dal data-ready.
    monkeypatch.setattr(
        schedules_endpoint.celery,
        "get_instance",
        lambda: AcceptTasksWithoutRunningCelery("data_extract"),
    )
    schedule_id = create_schedule(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_body,
    )
    register_schedule_cleanup(
        client,
        cleanup_registry,
        schedules_user.headers,
        schedule_id,
    )

    # act
    response = _trigger_data_ready_schedule_inline(
        monkeypatch,
        client,
        schedules_admin_headers,
        model=BRIDGE_DATASET_NAME,
        rundate=dataset_window.ref_from.strftime("%Y%m%d%H"),
        schedule_ids=[schedule_id],
    )
    published_request = _wait_for_successful_schedule_request(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_id,
    )
    listed_package = _wait_for_listing_entry(
        client,
        BRIDGE_DATASET_NAME,
        published_request["fileoutput"],
        schedules_user.headers,
        query=f"reftime:={dataset_window.ref_from.strftime('%Y-%m-%d %H:%M')}",
    )
    download_response = client.get(
        f"{API_URI}/opendata/{published_request['fileoutput']}",
        headers=schedules_user.headers,
    )

    try:
        # assert
        assert response.status_code == 202
        assert published_request["status"] == "SUCCESS"
        assert published_request["fileoutput"] == listed_package["filename"]
        assert listed_package["date"] == dataset_window.ref_from.strftime("%Y-%m-%d")
        assert download_response.status_code == 200
        assert download_response.data
        assert (
            published_request["fileoutput"]
            in download_response.headers["Content-Disposition"]
        )
    finally:
        download_response.close()


@pytest.mark.async_real
def test_crontab_schedule_publishes_opendata_package(
    client: FlaskClient,
    cleanup_registry,
    schedules_base,
    schedules_user,
) -> None:
    """Una schedule crontab pura pubblica, alla fine, un pacchetto opendata scaricabile.

    Esercita POST /schedules con RedBeat, celerybeat e worker reali, il listing
    GET /datasets/<name>/opendata, il download GET /opendata/<file> e
    DELETE /schedules/<id>.
    """
    # arrange
    dataset_window = fetch_dataset_window(
        client,
        schedules_user.headers,
        BRIDGE_DATASET_NAME,
    )
    trigger_at = _next_crontab_run_time()
    schedule_body = build_crontab_schedule(
        request_name="test_crontab_schedule_opendata_bridge",
        date_from=dataset_window.date_from,
        date_to=dataset_window.date_to,
        dataset_names=[BRIDGE_DATASET_NAME],
        run_filter=[dataset_window.ref_run[0]],
        hour=trigger_at.hour,
        minute=trigger_at.minute,
        opendata=True,
    )
    schedule_id = create_schedule(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_body,
    )
    # La schedule viene cancellata con la DELETE reale nell'act; se il test si ferma
    # prima, la cancella il cleanup dell'utente, che aspetta i worker sulle request.
    register_wait_for_user_requests(
        schedules_base,
        client,
        cleanup_registry,
        schedules_user,
    )
    # Celerybeat esegue la schedule crontab solo tramite la sua chiave RedBeat.
    periodic_task = read_periodic_task(schedule_id)

    # act
    published_request = _wait_for_successful_schedule_request(
        schedules_base,
        client,
        schedules_user.headers,
        schedule_id,
        timeout=180,
        interval=5,
        grace_timeout=180,
    )
    listed_package = _wait_for_listing_entry(
        client,
        BRIDGE_DATASET_NAME,
        published_request["fileoutput"],
        schedules_user.headers,
        query=(
            "reftime:>={date_from},<={date_to}".format(
                date_from=dataset_window.ref_from.strftime("%Y-%m-%d %H:%M"),
                date_to=dataset_window.ref_to.strftime("%Y-%m-%d %H:%M"),
            )
        ),
        timeout=60,
        interval=3,
    )
    # La DELETE reale deve togliere anche la chiave RedBeat: se restasse, celerybeat
    # lancerebbe data_extract ogni giorno per una schedule che non esiste piu.
    delete_schedule(client, schedules_user.headers, schedule_id)
    periodic_task_after_delete = read_periodic_task(schedule_id)
    download_response = client.get(
        f"{API_URI}/opendata/{published_request['fileoutput']}",
        headers=schedules_user.headers,
    )

    try:
        # assert
        assert published_request["status"] == "SUCCESS"
        assert published_request["fileoutput"] == listed_package["filename"]
        assert listed_package["date"] == "from {date_from} to {date_to}".format(
            date_from=dataset_window.ref_from.strftime("%Y-%m-%d"),
            date_to=dataset_window.ref_to.strftime("%Y-%m-%d"),
        )
        assert download_response.status_code == 200
        assert download_response.data
        assert (
            published_request["fileoutput"]
            in download_response.headers["Content-Disposition"]
        )
        # La chiave RedBeat esisteva ed eseguiva data_extract per l'utente e la
        # schedule del test (primo e decimo argomento del task).
        assert periodic_task is not None
        assert periodic_task.task == "data_extract"
        assert periodic_task.args[0] == schedules_user.user_id
        assert str(periodic_task.args[9]) == schedule_id
        # Dopo la DELETE reale celerybeat non ha piu nulla da eseguire.
        assert periodic_task_after_delete is None
    finally:
        download_response.close()