# Review — `schedules/conftest.py` (infrastruttura di dominio)

> File di review per modulo di supporto (fixture locali). Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/schedules/conftest.py](projects/mistral/backend/tests/integration/schedules/conftest.py)
- **Scopo**: fornire le fixture che abilitano lo scenario *ponte data-ready → opendata*: abilitazione dei dataset on-data-ready, header admin per `POST /data/ready`, e un utente schedule-capable per il dataset forecast del bridge.
- **Tipologia**: `conftest.py` di dominio (fixture locali, visibili a `integration/schedules/**`).
- **Nota cruciale**: la fixture `schedules_user` definita qui è **consumata di fatto solo da** [test_schedule_opendata_bridge.py](projects/mistral/backend/tests/integration/schedules/test_schedule_opendata_bridge.py). Gli altri tre moduli del dominio (`test_schedule_api_contracts_EXT.py`, `test_schedule_validation_EXT.py`, `test_scheduled_requests_EXT.py`) **ridefiniscono** una propria `schedules_user` a livello di modulo, che **shadowa** questa (vedi §4).

## 2. Backend realmente esercitato

- `SingleSchedule.ON_DATA_READY_DATASETS` ([endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L392)) — attributo di classe **sovrascritto temporaneamente** per abilitare il ramo on-data-ready del `post`.
- `BaseTests.do_login` (`restapi.tests`) — login admin di default per `schedules_admin_headers`.
- `create_data_ready_user` ([tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py)) — crea il super-utente (`admin_root`, quota, permessi schedule/postprocessing/open_dataset) usato dal bridge.

## 3. Elementi definiti

### Fixture `schedules_base`
- **Dipende da**: `test_runtime` ([tests/conftest.py](projects/mistral/backend/tests/conftest.py)).
- **Cosa fa**: istanzia `BaseTests()` e, dentro `test_runtime.override_attr(SingleSchedule, "ON_DATA_READY_DATASETS", DATA_READY_DATASETS)`, fa `yield base`; a fine test l'attributo originale è **ripristinato** dal context manager.
- **Effetto chiave**: senza questo override, una schedule on-data-ready su `lm5` verrebbe respinta con `400` ("Data-ready service is not available"). È la precondizione che rende eseguibile il bridge on-data-ready.

### Fixture `schedules_admin_headers`
- **Dipende da**: `client`, `schedules_base`.
- **Cosa fa**: `schedules_base.do_login(client, None, None)` → header admin di **default**; ritorna gli header.
- **Usata da**: il bridge per `trigger_data_ready_and_wait_accepted` (`POST /api/data/ready`, che richiede admin).

### Fixture `schedules_user`
- **Dipende da**: `client`, `cleanup_registry`, `schedules_base`, `test_runtime`.
- **Cosa fa**: `create_data_ready_user(schedules_base, client, test_runtime, [DATA_READY_DATASET_NAME])`; in caso di `LookupError` (dataset `lm5` assente) → **`pytest.skip`**; registra il cleanup (`register_data_ready_user_cleanup`) e ritorna l'utente.
- **Caratteristica**: l'utente è un **super-utente `admin_root`** (vedi review di `data_ready.py`); è **necessario** per creare schedule `opendata=True` nel bridge.
- **Usata da**: **solo** `test_schedule_opendata_bridge.py` (gli altri moduli la shadowano).

## 4. Comportamenti nascosti

- **Shadowing di `schedules_user`**: pytest dà precedenza alle fixture definite nel modulo di test rispetto a quelle del `conftest.py` della stessa cartella. Quindi:
  - `test_schedule_opendata_bridge.py` → usa **questa** `schedules_user` (super-utente `admin_root`, con `pytest.skip` su `lm5` mancante);
  - `test_schedule_api_contracts_EXT.py`, `test_schedule_validation_EXT.py`, `test_scheduled_requests_EXT.py` → usano la **propria** `schedules_user` locale (utente semplice via `create_authenticated_test_user`), e **non** vedono questa.
  Una lettura superficiale del conftest può far credere che tutti i test del dominio condividano lo stesso utente: **non è così**.
- **Override di attributo di classe a runtime**: `schedules_base` modifica `SingleSchedule.ON_DATA_READY_DATASETS` (stato di classe condiviso). Il ripristino è garantito dal `with` di `override_attr` (thread-safe, `finally`); un uso non-context-manager non ripristinerebbe.
- **Skip silenzioso ereditato**: chi usa `schedules_user` (il bridge) viene **saltato** se `lm5` non è disponibile, senza eseguire assert.
- **Login admin "di default"**: `schedules_admin_headers` usa l'admin condiviso dell'ambiente (`do_login(None, None)`), introducendo accoppiamento allo stato dell'utente di default.
- **Dipendenza a catena**: `schedules_admin_headers` e `schedules_user` dipendono entrambe da `schedules_base`, quindi attivano l'override `ON_DATA_READY_DATASETS` ogni volta.

## 5. Checklist di revisione

- [ ] Rendere evidente lo **shadowing**: documentare che solo il bridge usa la `schedules_user` del conftest (super-utente `admin_root`).
- [ ] Verificare che l'override di `ON_DATA_READY_DATASETS` venga sempre usato come context manager (ripristino garantito).
- [ ] Verificare che lo `skip` su `lm5` mancante sia atteso e monitorato (rischio "verde per skip").
- [ ] Confermare che l'uso del super-utente `admin_root` nel bridge sia voluto (necessario per `opendata=True`) e non mascheri controlli di autorizzazione.
- [ ] Verificare che il login admin di default non crei accoppiamento d'ordine con altri test che modificano l'admin.

## 6. Possibili criticità

- **Fixture omonima ma semanticamente diversa** tra conftest (admin_root) e moduli `*_EXT` (utente semplice): fonte di confusione; lo stesso nome `schedules_user` indica utenti con privilegi opposti a seconda del file.
- **Stato di classe mutato** (`ON_DATA_READY_DATASETS`): pur ripristinato, è uno stato globale condiviso; un fallimento fuori dal `with` lascerebbe l'attributo alterato (mitigato dal `finally` del context manager).
- **Super-utente di default nel bridge**: il ponte opendata gira come `admin_root`, quindi non esercita restrizioni di ruolo/quota (coerente con `data_ready.py`, ma da tenere presente leggendo SCHEDULES-001 sul gate opendata).
- **Skip mascherante**: in ambienti privi di `lm5`, il bridge non verifica nulla pur risultando non fallito.
