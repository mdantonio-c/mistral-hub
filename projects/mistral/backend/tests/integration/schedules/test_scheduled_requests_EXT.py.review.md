# Review — `test_scheduled_requests_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/schedules/test_scheduled_requests_EXT.py](projects/mistral/backend/tests/integration/schedules/test_scheduled_requests_EXT.py)
- **Scopo**: coprire l'endpoint `GET /schedules/<id>/requests` (last/list/get_total) e le operazioni di **stato** `PATCH /schedules/<id>` (enable/disable, conflitti) e `DELETE /schedules/<id>`.
- **Tipologia**: test di **integrazione HTTP** (controller reale + `SqlApiDbManager` + DB SQLAlchemy) con **seeding diretto** di righe `Schedule`/`Request` e **fake Celery** (`MagicMock`) per lo strato RedBeat/periodic-task. Marker di modulo: `pytestmark = [pytest.mark.integration, pytest.mark.deterministic]`. 8 test (2 classi).
- **Nota chiave**: le decisioni di `PATCH` (enable/disable già attivo → 409) sono **pilotate dal valore restituito dal fake** `get_periodic_task`, non dalla colonna DB `is_enabled` (vedi §6).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `ScheduledRequests.get` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L998) | `GET /schedules/<id>/requests` — `last=true` → ultimo `SUCCESS` (404 se assente); `get_total` → conteggio; altrimenti lista. |
| `SingleSchedule.patch` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L830) | enable/disable; `Conflict` (409) se task già nello stato; ricrea il periodic task su enable. |
| `SingleSchedule.delete` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L951) | `delete_periodic_task` (Celery) + `delete_schedule` (DB). |
| `SingleSchedule.request_and_owner_check` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L970) | Esistenza + ownership prima di patch/delete/get. |
| `create_periodic_task_with_routing` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) (import da `mistral.tasks`) | Ricreazione del task su enable; **monkeypatchata** a `MagicMock` nel test enable. |
| `SqlApiDbManager.get_last_scheduled_request` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L208) | Ultimo `Request` con `status="SUCCESS"`. |
| `SqlApiDbManager.get_schedule_requests` / `count_schedule_requests` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L233) | Lista e conteggio richieste della schedule. |
| `SqlApiDbManager.get_schedule_by_id` / `update_schedule_status` / `delete_schedule` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L223) | Ricostruzione schedule, aggiornamento `is_enabled`, cancellazione. |
| Modelli `Schedule` / `Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Righe seminate direttamente (`Request.schedule_id` FK, `status`). |
| `celery.get_instance` | `restapi.connectors` | **Sostituito** da `MagicMock` (`get_periodic_task`/`delete_periodic_task`). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `faker` | fixture | `pytest-faker` | `name` per righe seminate. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**. |
| `monkeypatch` | fixture | `pytest` | Patcha `celery.get_instance` e `create_periodic_task_with_routing`. |
| `schedules_user` | fixture **locale** | questo file | Utente `allowed_schedule=True` (`create_authenticated_test_user`). **Shadowa** la fixture del conftest. |
| `seed_schedule_row` | helper **locale** | questo file | Inserisce una `Schedule` (parametrizza `enabled`, `on_data_ready`, `period`, `every`). |
| `seed_request_row` | helper **locale** | questo file | Inserisce un `Request` legato alla schedule (`status` default `SUCCESS`). |
| `delete_schedule_row` / `delete_request_row` | helper **locale** | questo file | Teardown delle righe seminate. |
| `MagicMock` | mock | `unittest.mock` | Fake Celery: controlla esistenza/eliminazione del periodic task. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Seeding e verifica post-operazione. |

## 4. Analisi dettagliata di ogni test

### `TestScheduledRequests::test_last_true_no_successful_request_returns_404`
- **Obiettivo**: `?last=true` senza richieste `SUCCESS` → **404**.
- **Backend coinvolto**: `ScheduledRequests.get` → `get_last_scheduled_request` (None) → `NotFound`.
- **Flusso**: semina **solo** la schedule (nessun `Request`) → `GET …/requests?last=true`.
- **Setup**: `schedules_user`, `seed_schedule_row` (`on_data_ready=False`, no period).
- **Assert**: `status_code == 404`.
- **Casi coperti**: error path "nessuna richiesta riuscita".

### `TestScheduledRequests::test_last_false_returns_list_of_requests`
- **Obiettivo**: `?last=false` → lista di tutte le richieste.
- **Backend coinvolto**: `ScheduledRequests.get` → `get_schedule_requests`.
- **Flusso**: semina schedule + **3** `Request` `SUCCESS` → cleanup → `GET …/requests?last=false`.
- **Setup**: `schedules_user`; 3 righe richiesta linkate.
- **Assert**: `200`; `isinstance(data, list)`; `len(data) >= 3`.
- **Casi coperti**: listing completo richieste schedulate.

### `TestScheduledRequests::test_get_total_returns_count`
- **Obiettivo**: `?get_total=true` → conteggio totale.
- **Backend coinvolto**: `ScheduledRequests.get` (ramo `get_total`) → `count_schedule_requests`.
- **Flusso**: semina schedule + **5** `Request` → `GET …/requests?get_total=true`.
- **Setup**: `schedules_user`.
- **Assert**: `200`; `"total" in data`; `data["total"] >= 5`. *(Nota: a differenza di `GET /schedules?get_total`, qui il codice è **200**, non 206.)*
- **Casi coperti**: conteggio richieste schedulate.

### `TestSchedulePatchAndDelete::test_disable_enabled_periodic_schedule_success`
- **Obiettivo**: `PATCH is_active=false` su schedule periodica abilitata → **200**, `is_enabled=False`.
- **Backend coinvolto**: `SingleSchedule.patch` (ramo `on_data_ready is False`) → `get_periodic_task` truthy → `delete_periodic_task` → `update_schedule_status(False)`.
- **Flusso**: semina schedule `enabled=True, period=days, every=1, on_data_ready=False` → fake Celery (`get_periodic_task → {"name": id}`, `delete_periodic_task → True`) → `PATCH {"is_active": false}`.
- **Setup**: `schedules_user`, `monkeypatch` `celery.get_instance`.
- **Assert**: `200`; ricarica DB → `schedule_row.is_enabled is False`.
- **Casi coperti**: disable happy path (decisione guidata dal fake che dichiara il task esistente).

### `TestSchedulePatchAndDelete::test_disable_already_disabled_schedule_conflict`
- **Obiettivo**: `PATCH is_active=false` su schedule già disabilitata → **409**.
- **Backend coinvolto**: `patch` → `get_periodic_task` **None** → `is_active=False` + `task is None` → `Conflict`.
- **Flusso**: semina schedule `enabled=False, period=days` → fake Celery (`get_periodic_task → None`) → `PATCH {"is_active": false}`.
- **Setup**: `schedules_user`, `monkeypatch`.
- **Assert**: `status_code == 409`.
- **Casi coperti**: conflitto disable. **Il 409 è determinato dal fake** (`get_periodic_task=None`), non dalla colonna `is_enabled`.

### `TestSchedulePatchAndDelete::test_enable_disabled_schedule_recreates_periodic_task`
- **Obiettivo**: `PATCH is_active=true` su schedule disabilitata → **200**, `is_enabled=True`, ricreazione (fake) del periodic task.
- **Backend coinvolto**: `patch` → `get_periodic_task` None → ramo `is_active=True` → `get_schedule_by_id` (chiave `periodic`) → `create_periodic_task_with_routing` (MagicMock) → `update_schedule_status(True)`.
- **Flusso**: semina schedule `enabled=False, period=days, every=1` → fake Celery (`get_periodic_task → None`) + `monkeypatch` di `schedules_module.create_periodic_task_with_routing` → MagicMock → `PATCH {"is_active": true}`.
- **Setup**: `schedules_user`, **doppio** monkeypatch.
- **Assert**: `200`; ricarica DB → `is_enabled is True`.
- **Casi coperti**: enable + ricreazione task. La ricreazione RedBeat è **un no-op fake**: si verifica che il ramo venga preso e che lo stato DB sia aggiornato, non l'effettiva creazione del task.

### `TestSchedulePatchAndDelete::test_enable_already_enabled_schedule_conflict`
- **Obiettivo**: `PATCH is_active=true` su schedule già abilitata → **409**.
- **Backend coinvolto**: `patch` → `get_periodic_task` truthy → `is_active=True` + `task` presente → `Conflict`.
- **Flusso**: semina schedule `enabled=True, period=days` → fake Celery (`get_periodic_task → {"name": id}`) → `PATCH {"is_active": true}`.
- **Setup**: `schedules_user`, `monkeypatch`.
- **Assert**: `status_code == 409`.
- **Casi coperti**: conflitto enable (di nuovo guidato dal fake, non da `is_enabled`).

### `TestSchedulePatchAndDelete::test_delete_schedule_removes_db_and_periodic_task`
- **Obiettivo**: `DELETE /schedules/<id>` rimuove riga DB + periodic task (fake).
- **Backend coinvolto**: `SingleSchedule.delete` → `delete_periodic_task` (fake) → `delete_schedule` (DB).
- **Flusso**: semina schedule `enabled=True, period=days` → fake Celery (`delete_periodic_task → True`) → `DELETE`.
- **Setup**: `schedules_user`, `monkeypatch`.
- **Assert**: `200`; `db.Schedule.query.get(id) is None`.
- **Casi coperti**: delete + side effect DB (la `delete_periodic_task` è fake; non verifica RedBeat reale).

## 5. Call chain

```
GET /api/schedules/<id>/requests?last=true   → ScheduledRequests.get → check_request/check_owner
                                               → get_last_scheduled_request (status=SUCCESS) → None? NotFound 404
GET …/requests?last=false                    → get_schedule_requests → [ _get_request_response… ] → 200
GET …/requests?get_total=true                → count_schedule_requests → 200 {total}

PATCH /api/schedules/<id> {is_active}        → SingleSchedule.patch → request_and_owner_check
   (schedule.on_data_ready is False)
     ├─ task = c.get_periodic_task(id)        [MagicMock pilota il valore]
     ├─ is_active False & task None → Conflict 409
     ├─ is_active False & task     → c.delete_periodic_task → update_schedule_status(False) → 200
     ├─ is_active True  & task     → Conflict 409
     └─ is_active True  & task None → get_schedule_by_id
                                       → "periodic"? create_periodic_task_with_routing (MagicMock)
                                       → update_schedule_status(True) → 200
DELETE /api/schedules/<id>                   → SingleSchedule.delete → delete_periodic_task (fake)
                                               → delete_schedule (DB) → 200
seed_schedule_row / seed_request_row         → db.Schedule|Request(...) → add+commit
```

## 6. Comportamenti nascosti

- **Il conflitto enable/disable è guidato dal fake, non dal DB**: in `patch` la decisione 409 dipende da `c.get_periodic_task(...)` (cioè dal `MagicMock`), **non** dalla colonna `is_enabled`. I test impostano `enabled=True/False` nel seed per coerenza narrativa, ma il valore che forza il ramo è il return del fake. Un reviewer non deve concludere che il DB `is_enabled` sia l'oracolo del conflitto.
- **Ramo Celery solo se `on_data_ready is False`**: tutte le schedule patch/delete sono seminate con `on_data_ready=False` + `period=days/every=1` così da entrare nel ramo periodic. Una schedule `on_data_ready=True` salterebbe la logica RedBeat in `patch`.
- **Ricreazione task = no-op**: `create_periodic_task_with_routing` è monkeypatchata a `MagicMock`; si valida che il ramo `"periodic"` venga eseguito, non l'effettiva persistenza RedBeat.
- **Seeding diretto (no worker, no `POST`)**: `seed_request_row` crea `Request` con `status` arbitrario (`SUCCESS` di default) e `schedule_id` FK; nessuna estrazione reale. `last=true` con zero richieste → 404 perché `get_last_scheduled_request` filtra `status="SUCCESS"`.
- **Codici diversi per `get_total`**: `GET /schedules?get_total` → **206** (paginazione `TotalSchema`), mentre `GET /schedules/<id>/requests?get_total` → **200** con `{total}` (ramo applicativo dedicato). Differenza voluta lato backend.
- **Shadowing della fixture `schedules_user`**: come negli altri `*_EXT`, la versione locale (utente semplice) nasconde quella super-utente del conftest.

## 7. Checklist di revisione

- [ ] Esplicitare che enable/disable conflict dipende dal **fake** `get_periodic_task` e non da `is_enabled`: i test non provano la coerenza RedBeat↔DB reale.
- [ ] Confermare che la ricreazione del periodic task (MagicMock) sia una copertura del **ramo** e non del side effect reale.
- [ ] Verificare la differenza di status `206` vs `200` tra i due `get_total` (è intenzionale lato backend).
- [ ] Verificare che le righe `Request` seminate riflettano la forma reale prodotta dal worker (`status`, FK `schedule_id`).
- [ ] Verificare che gli assert `>=` su list/total siano sufficienti o se serva conteggio esatto.

## 8. Possibili criticità

- **Rischio di falso positivo sui conflitti**: poiché 409 è determinato dal `MagicMock`, il test verifica la **gestione del valore del fake**, non la reale presenza/assenza del task in RedBeat. Una divergenza tra `is_enabled` (DB) e stato RedBeat reale non sarebbe rilevata.
- **Copertura del solo ramo periodic**: crontab e on-data-ready in `patch`/`delete` non sono esercitati qui (il ramo enable gestisce anche `"crontab"`, non coperto).
- **Seeding sintetico**: stato preparato a mano; se il contratto reale di `Request`/`Schedule` cambia, i seed possono divergere silenziosamente.
- **Nessuno skip, ma nessun dato runtime**: il modulo è realmente deterministico (nessun `dataset_window`/`LookupError`); il rovescio è che **non** valida nulla del comportamento asincrono reale.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_last_true_no_successful_request_returns_404` | `ScheduledRequests.get` | 404 senza `SUCCESS` | — (DB seed) | `schedules_user` | Bassa |
| `test_last_false_returns_list_of_requests` | `get` (lista) | lista richieste | — | `schedules_user` | Bassa |
| `test_get_total_returns_count` | `get` (`get_total`) | 200 + `total` | — | `schedules_user` | Bassa |
| `test_disable_enabled_periodic_schedule_success` | `patch` (disable) | 200 + `is_enabled=False` | Celery `MagicMock` | `schedules_user`, `monkeypatch` | Media |
| `test_disable_already_disabled_schedule_conflict` | `patch` (conflict) | 409 | Celery `MagicMock` | `schedules_user`, `monkeypatch` | Media |
| `test_enable_disabled_schedule_recreates_periodic_task` | `patch` (enable) | 200 + ricreazione fake | Celery + `create_periodic_task_with_routing` MagicMock | `schedules_user`, `monkeypatch` | Media |
| `test_enable_already_enabled_schedule_conflict` | `patch` (conflict) | 409 | Celery `MagicMock` | `schedules_user`, `monkeypatch` | Media |
| `test_delete_schedule_removes_db_and_periodic_task` | `delete` | 200 + riga rimossa | Celery `MagicMock` | `schedules_user`, `monkeypatch` | Media |
