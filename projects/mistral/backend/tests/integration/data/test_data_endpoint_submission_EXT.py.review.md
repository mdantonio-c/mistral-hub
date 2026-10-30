# Review — `test_data_endpoint_submission_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** del contratto `POST /data` lato submission, sopra il baseline auth.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/test_data_endpoint_submission_EXT.py](projects/mistral/backend/tests/integration/data/test_data_endpoint_submission_EXT.py)
- **Scopo**: verificare il **percorso di submission** di `POST /data`: happy path (creazione `Request` + routing Celery), i tre rami del flag `push` (queue utente assente, queue inesistente lato broker, queue valida con persistenza della `pushing_queue`) e il ramo quota su dati osservati (`OBS`) negato.
- **Tipologia**: test di **integrazione HTTP** (controller reale + schema reale + DB SQLAlchemy reale) con **fake locali** per Celery/RabbitMQ/Arkimet e `monkeypatch` mirato su due funzioni di modulo. Marker: `integration`, `deterministic`. 5 test.
- **Isolamento**: non avvia worker, broker o estrazioni reali; nessun `pytest.skip` → **nessun test silenziosamente saltabile**.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Data.post` | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | Endpoint `POST /data`: sequenza di guardie (rate limit, catalogo, formato, licenze, postprocessors, output_format, push, only_reliable, quota OBS) → `create_request_record` → `send_task` → `202`. |
| `repo.check_user_request_limit` | [services/sqlapi_db_manager.py#L644](projects/mistral/backend/services/sqlapi_db_manager.py#L644) | Limite richieste/ora (qui non scatta: utenti freschi). |
| `repo.get_datasets` | [services/sqlapi_db_manager.py#L482](projects/mistral/backend/services/sqlapi_db_manager.py#L482) | Catalogo autorizzato: il payload usa `arkimet_id`, confrontato con `ds["id"]`. |
| `repo.get_license_group` | [services/sqlapi_db_manager.py#L546](projects/mistral/backend/services/sqlapi_db_manager.py#L546) | Verifica gruppo licenza comune (qui dataset singolo → ok). |
| `repo.create_request_record` | [services/sqlapi_db_manager.py#L111](projects/mistral/backend/services/sqlapi_db_manager.py#L111) | Crea `Request(status="CREATED")`; poi l'endpoint sovrascrive `task_id`/`status`. |
| `queue_sorting` | [tasks/data_extraction_utilities.py#L6](projects/mistral/backend/tasks/data_extraction_utilities.py#L6) | Sceglie la coda da `(data_type, is_operational)`; usa **solo** `reftime["date_from"]`. Reftime 2020 → `archived_forecast` deterministico. |
| `data_extract` (nome task) | [tasks/data_extraction.py#L44](projects/mistral/backend/tasks/data_extraction.py#L44) | Registrato come `"data_extract"`; **mai eseguito** (solo `send_task` registrato dal fake). |
| `get_observed_data_size_count` / `check_user_quota_for_observed_data` | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | Funzioni di modulo del ramo OBS, **monkeypatchate** nel 5° test. |
| Modelli `Request` / `User` | [models/sqlalchemy.py#L36](projects/mistral/backend/models/sqlalchemy.py#L36) | `Request.args` (JSONB), `task_id` (unique), `status`; `User.amqp_queue`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py#L39](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO** (utenti, dataset, request, file). |
| `monkeypatch` | fixture | `pytest` | Applica i fake runtime; rollback automatico a fine test. |
| `create_synthetic_dataset` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Dataset/licenza/attribution sintetici + cleanup. |
| `create_data_endpoint_user` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Utente temporaneo con permessi + `amqp_queue` forzata sul DB. |
| `build_data_payload` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Body JSON con reftime sintetica `2020-01-01`. |
| `patch_data_endpoint_runtime` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | `monkeypatch` su `arki/celery/rabbitmq` del modulo endpoint. |
| `RecordingCelery` / `FakeRabbit` | fake locali | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Registrano `send_task` / `queue_exists` senza servizi reali. |
| `latest_request_for_user` / `delete_requests_for_user` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Lettura ultima request / cleanup request. |
| `queue_sorting` | funzione reale | [tasks/data_extraction_utilities.py#L6](projects/mistral/backend/tasks/data_extraction_utilities.py#L6) | Ricalcolata nel test per confronto con la coda scelta dall'endpoint. |
| `DiskQuotaException` | eccezione | [mistral/exceptions.py](projects/mistral/backend/exceptions.py) | Sollevata dal fake quota nel 5° test → `Forbidden`. |
| `DatasetCategories` | enum | [models/sqlalchemy.py#L132](projects/mistral/backend/models/sqlalchemy.py#L132) | Categoria `OBS` per il dataset osservato. |

## 4. Analisi dettagliata di ogni test

### `test_post_data_happy_path_creates_request_and_records_celery_routing`
- **Obiettivo**: contratto principale di `POST /data` — `202`, `Request` persistita, routing Celery corretto, identificativi nel body.
- **Backend coinvolto**: intera `Data.post` fino a `send_task`; `create_request_record`; `queue_sorting`.
- **Flusso**: dataset FOR/grib pubblico → utente autorizzato → `patch_data_endpoint_runtime(celery_fake, format="grib", category="FOR")` → `POST /data`.
- **Setup**: `cleanup_registry.add(delete_requests_for_user)`; `RecordingCelery(task_id="task-happy-path-ext")`; `expected_queue = queue_sorting("FOR", {date_from: 2020-01-01Z})`.
- **Assert**:
  - HTTP `202`; `request` non `None`; `request.name`, `request.status == "PENDING"`, `request.task_id == "task-happy-path-ext"`.
  - `request.args["datasets"] == [arkimet_id]`; `request.args["reftime"]["from"].startswith("2020-01-01T00:00:00")`.
  - `content["request_id"] == request.id`, `content["task_id"] == "task-happy-path-ext"`.
  - `len(sent_tasks) == 1`; `name == "data_extract"`; `args[0]==user_id`, `args[1]==[arkimet_id]`, `args[6]==request.id`; `kwargs["queue"]==kwargs["routing_key"]==expected_queue`.
- **Casi coperti**: happy path completo + side effect DB + contratto di dispatch (nome task, args posizionali, queue/routing).

### `test_post_data_push_requires_user_queue_before_contacting_rabbit`
- **Obiettivo**: con `push=true`, rifiutare **subito** l'utente senza `amqp_queue`, prima di creare request o contattare RabbitMQ.
- **Backend coinvolto**: ramo `if push:` → `pushing_queue = user.amqp_queue` → `None` → `Forbidden`.
- **Flusso**: utente con `amqp_queue=None` (default) → `patch_data_endpoint_runtime` (senza rabbit_fake) → `POST /data?push=true`.
- **Setup**: dataset + utente; nessun fake Rabbit (non deve essere raggiunto).
- **Assert**: `403`; `latest_request_for_user(...) is None` (nessuna request creata).
- **Casi coperti**: error path / autorizzazione push. Verifica anche l'**ordine**: il rifiuto precede sia `queue_exists` sia `create_request_record`.

### `test_post_data_push_rejects_missing_rabbit_queue`
- **Obiettivo**: con queue di profilo valida ma **inesistente** lato broker, respingere il push.
- **Backend coinvolto**: `pushing_queue = user.amqp_queue` (valorizzata) → `rabbit.queue_exists(...)` → `False` → `Forbidden`.
- **Flusso**: utente con `amqp_queue="queue.data.endpoint.ext"` → `FakeRabbit(exists=False)` → `POST /data?push=true`.
- **Setup**: `patch_data_endpoint_runtime(rabbit_fake=...)`.
- **Assert**: `403`; `rabbit_fake.checked_queues == ["queue.data.endpoint.ext"]` (la queue corretta è stata interrogata); nessuna request creata.
- **Casi coperti**: error path / integrazione broker. Conferma che il backend avanza fino a `queue_exists` e usa esattamente la queue del profilo.

### `test_post_data_push_positive_persists_pushing_queue`
- **Obiettivo**: con Rabbit positivo, la `pushing_queue` deve finire **sia** nel record `Request.args` **sia** negli argomenti del task.
- **Backend coinvolto**: ramo push completo → `create_request_record` (args con `pushing_queue`) → `send_task` (arg posizionale 8).
- **Flusso**: utente con `amqp_queue="queue.push.ok.ext"` → `FakeRabbit(exists=True)` + `RecordingCelery(task_id="task-push-positive-ext")` → `POST /data?push=true`.
- **Setup**: `cleanup_registry.add(delete_requests_for_user)`.
- **Assert**: `202`; `checked_queues == ["queue.push.ok.ext"]`; `request.args["pushing_queue"] == "queue.push.ok.ext"`; `sent_tasks[0]["args"][8] == "queue.push.ok.ext"`.
- **Casi coperti**: happy path push. Il contratto osservabile **non** è la notifica AMQP reale, ma la **persistenza** del dato che il task userà in background.

### `test_post_data_observed_quota_forbidden_uses_fake_size_and_quota_checks`
- **Obiettivo**: ramo `OBS` → `403` quota senza toccare DBALLE né misurazioni reali di size.
- **Backend coinvolto**: `if data_type == "OBS" and not postprocessors and not force_obs_download:` → `get_observed_data_size_count` → `check_user_quota_for_observed_data` → `DiskQuotaException` → `Forbidden`.
- **Flusso**: dataset `OBS`/bufr → `patch_data_endpoint_runtime(format="bufr", category="OBS")` → `monkeypatch` di `get_observed_data_size_count` (→ `4096`, truthy) e di `check_user_quota_for_observed_data` (→ `raise DiskQuotaException`) → `POST /data`.
- **Setup**: i due `monkeypatch.setattr` sono sui **nomi di modulo** `data_endpoint_module.*` (l'endpoint li risolve dai globals a runtime — vedi §6).
- **Assert**: `403`; nessuna request creata (la quota è controllata **prima** di `create_request_record`).
- **Casi coperti**: error path / quota OBS. Protegge l'ordine “stima size → quota → 403” senza catalogo osservativo reale.

## 5. Call chain

```
POST /api/data[?push=<bool>]  → auth.require() (401 anonimo)
  → use_kwargs(query: push) + use_kwargs(DataExtraction)   (pre_load: check_output_format, Reftime.check_reftime)
  → Data.post:
      1. repo.check_user_request_limit                      (qui non scatta)
      2. repo.get_datasets → ds_name ∉ catalogo → 404
      3. arki.get_datasets_format → None → 400               [FAKE = "grib"/"bufr"]
      4. repo.get_license_group → None → 400
      5. filters &= arki.is_filter_allowed                   [FAKE = True]
      7. postprocessors? → get_user_permissions(allowed_postprocessing) → 401
      8. output_format incompat. grib → 400
      9. if push: user.amqp_queue falsy → 403
                  rabbitmq.get_instance().queue_exists(...) falsy → 403   [FAKE FakeRabbit]
     10. data_type = arki.get_datasets_category             [FAKE = "FOR"/"OBS"]
     11. only_reliable & data_type!="OBS" → 400
     12. data_type=="OBS" & !pp & !force → get_observed_data_size_count → check_user_quota_for_observed_data
                                            → DiskQuota/MaxOutputSize → 403   [MONKEYPATCH]
     13. repo.create_request_record (status CREATED)
         celery.get_instance().celery_app.send_task("data_extract",
             args=(user.id, datasets, parsed_reftime, filters, postprocessors, output_format,
                   request.id, only_reliable, pushing_queue, None, False, False, force_obs_download),
             countdown=1, queue=queue_sorting(data_type, reftime), routing_key=<idem>)   [FAKE RecordingCelery]
         request.task_id = task.id; request.status = task.status (PENDING); commit
     14. response({request_id, task_id}, 202)
```

## 6. Comportamenti nascosti

- **`queue_sorting` usa solo `date_from`**: il test ricostruisce `queue_sorting("FOR", {"date_from": ...})` ignorando `date_to`, coerente con [tasks/data_extraction_utilities.py#L6](projects/mistral/backend/tasks/data_extraction_utilities.py#L6). Reftime 2020 ⇒ `now - date_from` ≫ 3 giorni ⇒ `is_operational=False` ⇒ `archived_forecast` **sempre** (determinismo garantito dalla data sintetica vecchia).
- **Monkeypatch su funzioni di modulo (5° test)**: `get_observed_data_size_count` e `check_user_quota_for_observed_data` sono chiamate in `data.py` come **nomi nudi**; patcharle su `data_endpoint_module.<name>` funziona perché Python le risolve dai globals del modulo a runtime. È corretto ma sottile: un refactor che le importasse altrove invaliderebbe il patch.
- **`status` finale = `PENDING`**: `create_request_record` imposta `"CREATED"`, poi l'endpoint sovrascrive con `task.status` (`states.PENDING` del fake) e committa. Il test verifica lo stato **finale**.
- **Ordine dei rami come contratto implicito**: i test push/quota asseriscono *anche* l'assenza di request → verificano che il rifiuto avvenga **prima** di `create_request_record`. Se un refactor spostasse `create_request_record` più in alto, questi assert fallirebbero (rete di sicurezza utile).
- **`amqp_queue` forzata sul DB**: il valore letto da `user.amqp_queue` nell'endpoint proviene dall'utente autenticato ricaricato dal DB; l'helper lo imposta via `db_user.amqp_queue` + commit (vedi review di `support_EXT.py`).
- **Nessun `pytest.skip`**: a differenza dei domini che usano `dataset_window`/`datasets`, qui tutto è sintetico → nessun test si autoesclude silenziosamente.
- **`data_extract` mai eseguito**: il fake registra la submission; nessuna estrazione, nessun file prodotto, nessun accesso Arkimet/DBALLE.
- **Visibilità dataset via `open_dataset`**: i dataset sono pubblici e l'utente ha `open_dataset=True`, quindi l'autorizzazione passa senza esercitare il ramo dataset privati (vedi review di `support_EXT.py`).

## 7. Checklist di revisione

- [ ] Confermare la mappatura posizionale degli `args` di `send_task` (indici 0/1/6/8) come contratto stabile verso `data_extract`; è fragile a riordini della tupla.
- [ ] Verificare che `archived_forecast` resti il risultato atteso di `queue_sorting` per reftime 2020 (dipende dalla soglia `days_for_operationals=3`).
- [ ] Confermare che il ramo OBS sia raggiungibile solo con `not postprocessors and not force_obs_download` (i test non variano `force_obs_download`).
- [ ] Verificare che il monkeypatch sui nomi di modulo del ramo OBS resti valido dopo eventuali refactor di import in `data.py`.
- [ ] Confermare che `request.status == "PENDING"` derivi dalla sovrascrittura post-`create_request_record` e non da un default.

## 8. Possibili criticità

- **Accoppiamento all'ordine posizionale degli args del task**: gli assert su `args[6]`/`args[8]` rcompaiono in più test; un cambio di firma di `data_extract`/della tupla romperebbe i test pur essendo il comportamento corretto.
- **Determinismo basato su data “sufficientemente vecchia”**: `archived_forecast` dipende dalla soglia di 3 giorni; se la logica `queue_sorting` cambiasse soglia/segno, il confronto resterebbe verde solo perché il test ricalcola la stessa funzione (non un valore atteso indipendente).
- **Ramo OBS coperto solo nel caso negato**: il path “OBS entro quota → 202” non è testato qui; coperta solo la negazione via `DiskQuotaException` (non `MaxOutputSizeExceeded`).
- **Path push reale non esercitato**: si valida la persistenza della `pushing_queue`, non la pubblicazione AMQP effettiva (per design).
- **Dipendenza dalla disciplina di patch**: senza `patch_data_endpoint_runtime` i test contatterebbero Arkimet reale (config inesistente per dataset sintetici) — l'isolamento non è `autouse`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_post_data_happy_path_creates_request_and_records_celery_routing` | `Data.post` + `create_request_record` + `queue_sorting` | 202, Request persistita, routing/args Celery | `RecordingCelery` + `patch_data_endpoint_runtime` (arki) | `client`, `cleanup_registry`, `monkeypatch` | Alta |
| `test_post_data_push_requires_user_queue_before_contacting_rabbit` | ramo push (`amqp_queue` assente) | 403 + nessuna request | `patch_data_endpoint_runtime` (arki/celery) | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `test_post_data_push_rejects_missing_rabbit_queue` | ramo push (`queue_exists=False`) | 403 + queue interrogata + nessuna request | `FakeRabbit(exists=False)` | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `test_post_data_push_positive_persists_pushing_queue` | ramo push positivo + persistenza | 202 + `pushing_queue` in args DB e task | `FakeRabbit(exists=True)` + `RecordingCelery` | `client`, `cleanup_registry`, `monkeypatch` | Alta |
| `test_post_data_observed_quota_forbidden_uses_fake_size_and_quota_checks` | ramo OBS quota | 403 + nessuna request | `monkeypatch` di `get_observed_data_size_count` + `check_user_quota_for_observed_data` | `client`, `cleanup_registry`, `monkeypatch` | Alta |
