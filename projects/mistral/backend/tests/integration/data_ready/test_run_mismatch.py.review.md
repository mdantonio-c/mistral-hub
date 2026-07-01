# Review — `test_run_mismatch.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data_ready/test_run_mismatch.py](projects/mistral/backend/tests/integration/data_ready/test_run_mismatch.py)
- **Scopo**: verificare che un evento data-ready relativo a un **modello/dataset diverso** o con **run-hour diverso** non attivi una schedule `on-data-ready` esistente.
- **Tipologia**: test di **integrazione HTTP** (endpoint reale + DB SQLAlchemy). Marker: `integration`, `deterministic`, `runtime_sensitive`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `DataReady.post` | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py) | `POST /api/data/ready` — accoda `launch_all_on_data_ready_extractions` e ritorna `"1"`/202. |
| `SingleSchedule.post` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Crea la schedule crontab `on-data-ready` su `lm5`. |
| `launch_all_on_data_ready_extractions` (gating modello/runhour) | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | `if datasets[0] != model: continue` e `if runhour not in requested_runs: continue` — **NON eseguito inline** (vedi §6). |
| `GET /api/schedules/<id>/requests` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Listing per l'assert di cardinalità. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**. |
| `data_ready_base` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + override `ON_DATA_READY_DATASETS`. |
| `data_ready_admin_headers` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin per il trigger. |
| `data_ready_user` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente `admin_root` su `lm5`; **skip** se assente. |
| `build_crontab_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Body schedule crontab. |
| `create_schedule`, `list_schedule_requests`, `register_schedule_cleanup` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Creazione schedule + listing + cleanup LIFO. |
| `post_data_ready` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | `POST /data/ready` singola; ritorna `(response, content)`. |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra dataset via `/api/fields`; **skip** se 404. |
| `_mismatching_rundate` | helper locale | (questo file) | `reference + 1h`, formattato `%Y%m%d%H`. |

## 4. Analisi dettagliata di ogni test

### `test_data_ready_skips_schedule_for_different_model_dataset`
- **Obiettivo**: un evento data-ready per un **altro modello** (`lm2.2`) non attiva la schedule su `lm5`.
- **Backend coinvolto**: ramo `if datasets[0] != model: continue` di `launch_all_on_data_ready_extractions` (non eseguito inline).
- **Flusso**: `fetch_dataset_window(lm5)` → `build_crontab_schedule(hour/minute=now, on_data_ready=True, opendata=True)` su `lm5` → `create_schedule` → `register_schedule_cleanup` → `post_data_ready(model=SECOND_DATA_READY_DATASET_NAME="lm2.2", rundate=ref_from)`.
- **Setup**: `data_ready_user`, `cleanup_registry`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating sul modello. **ATTENZIONE**: worker non eseguito inline → assenza richieste non dimostra `datasets[0] != model` (falso positivo, §6/§8).

### `test_data_ready_skips_schedule_for_different_runhour`
- **Obiettivo**: un **run-hour** non corrispondente non attiva la schedule.
- **Backend coinvolto**: ramo `if runhour not in requested_runs: continue` (decodifica `run` via `arki.decode_run`), non eseguito inline.
- **Flusso**: come sopra ma `post_data_ready(model=lm5, rundate=_mismatching_rundate(ref_from))` (run spostato di +1h rispetto a `ref_run[0]` usato nel filtro).
- **Setup**: `data_ready_user`, `cleanup_registry`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating sul run-hour. **Stesso rischio di falso positivo**.

## 5. Call chain

```
POST /api/schedules (crontab on-data-ready, dataset=lm5, run=ref_run[0]) → 202

# Test 1 — modello diverso
POST /api/data/ready (Model=lm2.2, Cluster=g100) → "1", 202
   → celery.send_task("launch_all_on_data_ready_extractions", (lm2.2, ref_from))  # ACCODATO, non eseguito inline

# Test 2 — run-hour diverso
POST /api/data/ready (Model=lm5, rundate=ref_from+1h) → "1", 202
   → celery.send_task("launch_all_on_data_ready_extractions", (lm5, ref_from+1h))  # ACCODATO, non eseguito inline

GET /api/schedules/<id>/requests?last=False → []      # perché il task non gira

# Rami reali NON esercitati (on_data_ready_extractions.py):
#   if datasets[0] != model: continue
#   runhour = str(rundate.time())[0:5]; if runhour not in requested_runs: continue
```

## 6. Comportamenti nascosti

- **Il gating modello/run-hour reale non viene eseguito.** `post_data_ready` esegue una sola `POST`; l'endpoint **accoda** il launcher ma il file **non** lo esegue inline e **non** cabla fake Celery. I rami `datasets[0] != model` e `runhour not in requested_runs` di [on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) **non sono esercitati**: l'assenza di richieste deriva dal worker che non gira.
- **`run_filter` runtime, `rundate` derivato**: la schedule filtra su `dataset_window.ref_run[0]` (runtime), mentre il trigger usa `ref_from` (test 1) o `ref_from + 1h` (test 2). Il mismatch del run-hour del test 2 è costruito scommando +1h.
- **Cluster default `g100`**: entrambi i test non passano per l'early-return (cluster `g100` == `Env.PLATFORM` default), quindi l'endpoint accoda davvero il task.
- **Sentinella `"1"` ambiguo**: come negli altri file, `"1"` non distingue i percorsi dell'endpoint.
- **Skip silenziosi**: `data_ready_user`/`fetch_dataset_window` possono saltare entrambi i test se `lm5` manca.

## 7. Checklist di revisione

- [ ] **(Critico)** Valutare se i test debbano eseguire `launch_all_on_data_ready_extractions` inline per verificare davvero i gating modello/run-hour; allo stato attuale sono **non esercitati**.
- [ ] Verificare che `_mismatching_rundate` (+1h) produca sempre un run-hour effettivamente non incluso in `requested_runs`.
- [ ] Confermare che `lm2.2` sia un modello realmente "diverso" e non incrociato con `lm5` nei filtri.
- [ ] Monitorare gli skip su `lm5`.

## 8. Possibili criticità

- **Falso positivo**: l'assert "nessuna richiesta" è soddisfatto perché il worker non gira; i test passerebbero anche con i gating modello/run-hour rotti. Rischio principale.
- **Dipendenza da `arki.decode_run`**: il confronto run-hour reale passa per la decodifica Arkimet, non esercitata qui; un suo malfunzionamento non verrebbe rilevato.
- **Mix valori runtime/derivati**: la correttezza del mismatch del test 2 dipende dalla relazione fra `ref_run[0]` e `ref_from+1h`, non garantita in ogni dataset.
- **Accoppiamento runtime**: `runtime_sensitive` + skip su `lm5`, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Logica verificata | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_ready_skips_schedule_for_different_model_dataset` | schedule + trigger; gating modello non eseguito | nessuna richiesta per modello diverso | **Non esercitata** (worker non gira) | `data_ready_user`, `cleanup_registry` | Media (falso positivo) |
| `test_data_ready_skips_schedule_for_different_runhour` | schedule + trigger; gating run-hour non eseguito | nessuna richiesta per run-hour diverso | **Non esercitata** (worker non gira) | `data_ready_user`, `cleanup_registry` | Media (falso positivo) |
