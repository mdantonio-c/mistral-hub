# Review — `data_ready/conftest.py` (infrastruttura di dominio)

> File di review per modulo di supporto (fixture locali). Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data_ready/conftest.py](projects/mistral/backend/tests/integration/data_ready/conftest.py)
- **Scopo**: fornire alle prove del sottoalbero `data_ready` lo stato minimo riusabile: la lista dei dataset abilitati al data-ready (forzata), gli header admin per il trigger, il connettore SQLAlchemy e un utente temporaneo abilitato a creare schedule sul dataset di test.
- **Tipologia**: `conftest.py` di dominio (solo fixture locali, visibili a `integration/data_ready/**`).

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `SingleSchedule.ON_DATA_READY_DATASETS` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L392) | Attributo di classe (derivato da `Env.get("ON_DATA_READY_DATASETS")`) **sovrascritto a runtime** dalla fixture con `["lm5", "lm2.2"]`. |
| `BaseTests.do_login` | `restapi.tests` | Login dell'admin **di default** (`do_login(client, None, None)`). |
| `create_data_ready_user` | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Crea via API un utente con quota 1 GiB, `allowed_schedule`/`allowed_postprocessing`/`open_dataset` e ruolo **`admin_root`**. |
| `sqlalchemy.get_instance()` | `restapi.connectors` | Connettore DB esposto a setup helper e asserzioni. |
| `register_data_ready_user_cleanup` | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Registra teardown LIFO (utente, schedule, request). |

## 3. Elementi definiti (fixture)

| Fixture | Dipende da | Cosa fa | Effetti collaterali |
|---|---|---|---|
| `data_ready_base` | `test_runtime` | Istanzia `BaseTests()` e, **per la durata della fixture**, sostituisce `SingleSchedule.ON_DATA_READY_DATASETS` con `DATA_READY_DATASETS` (`["lm5","lm2.2"]`) tramite `test_runtime.override_attr` (context manager con ripristino allo `yield`). | Patcha un **attributo di classe** globale: tutte le richieste `POST /schedules` viste durante il test usano la lista forzata, non quella d'ambiente. |
| `data_ready_admin_headers` | `client`, `data_ready_base` | Login dell'admin di default; ritorna gli header. | Riusa l'account admin condiviso. |
| `data_ready_db` | — | Ritorna `sqlalchemy.get_instance()`. | Nessuno. |
| `data_ready_user` | `client`, `cleanup_registry`, `data_ready_base`, `test_runtime` | Crea l'utente data-ready su `DATA_READY_DATASET_NAME` (`lm5`); su `LookupError` fa `pytest.skip`; registra il cleanup. | Crea utente `admin_root` + file/permessi; teardown LIFO. |

## 4. Comportamenti nascosti

- **Override dell'attributo di classe `ON_DATA_READY_DATASETS` (il punto centrale)**: `data_ready_base` non è un semplice helper, ma **riscrive la configurazione autorevole** che il backend usa per decidere se un dataset è abilitato al data-ready. Senza questo override i test non potrebbero creare schedule on-data-ready su `lm5`/`lm2.2`. La lista d'ambiente reale (`Env.get("ON_DATA_READY_DATASETS")`) viene quindi **bypassata**: la regola di gating "dataset abilitato" è verificata contro un valore sintetico, non contro la config di produzione.
- **Nessun fake Celery è cablato qui.** Diversamente da quanto ci si potrebbe aspettare, questo `conftest.py` **non** esegue alcun monkeypatch di `celery.get_instance` e non istanzia `InlineDataReadyExtractionCelery`/`AcceptTasksWithoutRunningCelery`. Il cablaggio dei fake Celery vive **dentro** [test_periodic.py](projects/mistral/backend/tests/integration/data_ready/test_periodic.py) (helper `_trigger_data_ready_periodic_inline`, via `monkeypatch.setattr`). Gli altri tre file di test (`test_base_cases`, `test_crontab`, `test_run_mismatch`) **non** cablano alcun fake e non eseguono il task inline.
- **`create_data_ready_user` assegna `admin_root`**: l'utente "data-ready" è di fatto un super-utente (vedi [helpers/data_ready.py.review.md](projects/mistral/backend/tests/helpers/data_ready.py.review.md)). Serve anche perché le schedule `opendata=True` richiedono `admin_root` lato endpoint.
- **`data_ready_admin_headers` ≠ `data_ready_user.headers`**: il trigger `POST /data/ready` (che richiede il ruolo `operational`) viaggia con l'admin di default; le schedule sono create con l'utente `admin_root` temporaneo. Sono due identità distinte nello stesso test.
- **Skip silenzioso**: se `lm5` non è presente nel runtime, `create_data_ready_user` solleva `LookupError` e la fixture fa `pytest.skip` → tutti i test che dipendono da `data_ready_user` vengono **saltati** senza fallire.
- **Assert dentro l'helper di setup**: `create_data_ready_user` asserisce `user is not None`; un problema di creazione utente appare come errore di fixture.

## 5. Checklist di revisione

- [ ] Confermare che l'override di `ON_DATA_READY_DATASETS` sia volutamente accettato: i test verificano il gating "dataset abilitato" contro una lista forzata, non contro l'ambiente reale.
- [ ] Verificare che il ripristino del context manager `override_attr` avvenga sempre (anche su fallimento del test) per non inquinare le prove successive.
- [ ] Prendere atto che il fake Celery **non** è qui: la decisione "reale vs fake" va valutata file per file (vedi le review dei singoli test).
- [ ] Verificare che lo `skip` su `lm5` mancante non nasconda una regressione di disponibilità dataset in CI.
- [ ] Confermare che l'uso di `admin_root` non mascheri controlli di permesso/quota negli scenari data-ready.

## 6. Possibili criticità

- **Config di gating sintetica**: l'override di `ON_DATA_READY_DATASETS` rende il test di "dataset non abilitato" ([test_base_cases.py](projects/mistral/backend/tests/integration/data_ready/test_base_cases.py)) dipendente da una lista decisa dal test stesso; il contratto verificato è reale ma su input artificiale.
- **Super-utente di default**: tutti gli scenari girano come `admin_root`, riducendo il valore dei test su autorizzazioni e quote.
- **Skip silenzioso su dataset mancante**: la copertura può "sparire" in ambienti senza `lm5`, restando verde per skip.
- **Doppia identità (admin di default vs admin_root temporaneo)**: chi rivede deve tenere presente quale header viene usato in quale fase, altrimenti i 400/202 possono sembrare incoerenti.
