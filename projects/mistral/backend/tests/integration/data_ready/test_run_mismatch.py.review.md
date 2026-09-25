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
| `launch_all_on_data_ready_extractions` (gating modello/runhour) | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | `if datasets[0] != model: continue` e `if runhour not in requested_runs: continue` — eseguiti inline. |
| `GET /api/schedules/<id>/requests` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Listing per l'assert di cardinalità. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `monkeypatch` | fixture | `pytest` | Sostituisce il trasporto Celery dell'endpoint e del launcher. |
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**. |
| `data_ready_base` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + override `ON_DATA_READY_DATASETS`. |
| `data_ready_admin_headers` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin per il trigger. |
| `data_ready_db` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Connettore SQLAlchemy passato al fake annidato. |
| `data_ready_user` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente `admin_root` su `lm5`; **skip** se assente. |
| `build_crontab_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Body schedule crontab. |
| `create_schedule`, `list_schedule_requests`, `register_schedule_cleanup` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Creazione schedule + listing + cleanup LIFO. |
| `trigger_data_ready_inline` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Verifica una submit del launcher, esegue il task reale inline e intercetta l'eventuale `data_extract`. |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra dataset via `/api/fields`; **skip** se 404. |
| `_mismatching_rundate` | helper locale | (questo file) | `reference + 1h`, formattato `%Y%m%d%H`. |

## 4. Analisi dettagliata di ogni test

### `test_data_ready_skips_schedule_for_different_model_dataset`
- **Obiettivo**: un evento data-ready per un **altro modello** (`lm2.2`) non attiva la schedule su `lm5`.
- **Backend coinvolto**: ramo reale `if datasets[0] != model: continue` di `launch_all_on_data_ready_extractions`.
- **Flusso**: `fetch_dataset_window(lm5)` → schedule su `lm5` → `trigger_data_ready_inline(model="lm2.2", rundate=ref_from)`.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`, `cleanup_registry`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating reale sul modello; una regressione invierebbe `data_extract`, il fake creerebbe una riga e l'assert fallirebbe.

### `test_data_ready_skips_schedule_for_different_runhour`
- **Obiettivo**: un **run-hour** non corrispondente non attiva la schedule.
- **Backend coinvolto**: ramo reale `if runhour not in requested_runs: continue` (decodifica `run` via `arki.decode_run`).
- **Flusso**: come sopra ma `trigger_data_ready_inline(model=lm5, rundate=_mismatching_rundate(ref_from))`.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`, `cleanup_registry`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating reale sul run-hour; una submit annidata inattesa diventa una riga osservabile.

## 5. Call chain

```
POST /api/schedules (crontab on-data-ready, dataset=lm5, run=ref_run[0]) → 202

# Test 1 — modello diverso
trigger_data_ready_inline(Model=lm2.2):
   → POST /api/data/ready → submit launcher assorbita e contata → "1", 202
   → launch_all_on_data_ready_extractions.run(lm2.2, ref_from)
   → if datasets[0] != model: continue

# Test 2 — run-hour diverso
trigger_data_ready_inline(Model=lm5, rundate=ref_from+1h):
   → POST /api/data/ready → submit launcher assorbita e contata → "1", 202
   → launch_all_on_data_ready_extractions.run(lm5, ref_from+1h)
   → if runhour not in requested_runs: continue

GET /api/schedules/<id>/requests?last=False → []      # gating reale
```

## 6. Comportamenti nascosti

- **Il gating modello/run-hour è reale.** `trigger_data_ready_inline` assorbe e conta la submit dell'endpoint, poi chiama `.run(...)`; solo l'eventuale `data_extract` è sostituito da un fake che crea una `Request` osservabile.
- **Payload Celery non riutilizzato**: il helper ricostruisce gli argomenti di `.run(...)` dagli input della POST; verifica nome e cardinalità della submit, non i suoi argomenti serializzati.
- **`run_filter` runtime, `rundate` derivato**: la schedule filtra su `dataset_window.ref_run[0]` (runtime), mentre il trigger usa `ref_from` (test 1) o `ref_from + 1h` (test 2). Il mismatch del run-hour del test 2 è costruito scommando +1h.
- **Cluster default `g100`**: entrambi i test non passano per l'early-return (cluster `g100` == `Env.PLATFORM` default), quindi l'endpoint accoda davvero il task.
- **Sentinella `"1"` ambiguo**: come negli altri file, `"1"` non distingue i percorsi dell'endpoint.
- **Skip silenziosi**: `data_ready_user`/`fetch_dataset_window` possono saltare entrambi i test se `lm5` manca.

## 7. Checklist di revisione

- [x] I test eseguono `launch_all_on_data_ready_extractions` inline e verificano i gating modello/run-hour.
- [ ] Verificare che `_mismatching_rundate` (+1h) produca sempre un run-hour effettivamente non incluso in `requested_runs`.
- [ ] Confermare che `lm2.2` sia un modello realmente "diverso" e non incrociato con `lm5` nei filtri.
- [ ] Monitorare gli skip su `lm5`.

## 8. Possibili criticità

- **Worker di estrazione sostituito**: i test coprono la decisione di submit, non gli effetti reali di `data_extract`.
- **Dipendenza da `arki.decode_run`**: il confronto run-hour passa realmente per la decodifica Arkimet e resta sensibile ai dati runtime.
- **Mix valori runtime/derivati**: la correttezza del mismatch del test 2 dipende dalla relazione fra `ref_run[0]` e `ref_from+1h`, non garantita in ogni dataset.
- **Accoppiamento runtime**: `runtime_sensitive` + skip su `lm5`, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Logica verificata | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_ready_skips_schedule_for_different_model_dataset` | task reale inline + fake `data_extract` | nessuna richiesta per modello diverso | **REALE** (skip) | `data_ready_user`, `data_ready_db`, `monkeypatch`, `cleanup_registry` | Alta |
| `test_data_ready_skips_schedule_for_different_runhour` | task reale inline + fake `data_extract` | nessuna richiesta per run-hour diverso | **REALE** (skip) | `data_ready_user`, `data_ready_db`, `monkeypatch`, `cleanup_registry` | Alta |
