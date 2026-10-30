# Review — `test_schedule_validation_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/schedules/test_schedule_validation_EXT.py](projects/mistral/backend/tests/integration/schedules/test_schedule_validation_EXT.py)
- **Scopo**: coprire gli **edge di validazione** di `POST /schedules`: assenza di setting (400), periodo `< 15 min` (403), opendata per non-admin (403), opendata multidataset (400), opendata su dataset osservato (400), postprocessor senza permesso (401), push senza/with coda inesistente (403×2).
- **Tipologia**: test di **integrazione HTTP** (controller reale + schema marshmallow reale + DB SQLAlchemy). RabbitMQ **mockato** nei soli rami push. Marker di modulo: `pytestmark = [pytest.mark.integration, pytest.mark.deterministic]`. 8 test (classe `TestScheduleValidation`).
- **Attenzione**: il test `test_opendata_as_non_admin_returns_403` è collegato a un'anomalia di backend già documentata (**SCHEDULES-001**, vedi §8): nel runtime osservato l'endpoint ha risposto `202` invece di `403`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `ScheduledDataExtraction.validate_schedule` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L318) | `@pre_load`: "At least one schedule setting has to be specified" → **400** se mancano `period-settings`/`crontab-settings`/`on-data-ready`. |
| `SingleSchedule.post` (ramo `period_settings`) | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L408) | `MIN_PERIOD = 15`: periodo in `minutes` con `every < 15` → `Forbidden` **403**. |
| `SingleSchedule.post` (ramo `opendata`) | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L408) | `admin_root` mancante → **403**; `len(dataset_names) > 1` → **400**; `category.name == "OBS"` → **400**. |
| `SingleSchedule.post` (ramo `postprocessors`) | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L408) | `allowed_postprocessing` falso → `Unauthorized` **401**. |
| `SingleSchedule.post` (ramo `push`) | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py#L408) | `push=true` + `rabbit.queue_exists(...)` falso → `Forbidden` **403**. |
| `SqlApiDbManager.get_user_permissions` / `get_datasets` / `get_license_group` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py) | Permessi, esistenza dataset, coerenza license group (precondizioni ai rami testati). |
| Modello `Datasets` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L146) | `category` (OBS/FOR) e `license_id` usati dal ramo opendata. |
| `rabbitmq.get_instance` | `restapi.connectors` | **Sostituito** da `MagicMock` nei test push (`queue_exists → False`). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**. |
| `monkeypatch` | fixture | `pytest` | Patcha `rabbitmq.get_instance` nei test push. |
| `schedules_user` | fixture **locale** | questo file | Utente non-admin: `allowed_schedule`, `open_dataset`, `datasets=[agrmet, lm5, lm2.2]`. **Shadowa** la fixture omonima del conftest. |
| `admin_user` | fixture **locale** | questo file | Utente con ruolo `admin_root` (via `base.create_user(..., ["admin_root"])`) + stessi dataset. |
| `dataset_ids_for_user` | helper **locale** | questo file | Risolve `arkimet_id → id` e **asserisce** che ogni dataset esista (precondizione runtime hard, vedi §6). |
| `create_authenticated_test_user`, `register_test_user_cleanup`, `AuthenticatedTestUser` | helper | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Creazione/login/teardown utenti temporanei. |
| `DOWNLOAD_DIR` | costante | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py) | Radice output usata per costruire `output_dir` dell'admin user. |
| `MagicMock` | mock | `unittest.mock` | Fake RabbitMQ (`queue_exists.return_value = False`). |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Risoluzione dataset, scrittura `amqp_queue` nel test 8. |

## 4. Analisi dettagliata di ogni test

### `test_no_schedule_setting_returns_400`
- **Obiettivo**: payload senza alcun setting → **400**.
- **Backend coinvolto**: `validate_schedule` (`@pre_load`) prima dell'handler.
- **Flusso**: body con `request_name`+`reftime`+`dataset_names` ma **senza** `period-settings`/`crontab-settings`/`on-data-ready` → `POST`.
- **Setup**: `schedules_user`.
- **Assert**: `status_code == 400`.
- **Casi coperti**: validation error a livello di schema.

### `test_period_less_than_15_minutes_returns_403`
- **Obiettivo**: periodo `minutes` con `every=10` → **403**.
- **Backend coinvolto**: ramo `period_settings` + `MIN_PERIOD`.
- **Flusso**: body con `period-settings:{every:10, period:minutes}`, dataset `agrmet` → `POST`.
- **Setup**: `schedules_user` (autorizzato su `agrmet`, così il 403 misura il limite di frequenza e non l'autorizzazione).
- **Assert**: `status_code == 403`.
- **Casi coperti**: edge sul limite minimo di frequenza.

### `test_opendata_as_non_admin_returns_403` — **SCHEDULES-001**
- **Obiettivo**: `opendata=true` con utente **non admin** → **403**.
- **Backend coinvolto**: ramo `opendata` → `if "admin_root" not in user_roles: raise Forbidden`.
- **Flusso**: body `opendata:True`, dataset `lm5`, `period-settings:{every:1, period:days}` → `POST` con header non-admin.
- **Setup**: `schedules_user` (nessun ruolo admin).
- **Assert**: `status_code == 403`.
- **Casi coperti**: gate role-based opendata. **Anomalia nota (SCHEDULES-001)**: nel runtime osservato la chiamata ha restituito `202` creando la schedule; il test **non** usa `xfail`/`skip`, quindi in quell'ambiente **fallisce realmente**. Vedi §8 e [docs/problems_and_bugs_discovered_in_extension.md](projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md).

### `test_opendata_multidataset_returns_400`
- **Obiettivo**: `opendata=true` con **due** dataset → **400**.
- **Backend coinvolto**: ramo `opendata` → `if len(dataset_names) > 1: raise BadRequest` (preceduto dal controllo license-group).
- **Flusso**: body `opendata:True`, `dataset_names:[lm5, lm2.2]` → `POST` come `admin_user`.
- **Setup**: `admin_user` (admin per superare il gate role-based).
- **Assert**: `status_code == 400`.
- **Casi coperti**: edge opendata multidataset. **Ambiguità oracolo** (vedi §8): il 400 potrebbe originare dal controllo `get_license_group` precedente se `lm5`/`lm2.2` appartengono a gruppi license diversi.

### `test_opendata_observed_dataset_returns_400`
- **Obiettivo**: `opendata=true` su dataset **osservato** → **400**.
- **Backend coinvolto**: ramo `opendata` → `ds_entry.category.name == "OBS"` → `BadRequest`.
- **Flusso**: body `opendata:True`, dataset `agrmet` → `POST` come `admin_user`.
- **Setup**: `admin_user`; dipende dal fatto che **`agrmet` sia categoria OBS** nel DB runtime.
- **Assert**: `status_code == 400`.
- **Casi coperti**: edge opendata su dato osservato (non verificabile dal solo codice di test che `agrmet` sia OBS: è una precondizione del DB runtime).

### `test_postprocessor_unauthorized_returns_401`
- **Obiettivo**: postprocessor richiesto da utente **senza** `allowed_postprocessing` → **401**.
- **Backend coinvolto**: ramo `postprocessors` → `Unauthorized`.
- **Flusso**: crea utente locale con `allowed_postprocessing:False` → body con postprocessor `derived_variables` (`B12194`, valido per lo schema `AVProcessor`) → `POST`.
- **Setup**: utente dedicato creato **inline** nel test (non la fixture), con cleanup.
- **Assert**: `status_code == 401`.
- **Casi coperti**: autorizzazione postprocessing. Lo schema del postprocessor passa (variabile valida): il 401 nasce dal **permesso**, non dalla validazione.

### `test_push_queue_missing_returns_403`
- **Obiettivo**: `push=true` con utente **senza** `amqp_queue` → **403**.
- **Backend coinvolto**: ramo `push` → `rabbit.queue_exists(None)` falso → `Forbidden`.
- **Flusso**: `monkeypatch` `rabbitmq.get_instance` → `MagicMock(queue_exists=False)` → `POST /schedules?push=true`.
- **Setup**: `schedules_user` (nessuna coda configurata → `pushing_queue=None`).
- **Assert**: `status_code == 403`.
- **Casi coperti**: push senza coda. **RabbitMQ reale non contattato** (fake).

### `test_push_queue_nonexistent_returns_403`
- **Obiettivo**: `push=true` con coda **configurata ma inesistente** lato broker → **403**.
- **Backend coinvolto**: stesso ramo `push`, ma con `user.amqp_queue` valorizzato.
- **Flusso**: scrive `user.amqp_queue = "missing.prompt04.ext"` **direttamente nel DB** → `monkeypatch` RabbitMQ (`queue_exists=False`) → `POST …?push=true`.
- **Setup**: `schedules_user`; mutazione diretta del record utente.
- **Assert**: `status_code == 403`.
- **Casi coperti**: push con coda nominata ma assente sul broker (stesso `raise`, stato diverso). Senza il fake, l'esito dipenderebbe dal broker reale: il `MagicMock` rende deterministico il ramo.

## 5. Call chain

```
POST /api/schedules[?push=…]  → auth.require → use_kwargs(query push) → use_kwargs(ScheduledDataExtraction)
    └─(pre_load) validate_schedule → no setting? ValidationError → 400         [test 1]
    └─ SingleSchedule.post
         ├─ get_user_permissions(allowed_schedule) → 401 se non allowed
         ├─ get_datasets / dataset esiste? → 404 se no
         ├─ get_license_group(datasets) → 400 se gruppi diversi   ◄─ possibile origine 400 [test 4]
         ├─ if opendata:
         │     ├─ "admin_root" not in roles → Forbidden 403       [test 3] (SCHEDULES-001)
         │     ├─ len(datasets) > 1 → BadRequest 400              [test 4]
         │     └─ category=="OBS" → BadRequest 400                [test 5]
         ├─ if period_settings minutes & every<15 → Forbidden 403 [test 2]
         ├─ if postprocessors & not allowed_postprocessing → 401  [test 6]
         └─ if push: rabbit.queue_exists(q) False → Forbidden 403 [test 7,8]
```

## 6. Comportamenti nascosti

- **Precondizione runtime "hard" in fixture/helper**: `dataset_ids_for_user` esegue `assert dataset is not None` per `agrmet`, `lm5`, `lm2.2`. Se uno manca nel DB, **fallisce il setup della fixture** (non uno `skip`): il modulo è marcato `deterministic` ma presuppone questi dataset presenti. Differente dal pattern `dataset_window`→`pytest.skip` usato altrove.
- **Concessione esplicita dei dataset** (docstring di `dataset_ids_for_user`): i dataset sono autorizzati apposta perché il test isoli i rami opendata/multidataset/observed senza che le regole sui dataset privati `lm5`/`lm2.2` diventino l'oracolo dell'assert.
- **Due fixture utente con scopi opposti**: `schedules_user` (non admin) per i 403 role-based; `admin_user` (admin_root) per superare il gate e raggiungere i 400 opendata.
- **Mutazione diretta del DB** (test 8): `user.amqp_queue` impostata via SQLAlchemy, bypassando l'API admin.
- **RabbitMQ mockato** (test 7-8): `MagicMock.queue_exists → False`; il broker reale non è coinvolto, il ramo è reso deterministico.
- **Shadowing della fixture `schedules_user`**: come negli altri `*_EXT` del dominio, la fixture locale nasconde quella (super-utente) del conftest.

## 7. Checklist di revisione

- [ ] **SCHEDULES-001**: confermare lo stato dell'anomalia; il test asserisce `403` ma il runtime osservato dava `202`. Decidere se è bug backend (gate non applicato) o contratto da rivedere.
- [ ] Verificare in `test_opendata_multidataset_returns_400` che il 400 derivi davvero dal ramo "multidataset" e non dal controllo `get_license_group` precedente (oracolo ambiguo).
- [ ] Verificare la precondizione runtime di `agrmet=OBS` per `test_opendata_observed_dataset_returns_400`.
- [ ] Considerare che `dataset_ids_for_user` **fallisce** (non skippa) se i dataset mancano: valutarne la portabilità locale/CI.
- [ ] Confermare che 401 (postprocessing) vs 403 (push/period/opendata-role) vs 400 (validation/opendata-shape) corrispondano ai contratti voluti.

## 8. Possibili criticità

- **SCHEDULES-001 — gate opendata non affidabile**: `test_opendata_as_non_admin_returns_403` può **fallire realmente** (202 invece di 403) per un mismatch tra il gate `admin_root` dichiarato e i ruoli effettivi nel percorso HTTP. Tracciato in [docs/problems_and_bugs_discovered_in_extension.md](projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md). Non è coperto da `xfail`/`skip`: in CI emerge come failure.
- **Oracolo ambiguo sul 400 multidataset**: due rami diversi (license-group vs multidataset) producono lo stesso `400`; il test non distingue quale sia scattato.
- **Setup che fallisce invece di skippare**: l'`assert` su dataset presenti in `dataset_ids_for_user` rende il modulo fragile in ambienti privi di `agrmet`/`lm5`/`lm2.2`, in contrasto con il marker `deterministic`.
- **Dipendenza da metadati DB non controllati dal test** (`agrmet`=OBS, gruppi license di `lm5`/`lm2.2`): l'esito di alcuni rami dipende dallo stato del DB runtime, non da dati creati dal test.
- **Push verificato solo con fake negativo**: si testa sempre `queue_exists → False`; il ramo positivo (coda esistente) non è coperto qui.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_no_schedule_setting_returns_400` | `validate_schedule` | 400 senza setting | — | `schedules_user` | Bassa |
| `test_period_less_than_15_minutes_returns_403` | `post` (MIN_PERIOD) | 403 periodo `<15min` | — | `schedules_user` | Bassa |
| `test_opendata_as_non_admin_returns_403` | `post` (opendata role) | 403 non-admin **(SCHEDULES-001)** | — | `schedules_user` | Media (anomalia) |
| `test_opendata_multidataset_returns_400` | `post` (opendata multi) | 400 multidataset | — | `admin_user` | Media |
| `test_opendata_observed_dataset_returns_400` | `post` (opendata OBS) | 400 dataset osservato | — | `admin_user` | Media |
| `test_postprocessor_unauthorized_returns_401` | `post` (postproc perm) | 401 senza permesso | — | utente inline | Bassa |
| `test_push_queue_missing_returns_403` | `post` (push) | 403 coda assente | RabbitMQ `MagicMock` | `schedules_user`, `monkeypatch` | Media |
| `test_push_queue_nonexistent_returns_403` | `post` (push) | 403 coda inesistente | RabbitMQ `MagicMock` + DB write | `schedules_user`, `monkeypatch` | Media |
