# Review — `test_schedule_api_contracts_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/schedules/test_schedule_api_contracts_EXT.py](projects/mistral/backend/tests/integration/schedules/test_schedule_api_contracts_EXT.py)
- **Scopo**: verificare i **contratti CRUD di lettura** dell'area schedule: listing (`GET /schedules`), conteggio totale paginato (`get_total` → 206), get-by-id (`GET /schedules/<id>`) e diniego per owner mismatch (403).
- **Tipologia**: test di **integrazione HTTP** (controller reale + `SqlApiDbManager` + DB SQLAlchemy). **Nessun** fake Celery, **nessun** `monkeypatch`. Marker di modulo: `pytestmark = [pytest.mark.integration, pytest.mark.deterministic]`. 4 test (2 classi).
- **Nota chiave**: gli scenari **non passano dall'endpoint `POST /schedules`**; le righe schedule sono **seminate direttamente nel DB** (`seed_schedule_row`) per isolare il contratto di lettura da RedBeat/Celery e dalla validazione di creazione.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Schedules.get` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L365) | `GET /api/schedules` — se `get_total` → `pagination_total` (206); altrimenti lista via `get_user_schedules`. |
| `SingleSchedule.get` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L791) | `GET /api/schedules/<id>` — `request_and_owner_check` poi `get_schedule_by_id`. |
| `SingleSchedule.request_and_owner_check` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L970) | `NotFound` (404) se assente; `Forbidden` (403) se l'utente non è owner. |
| `SqlApiDbManager.get_user_schedules` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L381) | Paginazione delle schedule dell'utente + mapping via `_get_schedule_response`. |
| `SqlApiDbManager.count_user_schedules` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L101) | `count()` per `get_total`. |
| `SqlApiDbManager.get_schedule_by_id` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L223) | Dettaglio singola schedule. |
| `SqlApiDbManager._get_schedule_response` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L455) | Forma del payload: `id, name, args, enabled, on_data_ready, period, every, …`; aggiunge `periodic`/`crontab` derivati. |
| `SqlApiDbManager.check_request` / `check_owner` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L69) | Esistenza + ownership della schedule. |
| Modello `Schedule` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L78) | Riga seminata direttamente (`args` JSONB, `period`, `every`, `is_enabled`, `on_data_ready`, `opendata`). |
| `PeriodEnum` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L70) | `seed_schedule_row` fissa `period=PeriodEnum.days, every=1`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `faker` | fixture | plugin `pytest-faker` | `faker.pystr()` per il `name` della schedule seminata. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**; non ingoia eccezioni. |
| `schedules_user` | fixture **locale** | questo file | Crea un utente autenticato `allowed_schedule=True` via `create_authenticated_test_user`; **shadowa** la `schedules_user` del conftest locale (vedi §6). |
| `create_authenticated_test_user`, `register_test_user_cleanup`, `AuthenticatedTestUser` | helper | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Creazione utente + login reali; cleanup utente + cartella output. |
| `seed_schedule_row` | helper **locale** | questo file | Inserisce una `Schedule` direttamente nel DB (bypassa `POST`); ritorna l'id. |
| `delete_schedule_row` | helper **locale** | questo file | Rimuove la riga seminata se ancora presente. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Handle DB per seeding e verifica. |

## 4. Analisi dettagliata di ogni test

### `TestSchedulesListing::test_get_schedules_returns_expected_shape`
- **Obiettivo**: `GET /schedules` ritorna una **lista** con i campi standard della schedule.
- **Backend coinvolto**: `Schedules.get` (ramo lista) → `get_user_schedules` → `_get_schedule_response`.
- **Flusso**: semina 1 schedule per l'utente → registra cleanup → `GET /schedules` → cerca l'item per `id`.
- **Setup**: `schedules_user` (locale), `seed_schedule_row(dataset_names=["agrmet"])`.
- **Assert**: `200`; `isinstance(data, list)` e `len >= 1`; item con `id` presente; chiavi `id`, `name`, `args`, `enabled`, `on_data_ready`.
- **Casi coperti**: happy path / contratto di forma del listing.

### `TestSchedulesListing::test_get_total_returns_206_with_count`
- **Obiettivo**: `GET /schedules?get_total=true` → **206** con campo `total`.
- **Backend coinvolto**: `Schedules.get` (ramo `get_total`) → `count_user_schedules` → `pagination_total` + `@marshal_with(TotalSchema, code=206)`.
- **Flusso**: semina 3 schedule → cleanup per ognuna → `GET …?get_total=true`.
- **Setup**: `schedules_user`; 3 righe seminate (closure `sid=schedule_id` per evitare late-binding nel lambda).
- **Assert**: `status_code == 206`; `"total" in data`; `data["total"] >= 3`.
- **Casi coperti**: contratto di paginazione (codice parziale 206).

### `TestScheduleGetById::test_get_schedule_by_id_returns_details`
- **Obiettivo**: `GET /schedules/<id>` ritorna il dettaglio della schedule.
- **Backend coinvolto**: `SingleSchedule.get` → `request_and_owner_check` (owner OK) → `get_schedule_by_id`.
- **Flusso**: semina 1 schedule → cleanup → `GET /schedules/<id>`.
- **Setup**: `schedules_user`, `seed_schedule_row`.
- **Assert**: `200`; `data["id"] == schedule_id`; chiavi `name`, `args`, `enabled`, `on_data_ready`.
- **Casi coperti**: happy path get-by-id.

### `TestScheduleGetById::test_get_schedule_owner_mismatch_forbidden`
- **Obiettivo**: un utente non può leggere la schedule di un altro utente → **403**.
- **Backend coinvolto**: `SingleSchedule.get` → `request_and_owner_check` → `check_owner` falso → `Forbidden`.
- **Flusso**: crea un **secondo** utente (`other_user`) + cleanup → semina schedule di proprietà di `other_user` → `GET /schedules/<id>` con gli header di `schedules_user`.
- **Setup**: due utenti temporanei; schedule legata a `other_user.user_id`.
- **Assert**: `status_code == 403`.
- **Casi coperti**: error path / controllo di ownership. La schedule **esiste** (quindi non è 404): il 403 misura il ramo `check_owner`, non `check_request`.

## 5. Call chain

```
GET /api/schedules                  → auth.require → get_pagination → Schedules.get
                                       → get_total? count_user_schedules → pagination_total → 206
                                       : get_user_schedules(page,size) → [_get_schedule_response(s)…] → 200
GET /api/schedules?get_total=true   → Schedules.get → count_user_schedules → 206 {total}
GET /api/schedules/<id>             → auth.require → SingleSchedule.get
                                       → request_and_owner_check(check_request → check_owner)
                                       → owner KO? Forbidden 403
                                       → get_schedule_by_id → _get_schedule_response → 200
seed_schedule_row → db.Schedule(args=…, period=days, every=1, is_enabled, on_data_ready) → add+commit
```

## 6. Comportamenti nascosti

- **Seeding diretto del DB (no `POST`)**: `seed_schedule_row` scrive una `Schedule` con `args` già strutturato (`datasets`, `reftime=None`, `filters=None`, …). I test verificano **solo** il contratto di lettura; la logica di creazione/validazione dello scheduler **non è esercitata**.
- **`schedules_user` locale che shadowa il conftest**: questo file ridefinisce `schedules_user` come utente "semplice" (`allowed_schedule=True`, `create_authenticated_test_user`). La fixture omonima del conftest locale (super-utente `admin_root` via `create_data_ready_user`) **non viene usata qui** (vedi review del conftest).
- **Schedule seminata "ibrida"**: `seed_schedule_row` imposta **sia** `on_data_ready=True` (default) **sia** `period=days, every=1`. In `_get_schedule_response`, con `is_crontab` non valorizzato e `period`+`every` presenti, viene aggiunta la chiave derivata `periodic`. Combinazione non tipica di un payload reale, ma irrilevante per gli assert (che controllano solo le chiavi base).
- **Closure nei lambda di cleanup**: nel test `get_total` il cleanup usa `lambda sid=schedule_id: …` per catturare il valore corrente (evita il classico bug di late-binding nei cicli).
- **Asserzioni "≥"**: i conteggi usano `>= 3` / `len >= 1`: tollerano residui/altre schedule dell'utente, ma non isolano un conteggio esatto.

## 7. Checklist di revisione

- [ ] Confermare che il **bypass del `POST`** sia una scelta voluta: questi test non proteggono la creazione, solo la lettura.
- [ ] Verificare che lo shadowing di `schedules_user` (locale vs conftest) sia intenzionale e non fonte di confusione per chi legge.
- [ ] Verificare che la combinazione `on_data_ready=True` + `period/every` nel seed non introduca ambiguità nel mapping `_get_schedule_response`.
- [ ] Verificare che gli assert `>=` siano accettabili o se serva un confronto esatto su id noti.
- [ ] Confermare che 206 (non 200) sia il contratto reale di `get_total` (lo è, via `marshal_with(TotalSchema, code=206)`).

## 8. Possibili criticità

- **Copertura di lettura, non di scrittura**: poiché si semina direttamente la riga, eventuali regressioni nel percorso di **creazione** (POST, RedBeat, Celery) non sarebbero rilevate da questo modulo.
- **Disallineamento seed/realtà**: `args` e i flag sono costruiti a mano; se la forma reale prodotta dal `POST` cambia, il seed può divergere silenziosamente senza far fallire i test.
- **Conteggi non isolati** (`>=`): in un DB condiviso/sporco i numeri esatti non sono verificati; il valore della soglia è basso.
- **Owner mismatch single-shot**: testato solo su `GET /schedules/<id>`; il listing `GET /schedules` filtra già per utente, quindi l'isolamento per-owner del listing non è asserito esplicitamente.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_get_schedules_returns_expected_shape` | `Schedules.get` (lista) | forma del listing + campi base | — (DB seed) | `schedules_user` (locale), `cleanup_registry` | Bassa |
| `test_get_total_returns_206_with_count` | `Schedules.get` (`get_total`) | 206 + `total` | — | `schedules_user`, `cleanup_registry` | Bassa |
| `test_get_schedule_by_id_returns_details` | `SingleSchedule.get` | dettaglio by-id | — | `schedules_user`, `cleanup_registry` | Bassa |
| `test_get_schedule_owner_mismatch_forbidden` | `SingleSchedule.get` + `check_owner` | 403 su schedule altrui | — | due utenti temporanei | Media |
