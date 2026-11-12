# Review — `test_schedule_validation.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/schedules/test_schedule_validation.py](projects/mistral/backend/tests/integration/schedules/test_schedule_validation.py)
- **Scopo**: coprire gli **edge di validazione** di `POST /schedules`: assenza di setting (400), periodo `< 15 min` (403), opendata per non-admin (403), opendata multidataset (400), opendata su dataset osservato (400), postprocessor senza permesso (401), push senza/with coda inesistente (403×2).
- **Tipologia**: test di **integrazione HTTP** (controller reale + schema marshmallow reale + DB SQLAlchemy). RabbitMQ **mockato** nei soli rami push; Celery/RedBeat **mai raggiunti** (guardia autouse, vedi §6). Marker di modulo: `pytestmark = [pytest.mark.integration, pytest.mark.deterministic]`. 8 test (classe `TestScheduleValidation`).
- **Attenzione**: il test `test_opendata_as_non_admin_returns_403` era collegato all'anomalia **SCHEDULES-001** (vedi §8): l'utente "non admin" riceveva un ruolo casuale e a volte l'endpoint rispondeva `202` invece di `403`. Correzione applicata nel test: `schedules_user` ha ora il solo ruolo `Role.USER`. **Risolta**: validata il 10/11/2026 su commit `7858231d` con 10 run consecutive verdi del file (8 passed ciascuna) e run completa `--folder custom` verde.

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
| `schedules_endpoint.celery` | [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py) | **Sostituito** in tutti i test dalla guardia `forbid_real_schedule_dispatch`: se l'handler arriva a `celery.get_instance()`, il test fallisce prima di creare la schedule. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**. |
| `monkeypatch` | fixture | `pytest` | Patcha `rabbitmq.get_instance` nei test push e il nome `celery` del modulo endpoint (guardia). |
| `forbid_real_schedule_dispatch` | fixture **locale autouse** | questo file | Sostituisce `celery` nel solo modulo endpoint con una funzione che chiama `pytest.fail`. |
| `schedules_user` | fixture **locale** | questo file | Utente non-admin con ruolo esplicito `Role.USER` (`roles` nei permessi, come in `admin/support.py`): `allowed_schedule`, `open_dataset`, `datasets=[agrmet, lm5, lm2.2]`. **Shadowa** la fixture omonima del conftest. |
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
- **Setup**: `schedules_user` (solo `Role.USER`); in arrange il test asserisce che i ruoli persistiti dell'utente siano esattamente `[Role.USER.value]`.
- **Assert**: ruoli persistiti `== [Role.USER.value]`; `status_code == 403`.
- **Casi coperti**: gate role-based opendata. **SCHEDULES-001 (corretta nel test)**: prima `schedules_user` non passava ruoli e `BaseTests.create_user` ne sceglieva uno a caso, incluso `admin_root`, superando il gate. Prima della guardia la chiamata restituiva `202` e creava una schedule reale con il relativo task RedBeat. Ora il ruolo è fissato e l'assert in arrange rende esplicita la precondizione. Risolta e validata (10 run consecutive verdi). Vedi §8.

### `test_opendata_multidataset_returns_400`
- **Obiettivo**: `opendata=true` con **due** dataset → **400**.
- **Backend coinvolto**: ramo `opendata` → `if len(dataset_names) > 1: raise BadRequest` (preceduto dal controllo license-group).
- **Flusso**: body `opendata:True`, `dataset_names:[lm5, lm2.2]` → `POST` come `admin_user`.
- **Setup**: `admin_user` (admin per superare il gate role-based).
- **Assert**: `status_code == 400` e body `== "Multi dataset for opendata schedules is not supported"`.
- **Casi coperti**: edge opendata multidataset. L'assert sul messaggio distingue il ramo multidataset dal controllo `get_license_group` precedente, che risponde anch'esso `400` ma con "Invalid set of datasets : datasets belongs to different license groups". Nel runtime verificato `lm5` e `lm2.2` sono nello stesso gruppo licenza: non servono dataset sintetici.

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
         ├─ get_license_group(datasets) → 400 se gruppi diversi   (escluso dal test 4 via messaggio)
         ├─ if opendata:
         │     ├─ "admin_root" not in roles → Forbidden 403       [test 3] (SCHEDULES-001)
         │     ├─ len(datasets) > 1 → BadRequest 400              [test 4]
         │     └─ category=="OBS" → BadRequest 400                [test 5]
         ├─ if period_settings minutes & every<15 → Forbidden 403 [test 2]
         ├─ if postprocessors & not allowed_postprocessing → 401  [test 6]
         ├─ if push: rabbit.queue_exists(q) False → Forbidden 403 [test 7,8]
         └─ celery.get_instance()  ◄─ guardia: pytest.fail (validazione superata per errore)
              └─ (mai raggiunti) create_schedule_record → task RedBeat → data_extract se on-data-ready
```

## 6. Comportamenti nascosti

- **Precondizione runtime "hard" in fixture/helper**: `dataset_ids_for_user` esegue `assert dataset is not None` per `agrmet`, `lm5`, `lm2.2`. Se uno manca nel DB, **fallisce il setup della fixture** (non uno `skip`): il modulo è marcato `deterministic` ma presuppone questi dataset presenti. Differente dal pattern `dataset_window`→`pytest.skip` usato altrove.
- **Concessione esplicita dei dataset** (docstring di `dataset_ids_for_user`): i dataset sono autorizzati apposta perché il test isoli i rami opendata/multidataset/observed senza che le regole sui dataset privati `lm5`/`lm2.2` diventino l'oracolo dell'assert.
- **Due fixture utente con scopi opposti**: `schedules_user` (non admin) per i 403 role-based; `admin_user` (admin_root) per superare il gate e raggiungere i 400 opendata.
- **Mutazione diretta del DB** (test 8): `user.amqp_queue` impostata via SQLAlchemy, bypassando l'API admin.
- **RabbitMQ mockato** (test 7-8): `MagicMock.queue_exists → False`; il broker reale non è coinvolto, il ramo è reso deterministico.
- **Shadowing della fixture `schedules_user`**: come negli altri test del dominio che la ridefiniscono, la fixture locale nasconde quella (super-utente) del conftest.
- **Guardia sui servizi reali**: `forbid_real_schedule_dispatch` sostituisce il nome `celery` del modulo endpoint. Tutte le validazioni dell'handler avvengono prima di `celery.get_instance()`, mentre riga `schedules`, task RedBeat e primo `data_extract` vengono dopo. `pytest.fail` solleva un'eccezione che il catch-all di restapi non converte in risposta HTTP, quindi una validazione superata per errore produce un fallimento esplicito anche nei test che si aspettano 400.
- **Ruolo casuale degli utenti temporanei**: `create_authenticated_test_user` non passa ruoli e `BaseTests.create_user` ne sceglie uno a caso tra quelli dello schema admin. Era la causa di SCHEDULES-001; `schedules_user` ora passa `roles=[Role.USER]` nei permessi. L'utente inline di `test_postprocessor_unauthorized_returns_401` mantiene il ruolo casuale, ma il ramo postprocessing non dipende dal ruolo.

## 7. Checklist di revisione

- [x] **SCHEDULES-001**: ruoli di `schedules_user` resi espliciti (`Role.USER`), come in `admin/support.py`, con assert in arrange sui ruoli persistiti. **Risolta**: validata il 10/11/2026 su commit `7858231d` con 10 run consecutive verdi del file (8 passed ciascuna) e run completa `--folder custom` verde.
- [x] Una validazione superata per errore non crea schedule né task RedBeat reali: la guardia fa fallire il test.
- [x] `test_opendata_multidataset_returns_400` asserisce il messaggio del ramo "multidataset", escludendo il 400 del controllo `get_license_group` precedente.
- [ ] Verificare la precondizione runtime di `agrmet=OBS` per `test_opendata_observed_dataset_returns_400`.
- [ ] Considerare che `dataset_ids_for_user` **fallisce** (non skippa) se i dataset mancano: valutarne la portabilità locale/CI.
- [ ] Confermare che 401 (postprocessing) vs 403 (push/period/opendata-role) vs 400 (validation/opendata-shape) corrispondano ai contratti voluti.

## 8. Possibili criticità

- **SCHEDULES-001 — test instabile per ruolo casuale (risolta)**: `test_opendata_as_non_admin_returns_403` falliva circa una volta su cinque quando `schedules_user` riceveva per caso `admin_root`. Ora la fixture passa `roles=[Role.USER]` e il test asserisce in arrange che i ruoli persistiti siano solo `Role.USER`: una regressione nella fixture fallisce sull'assert di precondizione, non sul gate. Nessun `xfail`/`skip`/rerun. Prima della guardia, un'esecuzione con esito `202` aveva lasciato attiva in RedBeat la schedule `test_opendata_non_admin`. Validazione: 10 run consecutive verdi del file e run completa verde su commit `7858231d`; i conteggi di chiavi `redbeat:*` (Redis DB 3) e di schedule nel DB sono identici prima e dopo, quindi nessun residuo.
- **Oracolo del 400 multidataset (risolto)**: license-group e multidataset producono entrambi `400`; il test ora asserisce il messaggio "Multi dataset for opendata schedules is not supported". Se in futuro `lm5`/`lm2.2` finissero in gruppi licenza diversi il test fallirebbe invece di passare per il motivo sbagliato.
- **Setup che fallisce invece di skippare**: l'`assert` su dataset presenti in `dataset_ids_for_user` rende il modulo fragile in ambienti privi di `agrmet`/`lm5`/`lm2.2`, in contrasto con il marker `deterministic`.
- **Dipendenza da metadati DB non controllati dal test** (`agrmet`=OBS, gruppi license di `lm5`/`lm2.2`): l'esito di alcuni rami dipende dallo stato del DB runtime, non da dati creati dal test.
- **Push verificato solo con fake negativo**: si testa sempre `queue_exists → False`; il ramo positivo (coda esistente) non è coperto qui.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_no_schedule_setting_returns_400` | `validate_schedule` | 400 senza setting | — | `schedules_user` | Bassa |
| `test_period_less_than_15_minutes_returns_403` | `post` (MIN_PERIOD) | 403 periodo `<15min` | — | `schedules_user` | Bassa |
| `test_opendata_as_non_admin_returns_403` | `post` (opendata role) | ruolo persistito solo `Role.USER` + 403 non-admin (SCHEDULES-001 risolta, 10 run verdi) | guardia Celery | `schedules_user` | Bassa |
| `test_opendata_multidataset_returns_400` | `post` (opendata multi) | 400 + messaggio multidataset | — | `admin_user` | Media |
| `test_opendata_observed_dataset_returns_400` | `post` (opendata OBS) | 400 dataset osservato | — | `admin_user` | Media |
| `test_postprocessor_unauthorized_returns_401` | `post` (postproc perm) | 401 senza permesso | — | utente inline | Bassa |
| `test_push_queue_missing_returns_403` | `post` (push) | 403 coda assente | RabbitMQ `MagicMock` | `schedules_user`, `monkeypatch` | Media |
| `test_push_queue_nonexistent_returns_403` | `post` (push) | 403 coda inesistente | RabbitMQ `MagicMock` + DB write | `schedules_user`, `monkeypatch` | Media |
