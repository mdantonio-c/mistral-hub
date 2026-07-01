# Review — `test_periodic.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> **File chiave**: è l'unico del sottoalbero che esegue *inline* la logica reale di scheduling, sostituendo solo il trasporto Celery con dei fake.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data_ready/test_periodic.py](projects/mistral/backend/tests/integration/data_ready/test_periodic.py)
- **Scopo**: verificare la regola periodica "ogni N giorni" del data-ready: una nuova richiesta viene generata **solo** quando l'intervallo è effettivamente trascorso rispetto all'ultima richiesta `SUCCESS`.
- **Tipologia**: test di **integrazione "ibrida"** — endpoint reale + decisione di scheduling reale + **fake Celery** per trasporto ed estrazione. Marker: `integration`, `deterministic`, `runtime_sensitive`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo | Reale / Fake |
|---|---|---|---|
| `DataReady.post` | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py) | `POST /api/data/ready`; la sua `send_task` è assorbita dal fake. | **Reale** (submission assorbita) |
| `launch_all_on_data_ready_extractions.run(...)` | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | Decisione di scheduling eseguita **inline nel processo di test**. | **Reale** ✅ |
| `SqlApiDbManager.get_last_scheduled_request` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L208) | Recupera l'ultima `Request` `SUCCESS` della schedule (base del calcolo periodo). | **Reale** ✅ |
| ramo periodico `if r["period"] == "days"` | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | `next_submission = submission_date + every*giorni`; `if req_date.date() != next_submission: continue`. | **Reale** ✅ |
| `InlineDataReadyExtractionCelery.send_task("data_extract")` | [tests/helpers/celery_fakes.py](projects/mistral/backend/tests/helpers/celery_fakes.py) | **Crea** la riga `Request` `SUCCESS` (o salta per dedup-by-reftime). | **Fake** ⚠️ |
| `AcceptTasksWithoutRunningCelery` | [tests/helpers/celery_fakes.py](projects/mistral/backend/tests/helpers/celery_fakes.py) | Assorbe la submission del launcher fatta dall'endpoint (verifica il nome). | **Fake** |
| `create_request_record`, `get_schedule_name` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L111) | Usate **dal fake** per materializzare la riga. | Reale ma invocata dal fake |
| Modelli `Schedule`, `Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Storia richieste ispezionata via API e seminata via DB. | **Reale** |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `monkeypatch` | fixture | `pytest` | Sostituisce `celery.get_instance` su endpoint e task (vedi §6). |
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `data_ready_base` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + override `ON_DATA_READY_DATASETS`. |
| `data_ready_admin_headers` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin per il trigger. |
| `data_ready_db` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `sqlalchemy.get_instance()` (seeding + fake). |
| `data_ready_user` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente `admin_root` su `lm5`; **skip** se assente. |
| `build_periodic_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Body schedule periodica (`every`/`period`). |
| `create_schedule`, `list_schedule_requests`, `delete_request` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | CRUD schedule/request via API. |
| `create_schedule_request_record` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | **Semina diretta nel DB** di una `Request` storica (reftime stringa, `submission_date`/`status` forzati). |
| `trigger_data_ready_and_wait_accepted` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Ripete `POST /data/ready` finché 202. |
| `wait_for_schedule_requests` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Poll fino a `expected_count` richieste. |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra dataset via `/api/fields`; **skip** se 404. |
| `_trigger_data_ready_periodic_inline`, `_create_two_day_periodic_schedule` | helper locali | (questo file) | Cablano i fake ed eseguono il task inline / preparano la schedule a 2 giorni. |

## 4. Analisi dettagliata di ogni test

### Helper locale `_trigger_data_ready_periodic_inline` (il cuore del file)
- **Obiettivo**: pilotare un evento data-ready lungo il percorso reale ma **tutto in-process**.
- **Flusso**:
  1. `monkeypatch.setattr(data_ready_endpoint.celery, "get_instance", lambda: AcceptTasksWithoutRunningCelery("launch_all_on_data_ready_extractions"))` → la submission del launcher fatta dall'endpoint è **assorbita** (registrata, nome verificato).
  2. `trigger_data_ready_and_wait_accepted(...)` → `POST /data/ready` finché 202.
  3. `monkeypatch.setattr(on_data_ready_task.celery, "get_instance", lambda: InlineDataReadyExtractionCelery(data_ready_db))` → la `send_task("data_extract")` interna diventa una **scrittura DB sintetica**.
  4. `on_data_ready_task.launch_all_on_data_ready_extractions.run(model, datetime.strptime(rundate, "%Y%m%d%H"))` → esegue **la decisione di scheduling reale** inline.
- **Nota**: la submission del launcher dall'endpoint viene scartata; il task viene poi rieseguito **manualmente** con `.run(...)`. È questo passaggio che rende osservabile la logica reale (conferma indiretta che senza `.run()` — come negli altri file — la logica non gira).

### Helper locale `_create_two_day_periodic_schedule`
- Crea una schedule periodica `every=2, period="days"` su `lm5`, poi **cancella le richieste auto-generate** alla creazione (`delete_request`) per controllare la storia. Ritorna `(schedule_id, ref_from, date_from)`. `ref_from`/`ref_to` sono normalizzati con `second=0, microsecond=1` (vedi §6 sul `microsecond=1`).

### `test_data_ready_creates_request_when_daily_period_has_elapsed`
- **Obiettivo**: una schedule `every=1 day` crea una seconda richiesta dopo **un** giorno trascorso.
- **Backend coinvolto**: ramo periodico reale `period=="days"`; creazione riga via fake.
- **Flusso**: crea schedule `every=1` → **semina** una `Request` `SUCCESS` con `submission_date = ref_from - 1 giorno` → `_trigger_data_ready_periodic_inline(rundate=ref_from)`.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`.
- **Assert**: `response.status_code == 202`; `wait_for_schedule_requests(expected_count=2, timeout=5, interval=1)`; `len(requests) == 2`.
- **Casi coperti**: "periodo trascorso → genera". **Decisione di submit = REALE**; **creazione della seconda riga = FAKE**. Il conteggio `2` = 1 seminata + 1 creata dal fake (vedi §6 sul perché il dedup del fake **non** scatta).

### `test_data_ready_creates_request_when_two_day_period_has_elapsed`
- **Obiettivo**: una schedule `every=2 days` rigenera solo quando sono passati **due** giorni interi.
- **Backend coinvolto**: stesso ramo reale; creazione via fake.
- **Flusso**: `_create_two_day_periodic_schedule` → semina `Request` `SUCCESS` con `submission_date = ref_from - 2 giorni` → trigger inline con `rundate=ref_from`.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`.
- **Assert**: `status_code == 202`; `wait_for_schedule_requests(expected_count=2)`; `len == 2`.
- **Casi coperti**: confine "esattamente 2 giorni → genera". **Decisione = REALE**, **riga = FAKE**.

### `test_data_ready_skips_request_before_two_day_period_elapses`
- **Obiettivo**: una schedule `every=2 days` **non** deve rigenerare dopo un solo giorno.
- **Backend coinvolto**: ramo reale `if req_date.date() != next_submission: continue` (decisione di **skip**).
- **Flusso**: `_create_two_day_periodic_schedule` → semina `Request` `SUCCESS` con `submission_date = ref_from - 1 giorno` → trigger inline con `rundate=ref_from`.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`.
- **Assert**: `status_code == 202`; `wait_for_schedule_requests(expected_count=1)`; `len == 1`.
- **Casi coperti**: "periodo non trascorso → salta". **È il test più solido del sottoalbero**: la decisione di **skip** è reale e, se fosse rotta, il fake creerebbe una riga e il conteggio diventerebbe 2 → il test fallirebbe. Qui il fake **non** viene mai invocato.

## 5. Call chain

```
_trigger_data_ready_periodic_inline:
  monkeypatch endpoint.celery.get_instance → AcceptTasksWithoutRunningCelery("launch_all_on_data_ready_extractions")
  POST /api/data/ready (loop→202)
     → endpoint.send_task("launch_all_on_data_ready_extractions")  → ASSORBITO dal fake (nome verificato)
     → "1", 202
  monkeypatch task.celery.get_instance → InlineDataReadyExtractionCelery(db)
  launch_all_on_data_ready_extractions.run(model, rundate_dt)                # ── LOGICA REALE inline ──
     for schedule in db.Schedule.query.all():
        gating reale: enabled? on_data_ready? datasets[0]==model? runhour?   # REALE
        if r["period"]=="days":
           last_req = get_last_scheduled_request(db, id)                     # legge la riga seminata
           submission_date = parse(last_req.submission_date).date()
           next_submission = submission_date + timedelta(days=every)
           if req_date.date() != next_submission: continue                   # ── DECISIONE REALE ──
        send_task("data_extract", (...data_ready=True, opendata...))
           → InlineDataReadyExtractionCelery.send_task:                      # ── FAKE ──
               assert name=="data_extract"; assert data_ready is True
               last = ultima Request SUCCESS della schedule
               if last and last.args["reftime"] == reftime: return          # dedup RE-IMPLEMENTATO nel fake
               else: create_request_record(...) ; status=SUCCESS ; commit    # CREAZIONE riga = FAKE
wait_for_schedule_requests(expected_count) → GET /api/schedules/<id>/requests?last=False
```

## 6. Comportamenti nascosti

- **Doppio cablaggio Celery via `monkeypatch` (qui, non in `conftest`)**: l'endpoint usa `AcceptTasksWithoutRunningCelery` (assorbe), il task usa `InlineDataReadyExtractionCelery` (crea la riga). È **questo** il cablaggio dei fake che il sottoalbero usa — assente negli altri tre file.
- **Decisione REALE, materializzazione FAKE**: la regola "periodo trascorso?" è eseguita dal backend reale; ma la **creazione** della `Request` e l'eventuale **dedup-by-reftime** sono implementate nel fake [celery_fakes.py](projects/mistral/backend/tests/helpers/celery_fakes.py). Per i due test "creates", il conteggio `2` dipende dal fake che crea la riga.
- **Il dedup del fake non scatta (per mismatch di formato)**: il fake confronta `last_request.args.get("reftime") == reftime`. La riga **seminata** ha `reftime` **stringa** (da `create_schedule_request_record`), mentre il task reale passa `reftime` come **dict** `{"from":..,"to":..}`. I due valori non sono mai uguali → il fake **non** deduplica e crea sempre la nuova riga. Il conteggio `2` poggia quindi su questa differenza di formato, non su una vera assenza di duplicato.
- **`microsecond=1` deliberato**: i seed forzano `microsecond=1` perché il task reale parsa `last_req["submission_date"]` con `"%Y-%m-%dT%H:%M:%S.%f"`; con microsecondi a zero `isoformat()` ometterebbe la parte frazionaria e lo `strptime` fallirebbe. Accoppiamento fragile al formato datetime.
- **Il launcher itera TUTTE le schedule** (`db.Schedule.query.all()`): eventuali schedule residue di altri test potrebbero entrare nel ciclo; la pulizia LIFO mitiga, ma è un accoppiamento allo stato globale del DB.
- **`wait_for_schedule_requests` è quasi sincrono**: dato che `.run()` è eseguito inline prima del poll, il conteggio è già definitivo e il poll ritorna subito (timeout 5s è solo margine).
- **Skip silenziosi**: `data_ready_user`/`fetch_dataset_window` possono saltare tutti e tre i test se `lm5` manca.

## 7. Checklist di revisione

- [ ] **(Crux)** Per i test "creates" distinguere chiaramente ciò che è **reale** (decisione di submit) da ciò che è **fake** (creazione riga + dedup): la `Request` finale non è prodotta dal worker reale.
- [ ] Verificare che la logica di dedup del fake resti allineata al comportamento reale del path data-ready (vedi [helpers/celery_fakes.py.review.md](projects/mistral/backend/tests/helpers/celery_fakes.py.review.md)); oggi il dedup non scatta per mismatch dict/stringa.
- [ ] Confermare che `create_schedule_request_record` rispecchi gli argomenti reali di una richiesta prodotta dal worker (reftime come stringa vs dict).
- [ ] Verificare l'invariante `microsecond=1` e valutare se il backend dovrebbe gestire `submission_date` senza frazione di secondo.
- [ ] Confermare che l'iterazione su tutte le schedule non introduca interferenze tra test.
- [ ] Monitorare gli skip su `lm5`.

## 8. Possibili criticità

- **Falso positivo parziale sui test "creates"**: il conteggio `2` non prova che il **worker reale** crei la richiesta, ma che (a) la decisione reale dice "submit" e (b) il fake crea la riga senza deduplicare. Una regressione che facesse sottomettere il task **due** volte verrebbe mascherata dal dedup del fake (o, al contrario, il dedup non scatta per il mismatch di formato): la semantica osservata è in parte quella del test double.
- **Dedup re-implementato nel fake**: se il backend reale cambiasse la logica di de-duplicazione, il fake divergerebbe silenziosamente e i test resterebbero verdi pur non rispecchiando la produzione.
- **Accoppiamento al formato `reftime`/`submission_date`**: stringa vs dict e `microsecond=1` rendono i test fragili a modifiche innocue di serializzazione.
- **Test "skip" (il più solido) vs test "creates" (più deboli)**: solo `test_data_ready_skips_request_before_two_day_period_elapses` verifica una decisione reale senza dipendere dalla creazione del fake.
- **`runtime_sensitive` + skip su `lm5`**: copertura dipendente dall'ambiente, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Logica verificata | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_ready_creates_request_when_daily_period_has_elapsed` | task reale inline + fake `data_extract` | 2ª richiesta dopo 1 giorno (`every=1`) | **Decisione REALE** + riga **FAKE** | `data_ready_user`, `data_ready_db`, `monkeypatch` | Alta |
| `test_data_ready_creates_request_when_two_day_period_has_elapsed` | task reale inline + fake `data_extract` | rigenera a 2 giorni esatti (`every=2`) | **Decisione REALE** + riga **FAKE** | `data_ready_user`, `data_ready_db`, `monkeypatch` | Alta |
| `test_data_ready_skips_request_before_two_day_period_elapses` | task reale inline (fake non invocato) | nessuna rigenerazione dopo 1 giorno (`every=2`) | **REALE** (skip) ✅ | `data_ready_user`, `data_ready_db`, `monkeypatch` | Alta |
