# EXTENSION TRACEABILITY - Prompt 02, contratto POST /data lato submission.
# Origine: questo modulo estende la copertura del dominio integration/data senza
# modificare il baseline auth test_data_endpoint_auth.py e senza introdurre fixture
# globali; usa solo helper locali di support_EXT.py.
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
# Baseline non toccata: il file aggiunge solo casi EXT e non cambia i test legacy.

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

from mistral.tests.integration.data.support_EXT import (
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
    # Prepariamo uno scenario minimale ma completo: dataset sintetico, utente temporaneo,
    # cleanup della request prodotta dall'endpoint e fake Celery che registra send_task.
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
    # Eseguiamo la singola chiamata HTTP reale che deve attraversare auth, schema,
    # validazione endpoint, repository layer e submit sintetica verso Celery.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # Colleghiamo prima il payload HTTP alla request persistita, poi al task sintetico
    # registrato dal fake, cosi il contratto viene verificato da piu lati osservabili.
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
    # Prepariamo solo il minimo indispensabile: dataset sintetico valido, utente senza
    # queue AMQP e fake runtime locale per evitare che il test dipenda da servizi esterni.
    db = sqlalchemy.get_instance()
    dataset = create_synthetic_dataset(cleanup_registry=cleanup_registry, db=db)
    user = create_data_endpoint_user(client, cleanup_registry, dataset_ids=[dataset.id])
    patch_data_endpoint_runtime(monkeypatch, data_endpoint_module)
    payload = build_data_payload([dataset.arkimet_id], request_name="missing-push-queue")

    # act
    # La chiamata forza il ramo push tramite query string, come farebbe un client reale.
    response = client.post(f"{DATA_ENDPOINT}?push=true", headers=user.headers, json=payload)

    # assert
    # Il backend deve rispondere con 403 e non deve lasciare alcuna request persistita.
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
    # Costruiamo un utente con queue salvata nel DB e un fake Rabbit configurato per
    # negare l'esistenza della queue, mantenendo invariato il resto del runtime.
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
    # Eseguiamo una sola submit push per verificare il ramo 403 guidato da Rabbit fake.
    response = client.post(f"{DATA_ENDPOINT}?push=true", headers=user.headers, json=payload)

    # assert
    # Il backend deve riportare il rifiuto e lasciare visibile quale queue e stata
    # controllata dal fake, senza creare request persistite.
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
    # Prepariamo dataset e utente con queue nota, registriamo cleanup delle request e
    # usiamo fake Rabbit/Celery per ispezionare l'intero flusso senza side effect esterni.
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
    # La chiamata attiva il ramo push reale dell'endpoint, ma tutta la parte di broker e
    # task dispatch resta confinata nei fake locali.
    response = client.post(f"{DATA_ENDPOINT}?push=true", headers=user.headers, json=payload)

    # assert
    # Verifichiamo che queue_exists sia stato consultato, che la request sia persistita e
    # che la pushing_queue sia passata sia al DB sia agli argomenti del task sintetico.
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
    # Creiamo un dataset OBS sintetico e sostituiamo i due punti variabili del runtime:
    # stima dimensione e controllo quota. Nessun worker o estrazione reale deve partire.
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
    # La richiesta usa il percorso HTTP reale ma forza il ramo quota attraverso fake
    # locali, evitando qualsiasi accesso a DBALLE o a dati osservativi esterni.
    response = client.post(DATA_ENDPOINT, headers=user.headers, json=payload)

    # assert
    # L'endpoint deve rispondere con 403 e fermarsi prima della creazione della request,
    # perche il contratto quota viene applicato prima del repository create_request_record.
    assert response.status_code == 403
    assert latest_request_for_user(db, user.user_id) is None