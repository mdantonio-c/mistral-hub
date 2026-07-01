# TEST_REVIEW_GUIDE.md — Indice e mappa della suite di test backend

> **Scopo**: indice operativo per la revisione manuale della suite generata automaticamente.
> NON ripete il contenuto delle singole review: per il dettaglio di un file aprire il relativo `*.review.md` accanto al test.
> Generato senza modificare alcun file Python e senza usare `untracked_stuff`.

- **File di test**: 54 moduli `test_*.py` sotto `integration/`
- **Funzioni di test**: ≈284 `def test_…` (le istanze effettive sono di più per via di `@pytest.mark.parametrize`, soprattutto in `observed/`)
- **File di review prodotti**: 83 (`*.review.md`) — uno accanto a ogni `test_*.py`, `conftest.py`, `support*.py` e helper
- **File senza review**: solo i marker di package vuoti (`__init__.py`, `.gitkeep`) e il template non eseguibile `helpers/templates/endpoint_template.py` (review presente, ma è documentazione)

---

## 1. Struttura della suite

```
tests/
├── conftest.py                      → fixture globali (test_runtime, cleanup_registry) + marker
├── README.md / docs/                → documentazione di suite (non test)
├── test_arpaesimc.sh                → smoke script tool meteo (shell)
├── helpers/                         → building block riusabili cross-area (NON test)
│   ├── auth.py                       → utenti temporanei, login, Basic auth, cleanup
│   ├── celery_fakes.py               → fake del trasporto Celery (3 varianti)
│   ├── cleanup.py                    → CleanupRegistry (teardown LIFO)
│   ├── data_ready.py                 → builder/seed/poll per data-ready e schedule
│   ├── dataset_window.py             → normalizza /api/fields (skip su 404)
│   ├── datasets.py                   → first_public_dataset_id (skip se assente)
│   ├── polling.py                    → wait_until (no sleep ciechi)
│   ├── runtime.py                    → TestRuntime singleton (cache id + override_attr)
│   ├── schedules.py                  → builder payload schedule (on-data-ready/crontab/periodic)
│   └── templates/endpoint_template.py→ template guida (NON raccolto da pytest)
└── integration/                     → test reali per dominio
    ├── conftest.py                  → fixture HTTP condivise (auth_headers, fresh_access_key)
    ├── access_key/   (2 test + conftest + support)
    ├── admin/        (4 test + support_EXT)
    ├── arco/         (3 test)
    ├── connectors/   (1 test)
    ├── customizer/   (1 test)
    ├── data/         (4 test + support_EXT)
    ├── data_ready/   (4 test + conftest)
    ├── dataset/      (2 test + support)
    ├── fields/       (1 test + support_EXT)
    ├── initializer/  (1 test)
    ├── observed/     (5 test + conftest + support)
    ├── opendata/     (3 test + support)
    ├── postprocessing/(5 test + conftest + support)
    ├── requests/     (2 test + conftest + support)
    ├── schedules/    (4 test + conftest)
    ├── services/     (3 test)
    ├── tasks/        (5 test + support_EXT)
    ├── templates/    (2 test + support_EXT)
    ├── tools/        (1 test)
    └── user_limits/  (1 test)
```

Strati di lettura (dal `README.md` della suite): `conftest.py` globale → `helpers/` → `integration/` → `integration/<area>/{conftest,support}`. La risposta "dove vive davvero un comportamento di test" è quasi sempre in `integration/<area>/`.

---

## 2. Copertura per file

Legenda livello: **U** = unit/pure-function, **I** = integration HTTP/DB/FS, **T** = task-level (chiamata diretta al task), **E2E** = catena asincrona reale (beat→broker→worker).

| Dominio | File di test | Backend principale | Tipo | #test | Livello |
|---|---|---|---|---|---|
| access_key | `test_access_key_api.py` | `endpoints/access_key.py`, `services/access_key_service.py`, `models AccessKey` | integration | 5 | I |
| access_key | `test_access_key_validation.py` | `services/access_key_service.py` | integration | 5 | I |
| admin | `test_admin_attributions_EXT.py` | `endpoints/admin_attributions.py` | integration | 4 | I |
| admin | `test_admin_datasets_EXT.py` | `endpoints/admin_datasets.py` | integration | 3 | I |
| admin | `test_admin_license_groups_EXT.py` | `endpoints/admin_license_groups.py` | integration | 3 | I |
| admin | `test_admin_licenses_EXT.py` | `endpoints/admin_licenses.py` | integration | 4 | I |
| arco | `test_arco_catalog.py` | `endpoints/arco.py` (S3+DB mockati) | integration | 1 | I |
| arco | `test_arco_proxy.py` | `endpoints/arco.py`, access-key | integration | 2 | I |
| arco | `test_arco_edge_cases_EXT.py` | `endpoints/arco.py` (`guess_mime_type`, `_round_coord`) | unit+integration | 11 | U/I |
| connectors | `test_s3_connector_EXT.py` | `connectors/s3/__init__.py` (boto mockato) | unit | 6 | U |
| customizer | `test_user_customizer_EXT.py` | `customization.py` hooks (+DB) | unit+integration | 5 | U/I |
| data | `test_data_endpoint_auth.py` | `endpoints/data.py` | integration | 1 | I |
| data | `test_data_endpoint_submission_EXT.py` | `endpoints/data.py` (Celery/Rabbit fake locali) | integration | 5 | I |
| data | `test_data_endpoint_validation_EXT.py` | `endpoints/data.py` (Arkimet fake) | integration | 7 | I |
| data | `test_file_download_EXT.py` | `endpoints/file.py` | integration | 3 | I |
| data_ready | `test_base_cases.py` | `endpoints/data_ready.py`, `tasks/on_data_ready_extractions.py` | integration | 4 | I |
| data_ready | `test_crontab.py` | crontab branch `on_data_ready_extractions` | integration | 2 | I |
| data_ready | `test_periodic.py` | `on_data_ready_extractions` (inline) + Celery fake | integration | 3 | I/T |
| data_ready | `test_run_mismatch.py` | model/runhour branch `on_data_ready_extractions` | integration | 2 | I |
| dataset | `test_dataset_authorization.py` | `endpoints/datasets.py`, `get_datasets` | integration | 1 | I |
| dataset | `test_dataset_visibility.py` | `endpoints/datasets.py` (anonimo) | integration | 1 | I |
| fields | `test_fields_api_EXT.py` | `endpoints/fields.py`, `services/dballe.py`, `services/arkimet.py` | integration | 21 | I |
| initializer | `test_initializer_smoke_EXT.py` | `initialization.py` (tutto fakeato) | smoke | 3 | U |
| observed | `test_observations_auth.py` | `endpoints/maps_observed.py` (`/observations`) | integration | 2 | I |
| observed | `test_observations_download_EXT.py` | `MapsObservations.post`, `services/dballe.py` | integration | 15 | I |
| observed | `test_observations_edge_cases_EXT.py` | `MapsObservations.get` (rami) | integration | 9 | I |
| observed | `test_observations_filters.py` | `MapsObservations.get`, dballe/arkimet | integration | 10 (×~28) | I |
| observed | `test_observations_station_details.py` | `MapsObservations.get` (stationDetails) | integration | 4 (×12) | I |
| opendata | `test_authorization.py` | `endpoints/opendata.py` (autorizzazione) | integration | 2 | I |
| opendata | `test_download.py` | `OpendataDownload/DownloadFile.get` | integration | 12 | I |
| opendata | `test_listing_filters.py` | `OpendataFileList.get`, `arki.decode_run` | integration | 4 | I |
| postprocessing | `test_forecast_basic.py` | `tools/derived_variables.py`, `statistic_elaboration.py` | integration (real binari) | 3 | I/T |
| postprocessing | `test_forecast_spatial.py` | `tools/grid_*`, `spare_point_interpol.py` | integration (real binari) | 4 | I/T |
| postprocessing | `test_forecast_chaining.py` | catena postprocessor + `output_formatting.py` | integration (real binari) | 2 | I/T |
| postprocessing | `test_observed_postprocessing.py` | `dballe.extract_data*`, `quality_check_filter.py` | integration (real binari) | 4 | I/T |
| postprocessing | `test_error_handling.py` | `data_extraction` error hooks | integration | 5 | I/T |
| requests | `test_delete_pending_request.py` | `endpoints/requests.py`, `tasks/requests_cleanup.py` | integration+task | 3 | I/T |
| requests | `test_requests_listing_archive_clone_EXT.py` | `UserRequests.get/put`, `CloneUserRequests.get` | integration | 10 | I |
| schedules | `test_schedule_api_contracts_EXT.py` | `Schedules.get`, `SingleSchedule.get` | integration | 4 | I |
| schedules | `test_schedule_validation_EXT.py` | `SingleSchedule.post` (rami validazione) | integration | 8 | I |
| schedules | `test_scheduled_requests_EXT.py` | `ScheduledRequests.get`, patch/delete | integration | 8 | I |
| schedules | `test_schedule_opendata_bridge.py` | schedule→data_ready→data_extract→opendata | integration + **async_real** | 2 | I/**E2E** |
| services | `test_access_key_service_EXT.py` | `services/access_key_service.py`, `models AccessKey` | unit | 4 | U |
| services | `test_arkimet_query_parsing_EXT.py` | `services/arkimet.py` (parser puri) | unit | 6 | U |
| services | `test_dballe_query_parsing_EXT.py` | `services/dballe.py` (parser puri) | unit | 8 | U |
| tasks | `test_data_extraction_helpers_EXT.py` | `data_extraction.py` (`human_size`…) | unit | 5 | U |
| tasks | `test_queue_sorting_EXT.py` | `data_extraction_utilities.py` (`queue_sorting`) | unit | 3 | U |
| tasks | `test_on_data_ready_task_edges_EXT.py` | `on_data_ready_extractions.py` | task (DB seed) | 4 | T |
| tasks | `test_requests_cleanup_expiration_EXT.py` | `requests_cleanup.py` (`automatic_cleanup`) | task (DB+FS) | 3 | T |
| tasks | `test_data_extraction_quota_and_notifications_EXT.py` | `data_extraction.py` (quota/notify) | unit+task (molti fake) | 8 | U/T |
| templates | `test_templates_listing_EXT.py` | `endpoints/templates.py` (`Templates.get`) | integration+FS | 5 | I |
| templates | `test_templates_upload_delete_EXT.py` | `Template.post/get/delete` | integration+FS | 10 | I |
| tools | `test_tool_helpers_EXT.py` | `tools/grid_*`, `spare_point_interpol.py` | unit | 9 | U |
| user_limits | `test_usage_and_hourly_EXT.py` | `endpoints/usage.py`, `request_hourly_report.py` | integration+DB+FS | 6 | I |

---

## 3. Mappa backend → test

| Modulo backend | Coperto da (domini/file) |
|---|---|
| `endpoints/access_key.py` | access_key/* |
| `services/access_key_service.py` | access_key/*, services/test_access_key_service, arco (validazione) |
| `models/sqlalchemy.py` (AccessKey) | access_key/*, services/test_access_key_service |
| `endpoints/admin_attributions.py` | admin/test_admin_attributions |
| `endpoints/admin_datasets.py` | admin/test_admin_datasets |
| `endpoints/admin_license_groups.py` | admin/test_admin_license_groups |
| `endpoints/admin_licenses.py` | admin/test_admin_licenses |
| `endpoints/arco.py` | arco/* |
| `connectors/s3/__init__.py` | connectors/test_s3_connector (reale), arco/* (mockato) |
| `customization.py` | customizer/test_user_customizer, observed (permessi default user) |
| `endpoints/data.py` | data/* (auth, submission, validation) |
| `endpoints/file.py` | data/test_file_download |
| `endpoints/data_ready.py` | data_ready/*, schedules/bridge |
| `endpoints/datasets.py` | dataset/* |
| `endpoints/fields.py` | fields/test_fields_api (+ `dataset_window` usato cross-dominio) |
| `endpoints/maps_observed.py` | observed/* (`/observations` GET+POST) |
| `endpoints/opendata.py` | opendata/*, schedules/bridge |
| `endpoints/requests.py` | requests/* |
| `endpoints/schedules.py` | schedules/*, data_ready/* (creazione schedule) |
| `endpoints/templates.py` | templates/* |
| `endpoints/usage.py` | user_limits |
| `endpoints/request_hourly_report.py` | user_limits |
| `services/arkimet.py` | services/test_arkimet_query_parsing (puri), fields, observed, opendata (`decode_run`), postprocessing |
| `services/dballe.py` | services/test_dballe_query_parsing (puri), observed/*, fields, postprocessing |
| `services/sqlapi_db_manager.py` | requests, data, schedules, opendata, fields, dataset, user_limits, admin (license response) |
| `tasks/data_extraction.py` | tasks/*, postprocessing/*, data (submission, mockata) |
| `tasks/data_extraction_utilities.py` | tasks/test_queue_sorting, data (routing) |
| `tasks/on_data_ready_extractions.py` | data_ready/*, schedules/bridge, tasks/test_on_data_ready_task_edges |
| `tasks/requests_cleanup.py` | tasks/test_requests_cleanup_expiration, requests/test_delete_pending, initializer (cron) |
| `tools/*.py` | postprocessing/* (via pipeline reale), tools/test_tool_helpers (puri) |
| `initialization.py` | initializer/test_initializer_smoke (fakeato) |

---

## 4. Mappa test → backend

Per il dettaglio completo aprire il `*.review.md` del file. Sintesi della superficie reale esercitata:

- **access_key/** → access-key lifecycle + validazione Basic (`endpoints/access_key.py`, `services/access_key_service.py`, `AccessKey`).
- **admin/** → CRUD admin con schema dinamiche `OneOf` runtime (`endpoints/admin_*.py`, modelli).
- **arco/** → proxy S3 + catalogo, auth manuale via access key; S3/DB quasi sempre fakeati.
- **connectors/** → solo `S3Ext.connect/is_connected/disconnect` con boto3 fakeato (nessuna rete).
- **customizer/** → hook `custom_user_properties_*`, `manipulate_profile`, `get_custom_*_fields` chiamati con utente dummy.
- **data/** → `POST /data` (validazione, quota, routing) + `GET /data/<file>`; task mai eseguito (solo `send_task`).
- **data_ready/** → `POST /data/ready` + decisione di scheduling; il worker è spesso **solo accodato** (vedi §10).
- **dataset/** → visibilità pubblica/privata e autorizzazione m2m.
- **fields/** → `/api/fields` su dati reali + validazioni sintetiche; arkimet category monkeypatchata in 2 test.
- **initializer/** → smoke su `Initializer.__init__` con SQLAlchemy/Celery/Arkimet tutti fakeati.
- **observed/** → `/observations` GET/POST su DBALLE/Arkimet reali; unica patch = soglia `LASTDAYS`.
- **opendata/** → listing/filtri/download/autorizzazione; dati auto-seminati su DB+FS reali.
- **postprocessing/** → pipeline di estrazione **reale** con binari `vg6d_*`/`v7d_*`/`dballe`/`eccodes`.
- **requests/** → listing/archive/clone + delete con grace period + `automatic_cleanup` (effetto globale).
- **schedules/** → CRUD/validazione schedule + bridge on-data-ready→opendata (1 test **async_real**).
- **services/** → parser puri arkimet/dballe + validità access key (nessun DB/HTTP).
- **tasks/** → helper puri + task con quota/notifiche/cleanup, molti sistemi esterni fakeati.
- **templates/** → upload/list/delete file su filesystem reale dell'utente.
- **tools/** → helper puri di interpolazione/cropping (nessun binario).
- **user_limits/** → `/usage` (quota+`du`) e `/requests/hourly-report` con seeding DB reale.

---

## 5. Helper globali

| Helper | Dove è definito | Utilizzato da | Descrizione |
|---|---|---|---|
| `create_authenticated_test_user`, `delete_test_user`, `register_test_user_cleanup`, `make_basic_auth`, `AuthenticatedTestUser` | [helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | access_key, data, fields, templates, tasks, requests, schedules… | Utenti temporanei autenticati + teardown + Basic auth |
| `AcceptTasksWithoutRunningCelery`, `InlineDataReadyExtractionCelery`, `InlineDataExtractCelery` | [helpers/celery_fakes.py](projects/mistral/backend/tests/helpers/celery_fakes.py) | data_ready/test_periodic, schedules/bridge | Fake del trasporto Celery (registra/ inline/ riproduce dedup) |
| `CleanupRegistry` | [helpers/cleanup.py](projects/mistral/backend/tests/helpers/cleanup.py) | tutta la suite (via `cleanup_registry`) | Teardown LIFO, non ingoia eccezioni |
| builder/seed/poll data-ready | [helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | data_ready/*, schedules/* | Crea utente `admin_root`, schedule, request sintetiche, polling |
| `fetch_dataset_window`, `DatasetWindow` | [helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | observed, postprocessing, schedules, data | Normalizza `/api/fields`; **`pytest.skip` su 404** |
| `first_public_dataset_id` | [helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py) | dataset/* | **`pytest.skip`** se nessun dataset pubblico |
| `wait_until` | [helpers/polling.py](projects/mistral/backend/tests/helpers/polling.py) | data_ready, schedules | Retry su predicato, no sleep ciechi |
| `TestRuntime` (`dataset_id`, `override_attr`) | [helpers/runtime.py](projects/mistral/backend/tests/helpers/runtime.py) | observed, fields, data_ready, schedules, postprocessing | Singleton di sessione: cache id + override attributi |
| `build_on_data_ready/crontab/periodic_schedule` | [helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py) | schedules, data_ready | Builder payload schedule |

Moduli `support`/`support_EXT` locali (NON globali, ma sostanziosi): `admin` (441), `data` (450), `fields` (468), `observed` (579), `opendata` (532), `postprocessing` (920), `tasks` (398), `templates` (184), `requests` (70), `dataset` (33), `access_key` (14). Ognuno ha la sua review.

---

## 6. Fixture globali

| Fixture | Dove è definita | Utilizzata da | Scopo |
|---|---|---|---|
| `test_runtime` | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | observed, fields, data_ready, schedules, postprocessing, user_limits | Singleton di sessione (cache id dataset, override attributi) |
| `cleanup_registry` | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | quasi tutti i domini | Teardown LIFO automatico dopo lo `yield` |
| `auth_headers` | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | access_key, fields, … | Login del **default user** (stato condiviso) |
| `fresh_access_key` | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | access_key, arco | Crea una access key per il default user |
| `client`, `app`, `faker` | `restapi.tests` (framework) | tutti | Client HTTP / app Flask / dati finti |

Fixture locali rilevanti (con comportamento nascosto da revisionare): `fresh_access_key_with_expiration` (access_key), `data_ready_base/admin_headers/user` (data_ready — override `ON_DATA_READY_DATASETS`, ruolo `admin_root`), `schedules_base/admin_headers/user` (schedules — **shadowed** dai `_EXT` locali), `pp_forecast_env`/`pp_observed_env` (postprocessing), scenario `dballe_/arkimet_/mixed_observed_case` (observed — pattern `parametrize`+`getfixturevalue`), `pending_request_user`/`pending_delete_requests` (requests).

---

## 7. Mock globali

| Mock/Fake | Dove | Utilizzo | Note |
|---|---|---|---|
| Fake Celery (3) | [helpers/celery_fakes.py](projects/mistral/backend/tests/helpers/celery_fakes.py) | data_ready/test_periodic, schedules/bridge | `InlineDataReadyExtractionCelery` **riproduce** la dedup-by-reftime → rischio falso positivo (vedi §10) |
| `RecordingCelery`+`FakeRabbit` (locali) | data/support_EXT | data/test_data_endpoint_submission | Montati via `monkeypatch`; task `data_extract` mai eseguito |
| Fake Arkimet (format/category) | data/support_EXT, fields | data/validation, fields (2 test) | `is_filter_allowed`/`get_datasets_*` sostituiti |
| Fake S3 (boto3) | connectors, arco (inline) | connectors/*, arco/* | Nessuna rete; arco fakea anche il DB |
| Fake SMTP / AMQP / `du` / template | tasks/support_EXT | tasks/quota_and_notifications | **Over-mock**: il test notifiche assembla solo dict (vedi §10) |
| `MagicMock` Celery RedBeat | schedules/test_scheduled_requests | enable/disable schedule | I conflitti 409 dipendono dal **ritorno del fake**, non dal DB |
| `monkeypatch` `datetime` | tasks/helpers, tasks/queue_sorting, user_limits/hourly | clock deterministico | In user_limits patcha il modulo `datetime` condiviso (isolamento solo via restore) |
| Fake Initializer (SQLAlchemy/Celery/Arkimet) | initializer/test_initializer_smoke | smoke | Asserzioni **tautologiche sui fake** (vedi §10) |

---

## 8. Componenti più testati (ranking per superficie esercitata)

1. **`services/dballe.py`** — observed (40, parametrizzati ×~52), fields (21), postprocessing (18), services/dballe (8). Il modulo più sollecitato della suite.
2. **`endpoints/maps_observed.py`** — observed (40 funzioni, molte istanze).
3. **`tasks/data_extraction.py`** — tasks (23), postprocessing (18), data (16).
4. **`endpoints/schedules.py`** — schedules (22), + creazione schedule da data_ready (11).
5. **`endpoints/fields.py`** — fields (21) + helper `dataset_window` usato da molti domini.
6. **`endpoints/opendata.py`** — opendata (18) + bridge schedule.
7. **`tools/*.py`** — postprocessing (18, pipeline reale) + tools (9, puri).
8. **`endpoints/data.py`** — data (16).
9. **`services/sqlapi_db_manager.py`** — trasversale (requests, schedules, opendata, fields, dataset, user_limits, admin).
10. **`endpoints/access_key.py` + `services/access_key_service.py`** — access_key (10) + services (4) + arco.

---

## 9. Componenti poco testati / scoperti

- **`endpoints/rabbit_out_bindings.py`** — **nessun test** (confermato: referenziato solo nella documentazione di gap).
- **`endpoints/maps_observed.py`** — coperto solo il ramo `/observations`; la parte "maps" non risulta esercitata dai test (non verificabile copertura oltre `/observations`).
- **`connectors/s3/__init__.py`** — solo unit con boto3 fakeato; `get_connection_exception` non testato; nessuna verifica reale di connessione.
- **`customization.py`** — il ramo dinamico `get_custom_input_fields` (POST con `OneOf` datasets) e la persistenza ORM in `custom_user_properties_post` non sono coperti.
- **`initialization.py`** — solo smoke su fake: i dati di seed reali non sono validati.
- **`endpoints/request_hourly_report.py` / `endpoints/usage.py`** — un solo modulo (6 test) li copre; contratto `request_par_hour` `None` vs `0` ambiguo.
- **`tasks/data_extraction.py`** — il ramo "tutti i retry email falliti" e parte della gestione quota a valle dell'estimate non sono coperti.
- Riferimento storico ai gap: [docs/coverage_extension_blueprint.md](projects/mistral/backend/tests/docs/coverage_extension_blueprint.md).

---

## 10. Rischi trasversali e criticità (sintesi per il revisore)

Questa sezione concentra i punti emersi dalle review che meritano attenzione prioritaria.

### 10.1 Skip silenziosi (rischio "verde ma non eseguito")
- **opendata**: in assenza di ≥1 `Attribution` nel DB, **15 dei 18 test** vengono saltati (inclusi tutti quelli di autorizzazione/sicurezza), anche due validazioni `400` che non avrebbero bisogno del dataset.
- **observed / fields / postprocessing / schedules-bridge**: numerosi test fanno `pytest.skip` quando il dataset/prodotto/finestra non è disponibile (`fetch_dataset_window` 404, `require_*`). La copertura reale dipende dai dati runtime.
- **dataset**: `first_public_dataset_id` salta se non c'è alcun dataset pubblico.

### 10.2 Logica verificata nel fake invece che nel backend (rischio falso positivo)
- **data_ready/test_base_cases (t3/t4), test_crontab, test_run_mismatch**: asseriscono "nessuna richiesta generata" ma `launch_all_on_data_ready_extractions` è **solo accodato, mai eseguito inline** → la decisione reale di gating **non è esercitata**: l'esito vuoto è tautologico.
- **data_ready/test_periodic**: la decisione "periodo trascorso" è reale, ma la creazione della `Request` e la dedup-by-reftime sono **reimplementate nel fake** `InlineDataReadyExtractionCelery`.
- **schedules/test_scheduled_requests**: i conflitti 409 enable/disable dipendono dal valore di ritorno del fake `get_periodic_task`, non dallo stato DB `is_enabled`.
- **initializer**: le asserzioni del test di wiring sono tautologiche sui fake (non validano i dati di seed).

### 10.3 Over-mocking
- **tasks/test_data_extraction_quota_and_notifications**: Arkimet + `du` + SMTP + RabbitMQ + template + `get_backend_url` tutti fakeati; il test notifiche AMQP verifica di fatto solo l'assemblaggio di un dict.
- **arco**: nessun test esercita S3/DB reali.

### 10.4 Marker fuorviante
- File marcati `integration` che sono in realtà **unit** puri: `services/*`, `tasks/test_data_extraction_helpers`, `tasks/test_queue_sorting`, `tools/test_tool_helpers`, `connectors/test_s3_connector`.

### 10.5 Bug di backend emersi durante la stesura dei test (documentati nelle review e in [docs/problems_and_bugs_discovered_in_extension.md](projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md))
- **ADMIN-001**: in `admin_licenses.py`/`admin_datasets.py` i controlli FK usano `...first` senza `()` → rami `NotFound` morti; lo `skip` aggira il `400` anticipato della `OneOf`.
- **ARCO-001**: il ramo errore-S3-generico→500 del proxy fa un `raise Exception` nudo; il relativo test è skippato.
- **SCHEDULES-001**: `test_opendata_as_non_admin_returns_403` può realmente fallire (202 vs 403).
- **EDGE-001 (observed)**: `NotFound("Station data not found")` è codice morto (`parse_obs_maps_response` ritorna sempre dict non vuoto).
- **TEMPLATES-001/002**: `Template.get` ha la condizione di esistenza **invertita**; estensione di un upload non valido mascherata da `FileNotFoundError`. Mismatch doc/impl (202 dichiarato, 200 reale; refuso `"succesfully deleted"`).

### 10.6 Stato condiviso / accoppiamento d'ordine
- Le fixture `auth_headers`/`fresh_access_key` operano sul **default user** condiviso: più domini ne mutano la chiave/permessi (`customization.py` imposta `allowed_obs_archive=True` sul default user, abilitando scenari observed e il 409 di edge_cases). Possibile fragilità in esecuzione parallela.
- `data_ready`/`schedules` girano spesso come `admin_root`, riducendo il valore dei controlli su permessi/quote.
- Alcuni test mutano licenze/dataset **reali** (`agrmet`) con ripristino in `finally`/`cleanup_registry`: se il teardown salta, il catalogo resta sporco.

---

## 11. Mappa complessiva (relazioni test → backend)

```
tests/integration/access_key/
  test_access_key_api.py / test_access_key_validation.py
    ↓ endpoints/access_key.py (AccessKeyResource, AccessKeyValidationResource)
    ↓ services/access_key_service.py (validate_access_key_from_request → is_access_key_valid)
    ↓ models/sqlalchemy.py (AccessKey.generate/is_valid)

tests/integration/admin/
  test_admin_{attributions,datasets,licenses,license_groups}_EXT.py
    ↓ endpoints/admin_*.py (CRUD + schema OneOf dinamiche)
    ↓ services/sqlapi_db_manager.py (_get_license_response…) → models

tests/integration/arco/
  test_arco_{catalog,proxy,edge_cases}.py
    ↓ endpoints/arco.py (ArcoResource.get, ArcoDatasetsResource.get)
    ↓ services/access_key_service.py   ↓ connectors/s3 (FAKE)

tests/integration/data/  +  tests/integration/tasks/
  test_data_endpoint_*.py / test_queue_sorting / test_data_extraction_*
    ↓ endpoints/data.py (Data.post, validazione, quota)
    ↓ tasks/data_extraction_utilities.py (queue_sorting)
    ↓ tasks/data_extraction.py (data_extract — FAKE transport in data/, reale in postprocessing/)

tests/integration/data_ready/  +  tests/integration/schedules/
  test_{base_cases,crontab,periodic,run_mismatch}.py / test_schedule_*.py
    ↓ endpoints/data_ready.py + endpoints/schedules.py
    ↓ tasks/on_data_ready_extractions.py (decisione scheduling)
    ↓ [bridge async_real] → tasks/data_extraction.py → endpoints/opendata.py

tests/integration/observed/  +  tests/integration/fields/
  test_observations_*.py / test_fields_api_EXT.py
    ↓ endpoints/maps_observed.py (/observations) + endpoints/fields.py
    ↓ services/dballe.py + services/arkimet.py (DBALLE/Arkimet reali; patch solo LASTDAYS)

tests/integration/postprocessing/
  test_forecast_*.py / test_observed_postprocessing.py / test_error_handling.py
    ↓ tasks/data_extraction.py (pipeline reale)
    ↓ tools/{derived_variables,grid_cropping,grid_interpolation,spare_point_interpol,
             statistic_elaboration,quality_check_filter,output_formatting}.py
    ↓ binari esterni: vg6d_transform / vg6d_getpoint / v7d_transform / dballe / eccodes

tests/integration/opendata/
  test_{authorization,download,listing_filters}.py
    ↓ endpoints/opendata.py (OpendataFileList/Download/DownloadFile.get)
    ↓ services/sqlapi_db_manager.py (check_dataset_authorization) + FS /opendata

tests/integration/requests/
  test_delete_pending_request.py / test_requests_listing_archive_clone_EXT.py
    ↓ endpoints/requests.py (UserRequests.get/put/delete, CloneUserRequests.get)
    ↓ tasks/requests_cleanup.py (automatic_cleanup — effetto globale)

tests/integration/{services,tools,connectors}/   (UNIT puri)
  test_{access_key_service,arkimet_query_parsing,dballe_query_parsing}_EXT.py
    ↓ services/{access_key_service,arkimet,dballe}.py (funzioni pure)
  test_tool_helpers_EXT.py    ↓ tools/*.py (get_trans_type, check_*_filepath, format_sub_type)
  test_s3_connector_EXT.py    ↓ connectors/s3/__init__.py (boto3 FAKE)

tests/integration/{customizer,initializer,templates,user_limits}/
  test_user_customizer_EXT.py     ↓ customization.py (hook con utente dummy)
  test_initializer_smoke_EXT.py   ↓ initialization.py (SQLAlchemy/Celery/Arkimet FAKE)
  test_templates_*.py             ↓ endpoints/templates.py (+ FS /data/<uuid>/uploads)
  test_usage_and_hourly_EXT.py    ↓ endpoints/usage.py + request_hourly_report.py (+ DB/FS reali)
```

---

## 12. Come usare questa guida in review

1. Parti dal dominio che ti interessa nella tabella **§2 Copertura**.
2. Apri il `*.review.md` accanto al file di test per il dettaglio (sezioni 1–9).
3. Per capire fixture/helper condivisi, usa **§5/§6/§7** e le review in `helpers/` e nei `conftest.py`/`support*.py`.
4. Prima di fidarti di un test "verde", controlla **§10.1 (skip)** e **§10.2 (logica nel fake)** per il dominio.
5. I bug backend già individuati sono in **§10.5** (non vanno "corretti" in fase di review: sono note per il revisore).
