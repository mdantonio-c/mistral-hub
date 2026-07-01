# Review — `test_crontab.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data_ready/test_crontab.py](projects/mistral/backend/tests/integration/data_ready/test_crontab.py)
- **Scopo**: verificare che una schedule `on-data-ready` con **crontab non corrispondente** (sia completa sia parziale) **non** generi richieste quando arriva un evento data-ready.
- **Tipologia**: test di **integrazione HTTP** (endpoint reale + DB SQLAlchemy). Marker: `integration`, `deterministic`, `runtime_sensitive`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `DataReady.post` | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py) | `POST /api/data/ready` — accoda `launch_all_on_data_ready_extractions` e ritorna `"1"`/202. |
| `SingleSchedule.post` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Crea la schedule crontab `on-data-ready`. |
| `launch_all_on_data_ready_extractions` (ramo crontab) | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | Confronto `crontab_set` (`day_of_month`/`month_of_year` oppure `day_of_week`) vs `req_date` — **NON eseguito inline** (vedi §6). |
| `GET /api/schedules/<id>/requests` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | Listing usato per l'assert di cardinalità. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `data_ready_base` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + override `ON_DATA_READY_DATASETS`. |
| `data_ready_admin_headers` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin per il trigger. |
| `data_ready_user` | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente `admin_root` su `lm5`; **skip** se assente. |
| `build_crontab_schedule` | helper | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | Body schedule crontab (solo i campi forniti). |
| `create_schedule`, `list_schedule_requests` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Creazione schedule (202) + listing richieste. |
| `trigger_data_ready_and_wait_accepted` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | **Ripete** la `POST /data/ready` finché 202 (retry con side effect multipli). |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra dataset via `/api/fields`; **skip** se 404. |

> **Nota cleanup**: questi due test **non** chiamano `register_schedule_cleanup`. La rimozione della schedule è demandata al teardown LIFO di `register_data_ready_user_cleanup` (cancellazione di tutte le schedule dell'utente). Vedi §8.

## 4. Analisi dettagliata di ogni test

### `test_data_ready_skips_schedule_when_full_crontab_does_not_match`
- **Obiettivo**: un crontab **completamente specificato** che non coincide impedisce la generazione di richieste.
- **Backend coinvolto**: ramo `elif r["crontab_set"]:` → confronto `day_of_month`/`month_of_year` vs `req_date` in `launch_all_on_data_ready_extractions` (non eseguito inline).
- **Flusso**: `fetch_dataset_window(lm5)` → `build_crontab_schedule(minute=59, hour=23, day_of_week=6, day_of_month=30, month_of_year=11, on_data_ready=True, opendata=True)` → `create_schedule` → `trigger_data_ready_and_wait_accepted(model=lm5, rundate="2021101900")`.
- **Setup**: `data_ready_user`; nessun cleanup esplicito della schedule.
- **Assert**: `response.status_code == 202` e `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating crontab completo. **ATTENZIONE**: il worker non è eseguito inline → l'assenza di richieste **non** dimostra il confronto crontab reale (rischio falso positivo, §6/§8).

### `test_data_ready_skips_schedule_when_partial_crontab_does_not_match`
- **Obiettivo**: anche un crontab **parziale** non corrispondente impedisce la generazione.
- **Backend coinvolto**: ramo `elif "day_of_week" in crontab_dic:` → confronto `req_date.weekday()` vs `day_of_week` (non eseguito inline).
- **Flusso**: come sopra ma `build_crontab_schedule(minute=59, hour=23, day_of_week=2, month_of_year=11)` (niente `day_of_month`) → trigger con `rundate="2021101900"`.
- **Setup**: `data_ready_user`; nessun cleanup esplicito della schedule.
- **Assert**: `response.status_code == 202` e `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating crontab parziale (`day_of_week`). **Stesso rischio di falso positivo**.

## 5. Call chain

```
POST /api/schedules (crontab on-data-ready, campi non coincidenti) → 202 (schedule creata)
trigger_data_ready_and_wait_accepted:
  loop: POST /api/data/ready (Cluster=g100) → "1", 202   # ripetuta a ogni retry
        → celery.send_task("launch_all_on_data_ready_extractions", (lm5, 2021-10-19 00:00))  # ACCODATO, NON eseguito inline
GET /api/schedules/<id>/requests?last=False → []          # perché il task non gira

# Ramo reale che NON viene esercitato (in on_data_ready_extractions.py):
#   if r["crontab_set"]:
#     crontab_dic = eval(r["crontab_set"])
#     if day_of_month & month_of_year in dic: skip se req_date.day/month != ...
#     elif day_of_week in dic:                skip se req_date.weekday() != ...
```

## 6. Comportamenti nascosti

- **Il confronto crontab reale non viene eseguito.** `trigger_data_ready_and_wait_accepted` esegue solo la `POST /data/ready` (in retry); l'endpoint **accoda** il task ma il file **non** lo esegue inline e **non** cabla fake Celery. Quindi il ramo `elif r["crontab_set"]` di [on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) **non è esercitato**: l'assenza di richieste deriva dal worker che non gira, non dal mismatch crontab.
- **Retry con side effect multipli**: `trigger_data_ready_and_wait_accepted` **ri-sottomette** l'evento a ogni iterazione (vedi [helpers/data_ready.py.review.md](projects/mistral/backend/tests/helpers/data_ready.py.review.md) e [helpers/polling.py](projects/mistral/backend/tests/helpers/polling.py)); ogni POST accoda un nuovo task launcher.
- **`rundate="2021101900"` hard-coded**: data fissa scelta per non coincidere col crontab; il `run_filter` invece usa `dataset_window.ref_run[0]` (runtime). Mix di valori fissi e runtime.
- **`eval(r["crontab_set"])`** nel backend: il confronto reale usa `eval` sulla stringa crontab (osservazione di sicurezza lato produzione, non esercitata qui).
- **Skip silenziosi**: `data_ready_user`/`fetch_dataset_window` possono saltare entrambi i test se `lm5` manca.

## 7. Checklist di revisione

- [ ] **(Critico)** Valutare se i test debbano eseguire `launch_all_on_data_ready_extractions` inline (come `test_periodic`) per verificare davvero il confronto crontab; allo stato attuale è **non esercitato**.
- [ ] Confermare che la mancanza di `register_schedule_cleanup` sia intenzionale (cleanup affidato al teardown utente).
- [ ] Verificare che `rundate="2021101900"` non coincida mai col crontab in nessun fuso/ambiente.
- [ ] Monitorare gli skip su `lm5`.

## 8. Possibili criticità

- **Falso positivo**: l'assert "nessuna richiesta" è soddisfatto perché il worker non gira; i test passerebbero anche con il confronto crontab rotto. Rischio principale.
- **Cleanup implicito**: senza `register_schedule_cleanup`, la schedule sopravvive fino al teardown LIFO dell'utente; se quel teardown fallisce, resta stato residuo.
- **Side effect dei retry**: più POST → più task accodati; in presenza di un worker reale potrebbe emergere non-determinismo.
- **Accoppiamento runtime**: `runtime_sensitive` + skip su `lm5`, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Logica verificata | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_ready_skips_schedule_when_full_crontab_does_not_match` | schedule + trigger; gating crontab non eseguito | nessuna richiesta su crontab completo non coincidente | **Non esercitata** (worker non gira) | `data_ready_user`, `data_ready_admin_headers` | Media (falso positivo) |
| `test_data_ready_skips_schedule_when_partial_crontab_does_not_match` | schedule + trigger; gating crontab non eseguito | nessuna richiesta su crontab parziale (`day_of_week`) | **Non esercitata** (worker non gira) | `data_ready_user`, `data_ready_admin_headers` | Media (falso positivo) |
