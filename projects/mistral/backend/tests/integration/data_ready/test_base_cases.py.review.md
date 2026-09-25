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
| `launch_all_on_data_ready_extractions` | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | Logica di gating reale — eseguita inline nei test su schedule inattiva e senza flag. |
| Modelli `Schedule`, `Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Tabelle ispezionate indirettamente via `GET /schedules/<id>/requests`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `monkeypatch` | fixture | `pytest` | Sostituisce il trasporto Celery dell'endpoint e del launcher. |
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**. |
| `data_ready_base` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + **override** `SingleSchedule.ON_DATA_READY_DATASETS` = `["lm5","lm2.2"]`. |
| `data_ready_admin_headers` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin di default (trigger `POST /data/ready`). |
| `data_ready_db` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Connettore SQLAlchemy passato al fake annidato. |
| `data_ready_user` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente `admin_root` su `lm5`; **skip** se dataset assente. |
| `build_on_data_ready_schedule`, `build_crontab_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Builder dei body schedule. |
| `post_data_ready` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | `POST /data/ready` singola; ritorna `(response, content)`. |
| `trigger_data_ready_inline` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Assorbe e verifica la submit dell'endpoint, esegue il launcher reale inline e intercetta l'eventuale `data_extract`. |
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
- **Backend coinvolto**: creazione schedule (`SingleSchedule.post`), disattivazione (`patch`) e ramo reale `if not enabled: continue` del launcher.
- **Flusso**: `fetch_dataset_window(lm5)` → `build_crontab_schedule(on_data_ready=True, opendata=True, hour/minute=now)` → `create_schedule` → `set_schedule_active(is_active=False)` → `trigger_data_ready_inline(model=lm5)`.
- **Setup**: `data_ready_user`, `cleanup_registry`, `data_ready_db`, `monkeypatch`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, **`list_schedule_requests(...)` vuoto**.
- **Casi coperti**: gating reale "schedule inattiva". Se il ramo di skip fosse rotto, il fake annidato materializzerebbe una richiesta e l'assert finale fallirebbe.

### `test_data_ready_skips_schedule_without_on_data_ready_flag`
- **Obiettivo**: una schedule ordinaria (`on-data-ready=False`) ignora gli eventi data-ready.
- **Backend coinvolto**: ramo reale `if not on_data_ready: continue` del launcher.
- **Flusso**: identico al test precedente ma `build_crontab_schedule(on_data_ready=False)`; nessuna disattivazione; trigger inline.
- **Setup**: `data_ready_user`, `cleanup_registry`, `data_ready_db`, `monkeypatch`.
- **Assert**: `status_code in {200,202}`, `content == "1"`, `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating reale "flag assente"; una regressione produrrebbe una riga osservabile tramite il fake.

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

# Test 3/4 — skip inattiva / senza flag
POST /api/schedules (crontab, on-data-ready)            → 202 (schedule creata)
[Test 3] PATCH /api/schedules/<id> {is_active:false}    → 200
trigger_data_ready_inline:
  POST /api/data/ready (Cluster=g100)
   → cluster=="g100" == exported "g100" → NON early-return
   → send_task("launch_all_on_data_ready_extractions") assorbito e contato dal fake
   → return "1", 202
  launch_all_on_data_ready_extractions.run(model, rundate)     # gating reale inline
   → [in caso di regressione] send_task("data_extract") → fake crea Request
GET /api/schedules/<id>/requests?last=False             → []   (perché il gating ha scartato la schedule)
```

## 6. Comportamenti nascosti

- **Confine Celery controllato (test 3 e 4).** `trigger_data_ready_inline` verifica che l'endpoint tenti esattamente una submit del launcher, esegue `launch_all_on_data_ready_extractions.run(...)` nel processo di test e sostituisce solo la submit annidata di `data_extract` con `InlineDataReadyExtractionCelery`.
- **Argomenti del launcher ricostruiti dal test**: il helper esegue `.run(model, datetime.strptime(rundate, ...))` usando gli stessi input della POST, ma non inoltra gli argomenti registrati dalla submit Celery. Il nome e il numero delle submit sono verificati; il payload della submit non lo è.
- **Sentinella `"1"` ambiguo**: l'endpoint ritorna `"1"`/202 **sia** nel ramo early-return **sia** nel ramo che accoda il task. L'assert `content == "1"` non distingue i due percorsi.
- **`ON_DATA_READY_DATASETS` forzato**: il rifiuto del test 2 dipende dalla lista sovrascritta in `conftest`, non dalla config d'ambiente.
- **`Env.PLATFORM` non verificabile dal codice del test**: il test 1 assume `PLATFORM != "meucci"` (default `G100`); se l'ambiente esportasse `meucci`, l'early-return non scatterebbe (comportamento non coperto).
- **Skip silenziosi**: `data_ready_user` e `fetch_dataset_window` possono saltare i test 3/4 se `lm5` non è disponibile.
- **Assert dentro gli helper**: `create_schedule`, `set_schedule_active`, `list_schedule_requests` asseriscono internamente lo status; un fallimento d'arrange appare come errore di helper.

## 7. Checklist di revisione

- [x] I test 3/4 eseguono `launch_all_on_data_ready_extractions` inline e rendono osservabile una regressione dei gating `enabled`/`on_data_ready`.
- [ ] Confermare che il sentinella `"1"` sia sufficiente, o se serva distinguere early-return da task-accodato.
- [ ] Verificare l'assunzione su `Env.PLATFORM` per il test 1.
- [ ] Confermare che il dataset scelto nel test 2 esista sempre e sia stabile fuori da `{lm5,lm2.2}`.
- [ ] Monitorare gli skip su `lm5` mancante.

## 8. Possibili criticità

- **Trasporto/worker sostituiti**: i test verificano la decisione reale del launcher, non l'esecuzione del worker `data_extract`; l'eventuale richiesta è materializzata dal fake.
- **Contratto su input sintetico (test 2)**: la regola "dataset non abilitato → 400" è reale, ma misurata contro `ON_DATA_READY_DATASETS` forzato in fixture.
- **Sentinella poco informativo**: `"1"` condiviso fra rami diversi riduce il potere diagnostico dell'assert.
- **Accoppiamento al runtime**: marker `runtime_sensitive` + skip su `lm5` rendono la copertura dipendente dall'ambiente, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Logica verificata | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_ready_non_filesystem_export_returns_one` | `DataReady.post` early-return | `"1"`/202 per cluster non esportato | **Reale** (no fake) | `data_ready_base`, `data_ready_admin_headers` | Bassa |
| `test_data_ready_schedule_rejects_dataset_not_enabled` | `SingleSchedule.post` (data-ready) | 400 su dataset non abilitato | **Reale** (su lista forzata) | `data_ready_base`, `data_ready_admin_headers` | Media |
| `test_data_ready_skips_inactive_schedule` | schedule + `patch` + task reale inline | nessuna richiesta da schedule inattiva | **REALE** (skip) | `data_ready_user`, `data_ready_db`, `monkeypatch`, `cleanup_registry` | Alta |
| `test_data_ready_skips_schedule_without_on_data_ready_flag` | schedule + task reale inline | nessuna richiesta senza flag | **REALE** (skip) | `data_ready_user`, `data_ready_db`, `monkeypatch`, `cleanup_registry` | Alta |
