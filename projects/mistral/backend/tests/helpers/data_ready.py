"""Helper di alto livello condivisi dai test di integrazione data-ready e schedule.

L'area data-ready della suite ripete spesso lo stesso tipo di setup:

- costruire un payload per ``/api/data/ready``,
- creare un utente temporaneo con i giusti permessi sui dataset,
- creare o cancellare schedule e righe di richiesta sintetiche,
- interrogare l'API finche gli effetti asincroni diventano visibili.

Tenere qui questa logica permette ai moduli di test di leggersi come brevi storie
di comportamento, invece di restare sepolti sotto chiamate API ripetitive e
dettagli di cleanup.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import mistral.endpoints.data_ready as data_ready_endpoint
import mistral.tasks.on_data_ready_extractions as on_data_ready_task
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    register_test_user_cleanup,
)
from mistral.tests.helpers.celery_fakes import (
    AcceptTasksWithoutRunningCelery,
    InlineDataReadyExtractionCelery,
)
from mistral.tests.helpers.polling import wait_until
from mistral.tests.helpers.runtime import TestRuntime
from mistral.tests.helpers.task_perimeter import confine_data_ready_schedules
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

DATA_READY_DATASET_NAME = "lm5"
SECOND_DATA_READY_DATASET_NAME = "lm2.2"
DATA_READY_DATASETS = [DATA_READY_DATASET_NAME, SECOND_DATA_READY_DATASET_NAME]
# Dominio riservato dalla RFC 2606: un indirizzo .invalid non viene mai consegnato.
UNDELIVERABLE_EMAIL_DOMAIN = "example.invalid"


def build_data_ready_payload(
    *,
    model: str,
    cluster: str = "g100",
    rundate: str,
) -> str:
    """Restituisce il body JSON esatto atteso dall'endpoint ``POST /api/data/ready``.

    I test usano questo helper per avviare il flusso data-ready con un modello di
    previsione, un nome di cluster e una data di run precisi, senza ripetere in
    ogni scenario la costruzione della richiesta.
    """
    return json.dumps({"Model": model, "Cluster": cluster, "rundate": rundate})


def create_data_ready_user(
    base: BaseTests,
    client: FlaskClient,
    test_runtime: TestRuntime,
    dataset_names: list[str],
    *,
    max_output_size: int = 1073741824,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo per gli scenari data-ready ed esegue il login.

    L'utente restituito ha quota e permessi sufficienti per creare schedule, avviare
    eventi data-ready e accedere ai dataset elencati in ``dataset_names``. L'helper
    converte anche i nomi dei dataset negli id numerici richiesti dall'API di
    creazione utenti. Un ``max_output_size`` piccolo fa rifiutare l'estrazione dal
    worker per superamento della quota.

    L'utente non riceve mai email reali: le notifiche di successo sono disattivate e
    l'indirizzo appartiene a un dominio riservato, usato dalle notifiche di errore
    che ``data_extract`` invia sempre. I worker Celery reali usano il mock SMTP solo
    negli stack inizializzati con ``rapydo --testing``.
    """
    db = sqlalchemy.get_instance()
    dataset_ids = [str(test_runtime.dataset_id(db, name)) for name in dataset_names]

    data: dict[str, Any] = {
        "disk_quota": 1073741824,
        "max_output_size": max_output_size,
        "allowed_postprocessing": True,
        "allowed_schedule": True,
        "open_dataset": True,
        "datasets": json.dumps(dataset_ids),
        # Senza questi due valori BaseTests sceglie a caso il flag e genera un
        # indirizzo Faker, spesso su domini reali come gmail.com.
        "notify_on_successful_request": False,
        "email": f"data-ready-{uuid4().hex[:12]}@{UNDELIVERABLE_EMAIL_DOMAIN}",
    }

    uuid, created_user = base.create_user(client, data, ["admin_root"])
    headers, _ = base.do_login(
        client, created_user.get("email"), created_user.get("password")
    )

    user = db.User.query.filter_by(uuid=uuid).first()
    assert user is not None
    # Se il campo sparisse dallo schema admin varrebbe il default True del customizer:
    # meglio fermarsi qui che lasciar partire email dai worker reali.
    assert user.notify_on_successful_request is False
    assert user.email.endswith(f"@{UNDELIVERABLE_EMAIL_DOMAIN}")

    return AuthenticatedTestUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
        email=user.email,
    )


def create_schedule(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    body: str,
) -> str:
    """Crea una schedule con ``POST /api/schedules`` e ne restituisce l'id.

    Cosi i test restano concentrati sul comportamento delle schedule invece che sul
    parsing della risposta. L'helper verifica che la schedule sia stata accettata
    (202) ed estrae l'identificativo creato dal payload JSON restituito.
    """
    response = client.post(
        f"{API_URI}/schedules",
        headers=headers,
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 202
    return str(base.get_content(response).get("schedule_id"))


def set_schedule_active(
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
    *,
    is_active: bool,
) -> None:
    """Attiva o disattiva una schedule con ``PATCH /api/schedules/<id>``.

    Diversi scenari data-ready usano la stessa definizione di schedule ma con uno
    stato di attivazione diverso. Questo helper centralizza la richiesta ``PATCH``
    e verifica che il cambio di stato sia riuscito.
    """
    response = client.patch(
        f"{API_URI}/schedules/{schedule_id}",
        headers=headers,
        data=json.dumps({"is_active": is_active}),
        content_type="application/json",
    )
    assert response.status_code == 200


def delete_request(client: FlaskClient, headers: Any, request_id: int | str) -> None:
    """Cancella una richiesta con ``DELETE /api/requests/<id>``.

    I test lo usano durante il cleanup o quando devono rimuovere una richiesta
    creata automaticamente prima di costruire uno scenario piu controllato.
    """
    response = client.delete(f"{API_URI}/requests/{request_id}", headers=headers)
    assert response.status_code == 200


def delete_schedule(client: FlaskClient, headers: Any, schedule_id: int | str) -> None:
    """Cancella una schedule con ``DELETE /api/schedules/<id>``.

    Piccolo wrapper di comodo usato soprattutto dal codice di cleanup, cosi il corpo
    dei test non deve ripetere le asserzioni sullo status code del teardown.
    """
    response = client.delete(f"{API_URI}/schedules/{schedule_id}", headers=headers)
    assert response.status_code == 200


def list_user_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> list[dict[str, Any]]:
    """Restituisce le richieste visibili all'utente autenticato come semplice lista.

    Chiama ``GET /api/requests``, che puo restituire legittimamente un payload
    vuoto. L'helper normalizza quel caso a ``[]``, cosi i test ragionano sul numero
    di elementi senza ripetere la gestione difensiva della risposta.
    """
    response = client.get(f"{API_URI}/requests", headers=headers)
    assert response.status_code == 200
    return base.get_content(response) or []


def list_user_schedules(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> list[dict[str, Any]]:
    """Restituisce le schedule visibili all'utente autenticato come semplice lista.

    Come l'helper analogo per le richieste, chiama ``GET /api/schedules``, nasconde
    piccoli dettagli sulla forma della risposta e garantisce che il chiamante riceva
    sempre una lista da scorrere o contare senza rischi.
    """
    response = client.get(f"{API_URI}/schedules", headers=headers)
    assert response.status_code == 200
    return base.get_content(response) or []


def list_schedule_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
) -> list[dict[str, Any]]:
    """Restituisce solo le righe di richiesta concrete generate da una schedule.

    L'endpoint ``GET /api/schedules/<id>/requests`` puo includere elementi che non
    sono semplici dizionari di richiesta. L'helper li scarta, cosi i test possono
    confrontare il numero di richieste e ispezionarne il payload senza altri
    controlli.
    """
    response = client.get(
        f"{API_URI}/schedules/{schedule_id}/requests?last=False",
        headers=headers,
    )
    assert response.status_code == 200
    content = base.get_content(response) or []
    return [item for item in content if isinstance(item, dict)]


def wait_for_schedule_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    schedule_id: str,
    *,
    expected_count: int,
    timeout: float = 60,
    interval: float = 5,
) -> list[dict[str, Any]]:
    """Interroga una schedule finche l'API espone il numero atteso di richieste.

    Anche nei test lo stato osservabile puo arrivare con un leggero ritardo rispetto
    all'azione che lo ha causato. Questo helper esegue il ciclo di retry e
    restituisce la lista finale delle richieste solo quando il conteggio desiderato
    e visibile.
    """
    def expected_requests():
        """Restituisce la lista delle richieste solo se ha la lunghezza attesa."""
        requests = list_schedule_requests(base, client, headers, schedule_id)
        return requests if len(requests) == expected_count else False

    return wait_until(
        expected_requests,
        timeout=timeout,
        interval=interval,
        message=(
            f"Expected {expected_count} requests for schedule {schedule_id}"
        ),
    )


def post_data_ready(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
    *,
    model: str,
    rundate: str,
    cluster: str = "g100",
) -> tuple[Any, Any]:
    """Invia un evento a ``POST /api/data/ready`` e restituisce risposta e contenuto.

    Alcuni test hanno bisogno dell'oggetto risposta Flask grezzo, altri soprattutto
    del body JSON decodificato. L'helper restituisce entrambi, cosi il chiamante puo
    verificare status code e payload senza inviare la richiesta due volte.
    """
    body = build_data_ready_payload(model=model, rundate=rundate, cluster=cluster)
    response = client.post(
        f"{API_URI}/data/ready",
        headers=headers,
        data=body,
        content_type="application/json",
    )
    return response, base.get_content(response)


def trigger_data_ready_and_wait_accepted(
    client: FlaskClient,
    headers: Any,
    *,
    model: str,
    rundate: str,
    cluster: str = "g100",
    timeout: float = 30,
    interval: float = 3,
):
    """Ripete ``POST /api/data/ready`` finche l'endpoint accetta l'evento con ``202``.

    L'endpoint puo rifiutare o ritardare per poco l'accettazione mentre il runtime
    circostante si stabilizza. Invece di far dormire ogni test alla cieca, l'helper
    interroga l'endpoint finche compare la risposta di accettazione attesa o scade
    il timeout.
    """
    body = build_data_ready_payload(model=model, rundate=rundate, cluster=cluster)

    def data_ready_accepted():
        """Restituisce la risposta solo quando l'endpoint segnala l'accettazione."""
        response = client.post(
            f"{API_URI}/data/ready",
            headers=headers,
            data=body,
            content_type="application/json",
        )
        return response if response.status_code == 202 else False

    return wait_until(
        data_ready_accepted,
        timeout=timeout,
        interval=interval,
        message="data/ready did not return 202 within timeout",
    )


def trigger_data_ready_inline(
    monkeypatch: Any,
    client: FlaskClient,
    headers: Any,
    db: Any,
    *,
    model: str,
    rundate: str,
    schedule_ids: Iterable[int | str],
    cluster: str = "g100",
):
    """Invia un evento data-ready ed esegue il launcher dentro il processo del test.

    Esercita ``POST /api/data/ready`` e il task
    ``launch_all_on_data_ready_extractions``. Il launcher reale scorre tutte le
    schedule del database: ``schedule_ids`` lo limita alle schedule create dal
    test chiamante.
    """
    endpoint_celery = AcceptTasksWithoutRunningCelery(
        "launch_all_on_data_ready_extractions"
    )
    monkeypatch.setattr(
        data_ready_endpoint.celery,
        "get_instance",
        lambda: endpoint_celery,
    )
    response = trigger_data_ready_and_wait_accepted(
        client,
        headers,
        model=model,
        rundate=rundate,
        cluster=cluster,
    )
    assert len(endpoint_celery.sent_tasks) == 1

    monkeypatch.setattr(
        on_data_ready_task.celery,
        "get_instance",
        lambda: InlineDataReadyExtractionCelery(db),
    )
    confine_data_ready_schedules(monkeypatch, schedule_ids)
    on_data_ready_task.launch_all_on_data_ready_extractions.run(
        model,
        datetime.strptime(rundate, "%Y%m%d%H"),
    )
    return response


def create_schedule_request_record(
    db,
    user_id: int,
    request_name: str,
    *,
    dataset_name: str,
    reftime: str,
    schedule_id: str,
    submission_date: datetime | None = None,
    status: str | None = None,
):
    """Inserisce una richiesta sintetica di schedule direttamente nel database di test.

    I test sulle schedule periodiche hanno spesso bisogno di una storia di richieste
    gia esistente per verificare se un nuovo evento data-ready debba generare una
    richiesta in piu. Questo helper prepara quella storia (tramite
    ``SqlApiDbManager.create_request_record``) senza invocare il vero worker di
    estrazione.
    """
    request = repo.create_request_record(
        db,
        user_id,
        request_name,
        {
            "datasets": dataset_name,
            "reftime": reftime,
            "filters": [],
            "postprocessors": [],
            "output_format": None,
            "only_reliable": True,
            "pushing_queue": None,
        },
        schedule_id,
        True,
    )

    if submission_date is not None:
        request.submission_date = submission_date
    if status is not None:
        request.status = status

    db.session.add(request)
    db.session.commit()
    return request


def delete_all_user_requests(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> None:
    """Cancella tutte le richieste visibili all'utente (``DELETE /api/requests/<id>``).

    Ogni cancellazione deve rispondere 200: un errore interrompe il cleanup.
    """
    for request in list_user_requests(base, client, headers):
        delete_request(client, headers, request.get("id"))


def delete_all_user_schedules(
    base: BaseTests,
    client: FlaskClient,
    headers: Any,
) -> None:
    """Cancella tutte le schedule visibili all'utente (``DELETE /api/schedules/<id>``).

    Le voci senza id vengono saltate; ogni cancellazione deve rispondere 200,
    altrimenti il cleanup si interrompe.
    """
    for schedule in list_user_schedules(base, client, headers):
        schedule_id = schedule.get("schedule_id") or schedule.get("id")
        if schedule_id is None:
            continue
        delete_schedule(client, headers, schedule_id)


def register_data_ready_user_cleanup(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    user: AuthenticatedTestUser,
) -> None:
    """Registra le azioni di cleanup tipiche di uno scenario data-ready.

    I test data-ready possono creare schedule, richieste, file dell'utente e l'utente
    stesso. Questo helper registra il teardown nell'ordine corretto, cosi i test
    successivi non ereditano stato residuo dagli scenari precedenti: per il LIFO del
    registro vengono cancellate prima le richieste, poi le schedule e infine
    l'utente con i suoi file.
    """
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    cleanup_registry.add(
        lambda: delete_all_user_schedules(base, client, user.headers)
    )
    cleanup_registry.add(
        lambda: delete_all_user_requests(base, client, user.headers)
    )


def register_schedule_cleanup(
    client: FlaskClient,
    cleanup_registry,
    headers: Any,
    schedule_id: str,
) -> None:
    """Registra la cancellazione differita di una schedule creata nel test corrente.

    I test che creano schedule vogliono di solito che il cleanup avvenga anche se
    un'asserzione fallisce a meta. Questo helper aggancia quel passo di teardown al
    registro di cleanup condiviso.
    """
    cleanup_registry.add(lambda: delete_schedule(client, headers, schedule_id))