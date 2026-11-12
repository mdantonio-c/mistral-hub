# Review — `data_ready/conftest.py` (infrastruttura di dominio)

> File di review per modulo di supporto (fixture locali). Non contiene test.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/integration/data_ready/conftest.py`
- **Scopo**: fornire alle prove del sottoalbero `data_ready` lo stato minimo riusabile: la lista dei dataset abilitati al data-ready (forzata), gli header admin per il trigger, il connettore SQLAlchemy e un utente temporaneo abilitato a creare schedule sul dataset di test. Impedisce inoltre che `POST`/`DELETE /schedules` raggiungano Celery e RedBeat reali.
- **Tipologia**: `conftest.py` di dominio (solo fixture locali, visibili a `integration/data_ready/**`).

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `SingleSchedule.ON_DATA_READY_DATASETS` | `projects/mistral/backend/endpoints/schedules.py` | Attributo di classe (derivato da `Env.get("ON_DATA_READY_DATASETS")`) **sovrascritto a runtime** dalla fixture con `["lm5", "lm2.2"]`. |
| `BaseTests.do_login` | `restapi.tests` | Login dell'admin **di default** (`do_login(client, None, None)`). |
| `create_data_ready_user` | `projects/mistral/backend/tests/helpers/data_ready.py` | Crea via API un utente con quota 1 GiB, `allowed_schedule`/`allowed_postprocessing`/`open_dataset` e ruolo **`admin_root`**. |
| `sqlalchemy.get_instance()` | `restapi.connectors` | Connettore DB esposto a setup helper e asserzioni. |
| `register_data_ready_user_cleanup` | `projects/mistral/backend/tests/helpers/data_ready.py` | Registra teardown LIFO (utente, schedule, request). |
| `schedules_endpoint.celery`, `create_periodic_task_with_routing`, `create_crontab_task_with_routing` | `projects/mistral/backend/endpoints/schedules.py` | **Sostituiti** nel solo modulo endpoint dalla fixture autouse `schedules_endpoint_without_real_celery`. |

## 3. Elementi definiti (fixture)

| Fixture | Dipende da | Cosa fa | Effetti collaterali |
|---|---|---|---|
| `data_ready_base` | `test_runtime` | Istanzia `BaseTests()` e, **per la durata della fixture**, sostituisce `SingleSchedule.ON_DATA_READY_DATASETS` con `DATA_READY_DATASETS` (`["lm5","lm2.2"]`) tramite `test_runtime.override_attr` (context manager con ripristino allo `yield`). | Patcha un **attributo di classe** globale: tutte le richieste `POST /schedules` viste durante il test usano la lista forzata, non quella d'ambiente. |
| `data_ready_admin_headers` | `client`, `data_ready_base` | Login dell'admin di default; ritorna gli header. | Riusa l'account admin condiviso. |
| `data_ready_db` | — | Ritorna `sqlalchemy.get_instance()`. | Nessuno. |
| `data_ready_user` | `client`, `cleanup_registry`, `data_ready_base`, `test_runtime` | Crea l'utente data-ready su `DATA_READY_DATASET_NAME` (`lm5`); su `LookupError` fa `pytest.skip`; registra il cleanup. | Crea utente `admin_root` + file/permessi; teardown LIFO. |
| `schedules_endpoint_without_real_celery` (autouse) | `monkeypatch` | Nel modulo endpoint `/schedules` sostituisce `celery` con un'istanza `AcceptTasksWithoutRunningCelery("data_extract")` e le funzioni di creazione dei task RedBeat con funzioni vuote. | Nessuno: il primo `data_extract` delle schedule on-data-ready resta in memoria e non nasce alcun task RedBeat. |

## 4. Comportamenti nascosti

- **Override dell'attributo di classe `ON_DATA_READY_DATASETS` (il punto centrale)**: `data_ready_base` non è un semplice helper, ma **riscrive la configurazione autorevole** che il backend usa per decidere se un dataset è abilitato al data-ready. Senza questo override i test non potrebbero creare schedule on-data-ready su `lm5`/`lm2.2`. La lista d'ambiente reale (`Env.get("ON_DATA_READY_DATASETS")`) viene quindi **bypassata**: la regola di gating "dataset abilitato" è verificata contro un valore sintetico, non contro la config di produzione.
- **Celery dell'endpoint `/schedules` sostituito per tutto il dominio.** La fixture autouse `schedules_endpoint_without_real_celery` patcha i nomi nel modulo endpoint, non il connettore condiviso. Senza di essa ogni schedule on-data-ready creata dai test inviava al broker reale un `data_extract`: i worker lo processavano dopo la cancellazione della schedule, con errori e tentativi di notifica email. Inoltre la schedule crontab di `test_data_ready_skips_schedule_without_on_data_ready_flag` lasciava un task RedBeat giornaliero a ogni esecuzione. Il motivo è che `trigger_data_ready_inline` patcha `restapi.connectors.celery.get_instance`, e `cleanup_registry` esegue la `DELETE /schedules` prima che `monkeypatch` venga annullato: la cancellazione del task finiva quindi sul fake. La decisione "reale vs fake" del trigger data-ready resta nei singoli test (`trigger_data_ready_inline`, `_trigger_data_ready_periodic_inline`).
- **`create_data_ready_user` assegna `admin_root`**: l'utente "data-ready" è di fatto un super-utente (vedi [helpers/data_ready.py.review.md](../../helpers/data_ready.py.review.md)). Serve anche perché le schedule `opendata=True` richiedono `admin_root` lato endpoint.
- **`data_ready_admin_headers` ≠ `data_ready_user.headers`**: il trigger `POST /data/ready` (che richiede il ruolo `operational`) viaggia con l'admin di default; le schedule sono create con l'utente `admin_root` temporaneo. Sono due identità distinte nello stesso test.
- **Skip silenzioso**: se `lm5` non è presente nel runtime, `create_data_ready_user` solleva `LookupError` e la fixture fa `pytest.skip` → tutti i test che dipendono da `data_ready_user` vengono **saltati** senza fallire. Solo `LookupError` produce lo skip: altri errori di creazione fanno fallire la fixture. Un secondo skip può arrivare dopo, nei test, da `fetch_dataset_window` se `/fields` risponde `404`.
- **`data_ready_db` non isola**: restituisce il connettore reale senza rollback né transazione dedicata; la pulizia dipende solo dal `cleanup_registry`.
- **Assert dentro l'helper di setup**: `create_data_ready_user` asserisce `user is not None`; un problema di creazione utente appare come errore di fixture.
- **Percorso comune ai quattro moduli del dominio** (`test_base_cases.py`, `test_crontab.py`, `test_periodic.py`, `test_run_mismatch.py`): tutti hanno marker `integration`, `deterministic`, `runtime_sensitive`. Nei casi con schedule il run e la finestra temporale partono da `/fields` reale (`fetch_dataset_window`) e la schedule è creata via API. `datetime`/`timedelta` servono solo a comporre gli scenari: il clock non è congelato.
- **Ordine delle guardie del launcher** (`projects/mistral/backend/tasks/on_data_ready_extractions.py`), per ogni schedule:
  - schedule abilitata;
  - flag `on_data_ready`;
  - numero di dataset (0 o ≥2 → skip);
  - modello (`datasets[0] != model`);
  - run richiesto (`filters["run"]` decodificato con `arki.decode_run`);
  - calendario (period o crontab).
  Uno scenario pensato per una guardia può essere fermato da una precedente.
- **Periodo giornaliero per uguaglianza**: la schedule riparte solo se la data dell'evento è **uguale** a ultima submission (o `creation_date` se non ci sono request) + `every` giorni; non è un `>=`, quindi un periodo saltato non viene recuperato.
- **Ramo crontab parziale**: se sono presenti sia `day_of_month` sia `month_of_year` confronta giorno e mese insieme; altrimenti, se c'è `day_of_week`, confronta solo il giorno della settimana (`weekday()`). `hour` e `minute` non sono mai confrontati.
- **Elenco vuoto non diagnostico**: un elenco di request vuoto dimostra solo che nessuna guardia ha lasciato passare la schedule, non quale l'abbia fermata (gli skip sono solo loggati).
- **Confine dei fake nel trigger**: `trigger_data_ready_inline` (in `projects/mistral/backend/tests/helpers/data_ready.py`) confina solo il launcher. Limita l'esecuzione alle `schedule_ids` del test e sostituisce il `data_extract` annidato con `InlineDataReadyExtractionCelery`. Quel fake scrive una request `SUCCESS` sintetica e non ne crea una nuova se l'ultima request `SUCCESS` della schedule ha lo stesso `reftime`. La prima submission eseguita alla creazione della schedule non passa dal trigger: è assorbita dalla fixture autouse descritta sopra e non genera request.

## 5. Checklist di revisione

- [ ] Confermare che l'override di `ON_DATA_READY_DATASETS` sia volutamente accettato: i test verificano il gating "dataset abilitato" contro una lista forzata, non contro l'ambiente reale.
- [ ] Verificare che il ripristino del context manager `override_attr` avvenga sempre (anche su fallimento del test) per non inquinare le prove successive.
- [ ] Prendere atto che qui c'è solo il fake per l'endpoint `/schedules`: il fake del trigger data-ready va valutato file per file (vedi le review dei singoli test).
- [ ] Verificare che i test del dominio non lascino chiavi `redbeat:<id>` nel Redis di RedBeat (db 3) né nuovi `data_extract` nel log dei worker.
- [ ] Verificare che lo `skip` su `lm5` mancante non nasconda una regressione di disponibilità dataset in CI.
- [ ] Confermare che l'uso di `admin_root` non mascheri controlli di permesso/quota negli scenari data-ready.

## 6. Possibili criticità

- **Config di gating sintetica**: l'override di `ON_DATA_READY_DATASETS` rende il test di "dataset non abilitato" (`projects/mistral/backend/tests/integration/data_ready/test_base_cases.py`) dipendente da una lista decisa dal test stesso; il contratto verificato è reale ma su input artificiale.
- **Super-utente di default**: tutti gli scenari girano come `admin_root`, riducendo il valore dei test su autorizzazioni e quote.
- **Skip silenzioso su dataset mancante**: la copertura può "sparire" in ambienti senza `lm5`, restando verde per skip.
- **Doppia identità (admin di default vs admin_root temporaneo)**: chi rivede deve tenere presente quale header viene usato in quale fase, altrimenti i 400/202 possono sembrare incoerenti.
- **Creazione dei task RedBeat non esercitata**: nel dominio `data_ready` le funzioni di routing RedBeat dell'endpoint sono vuote. La creazione reale dei task periodici non è verificata qui.
