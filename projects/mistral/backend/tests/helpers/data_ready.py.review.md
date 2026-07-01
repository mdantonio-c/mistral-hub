# Review — `helpers/data_ready.py` (helper condiviso)

> File di review per gli helper data-ready/schedule. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py)
- **Scopo**: building block per gli scenari `data_ready` e `schedules`: costruzione payload `/data/ready`, creazione utenti con permessi adatti, gestione schedule/request, polling degli effetti asincroni.
- **Tipologia**: helper di dominio condiviso (usato da `data_ready` e `schedules`).

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `POST /api/data/ready` | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py) | Trigger evento data-ready (atteso `202`). |
| `POST/PATCH/DELETE /api/schedules` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Creazione (`202`), attivazione (`200`), cancellazione (`200`). |
| `GET /api/requests`, `GET /api/schedules`, `GET /api/schedules/<id>/requests` | [endpoints/requests.py](projects/mistral/backend/endpoints/requests.py), [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Listing per asserzioni di cardinalità. |
| `SqlApiDbManager.create_request_record` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py) | Seeding diretto di righe `Request` sintetiche. |
| `DOWNLOAD_DIR` | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py) | Path output utente. |

## 3. Elementi definiti (selezione)

| Simbolo | Tipo | Cosa fa |
|---|---|---|
| `DATA_READY_DATASET_NAME` (`lm5`), `SECOND_..._NAME` (`lm2.2`), `DATA_READY_DATASETS` | costanti | Dataset usati negli scenari data-ready. |
| `build_data_ready_payload(model, cluster, rundate)` | builder | JSON body per `/data/ready`. |
| `create_data_ready_user(...)` | factory | Crea utente con quota/permessi (schedule, postprocessing, open_dataset) e ruolo `admin_root`. |
| `create_schedule`, `set_schedule_active`, `delete_request`, `delete_schedule` | wrapper API | CRUD su schedule/request con assert di status. |
| `list_user_requests`, `list_user_schedules`, `list_schedule_requests` | wrapper API | Listing normalizzati a lista. |
| `wait_for_schedule_requests(...)` | polling | Attende che la schedule esponga `expected_count` richieste (via `wait_until`). |
| `post_data_ready`, `trigger_data_ready_and_wait_accepted` | wrapper/polling | Submit data-ready (con retry fino a `202` nella variante polling). |
| `create_schedule_request_record(...)` | seeding DB | Inserisce una `Request` storica con reftime/status/submission_date controllati. |
| `delete_all_user_requests/schedules`, `register_data_ready_user_cleanup`, `register_schedule_cleanup` | cleanup | Teardown best-effort di richieste/schedule/utente. |

## 4. Comportamenti nascosti

- **`create_data_ready_user` assegna il ruolo `admin_root`** e quota da 1 GiB: l'utente "data-ready" è di fatto un super-utente; i test che lo usano non esercitano restrizioni di permesso.
- **`create_schedule_request_record` scrive direttamente nel DB** (bypassa worker): imposta `only_reliable=True`, `data_ready=True`, e permette di forzare `submission_date`/`status`. È il modo in cui i test "periodic" preparano una storia pregressa.
- **`trigger_data_ready_and_wait_accepted` ripete la `POST`** a ogni retry: side effect multipli possibili (vedi review di `polling.py`).
- **`register_data_ready_user_cleanup` registra teardown in ordine** (utente, schedule, request) sfruttando il LIFO del registry.
- **`list_schedule_requests` filtra solo i `dict`**: l'endpoint può restituire elementi non-richiesta che vengono scartati silenziosamente.

## 5. Checklist di revisione

- [ ] Verificare che l'uso di `admin_root` in `create_data_ready_user` non nasconda mancati controlli di autorizzazione negli scenari data-ready.
- [ ] Verificare che `create_schedule_request_record` rispecchi gli args reali di una richiesta prodotta dal worker.
- [ ] Confermare che il filtro `isinstance(item, dict)` in `list_schedule_requests` non scarti dati significativi.
- [ ] Verificare timeout/interval del polling per evitare flakiness in `async_real`.

## 6. Possibili criticità

- **Super-utente di default**: gli scenari data-ready girano come `admin_root`, riducendo il valore dei test su permessi/quote.
- **Seeding diretto del DB**: i test che si basano su `create_schedule_request_record` verificano la decisione di scheduling **dato uno stato sintetico**, non lo stato reale prodotto dall'estrazione.
- **Retry con side effect** in `trigger_data_ready_and_wait_accepted`.
