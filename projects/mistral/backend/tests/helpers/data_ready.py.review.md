# Review — `helpers/data_ready.py` (helper condiviso)

> File di review per gli helper data-ready/schedule. Non contiene test.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/helpers/data_ready.py`
- **Scopo**: building block per gli scenari `data_ready` e `schedules`: costruzione payload `/data/ready`, creazione utenti con permessi adatti, gestione schedule/request, polling degli effetti asincroni.
- **Tipologia**: helper di dominio condiviso (usato da `data_ready` e `schedules`).

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `POST /api/data/ready` | `projects/mistral/backend/endpoints/data_ready.py` | Trigger evento data-ready (atteso `202`). |
| `launch_all_on_data_ready_extractions.run(...)` | `projects/mistral/backend/tasks/on_data_ready_extractions.py` | Esecuzione inline della logica reale di gating tramite `trigger_data_ready_inline`. |
| `POST/PATCH/DELETE /api/schedules` | `projects/mistral/backend/endpoints/schedules.py` | Creazione (`202`), attivazione (`200`), cancellazione (`200`). |
| `GET /api/requests`, `GET /api/schedules`, `GET /api/schedules/<id>/requests` | `projects/mistral/backend/endpoints/requests.py`, `projects/mistral/backend/endpoints/schedules.py` | Listing per asserzioni di cardinalità. |
| `SqlApiDbManager.create_request_record` | `projects/mistral/backend/services/sqlapi_db_manager.py` | Seeding diretto di righe `Request` sintetiche. |
| `DOWNLOAD_DIR` | `projects/mistral/backend/endpoints/__init__.py` | Path output utente. |

## 3. Elementi definiti (selezione)

| Simbolo | Tipo | Cosa fa |
|---|---|---|
| `DATA_READY_DATASET_NAME` (`lm5`), `SECOND_..._NAME` (`lm2.2`), `DATA_READY_DATASETS` | costanti | Dataset usati negli scenari data-ready. |
| `build_data_ready_payload(model, cluster, rundate)` | builder | JSON body per `/data/ready` con chiavi esattamente `Model`, `Cluster` (default `g100`) e `rundate`. |
| `create_data_ready_user(...)` | factory | Crea utente con quota/permessi (schedule, postprocessing, open_dataset) e ruolo `admin_root`, senza email di successo e con indirizzo `@example.invalid`. Il parametro `max_output_size` (default 1 GiB) permette di far rifiutare l'estrazione dal worker per quota. |
| `create_schedule`, `set_schedule_active`, `delete_request`, `delete_schedule` | wrapper API | CRUD su schedule/request con assert di status. |
| `list_user_requests`, `list_user_schedules`, `list_schedule_requests` | wrapper API | Listing normalizzati a lista. |
| `wait_for_schedule_requests(...)` | polling | Attende che la schedule esponga `expected_count` richieste (via `wait_until`). |
| `post_data_ready`, `trigger_data_ready_and_wait_accepted` | wrapper/polling | Submit data-ready (con retry fino a `202` nella variante polling). |
| `trigger_data_ready_inline(..., schedule_ids)` | orchestrazione locale | Assorbe e conta la submit del launcher, confina il launcher alle `schedule_ids` del test (`projects/mistral/backend/tests/helpers/task_perimeter.py`), esegue `.run(...)` e intercetta l'eventuale `data_extract` con i fake Celery. |
| `create_schedule_request_record(...)` | seeding DB | Inserisce una `Request` storica con reftime/status/submission_date controllati. |
| `delete_all_user_requests/schedules`, `register_data_ready_user_cleanup`, `register_schedule_cleanup` | cleanup | Teardown via API di richieste/schedule/utente; ogni `DELETE` deve rispondere `200`, altrimenti il cleanup si interrompe (non è best-effort). |

## 4. Comportamenti nascosti

- **`create_data_ready_user` assegna il ruolo `admin_root`** e quota da 1 GiB: l'utente "data-ready" è di fatto un super-utente; i test che lo usano non esercitano restrizioni di permesso.
- **`create_data_ready_user` non fa partire email reali.** È l'utente dei test `async_real`, le cui estrazioni girano sui worker Celery reali. I worker usano il mock SMTP solo negli stack inizializzati con `rapydo --testing` (`APP_MODE=test`), e per questo `tests/conftest.py` salta i test `async_real` sugli altri stack; altrove `data_extract` invierebbe davvero. Senza valori espliciti `BaseTests` sceglie a caso `notify_on_successful_request` e genera un indirizzo Faker, spesso su domini reali. L'helper disattiva quindi le email di successo e usa un indirizzo sul dominio riservato `example.invalid` (RFC 2606) per quelle di errore, che `data_extract` invia sempre. Dopo la creazione due assert verificano entrambi i valori: se il campo sparisse dallo schema admin varrebbe il default `True` del customizer.
- **`create_schedule_request_record` scrive direttamente nel DB** (bypassa worker): imposta `only_reliable=True`, `data_ready=True`, e permette di forzare `submission_date`/`status`. È il modo in cui i test "periodic" preparano una storia pregressa.
- **`trigger_data_ready_and_wait_accepted` ripete la `POST`** a ogni retry: side effect multipli possibili (vedi review di `polling.py`).
- **`trigger_data_ready_inline` separa decisione e trasporto**: endpoint e launcher sono reali; `AcceptTasksWithoutRunningCelery` assorbe la submit iniziale e `InlineDataReadyExtractionCelery` materializza una riga se il launcher tenta `data_extract`. L'assert su una sola submit rende una regressione del gating osservabile senza worker esterni.
- **Argomenti ricostruiti**: `.run(...)` riceve `model` e `rundate` dagli input passati al helper, non dal payload registrato dalla submit Celery; nome e cardinalità della submit sono verificati, i suoi argomenti serializzati no.
- **`register_data_ready_user_cleanup` registra teardown in ordine** (utente, schedule, request) sfruttando il LIFO del registry: l'esecuzione è request → schedule → utente → directory.
- **`list_schedule_requests` filtra solo i `dict`**: l'endpoint può restituire elementi non-richiesta che vengono scartati silenziosamente. Interroga `GET /schedules/<id>/requests?last=False`.
- **`create_schedule` può già accodare un'estrazione**: con `on-data-ready` l'endpoint invia subito `data_extract` per la prima request. Ritorna lo `schedule_id` come stringa ed esige `202`.
- **Wrapper non idempotenti**: `delete_request`, `delete_schedule` e `set_schedule_active` esigono `200`; un `404` (riga già rimossa) fa fallire il teardown.
- **`wait_for_schedule_requests` attende un conteggio esatto**: `len == expected_count`, non `>=`, e non verifica il contenuto delle request. Default 60 s / 5 s. `trigger_data_ready_and_wait_accepted` usa invece 30 s / 3 s.
- **`post_data_ready` è un singolo `POST`** che ritorna `(response, contenuto decodificato)`: non sostituisce Celery, quindi l'endpoint accoda il launcher sul trasporto in uso.
- **`delete_all_user_*` enumerano ciò che l'utente vede** e lo cancellano via API (`delete_all_user_schedules` salta le voci senza id): usarli solo con utenti dedicati, mai con account condivisi.
- **Le patch Celery agiscono sul modulo connettore**: `trigger_data_ready_inline` sostituisce `get_instance` su `data_ready_endpoint.celery` e `on_data_ready_task.celery`, cioè sul modulo `restapi.connectors.celery` condiviso da tutti i moduli che lo importano. Non è un override del solo endpoint e non raggiunge worker in processi separati.

## 5. Checklist di revisione

- [ ] Verificare che l'uso di `admin_root` in `create_data_ready_user` non nasconda mancati controlli di autorizzazione negli scenari data-ready.
- [ ] Verificare che ogni nuovo test `async_real` crei i suoi utenti con `create_data_ready_user`, o con gli stessi due valori di notifica.
- [ ] Verificare che `create_schedule_request_record` rispecchi gli args reali di una richiesta prodotta dal worker.
- [ ] Confermare che il filtro `isinstance(item, dict)` in `list_schedule_requests` non scarti dati significativi.
- [ ] Verificare timeout/interval del polling per evitare flakiness in `async_real`.
- [ ] Valutare se `trigger_data_ready_inline` debba in futuro eseguire gli argomenti catturati dalla submit anziché ricostruirli dagli input HTTP.

## 6. Possibili criticità

- **Super-utente di default**: gli scenari data-ready girano come `admin_root`, riducendo il valore dei test su permessi/quote.
- **Seeding diretto del DB**: i test che si basano su `create_schedule_request_record` verificano la decisione di scheduling **dato uno stato sintetico**, non lo stato reale prodotto dall'estrazione.
- **Retry con side effect** in `trigger_data_ready_and_wait_accepted`.
- **Materializzazione fake**: `trigger_data_ready_inline` prova la decisione reale del launcher ma non esegue il worker `data_extract`; gli effetti finali sono sintetici.
