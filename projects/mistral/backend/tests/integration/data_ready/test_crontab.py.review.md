# Review — `test_crontab.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data_ready/test_crontab.py](projects/mistral/backend/tests/integration/data_ready/test_crontab.py)
- **Scopo**: verificare che una schedule `on-data-ready` con **crontab non corrispondente** (sia completa sia parziale) **non** generi richieste quando arriva un evento data-ready.
- **Tipologia**: test di **integrazione HTTP** (endpoint reale + DB SQLAlchemy). Marker: `integration`, `deterministic`, `runtime_sensitive`.

## 2. Backend realmente testato

| Elemento                                                | Path                                                                                             | Ruolo                                                                                                                                             |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DataReady.post`                                      | [endpoints/data_ready.py](projects/mistral/backend/endpoints/data_ready.py)                       | `POST /api/data/ready` — accoda `launch_all_on_data_ready_extractions` e ritorna `"1"`/202.                                                |
| `SingleSchedule.post`                                 | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py)                         | Crea la schedule crontab`on-data-ready`.                                                                                                        |
| `launch_all_on_data_ready_extractions` (ramo crontab) | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py) | Confronto `crontab_set` (`day_of_month`/`month_of_year` oppure `day_of_week`) vs `req_date`, eseguito inline. |
| `GET /api/schedules/<id>/requests`                    | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py)                         | Listing usato per l'assert di cardinalità.                                                                                                       |

## 3. Mappa delle dipendenze

| Dipendenza                                      | Tipo    | Dove definita                                                                              | Cosa fa / effetti collaterali                                                          |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| `monkeypatch`                                  | fixture | `pytest`                                                                                   | Sostituisce il trasporto Celery dell'endpoint e del launcher.                          |
| `client`                                      | fixture | `restapi.tests`                                                                          | `FlaskClient` di test.                                                               |
| `data_ready_base`                             | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | `BaseTests` + override `ON_DATA_READY_DATASETS`.                                   |
| `data_ready_admin_headers`                    | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Header admin per il trigger.                                                           |
| `data_ready_db`                               | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Connettore SQLAlchemy passato al fake annidato.                                        |
| `data_ready_user`                             | fixture | [data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py) | Utente`admin_root` su `lm5`; **skip** se assente.                            |
| `build_crontab_schedule`                      | helper  | [tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py)           | Body schedule crontab (solo i campi forniti).                                          |
| `create_schedule`, `list_schedule_requests` | helper  | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py)         | Creazione schedule (202) + listing richieste.                                          |
| `trigger_data_ready_inline`                   | helper  | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py)         | Verifica una submit del launcher, esegue il task reale inline e intercetta l'eventuale `data_extract`. |
| `fetch_dataset_window`                        | helper  | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra dataset via`/api/fields`; **skip** se 404.                            |

> **Nota cleanup**: questi due test **non** chiamano `register_schedule_cleanup`. La rimozione della schedule è demandata al teardown LIFO di `register_data_ready_user_cleanup` (cancellazione di tutte le schedule dell'utente). Vedi §8.

## 4. Analisi dettagliata di ogni test

### `test_data_ready_skips_schedule_when_full_crontab_does_not_match`

- **Obiettivo**: un crontab **completamente specificato** che non coincide impedisce la generazione di richieste.
- **Backend coinvolto**: ramo reale `elif r["crontab_set"]:` → confronto `day_of_month`/`month_of_year` vs `req_date`.
- **Flusso**: `fetch_dataset_window(lm5)` → schedule completa non coincidente → `trigger_data_ready_inline(model=lm5, rundate="2021101900")`.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`; nessun cleanup esplicito della schedule.
- **Assert**: `response.status_code == 202` e `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating crontab completo reale; una regressione invierebbe `data_extract`, il fake creerebbe una riga e l'assert fallirebbe.

### `test_data_ready_skips_schedule_when_partial_crontab_does_not_match`

- **Obiettivo**: anche un crontab **parziale** non corrispondente impedisce la generazione.
- **Backend coinvolto**: ramo reale `elif "day_of_week" in crontab_dic:` → confronto `req_date.weekday()` vs `day_of_week`.
- **Flusso**: come sopra ma crontab parziale (`day_of_week=2`, niente `day_of_month`) → trigger inline.
- **Setup**: `data_ready_user`, `data_ready_db`, `monkeypatch`; nessun cleanup esplicito della schedule.
- **Assert**: `response.status_code == 202` e `list_schedule_requests(...)` vuoto.
- **Casi coperti**: gating crontab parziale (`day_of_week`) reale.

## 5. Call chain

```
POST /api/schedules (crontab on-data-ready, campi non coincidenti) → 202 (schedule creata)
trigger_data_ready_inline:
  POST /api/data/ready (Cluster=g100) → submit launcher assorbita e contata → "1", 202
  launch_all_on_data_ready_extractions.run(lm5, 2021-10-19 00:00)
    → crontab completo: confronto day/month → continue
    → crontab parziale: confronto weekday → continue
GET /api/schedules/<id>/requests?last=False → []          # gating reale
```

## 6. Comportamenti nascosti

- **Il confronto crontab è reale.** `trigger_data_ready_inline` assorbe e conta la submit dell'endpoint, esegue `.run(...)` e trasforma solo un eventuale `data_extract` in una riga sintetica osservabile.
- **Retry controllato**: il trigger usa il polling esistente, ma l'assert `len(sent_tasks) == 1` impedisce che più submit accettate passino inosservate.
- **Payload Celery non riutilizzato**: il helper ricostruisce gli argomenti di `.run(...)` dagli input della POST; verifica nome e cardinalità della submit, non i suoi argomenti serializzati.
- **`rundate="2021101900"` hard-coded**: data fissa scelta per non coincidere col crontab; il `run_filter` invece usa `dataset_window.ref_run[0]` (runtime). Mix di valori fissi e runtime.
- **`eval(r["crontab_set"])`** nel backend: il confronto reale usa `eval` sulla stringa crontab (osservazione di sicurezza lato produzione, non esercitata qui).
- **Skip silenziosi**: `data_ready_user`/`fetch_dataset_window` possono saltare entrambi i test se `lm5` manca.

## 7. Checklist di revisione

- [x] Entrambi i test eseguono `launch_all_on_data_ready_extractions` inline e verificano il confronto crontab reale.
- [ ] Confermare che la mancanza di `register_schedule_cleanup` sia intenzionale (cleanup affidato al teardown utente).
- [ ] Verificare che `rundate="2021101900"` non coincida mai col crontab in nessun fuso/ambiente.
- [ ] Monitorare gli skip su `lm5`.

## 8. Possibili criticità

- **Worker di estrazione sostituito**: il test copre la decisione del launcher, non gli effetti reali di `data_extract`.
- **Cleanup implicito**: senza `register_schedule_cleanup`, la schedule sopravvive fino al teardown LIFO dell'utente; se quel teardown fallisce, resta stato residuo.
- **Polling con POST ripetibile**: richieste non accettate possono essere ritentate, ma il trasporto è locale e una seconda submit accettata fa fallire l'assert del helper.
- **Accoppiamento runtime**: `runtime_sensitive` + skip su `lm5`, in tensione col marker `deterministic`.

## 9. Riassunto finale

| Test                                                                   | Backend                                         | Cosa verifica                                           | Logica verificata                          | Fixture                                           | Complessità           |
| ---------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------- | ---------------------- |
| `test_data_ready_skips_schedule_when_full_crontab_does_not_match`    | task reale inline + fake `data_extract` | nessuna richiesta su crontab completo non coincidente   | **REALE** (skip) | `data_ready_user`, `data_ready_db`, `monkeypatch` | Alta |
| `test_data_ready_skips_schedule_when_partial_crontab_does_not_match` | task reale inline + fake `data_extract` | nessuna richiesta su crontab parziale (`day_of_week`) | **REALE** (skip) | `data_ready_user`, `data_ready_db`, `monkeypatch` | Alta |
