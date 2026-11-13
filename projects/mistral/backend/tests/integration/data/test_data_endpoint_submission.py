# Ambito: copre happy path con fake Celery, rami push con queue utente assente o
# non esistente, persistenza della pushing_queue nel record Request e ramo quota OBS
# vietato tramite fake locali.
# Finestra dati: nessuna finestra meteo reale e necessaria; le reftime sono sintetiche,
# stabili e abbastanza vecchie da produrre queue archived in modo deterministico.
# Runtime fake: arki, celery, rabbitmq, get_observed_data_size_count e
# check_user_quota_for_observed_data vengono monkeypatchati sul modulo endpoint per
# evitare worker reali, DBALLE reale e AMQP reale.
# Cleanup: utenti temporanei, dataset sintetici, request create dall'endpoint e file
# eventuali sono registrati nel cleanup_registry o rimossi da helper dedicati.

"""Test di submission per POST /data con fake locali e stato sintetico controllato."""

from __future__ import annotations

from datetime import datetime, timezone

import mistral.endpoints.data as data_endpoint_module
import pytest
from mistral.exceptions import DiskQuotaException
from mistral.models.sqlalchemy import DatasetCategories
from mistral.tasks.data_extraction_utilities import queue_sorting
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.integration.data.support import (
    FakeRabbit,
    RecordingCelery,
    build_data_payload,
    create_data_endpoint_user,
    create_synthetic_dataset,
    delete_requests_for_user,
    latest_request_for_user,
    patch_data_endpoint_runtime,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]

DATA_ENDPOINT = f"{API_URI}/data"


def test_post_data_happy_path_creates_request_and_records_celery_routing(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il contratto principale di POST /data con Celery fake e request persistita.

    Lo scenario usa un dataset forecast sintetico autorizzato tramite catalogo pubblico.
    Il test non pretende nessuna estrazione reale: controlla solo che il backend crei il
    record Request, scelga la queue corretta tramite queue_sorting e risponda con i due
    identificativi osservabili dal client HTTP.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    cleanup_registry.add(lambda: delete_requests_for_user(db, user.user_id))
    celery_fake = RecordingCelery(task_id="task-happy-path-ext")
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        celery_fake=celery_fake,
        dataset_format="grib",
        dataset_category="FOR",
    )
    payload = build_data_payload(
        [dataset.arkimet_id],
        request_name="submission-happy-path-ext",
    )
    expected_queue = queue_sorting(
        "FOR",
        {"date_from": datetime(2020, 1, 1, tzinfo=timezone.utc)},
    )

    # act
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    content = BaseTests().get_content(response)
    request = latest_request_for_user(db, user.user_id)
    assert response.status_code == 202
    assert request is not None
    assert request.name == "submission-happy-path-ext"
    assert request.status == "PENDING"
    assert request.task_id == "task-happy-path-ext"
    assert request.args["datasets"] == [dataset.arkimet_id]
    assert request.args["reftime"]["from"].startswith("2020-01-01T00:00:00")
    assert content["request_id"] == request.id
    assert content["task_id"] == "task-happy-path-ext"
    assert len(celery_fake.sent_tasks) == 1
    sent_task = celery_fake.sent_tasks[0]
    assert sent_task["name"] == "data_extract"
    assert sent_task["args"][0] == user.user_id
    assert sent_task["args"][1] == [dataset.arkimet_id]
    assert sent_task["args"][6] == request.id
    assert sent_task["kwargs"]["queue"] == expected_queue
    assert sent_task["kwargs"]["routing_key"] == expected_queue


def test_post_data_push_requires_user_queue_before_contacting_rabbit(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica che il ramo push rifiuti subito l'utente senza amqp_queue configurata.

    Questo caso protegge il contratto di autorizzazione lato endpoint: con `push=true`
    il backend deve fermarsi prima di creare una request o contattare RabbitMQ quando il
    profilo utente non espone nessuna queue di notifica.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    patch_data_endpoint_runtime(monkeypatch, data_endpoint_module)
    payload = build_data_payload([dataset.arkimet_id], request_name="missing-push-queue")

    # act
    response = client.post(f"{DATA_ENDPOINT}?push=true", headers=user.headers, json=payload)

    # assert
    assert response.status_code == 403
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_push_rejects_missing_rabbit_queue(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica che il backend respinga il push quando RabbitMQ non trova la queue utente.

    L'utente ha una amqp_queue valida a livello profilo, quindi il ramo deve avanzare
    fino al controllo queue_exists. Il fake Rabbit negativo consente di verificare questo
    contratto senza infrastruttura AMQP reale.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(
        client,
        cleanup_registry,
        dataset_ids=[dataset.id],
        amqp_queue="queue.data.endpoint.ext",
    )
    rabbit_fake = FakeRabbit(exists=False)
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        rabbit_fake=rabbit_fake,
    )
    payload = build_data_payload([dataset.arkimet_id], request_name="rabbit-negative")

    # act
    response = client.post(f"{DATA_ENDPOINT}?push=true", headers=user.headers, json=payload)

    # assert
    assert response.status_code == 403
    assert rabbit_fake.checked_queues == ["queue.data.endpoint.ext"]
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_push_positive_persists_pushing_queue(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica che con Rabbit positivo la pushing_queue finisca nel record Request.

    Il contratto osservabile qui non e la notifica AMQP reale, ma la persistenza del dato
    che il task usera poi in background. Per questo il test controlla risposta HTTP,
    request args e argomenti inviati al fake Celery.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(
        client,
        cleanup_registry,
        dataset_ids=[dataset.id],
        amqp_queue="queue.push.ok.ext",
    )
    cleanup_registry.add(lambda: delete_requests_for_user(db, user.user_id))
    rabbit_fake = FakeRabbit(exists=True)
    celery_fake = RecordingCelery(task_id="task-push-positive-ext")
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        celery_fake=celery_fake,
        rabbit_fake=rabbit_fake,
    )
    payload = build_data_payload([dataset.arkimet_id], request_name="push-positive")

    # act
    response = client.post(f"{DATA_ENDPOINT}?push=true", headers=user.headers, json=payload)

    # assert
    # args[8] di data_extract e la pushing_queue passata al task.
    request = latest_request_for_user(db, user.user_id)
    assert response.status_code == 202
    assert rabbit_fake.checked_queues == ["queue.push.ok.ext"]
    assert request is not None
    assert request.args["pushing_queue"] == "queue.push.ok.ext"
    assert celery_fake.sent_tasks[0]["args"][8] == "queue.push.ok.ext"


def test_post_data_observed_quota_forbidden_uses_fake_size_and_quota_checks(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 403 quota OBS senza toccare DBALLE reale o calcoli di size reali.

    Il ramo osservato del backend chiama prima una size estimation e poi il controllo di
    quota. Monkeypatchando entrambe le funzioni del modulo endpoint possiamo proteggere il
    contratto HTTP 403 in modo deterministico e leggero.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(
        cleanup_registry=cleanup_registry,
        db=db,
        category=DatasetCategories.OBS,
        fileformat="bufr",
    )
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_format="bufr",
        dataset_category="OBS",
    )
    monkeypatch.setattr(
        data_endpoint_module,
        "get_observed_data_size_count",
        lambda parsed_reftime, dataset_names, filters, license_group, output_format: 4096,
    )

    def _deny_observed_quota(user_id, db_handle, estimated_size) -> None:
        # Simuliamo esplicitamente il ramo quota piena senza dipendere da filesystem o
        # misurazioni reali della cartella output.
        raise DiskQuotaException("synthetic observed quota denial")

    monkeypatch.setattr(
        data_endpoint_module,
        "check_user_quota_for_observed_data",
        _deny_observed_quota,
    )
    payload = build_data_payload(
        [dataset.arkimet_id],
        request_name="observed-quota-denied",
    )

    # act
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # L'endpoint deve rispondere con 403 e fermarsi prima della creazione della request,
    # perche il contratto quota viene applicato prima del repository create_request_record.
    assert response.status_code == 403
    assert latest_request_for_user(db, user.user_id) is None


def test_post_data_unsupported_dataset_type_returns_400_without_request(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica che un tipo di dataset non supportato non crei request ne task.

    `queue_sorting` rifiuta il tipo prima della creazione del record Request: prima la
    request restava salvata in stato CREATED e il client riceveva un errore generico.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    cleanup_registry.add(lambda: delete_requests_for_user(db, user.user_id))
    celery_fake = patch_data_endpoint_runtime(
        monkeypatch,
        data_endpoint_module,
        dataset_category="UNKNOWN",
    )
    payload = build_data_payload([dataset.arkimet_id])

    # act
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    assert response.status_code == 400
    assert BaseTests().get_content(response) == "Unsupported dataset type: UNKNOWN"
    assert latest_request_for_user(db, user.user_id) is None
    assert celery_fake.sent_tasks == []


@pytest.mark.parametrize(
    ("reftime_from", "reftime_to"),
    [
        ("2020-01-01T00:00:00Z", "2020-01-01T01:00:00Z"),
        ("2020-01-01T02:00:00+02:00", "2020-01-01T03:00:00+02:00"),
        ("2019-12-31T19:00:00-05:00", "2019-12-31T20:00:00-05:00"),
    ],
    ids=["utc", "positive-offset", "negative-offset-previous-day"],
)
def test_post_data_saves_reftime_in_utc(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
    reftime_from: str,
    reftime_to: str,
) -> None:
    """Verifica che lo stesso istante, con qualunque fuso, dia la stessa finestra UTC.

    Prima l'offset veniva perso: l'ora locale era salvata come se fosse UTC.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    cleanup_registry.add(lambda: delete_requests_for_user(db, user.user_id))
    celery_fake = patch_data_endpoint_runtime(monkeypatch, data_endpoint_module)
    payload = build_data_payload(
        [dataset.arkimet_id], reftime_from=reftime_from, reftime_to=reftime_to
    )

    # act
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    expected_reftime = {
        "from": "2020-01-01T00:00:00.000000Z",
        "to": "2020-01-01T01:00:00.000000Z",
    }
    assert response.status_code == 202
    request = latest_request_for_user(db, user.user_id)
    assert request.args["reftime"] == expected_reftime
    assert celery_fake.sent_tasks[0]["args"][2] == expected_reftime
