# Review — `test_schedule_opendata_bridge.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo **baseline** (non `*_EXT`): copre il ponte storico *schedule → request opendata → listing/download*.
> **Due percorsi in un solo file**: un test `deterministic` (fake Celery inline) e un test `async_real` (catena reale beat → broker → worker). Documentati separatamente in §6.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/schedules/test_schedule_opendata_bridge.py](projects/mistral/backend/tests/integration/schedules/test_schedule_opendata_bridge.py)
- **Scopo**: verificare end-to-end che una schedule (on-data-ready oppure crontab) con `opendata=True` produca una `Request` `SUCCESS` con file, pubblicata nell'opendata listing e **scaricabile**.
- **Tipologia**: integrazione HTTP + scheduling. Marker di modulo: `pytestmark = [pytest.mark.integration, pytest.mark.runtime_sensitive]`. Marker **per-test aggiuntivi**:
  - `test_on_data_ready_schedule_publishes_opendata_package` → `@pytest.mark.deterministic` (trasporto Celery sostituito da fake, task eseguito **inline in-process**);
  - `test_crontab_schedule_publishes_opendata_package` → `@pytest.mark.async_real` (nessun fake: attende la catena reale RedBeat/celerybeat → RabbitMQ → worker).
- **Dataset reale**: `BRIDGE_DATASET_NAME = DATA_READY_DATASET_NAME` (`lm5`). Finestra dati derivata da `/api/fields` (vedi skip silenzioso, §6/§8).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `SingleSchedule.post` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L408) | Creazione schedule on-data-ready/crontab con `opendata=True` (richiede `admin_root`). |
| `DataReady.post` | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py#L35) | `POST /api/data/ready` → **202**; submette `launch_all_on_data_ready_extractions`. |
| `launch_all_on_data_ready_extractions` | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py#L11) | **Logica reale** di scheduling on-data-ready: filtra schedule per modello/run/periodo e submette `data_extract`. |
| task `data_extract` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py) | Estrazione reale: crea il file e pubblica l'opendata package (eseguito inline nel test deterministico, dal worker reale nel crontab). |
| `OpendataFileList.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L36) | `GET /api/datasets/<ds>/opendata?q=…` — listing per `reftime`; calcola il campo `date`. |
| `OpendataDownloadFile.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L203) | `GET /api/opendata/<filename>` — download come attachment (`Content-Disposition`). |
| `ScheduledRequests.get` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L998) | `GET /schedules/<id>/requests` usato dal poller per leggere `status`/`fileoutput`. |
| `SqlApiDbManager.get_schedule_requests` / `get_last_scheduled_request` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L208) | Sorgente dei dati di richiesta letti in polling. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO** (schedule + utente). |
| `schedules_base` | fixture **conftest locale** | [schedules/conftest.py](projects/mistral/backend/tests/integration/schedules/conftest.py) | `BaseTests()` + **override** `SingleSchedule.ON_DATA_READY_DATASETS` su `lm5` (indispensabile per il ramo on-data-ready). |
| `schedules_admin_headers` | fixture **conftest locale** | [schedules/conftest.py](projects/mistral/backend/tests/integration/schedules/conftest.py) | Login admin di default; usata per `POST /data/ready`. |
| `schedules_user` | fixture **conftest locale** | [schedules/conftest.py](projects/mistral/backend/tests/integration/schedules/conftest.py) | **Super-utente `admin_root`** via `create_data_ready_user`; `pytest.skip` se `lm5` assente. |
| `monkeypatch` | fixture | `pytest` | (solo test deterministico) sostituisce il **trasporto** Celery. |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | `/api/fields` → finestra reftime; **`pytest.skip` su 404** (skip silenzioso). |
| `build_on_data_ready_schedule` / `build_crontab_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Body schedule (`opendata=True`). |
| `create_schedule` / `register_schedule_cleanup` / `list_schedule_requests` / `trigger_data_ready_and_wait_accepted` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | CRUD schedule, polling data-ready (retry con side effect). |
| `AcceptTasksWithoutRunningCelery` / `InlineDataExtractCelery` | fake | [tests/helpers/celery_fakes.py](projects/mistral/backend/tests/helpers/celery_fakes.py) | (solo deterministico) accetta la submission senza inviarla / esegue `data_extract` reale inline. |
| `wait_until` | helper | [tests/helpers/polling.py](projects/mistral/backend/tests/helpers/polling.py) | Polling su predicato osservabile. |
| `wait_for_schedule_requests` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Importato; nel corpo si usa il poller locale `_wait_for_successful_schedule_request`. |
| `ScheduleRequestFailed` | classe locale | questo file | Sottoclasse di `AssertionError`: il poller la solleva se la richiesta va in `FAILURE`. |

## 4. Analisi dettagliata di ogni test

### `test_on_data_ready_schedule_publishes_opendata_package` — `deterministic` + `runtime_sensitive`
- **Obiettivo**: una schedule **on-data-ready** opendata produce un package scaricabile, con flusso interamente sincrono e deterministico.
- **Backend coinvolto**: `SingleSchedule.post` (reale) → `DataReady.post` (reale) → `launch_all_on_data_ready_extractions.run` (**logica reale**, eseguita a mano nel test) → `data_extract` (**reale**, inline) → opendata listing + download.
- **Flusso** (helper `_trigger_data_ready_schedule_inline`):
  1. `fetch_dataset_window(lm5)` (→ skip se 404);
  2. `build_on_data_ready_schedule(opendata=True, run_filter=[ref_run[0]])`;
  3. `monkeypatch` `schedules_endpoint.celery.get_instance` → `AcceptTasksWithoutRunningCelery("data_extract")` (la prima submission della `post` non parte);
  4. `create_schedule` (reale) + cleanup;
  5. `monkeypatch` `data_ready_endpoint.celery.get_instance` → `AcceptTasksWithoutRunningCelery("launch_all_on_data_ready_extractions")`; `trigger_data_ready_and_wait_accepted` → `POST /data/ready` **202**;
  6. `monkeypatch` `on_data_ready_task.celery.get_instance` → `InlineDataExtractCelery()`; il test **esegue direttamente** `launch_all_on_data_ready_extractions.run(model, rundate)` → la submission interna di `data_extract` viene eseguita **inline** (file + opendata reali);
  7. poll `_wait_for_successful_schedule_request` → listing `_wait_for_listing_entry` → download.
- **Setup**: `schedules_base` (override `ON_DATA_READY_DATASETS`), `schedules_admin_headers`, `schedules_user` (admin_root), `monkeypatch`, `cleanup_registry`.
- **Assert**: `response (data/ready) == 202`; `published_request["status"] == "SUCCESS"`; `fileoutput == listed_package["filename"]`; `listed_package["date"] == ref_from` (formato `%Y-%m-%d`, perché reftime from==to → `equal_whole_reftimes` in opendata); `download == 200` con `Content-Disposition` contenente il filename; `download_response.data` non vuoto. `finally: download_response.close()`.
- **Casi coperti**: happy path on-data-ready → opendata, con **logica di scheduling reale** ma trasporto fake.

### `test_crontab_schedule_publishes_opendata_package` — `async_real` + `runtime_sensitive`
- **Obiettivo**: una schedule **crontab pura** produce *eventualmente* un package scaricabile, attraversando l'infrastruttura asincrona reale.
- **Backend coinvolto**: `SingleSchedule.post` (reale, crea l'entry RedBeat) → **celerybeat reale** → **RabbitMQ reale** → **worker reale** → `data_extract` → opendata listing + download. **Nessun fake, nessun monkeypatch.**
- **Flusso**:
  1. `fetch_dataset_window(lm5)` (→ skip se 404);
  2. `trigger_at = _next_crontab_run_time()` (prossimo minuto "sicuro", +2 se mancano <15s al cambio minuto, per non correre con la pickup RedBeat);
  3. `build_crontab_schedule(hour, minute, opendata=True)` → `create_schedule` (reale) + cleanup;
  4. poll `_wait_for_successful_schedule_request(timeout=180, grace_timeout=180)` — attende che beat+worker producano la richiesta;
  5. listing `_wait_for_listing_entry(reftime:>=…,<=…)` → download.
- **Setup**: `schedules_base`, `schedules_user` (admin_root), `cleanup_registry`. **No** `schedules_admin_headers` (nessun `/data/ready`), **no** `monkeypatch`.
- **Assert**: `published_request["status"] == "SUCCESS"`; `fileoutput == listed_package["filename"]`; `listed_package["date"] == "from <from> to <to>"` (range, perché la finestra reale ha from≠to); `download == 200` con `Content-Disposition`; `finally: close()`.
- **Casi coperti**: happy path crontab **reale** → opendata. È il test di integrazione più completo (persistenza schedule + esecuzione asincrona vera).

## 5. Call chain

```
[DETERMINISTIC — on-data-ready, trasporto fake, task inline]
fetch_dataset_window(lm5)               → /api/fields (404 → pytest.skip)
POST /api/schedules (opendata,on-data-ready)
    └─ celery=AcceptTasksWithoutRunningCelery("data_extract")   → submission registrata, NON inviata
POST /api/data/ready (admin)            → 202
    └─ celery=AcceptTasksWithoutRunningCelery("launch_all_on_data_ready_extractions")
launch_all_on_data_ready_extractions.run(model, rundate)   ← eseguito A MANO dal test
    └─ celery=InlineDataExtractCelery() → data_extract.run(...) ESEGUITO INLINE (file+opendata reali)
poll GET /schedules/<id>/requests       → status SUCCESS & fileoutput
GET /api/datasets/lm5/opendata?q=reftime:=<d>  → package
GET /api/opendata/<file>                → 200 + Content-Disposition

[ASYNC_REAL — crontab, infrastruttura reale]
fetch_dataset_window(lm5)               → /api/fields (404 → pytest.skip)
POST /api/schedules (opendata,crontab @minute)  → entry RedBeat reale
   celerybeat reale → RabbitMQ reale → worker reale → data_extract
poll GET /schedules/<id>/requests (timeout 180 + grace 180) → SUCCESS & fileoutput
GET /api/datasets/lm5/opendata?q=reftime:>=…,<=…  → package
GET /api/opendata/<file>                → 200 + Content-Disposition
```

## 6. Comportamenti nascosti

- **Differenza cruciale "async reale" vs "fake inline"** (cuore della review):
  - **Test deterministico**: l'endpoint reale e la **logica di scheduling reale** (`launch_all_on_data_ready_extractions`) vengono eseguiti, ma il **solo strato di trasporto** Celery è sostituito **due volte**: `AcceptTasksWithoutRunningCelery` (la submission viene *registrata* e non inviata al broker) e `InlineDataExtractCelery` (il task `data_extract` viene **eseguito realmente in-process**). Il test inoltre **invoca a mano** `launch_all_on_data_ready_extractions.run(...)`: non c'è alcun beat/worker; il flusso è sincrono. I side effect (file, pubblicazione opendata) sono **reali**. Non è un fake che *reimplementa* la decisione: la decisione gira davvero, solo il trasporto è simulato.
  - **Test async_real**: **nessun** fake/monkeypatch. La schedule crontab è scritta in RedBeat e l'estrazione avviene solo quando **celerybeat reale** la preleva, la mette in **RabbitMQ reale** e un **worker reale** la consuma. Il test attende con polling (180s + 180s di grazia). È l'unico dei due a validare persistenza schedule + catena asincrona vera.
- **Skip silenzioso doppio**: `fetch_dataset_window` fa `pytest.skip` su 404, e la fixture `schedules_user` del conftest fa `pytest.skip` se `lm5` non è disponibile (`LookupError`). In un ambiente senza `lm5`, **entrambi** i test risultano *skipped* senza eseguire alcun assert — rischio "verde ma non eseguito".
- **`schedules_user` qui è il super-utente del conftest**: a differenza degli altri file del dominio (che ridefiniscono `schedules_user` come utente semplice), questo file **non** lo shadowa, quindi usa il `create_data_ready_user` con ruolo `admin_root`. È **necessario** perché `opendata=True` in `post` richiede `admin_root` (vedi anche SCHEDULES-001 nella review della validation).
- **Override `ON_DATA_READY_DATASETS`**: senza l'override fatto da `schedules_base`, `post` rifiuterebbe la schedule on-data-ready su `lm5` con 400 ("Data-ready service is not available").
- **Poller che fallisce su FAILURE**: `_wait_for_successful_schedule_request` solleva `ScheduleRequestFailed` (sottoclasse di `AssertionError`) se la richiesta entra in `FAILURE`, evitando di attendere inutilmente fino al timeout.
- **`grace_timeout`**: secondo finestra di attesa usata **solo** dal crontab (beat/worker possono far emergere la richiesta oltre il bound nominale).
- **Formato `date` divergente nel listing**: on-data-ready usa reftime from==to → `date` = giorno singolo; crontab usa una finestra reale from≠to → `date` = `"from … to …"`. Gli assert riflettono la logica di `OpendataFileList.get`.
- **Retry con side effect**: `trigger_data_ready_and_wait_accepted` ripete il `POST /data/ready` ad ogni tentativo (vedi review di `polling.py`).
- **`wait_for_schedule_requests` importato ma non usato nel corpo** (si usa il poller locale): import potenzialmente superfluo (non verificabile un intento diverso dal codice).

## 7. Checklist di revisione

- [ ] **Distinzione netta** tra il test `deterministic` (trasporto fake + task inline, decisione reale) e quello `async_real` (beat→broker→worker reali): assicurarsi che la guida globale non li tratti come equivalenti.
- [ ] Verificare in CI quali ambienti eseguono davvero i due test e quali li **skippano** (lm5 assente): la copertura reale è condizionata dai dati/infra.
- [ ] Verificare che il marker `async_real` sia escluso/incluso correttamente nei profili di esecuzione (es. `-m "integration and not async_real"`).
- [ ] Confermare timeout/grace (180+180s) adeguati a CI per evitare flakiness sul crontab.
- [ ] Verificare che l'override `ON_DATA_READY_DATASETS` e il super-utente `admin_root` non nascondano vincoli reali (es. autorizzazioni opendata).
- [ ] Confermare la chiusura della `download_response` (fatta in `finally`).

## 8. Possibili criticità

- **Copertura condizionata da runtime/infra**: entrambi i test sono `runtime_sensitive` e silenziosamente skippabili (lm5). Il crontab è inoltre `async_real`: richiede celerybeat+RabbitMQ+worker attivi, altrimenti non eseguibile in modo significativo.
- **Flakiness potenziale del crontab**: dipende dal timing del minuto schedulato e dalla pickup RedBeat; mitigato da `_next_crontab_run_time` e dal `grace_timeout`, ma resta sensibile al carico.
- **Il test deterministico non prova la catena asincrona**: esegue il task a mano e con trasporto fake; valida endpoint + logica di scheduling + estrazione reale, ma **non** beat/broker/worker. È il crontab a coprirli.
- **Dipendenza dal super-utente admin_root**: il bridge gira come admin (necessario per opendata); non esercita restrizioni di ruolo. La tensione con SCHEDULES-001 (gate opendata) va letta insieme alla review della validation.
- **Asserzione `date` accoppiata alla logica opendata**: cambi nel calcolo del campo `date` di `OpendataFileList.get` romperebbero gli assert in modo non ovvio.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/Fake | Fixture | Tipo |
|---|---|---|---|---|---|
| `test_on_data_ready_schedule_publishes_opendata_package` | `post` + `data/ready` + `launch_all_on_data_ready_extractions` + `data_extract` + opendata | bridge on-data-ready → opendata scaricabile | `AcceptTasksWithoutRunningCelery` ×2 + `InlineDataExtractCelery` (trasporto fake, task **inline reale**) | `schedules_base`, `schedules_admin_headers`, `schedules_user` (admin_root), `monkeypatch` | `deterministic` + `runtime_sensitive` (skippabile) |
| `test_crontab_schedule_publishes_opendata_package` | `post` (RedBeat) + **beat→broker→worker reali** + `data_extract` + opendata | bridge crontab **reale** → opendata scaricabile | **nessuno** (infra reale) | `schedules_base`, `schedules_user` (admin_root) | `async_real` + `runtime_sensitive` (skippabile) |
