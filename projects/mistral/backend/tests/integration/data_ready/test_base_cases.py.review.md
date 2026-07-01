# Review — `test_base_cases.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data_ready/test_base_cases.py](projects/mistral/backend/tests/integration/data_ready/test_base_cases.py)
- **Scopo**: coprire i comportamenti di base del flusso data-ready: ramo di *early-return* per piattaforma non esportata, rifiuto di una schedule su dataset non abilitato, e "non-attivazione" di schedule inattive o senza flag `on-data-ready`.
- **Tipologia**: test di **integrazione HTTP** (endpoint reale + DB SQLAlchemy). Marker: `integration`, `deterministic`, `runtime_sensitive`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `DataReady.post` | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py) | `POST /api/data/ready` — *early-return* `"1"`/202 se la piattaforma del cluster ≠ `Env.PLATFORM`; altrimenti sottomette il task `launch_all_on_data_ready_extractions` e ritorna `"1"`/202. |
| `SingleSchedule.post` (ramo data-ready) | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L474) | `POST /api/schedules` — con `data_ready=True` rifiuta (`BadRequest` 400) se i dataset non sono tutti in `ON_DATA_READY_DATASETS`. |
| `SingleSchedule.patch` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | `PATCH /api/schedules/<id>` — attiva/disattiva la schedule (usato per renderla inattiva). |
| `launch_all_on_data_ready_extractions` | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | Logica di gating reale — **NON eseguita inline** in questo file (vedi §6). |
| Modelli `Schedule`, `Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Tabelle ispezionate indirettamente via `GET /schedules/<id>/requests`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**. |
| `data_ready_base` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + **override** `SingleSchedule.ON_DATA_READY_DATASETS` = `["lm5","lm2.2"]`. |
| `data_ready_admin_headers` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin di default (trigger `POST /data/ready`). |
| `data_ready_user` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente `admin_root` su `lm5`; **skip** se dataset assente. |
| `build_on_data_ready_schedule`, `build_crontab_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Builder dei body schedule. |
| `post_data_ready` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | `POST /data/ready` singola; ritorna `(response, content)`. |
| `create_schedule`, `set_schedule_active`, `list_schedule_requests`, `register_schedule_cleanup` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | CRUD schedule + listing richieste (assert di status interni). |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra temporale del dataset via `/api/fields`; **skip** se 404. |
| `pytest.skip` | meccanismo | `pytest` | Skip indiretto via `data_ready_user`/`fetch_dataset_window` se il dataset manca. |

## 4. Analisi dettagliata di ogni test

### `test_data_ready_non_filesystem_export_returns_one`
- **Obiettivo**: l'evento data-ready per un cluster **non esportato** è accettato e ritorna il sentinella `"1"`.
- **Backend coinvolto**: `DataReady.post`, ramo *early-return* (`cluster=="meucci"` con `Env.PLATFORM` di default `G100` → `exported_platform != cluster`).
- **Flusso**: `post_data_ready(model=lm5, cluster="meucci", rundate="2023020217")`.
- **Setup**: solo header admin; nessuna schedule, nessun cleanup.
- **Assert**: `status_code in {200,202}` e `content == "1"`.
- **Casi coperti**: happy path del ramo di guardia piattaforma. **Verifica logica reale del backend** (nessuna schedulazione, nessun Celery, nessun fake). È l'unico test "pulito" del file.

### `test_data_ready_schedule_rejects_dataset_not_enabled`
- **Obiettivo**: rifiutare una schedule `on-data-ready` su un dataset **fuori** dall'insieme abilitato.
- **Backend coinvolto**: `SingleSchedule.post`, ramo `if data_ready: if not all(elem in ON_DATA_READY_DATASETS ...): raise BadRequest`.
- **Flusso**: `GET /datasets` → sceglie il **primo** dataset il cui id non è `lm5`/`lm2.2` → `build_on_data_ready_schedule(opendata=False)` → `POST /schedules`.
- **Setup**: header admin; nessuna schedule creata (la POST deve fallire).
- **Assert**: `status_code == 400` e messaggio contiene `"Data-ready service is not available"`.
- **Casi coperti**: error path. **Verifica logica reale del backend**, ma su input filtrato dalla lista **forzata** in `conftest` (vedi §6/§8).

### `test_data_ready_skips_inactive_schedule`
- **Obiettivo**: una schedule `on-data-ready` **inattiva** non deve generare richieste.
- **Backend coinvolto**: creazione schedule (`SingleSchedule.post`), disattivazione (`patch`); la decisione di skip vivrebbe in `launch_all_on_data_ready_extractions` (`if not enabled: continue`).
- **Flusso**: `fetch_dataset_window(lm5)` → `build_crontab_schedule(on_data_ready=True, opendata=True, hour/minute=now)` → `create_schedule` (utente `admin_root`) → `register_schedule_cleanup` → `set_schedule_active(is_active=False)` → `post_data_ready(model=lm5, cluster default "g100")`.
- **Setup**: `data_ready_user`, `cleanup_registry`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, **`list_schedule_requests(...)` vuoto**.
- **Casi coperti**: gating "schedule inattiva". **ATTENZIONE**: il task `launch_all_on_data_ready_extractions` **non viene eseguito inline** (nessun monkeypatch, nessun `.run()`), quindi l'assenza di richieste è garantita dal fatto che il worker non gira, **non** dal ramo `if not enabled: continue`. Vedi §6/§8 (rischio di falso positivo).

### `test_data_ready_skips_schedule_without_on_data_ready_flag`
- **Obiettivo**: una schedule ordinaria (`on-data-ready=False`) ignora gli eventi data-ready.
- **Backend coinvolto**: come sopra, ramo previsto `if not on_data_ready: continue`.
- **Flusso**: identico al test precedente ma `build_crontab_schedule(on_data_ready=False)`; nessuna disattivazione.
- **Setup**: `data_ready_user`, `cleanup_registry`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating "flag assente". **Stesso rischio di falso positivo**: il worker non è eseguito inline, quindi l'assenza di richieste non dimostra il ramo `if not on_data_ready`.

## 5. Call chain

```
# Test 1 — early return
POST /api/data/ready (Cluster=meucci) → require_any("operational") → use_kwargs
   → cluster="meucci"; Env.PLATFORM("G100").lower()="g100" != "meucci"
   → return self.response("1", 202)          # nessuna schedulazione

# Test 2 — rifiuto dataset non abilitato
POST /api/schedules (on-data-ready, dataset∉{lm5,lm2.2}, opendata=False)
   → require() → ScheduledDataExtraction → controlli dataset/licenza
   → if data_ready and not all(ds in ON_DATA_READY_DATASETS): raise BadRequest("Data-ready service is not available...") → 400

# Test 3/4 — "skip" inattiva / senza flag
POST /api/schedules (crontab, on-data-ready)            → 202 (schedule creata)
[Test 3] PATCH /api/schedules/<id> {is_active:false}    → 200
POST /api/data/ready (Cluster=g100)
   → cluster=="g100" == exported "g100" → NON early-return
   → celery.get_instance().send_task("launch_all_on_data_ready_extractions", (model,rundate))  # ACCODATO, NON eseguito inline
   → return "1", 202
GET /api/schedules/<id>/requests?last=False             → []   (perché il task non è mai girato)
```

## 6. Comportamenti nascosti

- **Il worker reale non viene eseguito (test 3 e 4).** `post_data_ready` esegue una sola `POST`; l'endpoint **accoda** `launch_all_on_data_ready_extractions` su Celery ma il file **non** lo esegue inline e **non** cabla alcun fake. Di conseguenza la logica di gating reale ([on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py)) **non viene esercitata**: l'assert "nessuna richiesta" è soddisfatto perché il worker non gira. Se nel runtime girasse un worker reale/eager che consuma la coda, l'esito dipenderebbe dai tempi (il codice dei test non lo prevede; il pattern di [test_periodic.py](projects/mistral/backend/tests/integration/data_ready/test_periodic.py), che esegue il task `.run()` esplicitamente, conferma che l'esecuzione inline è necessaria per osservare effetti).
- **Sentinella `"1"` ambiguo**: l'endpoint ritorna `"1"`/202 **sia** nel ramo early-return **sia** nel ramo che accoda il task. L'assert `content == "1"` non distingue i due percorsi.
- **`ON_DATA_READY_DATASETS` forzato**: il rifiuto del test 2 dipende dalla lista sovrascritta in `conftest`, non dalla config d'ambiente.
- **`Env.PLATFORM` non verificabile dal codice del test**: il test 1 assume `PLATFORM != "meucci"` (default `G100`); se l'ambiente esportasse `meucci`, l'early-return non scatterebbe (comportamento non coperto).
- **Skip silenziosi**: `data_ready_user` e `fetch_dataset_window` possono saltare i test 3/4 se `lm5` non è disponibile.
- **Assert dentro gli helper**: `create_schedule`, `set_schedule_active`, `list_schedule_requests` asseriscono internamente lo status; un fallimento d'arrange appare come errore di helper.

## 7. Checklist di revisione

- [ ] **(Critico)** Decidere se i test 3/4 debbano davvero esercitare `launch_all_on_data_ready_extractions` (eseguendolo inline come fa `test_periodic`): allo stato attuale **non** verificano il gating `enabled`/`on_data_ready`.
- [ ] Confermare che il sentinella `"1"` sia sufficiente, o se serva distinguere early-return da task-accodato.
- [ ] Verificare l'assunzione su `Env.PLATFORM` per il test 1.
- [ ] Confermare che il dataset scelto nel test 2 esista sempre e sia stabile fuori da `{lm5,lm2.2}`.
- [ ] Monitorare gli skip su `lm5` mancante.

## 8. Possibili criticità

- **Falso positivo (test 3 e 4)**: l'assenza di richieste è **vacuamente vera** perché il worker non gira; i test passerebbero anche se la logica `enabled`/`on_data_ready` fosse rotta. È il rischio principale del file.
- **Contratto su input sintetico (test 2)**: la regola "dataset non abilitato → 400" è reale, ma misurata contro `ON_DATA_READY_DATASETS` forzato in fixture.
- **Sentinella poco informativo**: `"1"` condiviso fra rami diversi riduce il potere diagnostico dell'assert.
- **Accoppiamento al runtime**: marker `runtime_sensitive` + skip su `lm5` rendono la copertura dipendente dall'ambiente, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Logica verificata | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_ready_non_filesystem_export_returns_one` | `DataReady.post` early-return | `"1"`/202 per cluster non esportato | **Reale** (no fake) | `data_ready_base`, `data_ready_admin_headers` | Bassa |
| `test_data_ready_schedule_rejects_dataset_not_enabled` | `SingleSchedule.post` (data-ready) | 400 su dataset non abilitato | **Reale** (su lista forzata) | `data_ready_base`, `data_ready_admin_headers` | Media |
| `test_data_ready_skips_inactive_schedule` | schedule + `patch`; gating non eseguito | nessuna richiesta da schedule inattiva | **Non esercitata** (worker non gira) | `data_ready_user`, `cleanup_registry` | Media (falso positivo) |
| `test_data_ready_skips_schedule_without_on_data_ready_flag` | schedule; gating non eseguito | nessuna richiesta senza flag | **Non esercitata** (worker non gira) | `data_ready_user`, `cleanup_registry` | Media (falso positivo) |
