# Guida alla revisione dei test backend

## 0. Scopo e come usare questa guida

Questa guida è l'indice unico di **copertura, stato e rischi** della suite di test backend di
Meteo-Hub (`projects/mistral/backend/tests`). È l'unico documento che riporta conteggi ed esiti.
Come lavorare, eseguire i test, posizionare fixture e helper e interpretare i marker è spiegato nel
[README](README.md); il dettaglio di ogni file è nella sua review (`<file>.py.review.md`).

Checklist per chi rivede un'area:

1. Parti dal dominio nella [§3](#3-indice-dei-file) e apri la review del file.
2. Se ti interessa una funzionalità backend, parti dalla [§4](#4-mappa-backend---test).
3. Per fixture, helper e fake condivisi controlla le avvertenze nella [§5](#5-fixture-helper-e-mock-condivisi).
4. Prima di fidarti di un esito verde, leggi skip condizionali e logica nei fake nella [§7](#7-rischi-per-il-revisore).
5. I bug backend elencati nella §7 sono note: non vanno corretti durante la revisione dei test.

## 1. Stato attuale

### Inventario

| Voce | Valore |
|---|---|
| Moduli `test_*.py` | **58** |
| Funzioni di test (`def test_` / `async def test_`) | **299** |
| Domini sotto `integration/` | **20** |
| File `*.review.md` | **90** |
| File `.py` (esclusi `__init__.py`) senza review accanto | **0** |

I 90 file `.py` con review sono: 58 moduli di test, 9 `conftest.py` (root, `integration/` e 7 domini),
10 `support.py`, 12 helper in `helpers/` e il modello `helpers/templates/endpoint_template.py`.

| Dominio | Moduli | Test | Dominio | Moduli | Test |
|---|---:|---:|---|---:|---:|
| `access_key` | 2 | 10 | `observed` | 5 | 40 |
| `admin` | 4 | 15 | `opendata` | 3 | 18 |
| `arco` | 3 | 14 | `postprocessing` | 5 | 18 |
| `connectors` | 1 | 6 | `requests` | 2 | 13 |
| `customizer` | 1 | 5 | `schedules` | 5 | 23 |
| `data` | 6 | 22 | `services` | 3 | 18 |
| `data_ready` | 4 | 11 | `tasks` | 5 | 23 |
| `dataset` | 2 | 5 | `templates` | 2 | 15 |
| `fields` | 1 | 21 | `tools` | 1 | 9 |
| `initializer` | 2 | 7 | `user_limits` | 1 | 6 |

Marker (tutti i 58 moduli hanno `integration`):

| Combinazione | Moduli |
|---|---:|
| `integration` + `deterministic` | 37 |
| `integration` + `deterministic` + `runtime_sensitive` | 18 |
| `integration` + `runtime_sensitive` + `async_real` (`test_data_extraction_real_worker`, `test_schedule_on_data_ready_real_worker`) | 2 |
| misto: modulo `integration` + `runtime_sensitive`, un test `deterministic` e uno `async_real` (`test_schedule_opendata_bridge`) | 1 |

Totale: `deterministic` in 56 moduli, `runtime_sensitive` in 21, `async_real` in 3 moduli / 5 test.
Il modello `helpers/templates/endpoint_template.py` usa un marker di esempio non registrato
(`example_area`) e non è raccolto da pytest.

### Ultima validazione completa

| Voce | Valore |
|---|---|
| Data | 12/11/2026 |
| Codice | commit `c73ff83b` con modifiche non committate (in stage) limitate alla documentazione: `README.md`, questa guida e 90 file `*.review.md`; nessun file `.py` modificato |
| Ambiente | stack in modalità test (`APP_MODE=test` nel container backend) |
| Comando | `rapydo shell backend 'restapi tests --wait --no-destroy --folder custom'` |
| Esito | **356 passed, 5 skipped, 2 xfailed**, 0 failed, 0 error, 10 warning |
| Durata | 537,22 s (8 min 57 s) |
| Istanze raccolte | 363 (le 299 funzioni più le istanze di `parametrize`) |
| `async_real` | 5/5 passed (eseguiti solo con stack `rapydo --testing start -f`; con stack in modalità development risultano saltati) |

Skip e xfail dell'esecuzione, tutti già previsti nella tabella seguente:

| Test | Esito | Motivo |
|---|---|---|
| `test_fields_forecast_summary_stats_false_is_skipped_for_known_backend_bug` (`test_fields_api`) | skip | `Fields.get` forecast con `SummaryStats=false` usa `resulting_fields` non definita |
| `test_observations_station_details_unknown_station_returns_not_found` (`test_observations_edge_cases`) | skip | EDGE-001 |
| `test_template_upload_rejects_wrong_extension` (`test_templates_upload_delete`) | skip | TEMPLATES-002 |
| `test_template_get_existing_file_returns_filepath_and_format` (`test_templates_upload_delete`) | skip | TEMPLATES-001 |
| `test_template_get_missing_file_returns_404` (`test_templates_upload_delete`) | skip | TEMPLATES-001 |
| test sul `ClientError` S3 generico (`test_arco_edge_cases`) | xfail strict | ARCO-001 |
| `test_second_run_on_aligned_state_writes_nothing` (`test_initializer_seed`) | xfail strict | confronto enum/stringa su `ds_entry.category` in `initialization.py` |

### Skip e xfail attesi

| Test | Esito | Motivo (bug backend) |
|---|---|---|
| `test_fields_forecast_summary_stats_false_is_skipped_for_known_backend_bug` (`test_fields_api`) | skip | `Fields.get` in modalità forecast con `SummaryStats=false` usa `resulting_fields`, definita solo nel ramo osservato (`projects/mistral/backend/endpoints/fields.py`). Senza codice. |
| `test_observations_station_details_unknown_station_returns_not_found` (`test_observations_edge_cases`) | skip | **EDGE-001**: il `NotFound("Station data not found")` di `MapsObservations` è irraggiungibile perché `parse_obs_maps_response` restituisce sempre un dict non vuoto. |
| 2 test su `GET /templates/<name>` (`test_templates_upload_delete`) | skip | **TEMPLATES-001**: `Template.get` ha il controllo di esistenza invertito (`if filepath.exists(): raise NotFound`). |
| test sull'estensione non ammessa (`test_templates_upload_delete`) | skip | **TEMPLATES-002**: lo status 400 è corretto ma il messaggio è mascherato da un `FileNotFoundError` nella pulizia. |
| test sul `ClientError` S3 generico (`test_arco_edge_cases`) | xfail strict | **ARCO-001**: `raise Exception from e` in `projects/mistral/backend/endpoints/arco.py` viene esposto come 400 invece di 500. |
| `test_second_run_on_aligned_state_writes_nothing` (`test_initializer_seed`) | xfail strict | `projects/mistral/backend/initialization.py` confronta l'enum `ds_entry.category` con una stringa: il dataset viene riscritto a ogni avvio. Senza codice. |

Gli altri skip sono condizionali all'ambiente (dati, dataset o stack assenti): sono elencati nella §7.

## 2. Struttura della suite

```text
projects/mistral/backend/tests/
├── README.md, TEST_REVIEW_GUIDE.md
├── conftest.py                  marker, fixture di sessione, skip async_real
├── test_arpaesimc.sh            smoke shell dei tool meteo (non pytest)
├── helpers/                     helper trasversali (12 moduli) + templates/endpoint_template.py
└── integration/
    ├── conftest.py              fixture HTTP condivise (auth, access key, perimetro cleanup)
    ├── access_key/   admin/        arco/        connectors/   customizer/
    ├── data/         data_ready/   dataset/     fields/       initializer/
    ├── observed/     opendata/     postprocessing/  requests/ schedules/
    └── services/     tasks/        templates/   tools/        user_limits/
```

Domini con `conftest.py` locale: `access_key`, `admin`, `data_ready`, `observed`, `postprocessing`,
`requests`, `schedules`. Domini con `support.py`: `access_key`, `admin`, `data`, `fields`,
`observed`, `opendata`, `postprocessing`, `requests`, `tasks`, `templates`.

## 3. Indice dei file

Livello: **U** unitario (funzioni o classi chiamate direttamente, senza HTTP); **I** integrazione
HTTP con DB e servizi reali; **T** task Celery eseguito in-process; **E2E** worker Celery reale
(`async_real`). Le tabelle indicano per titolo la cartella; i link puntano alle review.

### Root e helper (`projects/mistral/backend/tests/`)

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Marker, `test_runtime`, `cleanup_registry`, skip `async_real` senza mock SMTP | — | — | — | [review](conftest.py.review.md) |
| `helpers/auth.py` | Utenti temporanei autenticati, header, cleanup utenti | API utenti `restapi` | — | — | [review](helpers/auth.py.review.md) |
| `helpers/celery_fakes.py` | Fake del trasporto Celery, esecuzione inline del data-ready | `launch_all_on_data_ready_extractions` | — | — | [review](helpers/celery_fakes.py.review.md) |
| `helpers/cleanup.py` | Registro di cleanup LIFO per callback e percorsi | — | — | — | [review](helpers/cleanup.py.review.md) |
| `helpers/data_ready.py` | Utenti dedicati, payload `/data/ready`, schedule, polling e cleanup del cluster data-ready/schedules | `DataReady`, `Schedules` | — | — | [review](helpers/data_ready.py.review.md) |
| `helpers/datasets.py` | Bundle dataset sintetici, rete privata, `require_dataset` | modelli `Datasets`, `License`, `Attribution` | — | — | [review](helpers/datasets.py.review.md) |
| `helpers/dataset_window.py` | Finestra temporale e run di un dataset letti da `/fields` | `Fields` | — | — | [review](helpers/dataset_window.py.review.md) |
| `helpers/observed_windows.py` | Finestre observed, override `BeDballe.LASTDAYS`, probe dataset/prodotti | `BeDballe` | — | — | [review](helpers/observed_windows.py.review.md) |
| `helpers/polling.py` | Attesa generica `wait_until` | — | — | — | [review](helpers/polling.py.review.md) |
| `helpers/real_workers.py` | Supporto `async_real`: controllo stack, attese worker, email mock SMTP, RedBeat | worker Celery reali | — | — | [review](helpers/real_workers.py.review.md) |
| `helpers/runtime.py` | `TestRuntime`: cache e override di sessione | `Datasets` | — | — | [review](helpers/runtime.py.review.md) |
| `helpers/schedules.py` | Payload JSON di schedule on-data-ready, crontab e periodiche | `Schedules` | — | — | [review](helpers/schedules.py.review.md) |
| `helpers/task_perimeter.py` | Confina i task globali alle righe e ai file del test | `automatic_cleanup`, `launch_all_on_data_ready_extractions` | — | — | [review](helpers/task_perimeter.py.review.md) |
| `helpers/templates/endpoint_template.py` | Modello di modulo di test, non raccolto | — | — | — | [review](helpers/templates/endpoint_template.py.review.md) |
| `integration/conftest.py` | `auth_headers`, `access_key_owner`, `fresh_access_key`, `requests_cleanup_perimeter` | `AccessKeyResource`, `automatic_cleanup` | — | — | [review](integration/conftest.py.review.md) |

### `integration/access_key/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Chiave con scadenza esplicita | `AccessKeyResource` | — | — | [review](integration/access_key/conftest.py.review.md) |
| `support.py` | URL degli endpoint access key | — | — | — | [review](integration/access_key/support.py.review.md) |
| `test_access_key_api.py` | Ciclo di vita: recupero, nuova chiave, chiave senza scadenza e scaduta | `AccessKeyResource` | I | 5 | [review](integration/access_key/test_access_key_api.py.review.md) |
| `test_access_key_validation.py` | Validazione con credenziali mancanti, email o chiave errata, casi validi | `AccessKeyValidationResource` | I | 5 | [review](integration/access_key/test_access_key_validation.py.review.md) |

### `integration/admin/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Header dell'admin di default | — | — | — | [review](integration/admin/conftest.py.review.md) |
| `support.py` | URL, payload, creazione via API con cleanup, pulizia DB | — | — | — | [review](integration/admin/support.py.review.md) |
| `test_admin_attributions.py` | CRUD admin delle attribution | `AdminAttributions` | I | 5 | [review](integration/admin/test_admin_attributions.py.review.md) |
| `test_admin_datasets.py` | CRUD admin dei dataset e cambio di license/attribution | `AdminDatasets` | I | 3 | [review](integration/admin/test_admin_datasets.py.review.md) |
| `test_admin_license_groups.py` | CRUD admin dei license group (`is_public`, `dballe_dsn`) | `AdminLicGroups` | I | 3 | [review](integration/admin/test_admin_license_groups.py.review.md) |
| `test_admin_licenses.py` | CRUD admin delle license, cambio group, `url=""` → `None` | `AdminLicenses` | I | 4 | [review](integration/admin/test_admin_licenses.py.review.md) |

### `integration/arco/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `test_arco_catalog.py` | Catalogo ARCO | `ArcoDatasetsResource`, `DatasetSchema` | I | 1 | [review](integration/arco/test_arco_catalog.py.review.md) |
| `test_arco_edge_cases.py` | Helper puri, errori S3, autorizzazione e casi limite del proxy | `ArcoResource`, `guess_mime_type`, `_round_coord` | U/I | 11 | [review](integration/arco/test_arco_edge_cases.py.review.md) |
| `test_arco_proxy.py` | Proxy ARCO e risposte integrate | `ArcoResource` | I | 2 | [review](integration/arco/test_arco_proxy.py.review.md) |

### `integration/connectors/`, `integration/customizer/`, `integration/services/`, `integration/tools/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `connectors/test_s3_connector.py` | Parametri obbligatori e costruzione del client del connector S3 | `S3Ext` | U | 6 | [review](integration/connectors/test_s3_connector.py.review.md) |
| `customizer/test_user_customizer.py` | Default del profilo utente e separazione `datasets` | `Customizer` | U | 5 | [review](integration/customizer/test_user_customizer.py.review.md) |
| `services/test_access_key_service.py` | Token e scadenza di `AccessKey`, validità della chiave | `is_access_key_valid`, modello `AccessKey` | U | 4 | [review](integration/services/test_access_key_service.py.review.md) |
| `services/test_arkimet_query_parsing.py` | Parser puri Arkimet | `BeArkimet.is_filter_allowed`, `parse_reftime`, `parse_matchers`, `decode_run` | U | 6 | [review](integration/services/test_arkimet_query_parsing.py.review.md) |
| `services/test_dballe_query_parsing.py` | Parser di query e filtri DB-All.e | `BeDballe.from_query_to_dic`, `parse_query_for_*`, `from_filters_to_lists` | U | 8 | [review](integration/services/test_dballe_query_parsing.py.review.md) |
| `tools/test_tool_helpers.py` | Mapping `sub_type` → `trans_type` e controlli sui file dei tool spaziali | `get_trans_type`, `check_template_filepath`, `check_coord_filepath`, `format_sub_type` | U | 9 | [review](integration/tools/test_tool_helpers.py.review.md) |

### `integration/data/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `support.py` | Payload, utenti con permessi di estrazione, dataset sintetici, fake Celery/RabbitMQ | — | — | — | [review](integration/data/support.py.review.md) |
| `test_data_endpoint_auth.py` | `POST /data` senza credenziali → 401 | `Data` | I | 1 | [review](integration/data/test_data_endpoint_auth.py.review.md) |
| `test_data_endpoint_submission.py` | Submission: creazione `Request` e routing Celery | `Data`, `queue_sorting` | I | 5 | [review](integration/data/test_data_endpoint_submission.py.review.md) |
| `test_data_endpoint_validation.py` | Rami di rifiuto prima della submission | `Data` | I | 7 | [review](integration/data/test_data_endpoint_validation.py.review.md) |
| `test_data_extraction_real_worker.py` | Estrazione riuscita, fallita con email, cleanup che revoca il task in coda | `Data`, `data_extract`, `automatic_cleanup` | E2E | 3 | [review](integration/data/test_data_extraction_real_worker.py.review.md) |
| `test_file_download.py` | Tre livelli di controllo di `GET /data/<filename>` | `FileDownload` | I | 3 | [review](integration/data/test_file_download.py.review.md) |
| `test_real_worker_cleanup.py` | Cleanup dei test `async_real` con worker simulati | `helpers/real_workers.py` | U | 3 | [review](integration/data/test_real_worker_cleanup.py.review.md) |

### `integration/data_ready/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Dataset abilitati, utenti admin dedicati, `/schedules` senza Celery reale | — | — | — | [review](integration/data_ready/conftest.py.review.md) |
| `test_base_cases.py` | Accettazione base, dataset non abilitati, schedule disattive o ignorate | `DataReady`, `launch_all_on_data_ready_extractions` | I/T | 4 | [review](integration/data_ready/test_base_cases.py.review.md) |
| `test_crontab.py` | Schedule on-data-ready che non parte se il crontab non combacia | idem | I/T | 2 | [review](integration/data_ready/test_crontab.py.review.md) |
| `test_periodic.py` | Nuova richiesta solo dopo il periodo previsto | idem | I/T | 3 | [review](integration/data_ready/test_periodic.py.review.md) |
| `test_run_mismatch.py` | Modello o run-hour non coerenti non attivano la schedule | idem | I/T | 2 | [review](integration/data_ready/test_run_mismatch.py.review.md) |

### `integration/dataset/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `test_dataset_authorization.py` | Dataset accessibili in base ai permessi, con cataloghi sintetici | `Datasets`, `SingleDataset`, `check_dataset_authorization` | I | 4 | [review](integration/dataset/test_dataset_authorization.py.review.md) |
| `test_dataset_visibility.py` | Visibilità anonima di un dataset pubblico sintetico | `Datasets` | I | 1 | [review](integration/dataset/test_dataset_visibility.py.review.md) |

### `integration/fields/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `support.py` | URL, finestre dati ammesse, utenti e dataset sintetici, override runtime | — | — | — | [review](integration/fields/support.py.review.md) |
| `test_fields_api.py` | `GET /fields` in modalità mappa osservata, osservata e forecast | `Fields`, `BeDballe`, `BeArkimet` | I | 21 | [review](integration/fields/test_fields_api.py.review.md) |

### `integration/initializer/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `test_initializer_seed.py` | Cosa l'initializer scrive davvero nel DB (18 istanze) | `Initializer` | I | 4 | [review](integration/initializer/test_initializer_seed.py.review.md) |
| `test_initializer_smoke.py` | Invarianti dell'initializer senza ripeterne il seeding | `Initializer` | U | 3 | [review](integration/initializer/test_initializer_smoke.py.review.md) |

### `integration/observed/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Scenari osservati `dballe`, `arkimet`, `mixed` con override di `BeDballe.LASTDAYS` | — | — | — | [review](integration/observed/conftest.py.review.md) |
| `support.py` | Scoperta di parametri validi, query, casi parametrizzati, parsing stazioni/prodotti | — | — | — | [review](integration/observed/support.py.review.md) |
| `test_observations_auth.py` | Errori di validazione con query incompleta | `MapsObservations` | I | 2 | [review](integration/observed/test_observations_auth.py.review.md) |
| `test_observations_download.py` | `POST /observations`: stream JSON/BUFR, `reliabilityCheck`, validazioni | `MapsObservations`, `BeDballe` | I | 15 | [review](integration/observed/test_observations_download.py.review.md) |
| `test_observations_edge_cases.py` | Limiti di intervallo, `interval`/`timerange`, casi limite | `MapsObservations` | I | 9 | [review](integration/observed/test_observations_edge_cases.py.review.md) |
| `test_observations_filters.py` | Filtri reftime, network, bounding box, product sui tre backend (28 istanze) | `MapsObservations`, `BeDballe` | I | 10 | [review](integration/observed/test_observations_filters.py.review.md) |
| `test_observations_station_details.py` | `onlyStations`, `stationDetails`, coordinate, network non valido (12 istanze) | `MapsObservations`, `parse_obs_maps_response` | I | 4 | [review](integration/observed/test_observations_station_details.py.review.md) |

### `integration/opendata/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `support.py` | Dataset, utenti, richieste e file opendata sintetici | — | — | — | [review](integration/opendata/support.py.review.md) |
| `test_authorization.py` | Package opendata di dataset privati: accesso negato o consentito | `OpendataFileList`, `OpendataDownload` | I | 2 | [review](integration/opendata/test_authorization.py.review.md) |
| `test_download.py` | Download, validazione `reftime`/`run`, zip multipli, file singolo e mancante | `OpendataDownload`, `OpendataDownloadFile` | I | 12 | [review](integration/opendata/test_download.py.review.md) |
| `test_listing_filters.py` | Listing dei package con filtri `run` e `reftime` | `OpendataFileList` | I | 4 | [review](integration/opendata/test_listing_filters.py.review.md) |

### `integration/postprocessing/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Ambienti forecast e observed | — | — | — | [review](integration/postprocessing/conftest.py.review.md) |
| `support.py` | Ambienti, builder dei postprocessor, template, assert su GRIB/JSON/BUFR | — | — | — | [review](integration/postprocessing/support.py.review.md) |
| `test_error_handling.py` | Postprocessor sconosciuti o input incompleti | `data_extract` | T | 5 | [review](integration/postprocessing/test_error_handling.py.review.md) |
| `test_forecast_basic.py` | Estrazione forecast, derived variables, statistic elaboration | `data_extract`, `pp_derived_variables`, `pp_statistic_elaboration` | T | 3 | [review](integration/postprocessing/test_forecast_basic.py.review.md) |
| `test_forecast_chaining.py` | Catena di più postprocessor forecast | `data_extract`, `tools/*` | T | 2 | [review](integration/postprocessing/test_forecast_chaining.py.review.md) |
| `test_forecast_spatial.py` | Interpolazione, cropping, template, BUFR per spare point | `pp_grid_interpolation`, `pp_grid_cropping`, `pp_sp_interpolation` | T | 4 | [review](integration/postprocessing/test_forecast_spatial.py.review.md) |
| `test_observed_postprocessing.py` | Estrazione observed e catena con output JSON | `data_extract`, `pp_quality_check_filter`, `pp_output_formatting` | T | 4 | [review](integration/postprocessing/test_observed_postprocessing.py.review.md) |

### `integration/requests/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Utente e richieste pending | — | — | — | [review](integration/requests/conftest.py.review.md) |
| `support.py` | Seed locali di richieste | — | — | — | [review](integration/requests/support.py.review.md) |
| `test_delete_pending_request.py` | Cancellazione manuale con grace period e task `automatic_cleanup` | `UserRequests`, `automatic_cleanup` | I/T | 3 | [review](integration/requests/test_delete_pending_request.py.review.md) |
| `test_requests_listing_archive_clone.py` | Listing, archiviazione e clonazione delle richieste | `UserRequests`, `CloneUserRequests` | I | 10 | [review](integration/requests/test_requests_listing_archive_clone.py.review.md) |

### `integration/schedules/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `conftest.py` | Utenti e base condivisi per i test schedule | — | — | — | [review](integration/schedules/conftest.py.review.md) |
| `test_schedule_api_contracts.py` | Contratti di lettura: listing, conteggio, dettaglio | `Schedules`, `SingleSchedule` | I | 4 | [review](integration/schedules/test_schedule_api_contracts.py.review.md) |
| `test_schedule_on_data_ready_real_worker.py` | Primo `data_extract` di una schedule on-data-ready su worker reale, nessuna voce RedBeat residua | `Schedules`, `data_extract` | E2E | 1 | [review](integration/schedules/test_schedule_on_data_ready_real_worker.py.review.md) |
| `test_schedule_opendata_bridge.py` | Schedule → richiesta → package opendata scaricabile; voce RedBeat creata e rimossa | `Schedules`, `DataReady`, `OpendataDownloadFile` | I/T + E2E | 2 | [review](integration/schedules/test_schedule_opendata_bridge.py.review.md) |
| `test_schedule_validation.py` | Validazione di `POST /schedules` | `Schedules` | I | 8 | [review](integration/schedules/test_schedule_validation.py.review.md) |
| `test_scheduled_requests.py` | `GET /schedules/<id>/requests` e cambio di stato della schedule | `ScheduledRequests`, `SingleSchedule` | I | 8 | [review](integration/schedules/test_scheduled_requests.py.review.md) |

### `integration/tasks/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `support.py` | Fake SMTP/RabbitMQ/Celery e seed DB (utente, request, schedule, fileoutput) | — | — | — | [review](integration/tasks/support.py.review.md) |
| `test_data_extraction_helpers.py` | Helper puri del task di estrazione | `human_size`, `adapt_reftime`, `package_data_license` | U | 5 | [review](integration/tasks/test_data_extraction_helpers.py.review.md) |
| `test_data_extraction_quota_and_notifications.py` | Quota utente e notifiche email/AMQP | `check_user_quota`, `notify_by_email`, `notify_by_amqp_queue` | T | 8 | [review](integration/tasks/test_data_extraction_quota_and_notifications.py.review.md) |
| `test_on_data_ready_task_edges.py` | Rami che saltano una schedule nel task on-data-ready | `launch_all_on_data_ready_extractions` | T | 4 | [review](integration/tasks/test_on_data_ready_task_edges.py.review.md) |
| `test_queue_sorting.py` | Scelta della coda Celery operational/archived | `queue_sorting` | U | 3 | [review](integration/tasks/test_queue_sorting.py.review.md) |
| `test_requests_cleanup_expiration.py` | Scadenza e cancellazione nel task di cleanup | `automatic_cleanup` | T | 3 | [review](integration/tasks/test_requests_cleanup_expiration.py.review.md) |

### `integration/templates/`, `integration/user_limits/`

| File | Scopo | Backend principale | Liv. | Test | Review |
|---|---|---|---|---:|---|
| `templates/support.py` | URL, utenti con quota, file template e zip shapefile sintetici | — | — | — | [review](integration/templates/support.py.review.md) |
| `templates/test_templates_listing.py` | `GET /templates`: autenticazione e forma `grib`/`shp` | `Templates` | I | 5 | [review](integration/templates/test_templates_listing.py.review.md) |
| `templates/test_templates_upload_delete.py` | Upload grib e shapefile, estensione non ammessa, dettaglio e delete | `Templates`, `Template` | I | 10 | [review](integration/templates/test_templates_upload_delete.py.review.md) |
| `user_limits/test_usage_and_hourly.py` | `GET /usage` (quota disco) e `GET /hourly` (richieste residue) | `Usage`, `HourlyReport` | I | 6 | [review](integration/user_limits/test_usage_and_hourly.py.review.md) |

## 4. Mappa backend -> test

Sorgenti relativi a `projects/mistral/backend/`; i test sono indicati con il nome del modulo
(univoco nella suite).

| Funzionalità / simbolo | Sorgente | Test che lo esercitano | Fixture / helper da aprire |
|---|---|---|---|
| `AccessKeyResource` (`/access-key`) | `endpoints/access_key.py` | `test_access_key_api`; `DELETE` solo nel teardown | `access_key_owner`, `fresh_access_key`, `fresh_access_key_with_expiration` |
| `AccessKeyValidationResource` | `endpoints/access_key.py` | `test_access_key_validation` | `fresh_access_key`, `make_basic_auth` |
| `is_access_key_valid`, `validate_access_key_from_request`, modello `AccessKey` | `services/access_key_service.py`, `models/sqlalchemy.py` | `test_access_key_service`; indiretti: access key, `test_arco_proxy`, `test_arco_edge_cases` | — |
| `AdminAttributions`, `AdminDatasets`, `AdminLicGroups`, `AdminLicenses` | `endpoints/admin_*.py` | `test_admin_attributions`, `test_admin_datasets`, `test_admin_license_groups`, `test_admin_licenses` | `admin_headers` (admin), `integration/admin/support.py` |
| `ArcoResource`, `ArcoDatasetsResource`, `guess_mime_type`, `_round_coord` | `endpoints/arco.py` | `test_arco_catalog`, `test_arco_proxy`, `test_arco_edge_cases` | `access_key_owner`, `fresh_access_key`, fake S3/DB inline |
| `S3Ext` | `connectors/s3/__init__.py` | `test_s3_connector` | monkeypatch di `boto3` |
| `Customizer` (`custom_user_properties_pre/post`, `manipulate_profile`) | `customization.py` | `test_user_customizer` | — |
| `Data` (`POST /data`) | `endpoints/data.py` | `test_data_endpoint_auth`, `test_data_endpoint_submission`, `test_data_endpoint_validation`, `test_data_extraction_real_worker` | `integration/data/support.py` (`RecordingCelery`, `patch_data_endpoint_runtime`), `fetch_dataset_window` |
| `validate_filters` | `services/filter_validation.py` | solo indiretto (`POST /data` e `POST /schedules` con filtri) | — |
| `FileDownload` (`/data/<filename>`) | `endpoints/file.py` | `test_file_download`, `test_data_extraction_real_worker` | `cleanup_registry` |
| `DataReady` + `launch_all_on_data_ready_extractions` | `endpoints/data_ready.py`, `tasks/on_data_ready_extractions.py` | `test_base_cases`, `test_crontab`, `test_periodic`, `test_run_mismatch`, `test_on_data_ready_task_edges`, `test_schedule_opendata_bridge`, `test_schedule_on_data_ready_real_worker` | `helpers/data_ready.py`, `helpers/celery_fakes.py`, `helpers/task_perimeter.py`, `helpers/schedules.py` |
| `Datasets`, `SingleDataset`, `check_dataset_authorization`, `get_datasets` | `endpoints/datasets.py`, `services/sqlapi_db_manager.py` | `test_dataset_authorization`, `test_dataset_visibility`; indiretti in `fields`, `observed`, `opendata` | `create_test_dataset`, `create_private_test_network`, `create_dataset_test_user` |
| `Fields` (`/fields`) | `endpoints/fields.py` | `test_fields_api`; letto come probe da `fetch_dataset_window` | `integration/fields/support.py`, `helpers/observed_windows.py`, `auth_headers`, `test_runtime` |
| `MapsObservations` (`/observations` GET e POST) | `endpoints/maps_observed.py` | i 5 moduli `test_observations_*` | `dballe_observed_case`, `arkimet_observed_case`, `mixed_observed_case`, `integration/observed/support.py`, `dballe_window_override` |
| `BeDballe` (parser, query, `parse_obs_maps_response`) | `services/dballe.py` | `test_dballe_query_parsing`; indiretti: `test_observations_*`, `test_fields_api`, `test_observed_postprocessing` | `require_dballe_product`, `dballe_window_override` |
| `BeArkimet` (parser e query) | `services/arkimet.py` | `test_arkimet_query_parsing`; indiretti: `test_fields_api`, `data`, forecast di `postprocessing` | `fetch_dataset_window`, `require_dataset` |
| `OpendataFileList`, `OpendataDownload`, `OpendataDownloadFile` | `endpoints/opendata.py` | `test_authorization`, `test_download`, `test_listing_filters`, `test_schedule_opendata_bridge` | `integration/opendata/support.py`, `cleanup_registry` |
| `UserRequests`, `CloneUserRequests` | `endpoints/requests.py` | `test_requests_listing_archive_clone`, `test_delete_pending_request` | `pending_request_user`, `pending_delete_requests`, `requests_user` |
| `automatic_cleanup` | `tasks/requests_cleanup.py` | `test_delete_pending_request`, `test_requests_cleanup_expiration`, `test_data_extraction_real_worker` | `requests_cleanup_perimeter`, `integration/tasks/support.py` |
| `Schedules`, `SingleSchedule` | `endpoints/schedules.py` | `test_schedule_api_contracts`, `test_schedule_validation`, `test_schedule_opendata_bridge`; creazione anche in `data_ready` | `helpers/schedules.py`, `forbid_real_schedule_dispatch`, `schedules_endpoint_without_real_celery` |
| `ScheduledRequests` | `endpoints/schedules.py` | `test_scheduled_requests` | `MagicMock` di RedBeat nel modulo |
| `data_extract` (task) | `tasks/data_extraction.py` | moduli `postprocessing`, `test_data_extraction_quota_and_notifications`, `test_data_extraction_real_worker`, `test_schedule_on_data_ready_real_worker` | `pp_forecast_env`, `pp_observed_env`, fake di `integration/tasks/support.py` |
| `human_size`, `adapt_reftime`, `package_data_license`, `check_user_quota`, `notify_by_email`, `notify_by_amqp_queue` | `tasks/data_extraction.py` | `test_data_extraction_helpers`, `test_data_extraction_quota_and_notifications` | fake SMTP/AMQP/`du` di `integration/tasks/support.py` |
| `queue_sorting` | `tasks/data_extraction_utilities.py` | `test_queue_sorting`, `test_data_endpoint_submission` | — |
| Postprocessor `pp_*` | `tools/*.py` | moduli `postprocessing` | `pp_forecast_env`, `pp_observed_env`, `integration/postprocessing/support.py` |
| `get_trans_type`, `check_template_filepath`, `check_coord_filepath`, `format_sub_type` | `tools/grid_interpolation.py`, `tools/spare_point_interpol.py`, `tools/grid_cropping.py` | `test_tool_helpers` | — |
| `Templates`, `Template` | `endpoints/templates.py` | `test_templates_listing`, `test_templates_upload_delete`; template usati in `test_forecast_spatial` | `integration/templates/support.py` |
| `Usage`, `HourlyReport` (`/usage`, `/hourly`) | `endpoints/usage.py`, `endpoints/request_hourly_report.py` | `test_usage_and_hourly` | `create_authenticated_test_user` |
| `Initializer` | `initialization.py` | `test_initializer_seed`, `test_initializer_smoke` | `initializer_harness` |
| `SqlApiDbManager` (fileoutput, richieste, schedule) | `services/sqlapi_db_manager.py` | solo indiretto (`requests`, `schedules`, `data_ready`, `dataset`, `tasks`) | — |
| `OutputBindings` (`/outbindings`) | `endpoints/rabbit_out_bindings.py` | nessuno | — |
| `endpoints/schemas.py` | `endpoints/schemas.py` | solo indiretto via `arco` | — |

## 5. Fixture, helper e mock condivisi

Dove posizionare fixture e helper, la semantica del cleanup e il significato dei fake sono spiegati
nel [README](README.md). Qui restano solo dove sono definiti, chi li usa e le avvertenze.

### Fixture globali

| Fixture | Definita in | Usata da | Avvertenze |
|---|---|---|---|
| `test_runtime` | `projects/mistral/backend/tests/conftest.py` | `data`, `data_ready`, `fields`, `observed`, `postprocessing`, `schedules` | Scope di sessione, cache mai svuotata; `dataset_id` cerca per nome **o** `arkimet_id` e solleva `LookupError`; il lock non vale tra processi. |
| `cleanup_registry` | `projects/mistral/backend/tests/conftest.py` | quasi tutti i domini | La lista si svuota solo a fine esecuzione completa (una seconda esecuzione non fa nulla); non registrare radici condivise. |
| `auth_headers` | `projects/mistral/backend/tests/integration/conftest.py` | `fields`, `observed` | Login reale dell'account predefinito. |
| `access_key_owner` | `projects/mistral/backend/tests/integration/conftest.py` | `access_key`, `arco` | Il revoke via `DELETE` accetta 204 o 404 perché l'utente può essere già stato cancellato. |
| `fresh_access_key` | `projects/mistral/backend/tests/integration/conftest.py` | `access_key`, `arco` | Richiede 200 e campo `key`; per Basic auth usare l'email del proprietario. |
| `requests_cleanup_perimeter` | `projects/mistral/backend/tests/integration/conftest.py` | `requests`, `tasks` | All'inizio non ammette alcun id. |

`integration/conftest.py` importa costanti da `integration/access_key/support.py` (dipendenza dal
basso verso l'alto da tenere presente se si sposta quel modulo).

### Helper globali (`projects/mistral/backend/tests/helpers/`)

| Helper | Usato da | Avvertenze |
|---|---|---|
| `auth.py` (`create_authenticated_test_user`, `create_dataset_test_user`, `register_test_user_cleanup`, `delete_test_user`, `make_basic_auth`) | quasi tutti i domini | `create_authenticated_test_user` non registra il cleanup; `delete_test_user` esige 204; `register_test_user_cleanup` cancella l'utente prima della sua cartella; `make_basic_auth` non valida i valori. |
| `celery_fakes.py` | `data_ready` (via `helpers/data_ready.py`), `schedules` | `delete_periodic_task` restituisce sempre `True` senza RedBeat; accoppiato ai 12 argomenti posizionali di `data_extract`; il fake inline del data-ready reimplementa la deduplica. |
| `cleanup.py` | `conftest.py` root, `data`, `opendata` | Vedi `cleanup_registry`. |
| `data_ready.py` | `data`, `data_ready`, `schedules`, `helpers/real_workers.py` | `create_data_ready_user` crea utenti `admin_root`; `create_schedule` esige 202 e può accodare la prima estrazione; `wait_for_schedule_requests` attende il conteggio **esatto** (60 s / 5 s); `trigger_data_ready_and_wait_accepted` ripete il POST; i `delete_all_user_*` vanno usati solo su utenti dedicati. |
| `datasets.py` (`create_test_dataset`, `delete_test_dataset_bundle`, `create_private_test_network`, `require_dataset`) | `dataset`, `fields`, `observed`, `opendata`, `postprocessing`, `helpers/observed_windows.py` | Crea solo righe di catalogo, senza dati Arkimet/DB-All.e; il rollback del teardown può scartare altre modifiche pendenti della sessione; `require_dataset` salta il test. |
| `dataset_window.py` (`fetch_dataset_window`) | `data`, `data_ready`, `schedules` | 404 da `/fields` → skip, altri status ≠ 200 → fallimento. |
| `observed_windows.py` (`dballe_window_override`, `require_observed_dataset_user`, `require_dballe_product`) | `fields`, `observed` | L'override è relativo a "adesso"; i probe saltano il test se mancano dataset agrmet o prodotti DB-All.e. |
| `polling.py` (`wait_until`) | `data`, `schedules`, `helpers/data_ready.py`, `helpers/real_workers.py` | Default 60 s / 2 s; un valore falso non è mai un successo; non intercetta le eccezioni del predicato. |
| `real_workers.py` | `conftest.py` root, `data`, `schedules` | Il controllo del mock SMTP è indiretto (legge solo segnali del backend); `register_wait_for_user_requests` va registrato dopo il cleanup dell'utente. |
| `runtime.py` (`TestRuntime`) | `conftest.py` root, `helpers/data_ready.py`, `observed` | Vedi `test_runtime`. |
| `schedules.py` | `data_ready`, `schedules` | Restituisce stringhe JSON; tutti e tre i builder hanno `opendata=True` di default. |
| `task_perimeter.py` | `integration/conftest.py`, `helpers/data_ready.py`, `requests`, `schedules`, `tasks` | Insieme di id vuoto → nessuna riga toccata; non rimuovere la facciata per far passare un test. |
| `templates/endpoint_template.py` | nessuno (modello) | Non raccolto; corpi `pass`. |

### Fake e mock locali

| Fake / mock | Definito in | Usato da | Avvertenze |
|---|---|---|---|
| `RecordingCelery`, `FakeRabbit`, `patch_data_endpoint_runtime` | `projects/mistral/backend/tests/integration/data/support.py` | `test_data_endpoint_*` | Non autouse: ogni test deve applicarli esplicitamente. |
| Fake SMTP, AMQP, `du`; `seed_fileoutput` | `projects/mistral/backend/tests/integration/tasks/support.py` | moduli `tasks` | Le notifiche sono verificate solo sul fake. |
| `schedules_endpoint_without_real_celery` (autouse) | `projects/mistral/backend/tests/integration/data_ready/conftest.py` | modulo endpoint `/schedules` di `data_ready` | Sostituisce Celery e la creazione RedBeat. |
| `forbid_real_schedule_dispatch` | `projects/mistral/backend/tests/integration/schedules/test_schedule_validation.py` | stesso modulo | Fa fallire il test se `POST /schedules` supera la validazione e arriverebbe a Celery/RedBeat. |
| `MagicMock` RedBeat | `projects/mistral/backend/tests/integration/schedules/test_scheduled_requests.py` | stesso modulo | Il 409 sul cambio di stato dipende dal mock. |
| Fake S3 e DB inline (`_Fake*`) | `projects/mistral/backend/tests/integration/arco/test_arco_edge_cases.py` | stesso modulo | — |
| Patch del nome `datetime` nel modulo endpoint | `projects/mistral/backend/tests/integration/user_limits/test_usage_and_hourly.py` | stesso modulo | Vale solo per il modulo patchato. |

### Fixture locali da conoscere

| Fixture | Definita in | Note |
|---|---|---|
| `fresh_access_key_with_expiration` | `integration/access_key/conftest.py` | Chiave con scadenza esplicita. |
| `admin_headers` | `integration/admin/conftest.py` | Header dell'admin di default. |
| `data_ready_admin_headers`, `schedules_admin_headers` | `integration/data_ready/conftest.py`, `integration/schedules/conftest.py` | Header admin dei rispettivi domini. |
| `data_ready_base`, `data_ready_db`, `data_ready_user` | `integration/data_ready/conftest.py` | Utenti `admin_root`; `lm5` assente → skip. |
| `schedules_base`, `schedules_user` | `integration/schedules/conftest.py` | `schedules_user` è ridefinita con privilegi diversi in `test_schedule_api_contracts`, `test_schedule_validation`, `test_scheduled_requests`. |
| `dballe_observed_case`, `arkimet_observed_case`, `mixed_observed_case` | `integration/observed/conftest.py` | Richiamate con `getfixturevalue`. |
| `pp_forecast_env`, `pp_observed_env` | `integration/postprocessing/conftest.py` | Ambienti di estrazione con postprocessor. |
| `pending_request_user`, `pending_delete_requests` | `integration/requests/conftest.py` | — |
| `requests_user`, `real_worker_user`, `initializer_harness` | nei rispettivi moduli di test | Fixture definite nel modulo stesso. |

## 6. Copertura

### Componenti più testati

| Componente | Perché |
|---|---|
| `endpoints/maps_observed.py` + `services/dballe.py` | 40 test observed sui tre backend, più parser DB-All.e e uso indiretto in `fields` e `postprocessing`. |
| `tasks/data_extraction.py` e `tools/*` | 18 test di postprocessing, 13 di helper/quota/notifiche, 3 `async_real`. |
| `endpoints/schedules.py` | 23 test `schedules` più la creazione nei test `data_ready`. |
| `endpoints/fields.py` | 21 test sulle tre modalità, più l'uso come probe. |
| `endpoints/data.py` | 13 test sull'endpoint più i test `async_real`. |
| `endpoints/opendata.py` | 18 test con dati sintetici, più il ponte dalle schedule. |
| Access key | Endpoint, validazione, service e uso in `arco`. |

### Componenti scoperti o poco testati

| Componente | Sorgente | Lacuna |
|---|---|---|
| `OutputBindings` (`/outbindings`) | `projects/mistral/backend/endpoints/rabbit_out_bindings.py` | Nessun test. |
| `validate_filters` | `projects/mistral/backend/services/filter_validation.py` | Nessun test dedicato; rami negativi scoperti. |
| `endpoints/schemas.py` | `projects/mistral/backend/endpoints/schemas.py` | Solo indiretto via `arco`. |
| Connector S3 | `projects/mistral/backend/connectors/s3/__init__.py` | Solo con fake; `get_connection_exception`, `Config` e default di `verify_ssl` non verificati. |
| `Customizer` | `projects/mistral/backend/customization.py` | Persistenza del post hook e `get_custom_input_fields` dinamico scoperti. |
| `DELETE /access-key` | `projects/mistral/backend/endpoints/access_key.py` | Solo nel teardown (accetta 204/404). |
| `data_extract` | `projects/mistral/backend/tasks/data_extraction.py` | Email con tutti i tentativi falliti, `DeleteScheduleException`, `error_message` AMQP. |
| `UserRequests` | `projects/mistral/backend/endpoints/requests.py` | Paginazione, ordinamento, `input_filter`; cancellazione con fileoutput. |
| `FileDownload` | `projects/mistral/backend/endpoints/file.py` | 404 per record DB mancante e ramo opendata. |
| Opendata | `projects/mistral/backend/endpoints/opendata.py` | `archived=True` e rami `ServerError`. |
| `ScheduledRequests` | `projects/mistral/backend/endpoints/schedules.py` | Patch/delete di schedule crontab e on-data-ready. |
| Data-ready | `projects/mistral/backend/endpoints/data_ready.py` | Creazione RedBeat non esercitata (fake). |
| `adapt_reftime` | `projects/mistral/backend/tasks/data_extraction.py` | Rami di correzione. |
| Tool spaziali | `projects/mistral/backend/tools/` | `sub_type` sconosciuto. |
| `HourlyReport` | `projects/mistral/backend/endpoints/request_hourly_report.py` | `request_par_hour=0`. |
| `Initializer` | `projects/mistral/backend/initialization.py` | Ramo con cron assente (smoke). |

## 7. Rischi per il revisore

### Skip silenziosi

Un esito verde può nascondere test non eseguiti: controlla sempre il numero di skip rispetto alla §1.

| Origine dello skip | Dove |
|---|---|
| `async_real` senza segnali di mock SMTP (`NO_SMTP_MOCK_REASON`) | `projects/mistral/backend/tests/conftest.py`, `helpers/real_workers.py` |
| Dataset reale assente (`require_dataset`) | `projects/mistral/backend/tests/helpers/datasets.py` |
| `/fields` risponde 404 (`fetch_dataset_window`) | `projects/mistral/backend/tests/helpers/dataset_window.py` |
| Dataset agrmet o prodotto DB-All.e assente | `projects/mistral/backend/tests/helpers/observed_windows.py` |
| Scoperta di parametri observed fallita | `projects/mistral/backend/tests/integration/observed/support.py`, `test_observations_edge_cases.py` |
| Caso forecast non disponibile (`require_forecast_fields_case`) | `projects/mistral/backend/tests/integration/fields/support.py` |
| Variabili o dati DB-All.e assenti, archivio spare point mancante | `projects/mistral/backend/tests/integration/postprocessing/support.py` |
| Dataset `lm5` assente (`LookupError`) | `integration/data_ready/conftest.py`, `integration/schedules/conftest.py`, `integration/data/test_data_extraction_real_worker.py` |
| Bug backend noti | vedi §1 (5 skip) |

### Logica verificata nel fake

- `test_periodic` e gli altri test `data_ready`: la decisione del launcher è reale, ma la creazione
  delle richieste e la deduplica passano dal fake inline di `helpers/celery_fakes.py`; `data_extract`
  è solo materializzato.
- `test_scheduled_requests`: il 409 sul cambio di stato nasce dal `MagicMock` di RedBeat.
- `test_initializer_smoke`: le asserzioni guardano i fake, non il DB (il DB è coperto da `test_initializer_seed`).

### Over-mocking

- `test_data_extraction_quota_and_notifications`: SMTP, AMQP, `du` e `arki` sostituiti.
- `test_arco_edge_cases` e `test_s3_connector`: S3 e DB solo con fake.
- Moduli `postprocessing`: durante il task `mark_task_as_failed`, `mark_task_as_failed_ignore` e
  `notify_by_email` sono sostituiti (`integration/postprocessing/support.py`), quindi la gestione
  reale dei fallimenti e le email non sono esercitate.
- `test_on_data_ready_task_edges`: `send_task` è un `MagicMock`.

### Marker fuorvianti

- Test unitari puri marcati `integration`: `services/*`, `test_data_extraction_helpers`,
  `test_queue_sorting`, `test_tool_helpers`, `test_s3_connector`, gli helper puri di `test_arco_edge_cases`.
- `deterministic` + `runtime_sensitive` insieme su 18 moduli che dipendono dai dati presenti.
- `test_observations_auth` è `runtime_sensitive` pur verificando solo errori di validazione.

### Stato condiviso

- `auth_headers` usa l'utente di default, i cui permessi (es. `allowed_obs_archive`) dipendono dai default di `Customizer`.
- Il dominio `admin` opera con l'admin di default.
- `BeDballe.LASTDAYS` è un attributo di classe: gli override devono essere sempre ripristinati.
- La cache di `TestRuntime` vive per tutta la sessione.
- `data_ready` sovrascrive i dataset abilitati al data-ready; `data_ready` e `schedules` creano utenti `admin_root`.

### Bug backend ancora aperti

| Codice | Sorgente | Problema | Effetto sui test |
|---|---|---|---|
| — | `projects/mistral/backend/endpoints/fields.py` | `resulting_fields` non definita nel ramo forecast con `SummaryStats=false` | skip |
| EDGE-001 | `projects/mistral/backend/endpoints/maps_observed.py` | `NotFound("Station data not found")` irraggiungibile | skip |
| TEMPLATES-001 | `projects/mistral/backend/endpoints/templates.py` | Controllo di esistenza invertito in `Template.get` | 2 skip |
| TEMPLATES-002 | `projects/mistral/backend/endpoints/templates.py` | Messaggio dell'estensione non ammessa mascherato da `FileNotFoundError` | skip |
| ARCO-001 | `projects/mistral/backend/endpoints/arco.py` | `ClientError` S3 generico esposto come 400 invece di 500 | xfail strict |
| — | `projects/mistral/backend/initialization.py` | Confronto enum/stringa su `category`: dataset riscritto a ogni avvio | xfail strict |
| ADMIN-001 | `projects/mistral/backend/endpoints/admin_licenses.py`, `admin_datasets.py` | `.first` senza `()`: il `NotFound` è irraggiungibile | il test verifica il 400 di validazione, nessuno skip |
| — | `projects/mistral/backend/tasks/data_extraction.py` | `notify_by_email`: `if i < MAX_RETRIES` sempre vero, nessun errore finale dopo l'ultimo tentativo | ramo non testato |
| — | `projects/mistral/backend/services/access_key_service.py`, `models/sqlalchemy.py` | Scadenza della chiave: il service usa datetime aware e `<`, il modello naive e `>` (esito diverso a scadenza esatta) | non testato al limite |
| — | `projects/mistral/backend/endpoints/admin_datasets.py`, `admin_licenses.py`, `templates.py` | Documentazione OpenAPI diversa dall'implementazione: PUT e DELETE di dataset e license admin dichiarano 200 ma rispondono 204, l'upload template dichiara 202 ma risponde 200, refuso `succesfully` nel messaggio di delete | i test asseriscono il comportamento reale |

Problema risolto: SCHEDULES-001 (`schedules_user` di `test_schedule_validation` ora ha `Role.USER`).
