# Blueprint Estensione Copertura Backend

Data analisi iniziale: 2026-05-22.
Revisione vincoli operativi: 2026-05-28.

## Sintesi iniziale

1. La suite rifattorizzata e valida e copre i contratti legacy principali sotto `tests/integration/`.
2. Le aree gia forti sono access key, dataset visibility, observed GET, opendata listing/download, data-ready gating, request cleanup base, postprocessing e schedule/opendata bridge.
3. Il buco piu critico resta il contratto HTTP di `POST /data`: oggi e coperto quasi solo per autenticazione e indirettamente tramite task/postprocessing.
4. `tools` non e un'area scoperta: i postprocessor principali sono coperti da `integration/postprocessing`, ma helper e rami di errore restano scoperti.
5. I gap ad alto valore restano `fields`, observed download POST, schedule CRUD completo, request list/archive/clone, template upload/download/delete e admin CRUD.
6. I task hanno copertura parziale: `automatic_cleanup` e data-ready sono coperti solo in alcuni rami; quota, notification, AMQP e helper puri restano scoperti.
7. I service `arkimet`, `dballe` e `SqlApiDbManager` hanno molte funzioni pure testabili senza runtime pesante.
8. Le superfici extra emerse restano customizer, initializer, models, connector S3, migrations, schemas, file/usage/hourly e admin endpoints.
9. La strategia consigliata resta narrow-first: aggiungere solo artefatti nella suite sotto `integration/`, senza test root e senza fixture globali nuove salvo riuso reale documentato.
10. Le prime fasi devono massimizzare valore/rischio con test deterministici e import/unit-level, poi allargare ai test runtime-sensitive solo dove il contratto non e simulabile in modo credibile.
11. I test runtime-sensitive devono sfruttare prima i dati reali gia presenti nel runtime, cioe a costo zero, ma solo dentro finestre temporali esplicite: `lm2.2` solo `2019-09-10`, `lm5` solo `2021-10-19`, `agrmet` Arkimet solo `2020-03-31` e `2020-04-01`, `agrmet` DBALLE solo `2020-04-06` con default `00:00` e soli 4 dati alle `01:00` e `02:00`.
12. La tracciabilita dell'estensione resta tassativa: ogni nuovo artefatto eseguibile o artefatto di test toccato dall'estensione deve usare il suffisso `_EXT` nel nome del file e nei simboli nuovi o rinominati introdotti dal lavoro, salvo il nome speciale `conftest.py` che segue una regola dedicata.
13. `conftest.py` puo essere creato o modificato quando serve davvero per ridurre duplicazioni o chiarire il perimetro fixture, ma ogni cartella toccata da questa scelta deve contenere o aggiornare un file locale `README_conftest_EXT.md` che documenti il motivo della scelta, le fixture esposte, il loro scope, il cleanup e i test che le usano.
14. Tutti i nuovi artefatti `_EXT` devono essere accompagnati da commenti molto verbosi che spieghino provenienza, scenario coperto, motivo del fake/mock o del dato reale, finestra dati usata, strategia di cleanup e perche la baseline legacy non e stata alterata oltre il necessario.
15. Il piano deve anche fare analisi critica dei limiti: se le finestre temporali disponibili non bastano per testare correttamente una funzionalita in modo runtime-realistic, la mancanza va segnalata esplicitamente insieme ai dati aggiuntivi che sarebbero utili in futuro, senza bloccare l'estensione della copertura oggi possibile.
16. I test su `lm5` e `lm2.2` devono essere portabili tra locale e CI: in locale possono esistere restrizioni autorizzative che in CI non esistono, quindi fixture e helper devono essere agnostici rispetto a questa differenza e non devono usare il setup locale come oracolo comportamentale fisso.
17. I prompt implementativi aggiornati in `coverage_extension_prompts/` devono trattare `untracked_stuff` come inesistente e non possono modificare alcun codice fuori da `projects/mistral/backend/tests`.
18. La policy dell'estensione non ammette `xfail`: ogni bug o comportamento anomalo che impedisce un assert verde deve essere gestito con `skip` esplicito, fortemente documentato e accompagnato da una spiegazione del criterio per riattivare il test.
19. Ogni bug scoperto o skip forzato introdotto dall'estensione deve essere censito o aggiornato in `projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.

## Fonti e assunzioni

Fonti autoritative lette in ordine:

- `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
- `projects/mistral/backend/tests/README.md`
- `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`
- `projects/mistral/backend/tests/helpers/templates/endpoint_template.py`

Assunzioni operative:

- Il path `projects/mistral/backend/tests/docs/rischi_residui_suite_test.md` non esiste nella suite corrente; i rischi runtime sono quindi ricavati dalla documentazione mantenuta e dai marker `runtime_sensitive` / `async_real`.
- I comandi di validazione devono usare il path container `tests/custom/...`.
- La suite non deve reintrodurre file `test_*.py` nel root di `projects/mistral/backend/tests`.
- I test unitari puri proposti restano dentro domini `tests/integration/<area>/` con marker `deterministic`, per conservare il layout esistente.
- Il piano puo aggiungere o rinominare file solo dentro `projects/mistral/backend/tests`; il backend applicativo fuori da quel perimetro resta strettamente read-only.
- Il path `/home/federico/mistral/meteo-hub/untracked_stuff` e off-limits e va trattato come se non esistesse: niente letture, niente ricerche, niente riferimenti, niente copia di codice o idee operative.
- La restrizione autorizzativa su `lm5` e `lm2.2` e specifica del setup locale dell'utente; la CI di produzione inizializza il database senza questa restrizione. I test devono quindi essere progettati per passare in entrambi i contesti.

## Vincoli tassativi dell'estensione

- Perimetro assoluto: l'estensione puo modificare solo file sotto `projects/mistral/backend/tests`; ogni richiesta di fix al backend applicativo va solo documentata come rischio o blocco, non implementata.
- Convenzione di naming `_EXT`: si applica a ogni nuovo artefatto eseguibile della suite aggiunto dal piano, inclusi moduli test, helper, utility, fixture module e simboli nuovi o rinominati introdotti nei file `_EXT`, con eccezione del nome riservato `conftest.py`.
- Eccezione documentale: questo blueprint e il prompt pack mantengono i nomi richiesti dall'utente per non rompere il punto di ingresso della documentazione; la convenzione `_EXT` e invece tassativa per gli artefatti Python della suite proposti dal piano.
- Eccezione pytest per `conftest.py`: il filename resta quello standard richiesto da pytest, ma ogni cartella in cui un `conftest.py` viene creato o modificato deve contenere anche `README_conftest_EXT.md` aggiornato e molto verboso.
- Strategia per `conftest.py`: e consentito creare nuovi `conftest.py` o modificarne di esistenti quando il vantaggio e chiaro, cioe riuso reale di fixture, riduzione di duplicazione o miglior separazione del dominio; la scelta non e mai implicita e va sempre spiegata nel relativo `README_conftest_EXT.md`.
- Strategia sui file legacy: la suite rifattorizzata gia esistente resta baseline e non va ridenominata in massa; quando serve estendere un dominio, si preferiscono moduli fratelli `*_EXT.py` invece di toccare i file legacy. Se una modifica a un file legacy diventasse inevitabile, quella modifica richiede rinomina del modulo a `_EXT` e aggiornamento dei riferimenti solo dentro il perimetro `projects/mistral/backend/tests`.
- Commenti obbligatori: ogni file `_EXT.py` deve aprirsi con un blocco commenti molto esplicito che spieghi perche il file esiste, quale parte della baseline estende, quali rami copre, quali dataset reali usa o evita, quali fake/mock usa e quale cleanup garantisce. Ogni test o helper nuovo deve avere commenti introduttivi dedicati.
- Skip runtime obbligatori: se il runtime non espone le finestre dati documentate sotto, il test deve usare skip esplicito e descrittivo, non fallback impliciti e non date inventate.
- Policy no xfail: l'estensione non usa `pytest.xfail`; se il comportamento sotto test rivela un bug backend o un'anomalia non correggibile nel perimetro `tests`, il test deve usare solo `pytest.skip(...)` esplicito e fortemente documentato.
- Registro bug/skip obbligatorio: ogni bug scoperto o skip forzato introdotto dal lavoro deve aggiornare `projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md` con sintomo, contesto, analisi, mitigazione in suite e fix backend atteso.
- Strategia dati reali: quando i dati reali gia presenti bastano a coprire un contratto in modo affidabile, vanno usati prima di introdurre fake aggiuntivi. Quando invece non bastano, il piano deve dirlo esplicitamente e indicare quali dati aggiuntivi sarebbero utili in futuro.
- Portabilita locale/CI: i test che usano `lm5` o `lm2.2` non devono assumere che un utente sia autorizzato o non autorizzato in base al solo ambiente. Il setup dei test deve esplicitare l'autorizzazione necessaria oppure costruire assertion valide in entrambi gli ambienti.

Esempio minimo del blocco commenti richiesto in ogni file `_EXT.py`:

```python
# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal piano di estensione.
# EXTENSION SCOPE: integra la suite rifattorizzata senza modificare la baseline legacy.
# EXTENSION DATA WINDOW: nessun dataset reale / oppure dataset reale vincolato alle date documentate.
# EXTENSION RUNTIME: fake Celery/Rabbit/SMTP oppure motivazione del runtime reale inevitabile.
# EXTENSION CLEANUP: descrizione esplicita di cleanup_registry, temp dir e side effect ripuliti.
```

## Finestre dataset reali da rispettare

| Dataset/runtime surface | Finestra consentita | Note operative tassative |
| ----------------------- | ------------------- | ------------------------ |
| `lm2.2`                 | solo `2019-09-10`   | Non usare altre date nei test runtime-sensitive; ogni skip deve citare questa data. |
| `lm5`                   | solo `2021-10-19`   | Valida per schedule/data-ready/forecast quando non basta il fake. |
| `agrmet` in Arkimet     | solo `2020-03-31` e `2020-04-01` | Usare queste date per browse/fields/cataloghi che dipendono da Arkimet reale. |
| `agrmet` in DBALLE      | solo `2020-04-06`   | Preferire `00:00`; esistono esattamente 4 dati alle `01:00` e `02:00`, da usare solo in test mirati e commentati. |

Regola di uso delle finestre:

- Se il contratto puo essere coperto con fake o monkeypatch credibile, non usare dataset reali.
- Se il contratto puo essere coperto correttamente con dati reali gia presenti nelle finestre sopra, preferire quei dati a costo zero prima di introdurre fake superflui.
- Se il contratto richiede dati reali, la data scelta deve essere esplicitata nel commento del test e nei nomi delle variabili locali.
- Nei prompt, i domini `observed`, `fields`, `data_ready` e `schedules` sono quelli piu esposti a questi vincoli e devono dichiararli sempre.

## Analisi critica dei limiti dei dati disponibili

La disponibilita attuale non e debilitante per la maggior parte della copertura contrattuale prevista dal piano, perche molta logica user-facing, di validazione e di side effect puo essere coperta con combinazione di dati reali esistenti, fixture DB e fake mirati. Restano pero alcuni limiti runtime da segnalare esplicitamente.

Lacune da segnalare fin da ora, con dati aggiuntivi utili in futuro:

- Forecast runtime su `lm5` e `lm2.2`: una sola giornata per dataset permette diversi happy path reali ma limita test piu forti su transizioni cross-day, confronto fra piu runhour, duplicate detection su reftime differenti e validazione realistica di routing operational vs archived. Dati utili futuri: almeno 2-3 giorni ulteriori per ciascun dataset, con piu runhour e almeno un caso recente/non-archiviato.
- Observed runtime su `agrmet`: due giorni Arkimet e un solo giorno DBALLE consentono smoke e buona parte dei contratti su query e download, ma limitano copertura multi-day per `daily`, confronto piu robusto su `last`, casi archive vs non-archive e maggiore varieta network/product/station. Dati utili futuri: ulteriori giorni consecutivi in DBALLE e Arkimet, con maggiore copertura oraria e di stazioni.
- Alcuni contratti opendata e schedule basati su storia piu lunga dei file pubblicati potrebbero beneficiare di piu finestre temporali e di piu varianti di pubblicazione per verificare label giornaliere, esclusione archived e paginazione su basi dati piu ricche. Dati utili futuri: piu giornate pubblicate per lo stesso dataset e file diretti con varianti di stato archivio.

Regola di piano per i limiti:

- Se un test runtime-realistic non puo essere coperto correttamente con i dati disponibili, la mancanza va annotata nel piano e poi riportata nel lavoro implementativo, senza inventare date o rinunciare al resto della copertura possibile.

## Stato di partenza

### Copertura già presente

- Access key: ciclo GET/POST, rigenerazione, key senza scadenza, key scaduta e validazione BasicAuth in `integration/access_key/test_access_key_api.py` e `integration/access_key/test_access_key_validation.py`.
- ARCO: proxy autenticato e catalogo dataset in `integration/arco/test_arco_proxy.py` e `integration/arco/test_arco_catalog.py`.
- Data: solo protezione autenticazione di `POST /data` in `integration/data/test_data_endpoint_auth.py`.
- Dataset: catalogo pubblico, dettaglio, dataset inesistente, dataset privati e `open_dataset=False` in `integration/dataset/test_dataset_visibility.py` e `integration/dataset/test_dataset_authorization.py`.
- Data-ready: accettazione base, dataset non abilitato, schedule inattive/non data-ready, mismatch modello/runhour, crontab e periodicità in `integration/data_ready/*`.
- Observed GET: filtri reftime, network, bbox, product, combinazioni, `onlyStations` e `stationDetails` in `integration/observed/*`.
- Opendata: autorizzazione, listing, filtri, download zip/singolo e file mancante in `integration/opendata/*`.
- Postprocessing: forecast/observed, derived variables, statistic elaboration, grid interpolation/cropping, spare point, chaining, JSON output e failure base in `integration/postprocessing/*`.
- Requests: delete manuale entro/fuori grace period e `automatic_cleanup` su pending stale in `integration/requests/test_delete_pending_request.py`.
- Schedules: bridge `schedule -> request opendata -> listing/download`, con path inline e crontab reale, in `integration/schedules/test_schedule_opendata_bridge.py`.

### Aree coperte solo per migrazione legacy

La matrice `legacy_to_new_suite_matrix.md` dimostra che i contratti storici sono migrati, ma non estende automaticamente la copertura a endpoint/service/task nuovi o rami non presenti nei monoliti. In particolare restano fuori dai legacy: `fields`, `templates`, `usage`, `hourly`, `file`, admin CRUD, `rabbit_out_bindings`, molte validazioni di `POST /data`, observed download POST, service parser puri e connector S3.

### Behavior dei tools già coperti da `integration/postprocessing`

- `derived_variables.pp_derived_variables`: coperto direttamente tramite task reale per forecast e observed, più failure per input incompleti.
- `statistic_elaboration.pp_statistic_elaboration`: coperto direttamente per forecast e observed, più failure per timerange/input incompleti.
- `grid_interpolation.pp_grid_interpolation`: coperto direttamente senza template e con template.
- `grid_cropping.pp_grid_cropping`: coperto direttamente nel caso `coord`.
- `spare_point_interpol.pp_sp_interpolation`: coperto direttamente con shapefile valido e output BUFR.
- `output_formatting.pp_output_formatting`: coperto indirettamente/di fatto dai flussi `output_format="json"` in forecast e observed.
- `quality_check_filter.pp_quality_check_filter`: coperto indirettamente dal chaining observed con `only_reliable=True`, ma senza assert sul contenuto filtrato.

### Moduli senza evidenza di copertura dedicata

`endpoints/fields.py`, `endpoints/templates.py`, `endpoints/usage.py`, `endpoints/request_hourly_report.py`, `endpoints/file.py`, `endpoints/rabbit_out_bindings.py`, `endpoints/admin_*.py`, observed POST download, gran parte di `endpoints/data.py`, parte di `endpoints/schedules.py`, helper task in `tasks/data_extraction.py`, `tasks/data_extraction_utilities.py`, funzioni pure di `services/arkimet.py` e `services/dballe.py`, `customization.py`, `initialization.py`, `connectors/s3/__init__.py`, modelli `AccessKey.generate/is_valid` e migration smoke.

## Altre superfici backend emerse dall'analisi

| Superficie              | Path                                                   | Decisione                                            | Motivazione                                                                                                                            |
| ----------------------- | ------------------------------------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Customizer utente       | `projects/mistral/backend/customization.py`          | Test dedicati                                        | Ha contratto osservabile su default utente, campi admin/profile, associazione dataset e profilo serializzato.                          |
| Modelli e model methods | `projects/mistral/backend/models/sqlalchemy.py`      | Test dedicati mirati                                 | `AccessKey.generate` e `AccessKey.is_valid` sono logica pura; `__repr__` escluso.                                                |
| Initializer             | `projects/mistral/backend/initialization.py`         | Copertura indiretta + smoke mirato                   | Seeding massivo e registrazione cron; test completo rischia fragilità, ma serve smoke idempotenza/wiring con fake DB/celery o import. |
| Connector S3            | `projects/mistral/backend/connectors/s3/__init__.py` | Test dedicati con mock                               | Contratto autonomo: parametri obbligatori, endpoint, SSL,`is_connected`, `disconnect`.                                             |
| Migration scripts       | `projects/mistral/backend/migrations/**`             | Smoke/import o collect-only                          | Sono contratti Alembic, non logica business; evitare test uno-a-uno salvo regressioni schema.                                          |
| Endpoint schemas        | `projects/mistral/backend/endpoints/schemas.py`      | Copertura indiretta sufficiente, con smoke opzionale | Serializzazione access key/dataset è già attraversata da endpoint; test diretto solo se si modifica schema.                         |
| Exceptions              | `projects/mistral/backend/exceptions.py`             | Esclusione motivata                                  | Classi marker senza comportamento autonomo.                                                                                            |
| Constants package       | `projects/mistral/backend/endpoints/__init__.py`     | Esclusione motivata                                  | Solo costanti di path e alias typing; copertura indiretta dai task/endpoints.                                                          |
| Smoke toolchain shell   | `projects/mistral/backend/tests/test_arpaesimc.sh`   | Mantenere invariato                                  | E gia il punto giusto per smoke toolchain meteo, non da duplicare in pytest.                                                           |

## Matrice copertura e gap analysis

Priorita: P0 = massimo valore/rischio, P1 = alto valore, P2 = medio, P3 = coda o smoke.

| Area           | File/modulo                            | Perimetro             | Entry point testabili                                                                                                                                                       | Tipo test                                         | Copertura esistente                                                                                                    | Livello                               | Rischio/criticita                                                                            | Priorita |
| -------------- | -------------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------- | -------- |
| endpoints      | `endpoints/data.py`                  | richiesto             | `Data.post`, `DataExtraction`, `Postprocessors`, `get_observed_data_size_count`, `check_user_quota_for_observed_data`                                             | integration HTTP + service-level                  | `integration/data/test_data_endpoint_auth.py`; `integration/postprocessing/*` bypassa HTTP                         | parziale/indiretta                    | Accetta richieste, quota, autorizzazioni, queue routing, push, postprocessor validation      | P0       |
| endpoints      | `endpoints/fields.py`                | richiesto             | `Fields.get`, `FieldsQuery`                                                                                                                                             | integration HTTP runtime_sensitive                | nessuna evidenza                                                                                                       | assente                               | Alimenta browsing/filtri; rami OBS/FOR/archivio/autorizzazioni, descrizioni Arkimet forecast e rischio su `SummaryStats=False` | P0       |
| endpoints      | `endpoints/maps_observed.py`         | richiesto             | `MapsObservations.get`, `MapsObservations.post`                                                                                                                         | integration HTTP runtime_sensitive                | GET in `integration/observed/*`                                                                                      | parziale                              | POST download, `daily`/`last`/`interval`, varianti residue `stationDetails`/`singleStation`, `reliabilityCheck`, archive auth | P0       |
| endpoints      | `endpoints/schedules.py`             | richiesto             | `Schedules.get`, `SingleSchedule.post/get/patch/delete`, `ScheduledRequests.get`, schema schedule                                                                     | integration HTTP + task fake                      | `integration/data_ready/*`, `integration/schedules/test_schedule_opendata_bridge.py`                               | parziale                              | CRUD, ownership, min period, opendata admin, patch conflicts e scheduled requests            | P0       |
| endpoints      | `endpoints/requests.py`              | richiesto             | `UserRequests.get/put/delete`, `CloneUserRequests.get`                                                                                                                  | integration HTTP                                  | `integration/requests/test_delete_pending_request.py`                                                                | parziale                              | Listing, total, archive, clone, ownership, fileoutput shape                                  | P1       |
| endpoints      | `endpoints/templates.py`             | richiesto (endpoints) | `Templates.get`, `Template.post/get/delete`, `check_files_to_upload`, `convert_to_shapefile`                                                                        | integration HTTP + pure helper                    | nessuna evidenza                                                                                                       | assente                               | Upload quota, shapefile completeness, delete side effects; possibile bug su `Template.get` | P0       |
| endpoints      | `endpoints/file.py`                  | richiesto (endpoints) | `FileDownload.get`                                                                                                                                                        | integration HTTP                                  | opendata direct file in `integration/opendata/test_download.py` copre solo `/opendata/<filename>`                  | assente                               | Download output utente e ownership                                                           | P1       |
| endpoints      | `endpoints/opendata.py`              | richiesto             | `OpendataFileList.get`, `OpendataDownloadFile.get`, `OpendataDownload.get`, `Reftime`, `OpenDataDownloadQuery`                                                    | integration HTTP                                  | `integration/opendata/*`                                                                                             | parziale/completa sui casi principali | Variabili incoerenti, q malformata, private direct file, archived exclusion                  | P2       |
| endpoints      | `endpoints/data_ready.py`            | richiesto             | `DataReady.post`                                                                                                                                                          | integration HTTP + fake celery/smtp               | `integration/data_ready/*`, `integration/schedules/*`                                                              | parziale                              | Celery submission failure, SMTP alert path, role/cluster validation                          | P1       |
| endpoints      | `endpoints/datasets.py`              | richiesto             | `Datasets.get`, `SingleDataset.get`                                                                                                                                     | integration HTTP                                  | `integration/dataset/*`                                                                                              | parziale/completa base                | `licenceSpecs`, sorting, service unavailable branch                                        | P2       |
| endpoints      | `endpoints/access_key.py`            | richiesto             | `AccessKeyResource.post/get/delete`, `AccessKeyValidationResource.get`                                                                                                  | integration HTTP                                  | `integration/access_key/*`                                                                                           | parziale/completa base                | DELETE revoke non esplicito; service unit non diretto                                        | P2       |
| endpoints      | `endpoints/arco.py`                  | richiesto             | `ArcoResource.get`, `ArcoDatasetsResource.get`, `guess_mime_type`, `_round_coord`                                                                                   | integration HTTP + unit                           | `integration/arco/*`                                                                                                 | parziale                              | S3 errors, metadata fallback, pagination, coord rounding                                     | P2       |
| endpoints      | `endpoints/usage.py`                 | richiesto (endpoints) | `Usage.get`                                                                                                                                                               | integration HTTP deterministic                    | nessuna evidenza                                                                                                       | assente                               | Quota usata dal profilo/UX; semplice ma user-facing                                          | P2       |
| endpoints      | `endpoints/request_hourly_report.py` | richiesto (endpoints) | `HourlyReport.get`                                                                                                                                                        | integration HTTP deterministic                    | nessuna evidenza                                                                                                       | assente                               | Rate-limit feedback; edge con limite nullo                                                   | P2       |
| endpoints      | `endpoints/rabbit_out_bindings.py`   | richiesto (endpoints) | `OutputBindings.get/post/delete`, `get_queue`                                                                                                                           | integration HTTP + fake rabbit                    | nessuna evidenza                                                                                                       | assente                               | Admin/Rabbit side effects; runtime_sensitive se reale                                        | P2       |
| endpoints      | `endpoints/admin_attributions.py`    | richiesto (endpoints) | `AdminAttributions.get/post/put/delete`, `AttributionInput`                                                                                                             | integration HTTP deterministic                    | nessuna evidenza                                                                                                       | assente                               | CRUD admin metadata usato da catalogo                                                        | P1       |
| endpoints      | `endpoints/admin_license_groups.py`  | richiesto (endpoints) | `AdminLicGroups.get/post/put/delete`, `LicGroupInput`                                                                                                                   | integration HTTP deterministic                    | nessuna evidenza                                                                                                       | assente                               | License visibility/autorizzazioni dataset                                                    | P1       |
| endpoints      | `endpoints/admin_licenses.py`        | richiesto (endpoints) | `AdminLicenses.get/post/put/delete`, dynamic schemas                                                                                                                      | integration HTTP deterministic                    | nessuna evidenza                                                                                                       | assente                               | Relazioni group-license; bug potenziale `.first` non chiamato                              | P1       |
| endpoints      | `endpoints/admin_datasets.py`        | richiesto (endpoints) | `AdminDatasets.get/post/put/delete`, dynamic schemas, `DatasetInput.null_sort_index`                                                                                    | integration HTTP deterministic                    | dataset tests usano DB diretto, non admin API                                                                          | assente                               | CRUD catalogo; sort/null, relazioni license/attribution                                      | P1       |
| endpoints      | `endpoints/schemas.py`               | richiesto (endpoints) | `AccessKeySchema`, `DatasetSchema`                                                                                                                                      | smoke/unit                                        | access key/arco HTTP                                                                                                   | indiretta                             | Basso, schema output gia attraversato                                                        | P3       |
| tasks          | `tasks/data_extraction_utilities.py` | richiesto             | `queue_sorting`                                                                                                                                                           | unit deterministic                                | chiamata indiretta da `data.py`/`schedules.py` non assertata                                                       | assente                               | Routing worker operativo/archivio                                                            | P0       |
| tasks          | `tasks/data_extraction.py`           | richiesto             | `data_extract`, `check_user_quota`, `observed_extraction`, `adapt_reftime`, `notify_by_email`, `notify_by_amqp_queue`, `human_size`, `package_data_license` | task integration + unit helpers                   | `integration/postprocessing/*`, `integration/schedules/*`                                                          | parziale/indiretta                    | Quota, cleanup, notifications, duplicate data-ready, schedule disable, AMQP                  | P0       |
| tasks          | `tasks/on_data_ready_extractions.py` | richiesto             | `launch_all_on_data_ready_extractions`                                                                                                                                    | task integration with fake celery                 | `integration/data_ready/*`, `integration/schedules/*`                                                              | parziale                              | Skip no/multi dataset, bad run decode, send_task failure                                     | P1       |
| tasks          | `tasks/requests_cleanup.py`          | richiesto             | `automatic_cleanup`                                                                                                                                                       | task integration deterministic                    | `integration/requests/test_delete_pending_request.py`                                                                | parziale                              | Expiration archive/delete and orphan/tmp files absent                                        | P1       |
| tasks          | `tasks/__init__.py`                  | richiesto             | `create_periodic_task_with_routing`, `create_crontab_task_with_routing`                                                                                                 | unit with monkeypatch fake RedBeat                | indirectly through schedules                                                                                           | indiretta                             | Routing options may be lost in scheduling                                                    | P2       |
| services       | `services/access_key_service.py`     | richiesto             | `is_access_key_valid`, `access_key_get_by_user`, `validate_access_key_from_request`                                                                                   | unit + integration HTTP                           | `integration/access_key/*`                                                                                           | indiretta/completa user-facing        | Timezone, missing user/key, direct service contract                                          | P2       |
| services       | `services/sqlapi_db_manager.py`      | richiesto             | owner/request checks, request/schedule/fileoutput creation, delete, response builders, dataset/license auth, request limits, permissions                                    | service-level integration                         | dataset/requests/opendata/postprocessing/data_ready use parts                                                          | parziale                              | Central business layer; many branches used by endpoints/tasks                                | P1       |
| services       | `services/arkimet.py`                | richiesto             | parser/matcher helpers, dataset format/category, network mapping, descriptions                                                                                              | unit + runtime smoke                              | observed/postprocessing/data endpoints indirectly                                                                      | parziale/indiretta                    | Query translation regressions are high blast radius                                          | P0       |
| services       | `services/dballe.py`                 | richiesto             | query parsing, db type split, auth, maps parsing, extraction parser, pluvio aggregation, itertools query expansion, size-count helpers                                      | unit + runtime_sensitive service                  | observed GET, postprocessing observed                                                                                  | parziale/indiretta                    | Observed data correctness, quota estimate, archive split                                     | P0/P1    |
| tools          | `tools/derived_variables.py`         | richiesto             | `pp_derived_variables`                                                                                                                                                    | postprocessing integration + subprocess-fake unit | `integration/postprocessing/test_forecast_basic.py`, `test_observed_postprocessing.py`, `test_error_handling.py` | parziale/completa main path           | Command failure cleanup unasserted                                                           | P2       |
| tools          | `tools/statistic_elaboration.py`     | richiesto             | `pp_statistic_elaboration`, `run_statistic_elaboration`, `match_timerange`                                                                                            | postprocessing integration + unit                 | `integration/postprocessing/test_forecast_basic.py`, `test_observed_postprocessing.py`, `test_error_handling.py` | parziale                              | Step string, GRIB1/2 matching, BUFR split edge                                               | P1       |
| tools          | `tools/grid_interpolation.py`        | richiesto             | `check_template_filepath`, `get_trans_type`, `pp_grid_interpolation`                                                                                                  | unit + postprocessing integration                 | `integration/postprocessing/test_forecast_spatial.py`                                                                | parziale                              | Validation helpers not covered; command error cleanup                                        | P1       |
| tools          | `tools/grid_cropping.py`             | richiesto             | `format_sub_type`, `pp_grid_cropping`                                                                                                                                   | unit + postprocessing integration                 | `integration/postprocessing/test_forecast_spatial.py`                                                                | parziale                              | `bbox -> coordbb` not asserted                                                             | P2       |
| tools          | `tools/spare_point_interpol.py`      | richiesto             | `get_trans_type`, `check_coord_filepath`, `pp_sp_interpolation`                                                                                                       | unit + postprocessing integration                 | `integration/postprocessing/test_forecast_spatial.py`, `test_forecast_chaining.py`                                 | parziale                              | Missing/mismatch/corrupt shapefile branches                                                  | P1       |
| tools          | `tools/output_formatting.py`         | richiesto             | `pp_output_formatting`                                                                                                                                                    | postprocessing integration + subprocess-fake unit | JSON output in `integration/postprocessing/test_forecast_chaining.py` and `test_observed_postprocessing.py`        | indiretta/parziale                    | Non-json passthrough and unlink side effect unasserted                                       | P2       |
| tools          | `tools/quality_check_filter.py`      | richiesto             | `pp_quality_check_filter`                                                                                                                                                 | service/tool integration                          | `integration/postprocessing/test_observed_postprocessing.py` with `only_reliable=True`                             | indiretta                             | QC content not asserted                                                                      | P2       |
| models         | `models/sqlalchemy.py`               | emerso                | `AccessKey.generate`, `AccessKey.is_valid`, model relationships                                                                                                         | unit/service integration                          | access key API                                                                                                         | indiretta                             | Token expiry semantics                                                                       | P2       |
| customization  | `customization.py`                   | emerso                | `custom_user_properties_pre/post`, `manipulate_profile`, custom fields                                                                                                  | unit/service integration                          | user creation helpers rely indirectly                                                                                  | parziale/indiretta                    | Default permissions and user profile contract                                                | P1       |
| initialization | `initialization.py`                  | emerso                | seeding licenses/attributions/datasets, cleanup cron install                                                                                                                | smoke/import + optional fake connector            | stack startup indirectly                                                                                               | indiretta                             | Idempotenza inizializzazione e cron cleanup                                                  | P2       |
| connector      | `connectors/s3/__init__.py`          | emerso                | `S3Ext.connect/is_connected/disconnect/get_instance`                                                                                                                      | unit with monkeypatch boto3                       | ARCO tests may use real/fake S3 indirectly                                                                             | assente                               | S3 ARCO availability and config validation                                                   | P2       |
| migrations     | `migrations/**`                      | emerso                | Alembic revision imports/heads                                                                                                                                              | smoke/collect                                     | runtime DB migrated by stack                                                                                           | indiretta                             | Schema drift; low value per file                                                             | P3       |

## Regole di decisione

- Nuovi contratti HTTP user-facing vanno sotto `tests/integration/<dominio>/` in moduli nuovi `test_<focus>_EXT.py`; non e previsto toccare i file legacy gia presenti salvo deroga esplicita.
- Estensioni di domini esistenti vanno nel dominio esistente: `data`, `observed`, `opendata`, `requests`, `schedules`, `postprocessing`, `arco`, `access_key`, `dataset`.
- Nuovi domini sono ammessi solo quando il backend espone una superficie distinta: `fields`, `templates`, `admin`, `tasks`, `services`, `tools`, `customizer`, `connectors`.
- Nuove fixture o helper condivisi possono vivere in `support_EXT.py`, `fixtures_EXT.py`, `factories_EXT.py` oppure in `conftest.py` quando il dominio lo giustifica. Ogni creazione o modifica di `conftest.py` richiede `README_conftest_EXT.md` nella stessa cartella.
- Test task/Celery dedicati usano fake gia presenti in `helpers/celery_fakes.py` o fake locali `_EXT` quando il contratto e la submission o il side effect DB; usano `async_real` solo quando bisogna verificare beat/broker/worker reali e dopo avere documentato perche il fake non basta.
- Test service-level usano DB reale del container se il contratto dipende da modelli SQLAlchemy; funzioni pure restano deterministic senza dataset storici, salvo i pochi casi runtime-sensitive ancorati alle finestre dati documentate.
- Nei test runtime-sensitive usare prima i dati reali esistenti nelle finestre ammesse; se non bastano, segnalare esplicitamente il gap e i dati futuri utili.
- Per `lm5` e `lm2.2` le fixture devono essere environment-agnostic: il test non deve dipendere dall'esistenza o meno della restrizione locale, ma esplicitare il setup di autorizzazione richiesto oppure usare assertion valide in locale e in CI.
- Nessun test consigliato solo per classi eccezione marker, costanti pure e `__repr__` marcati `pragma: no cover`.
- Se un modulo e coperto solo via flusso postprocessing, non duplicare lo stesso happy path: aggiungere solo helper puri, error handling o invarianti non assertate.
- Ogni modulo `_EXT.py` e ogni helper/test nuovo al suo interno devono essere accompagnati da commenti verbose di tracciabilita, scenario e cleanup.

## Architettura target della nuova copertura

Nuove cartelle proposte sotto `projects/mistral/backend/tests/integration`:

- `admin/`: CRUD admin attributions, license groups, licenses, datasets. Usare moduli `test_admin_*_EXT.py` e, se il dominio accumula fixture comuni, consentire `conftest.py` con relativo `README_conftest_EXT.md`.
- `fields/`: contratti `/fields` per observed e forecast, auth, errori e descrizioni forecast. Tenere fixture inline, in `support_EXT.py` o in `conftest.py` se il riuso lo giustifica; in quel caso aggiungere `README_conftest_EXT.md`.
- `templates/`: listing/upload/delete/get helper e validazioni shapefile. Usare `test_templates_*_EXT.py` e, se serve, `support_EXT.py`, `fixtures_EXT.py` o `conftest.py` per zip/temp dir, sempre con `README_conftest_EXT.md` nella cartella se `conftest.py` viene toccato.
- `tasks/`: test deterministic su helper task e task side effects isolati. `support_EXT.py` o `conftest.py` per fake schedule/request/file e fake SMTP/Rabbit quando il riuso lo giustifica; `conftest.py` richiede `README_conftest_EXT.md`.
- `services/`: test puri/service-level su parser e manager. Nessun accesso HTTP; helper condivisi in moduli `_EXT` o in `conftest.py` locale se davvero utile, sempre con `README_conftest_EXT.md`.
- `tools/`: edge case non gia coperti da `postprocessing`. `support_EXT.py`, `fixtures_EXT.py` o `conftest.py` locale per fake `Popen` e file temporanei solo se il riuso lo giustifica, piu `README_conftest_EXT.md` in caso di `conftest.py`.
- `customizer/`: test custom user properties e profile fields in moduli `_EXT.py`.
- `connectors/`: test S3 connector con monkeypatch boto3, in moduli `_EXT.py`.

Estensioni a cartelle esistenti:

- `data/test_data_endpoint_submission_EXT.py`, `data/test_data_endpoint_validation_EXT.py`, `data/test_file_download_EXT.py`.
- `observed/test_observations_download_EXT.py`, `observed/test_observations_edge_cases_EXT.py`.
- `requests/test_requests_listing_archive_clone_EXT.py`.
- `schedules/test_schedule_api_contracts_EXT.py`, `schedules/test_schedule_validation_EXT.py`, `schedules/test_scheduled_requests_EXT.py`.
- `opendata/test_listing_edge_cases_EXT.py`, `opendata/test_direct_download_authorization_EXT.py`.
- `arco/test_arco_edge_cases_EXT.py`.
- `access_key/test_access_key_revoke_EXT.py`.
- `dataset/test_dataset_licence_specs_EXT.py`.

Fixture placement:

- Root `tests/conftest.py`: modificabile solo se emerge un riuso cross-suite reale; in tal caso il folder `projects/mistral/backend/tests/` deve contenere o aggiornare `README_conftest_EXT.md`.
- `tests/integration/conftest.py`: modificabile se almeno piu domini hanno bisogno dello stesso setup; la cartella `tests/integration/` deve allora contenere `README_conftest_EXT.md` aggiornato.
- `integration/<area>/`: fixture inline nei file `*_EXT.py`, moduli espliciti `support_EXT.py`, `fixtures_EXT.py`, `factories_EXT.py` oppure `conftest.py` locale quando il riuso locale e piu chiaro. Ogni `conftest.py` creato o modificato richiede `README_conftest_EXT.md` nella stessa cartella.
- `README_conftest_EXT.md`: deve descrivere origine della modifica, elenco fixture, scope pytest, cleanup, dipendenze, motivazione del livello scelto e file di test che consumano le fixture.
- `helpers/`: aggiungere helper globali solo se riusati da piu domini e comunque come nuovi moduli `*_EXT.py`; evitare di toccare helper legacy gia stabili salvo beneficio concreto e ben motivato.
- Attese osservabili: riusare `helpers/polling.py` in sola lettura; nessun `sleep` nei nuovi test.

Marker:

- HTTP/DB deterministici: `pytest.mark.integration`, `pytest.mark.deterministic`.
- Dataset/meteo/S3/filesystem reali: aggiungere `runtime_sensitive` e commentare la finestra dati esatta nel file `_EXT.py`.
- Beat/broker/worker reali: aggiungere `async_real` e `runtime_sensitive`.
- Unit puri dentro `integration/services`, `integration/tasks`, `integration/tools`: `integration`, `deterministic`.

## Piano di implementazione per fasi

| Fase | Obiettivo                             | Moduli coperti                                                                            | Test da aggiungere                                                                                                                                                                                                                                            | Fixture/helper                              | Validazione minima                                                                                                                   | Rischi runtime                            |
| ---- | ------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| 1    | Quick wins puri task/service/tool     | `queue_sorting`, `human_size`, `adapt_reftime`, parser Arkimet/Dballe, helper tools | `integration/tasks/test_queue_sorting_EXT.py`, `integration/tasks/test_data_extraction_helpers_EXT.py`, `integration/services/test_arkimet_query_parsing_EXT.py`, `integration/services/test_dballe_query_parsing_EXT.py`, `integration/tools/test_tool_helpers_EXT.py` | solo helper locali/fake oggetti o `support_EXT.py` | `restapi tests --folder custom/integration/tasks`, `--folder custom/integration/services`, `--folder custom/integration/tools` | basso |
| 2    | Contratto HTTP `POST /data`           | `endpoints/data.py`, queue routing, validation, push | `data/test_data_endpoint_submission_EXT.py`, `data/test_data_endpoint_validation_EXT.py`, `data/test_file_download_EXT.py` | fake Celery/Rabbit locale; riuso auth in sola lettura | `restapi tests --folder custom/integration/data` | medio; preferire fake, usare date reali solo se inevitabile |
| 3    | Observed download e fields            | `maps_observed.post`, edge GET controller-only, `fields.get` OBS/FOR | `observed/test_observations_download_EXT.py`, `observed/test_observations_edge_cases_EXT.py`, `fields/test_fields_api_EXT.py` | fixture inline o `support_EXT.py`; riuso helper observed e `helpers/dataset_window.py` in sola lettura | file/folder observed e fields | alto; OBS con `agrmet` Arkimet `2020-03-31`/`2020-04-01` e DBALLE `2020-04-06`, FOR con `lm5` `2021-10-19` o `lm2.2` `2019-09-10`, con portabilita locale/CI |
| 4    | Request e schedule API completo       | `requests.py`, `schedules.py`, task data-ready edge | `requests/test_requests_listing_archive_clone_EXT.py`, `schedules/test_schedule_api_contracts_EXT.py`, `schedules/test_schedule_validation_EXT.py`, `schedules/test_scheduled_requests_EXT.py`, `tasks/test_on_data_ready_task_edges_EXT.py` | `support_EXT.py` locale solo se serve riuso | folder requests, schedules, tasks | `lm5` solo `2021-10-19`, `lm2.2` solo `2019-09-10`, fake Celery/RedBeat preferiti |
| 5    | Templates, file, usage, hourly        | `templates.py`, `file.py`, `usage.py`, `request_hourly_report.py` | `templates/test_templates_listing_EXT.py`, `templates/test_templates_upload_delete_EXT.py`, `data/test_file_download_EXT.py`, `user_limits/test_usage_and_hourly_EXT.py` | user con quota/template, temp upload/output, `support_EXT.py` se riusato | file specifici | filesystem/quota, possibile bug esistente |
| 6    | Admin CRUD e customizer/models        | `admin_*.py`, `customization.py`, `models/sqlalchemy.py` | `admin/test_admin_attributions_EXT.py`, `admin/test_admin_license_groups_EXT.py`, `admin/test_admin_licenses_EXT.py`, `admin/test_admin_datasets_EXT.py`, `customizer/test_user_customizer_EXT.py`, `services/test_access_key_service_EXT.py` | admin local support `_EXT`, DB cleanup | folder admin/customizer/services | relazioni DB e duplicati |
| 7    | Cleanup avanzato, notifications, AMQP | `requests_cleanup`, `data_extract`, `notify_*`, `check_user_quota` | `tasks/test_requests_cleanup_expiration_EXT.py`, `tasks/test_data_extraction_quota_and_notifications_EXT.py` | fake SMTP/Rabbit/Popen locali in `support_EXT.py` solo se serve | folder tasks | side effects DB/filesystem |
| 8    | ARCO/S3/connector/initializer smoke   | `arco.py`, `connectors/s3`, `initialization.py`, migrations | `arco/test_arco_edge_cases_EXT.py`, `connectors/test_s3_connector_EXT.py`, `initializer/test_initializer_smoke_EXT.py` | monkeypatch boto3/S3/celery in moduli `_EXT` | file specifici + collect-only | S3 reale da evitare con mock |

Nota trasversale alla tabella delle fasi:

- Se una fase crea o modifica un `conftest.py`, la stessa fase deve creare o aggiornare anche `README_conftest_EXT.md` nella cartella coinvolta.
- Se una fase usa dati reali esistenti, deve prima tentare copertura a costo zero dentro le finestre documentate e poi segnalare in modo esplicito eventuali limiti che richiederebbero dati aggiuntivi futuri.
- Per `lm5` e `lm2.2`, le fixture della fase devono essere progettate per passare sia nel locale con restrizioni sia nella CI senza restrizioni.
- Se una fase scopre un bug backend o introduce uno skip forzato, la stessa fase deve aggiornare anche `projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.

## Strategia specifica per area

### Endpoints

- `/access-key`: gia coperti GET/POST/validate; aggiungere DELETE revoke e GET successivo 404 in `integration/access_key/test_access_key_revoke_EXT.py`.
- `/arco/<path>`: gia coperti auth/proxy; aggiungere S3 `NoSuchKey`, mime type, `_round_coord`, catalog metadata fallback/pagination in `integration/arco/test_arco_edge_cases_EXT.py` con fake S3.
- `/arco/datasets`: gia coperto happy path; aggiungere missing `.zmetadata`, unknown attribution/license e bounding rounding, senza S3 reale e senza toccare il backend applicativo.
- `/datasets` e `/datasets/<id>`: gia coperti base/authorization; aggiungere `licenceSpecs=True`, sort con `sort_index=None`, service error 503 in `integration/dataset/test_dataset_licence_specs_EXT.py`.
- `/data`: lasciare intatto `test_data_endpoint_auth.py` e mettere i nuovi scenari in `test_data_endpoint_submission_EXT.py` e `test_data_endpoint_validation_EXT.py`; coprire fake Celery, dataset inesistente, mixed dataset format/license, output_format invalid/incompatibile, postprocessor unauthorized, push queue missing/nonexistent, only_reliable invalid, observed quota forbidden. Per i casi runtime reali forecast, usare prima i dati `lm2.2` `2019-09-10` e `lm5` `2021-10-19` gia presenti; helper e fixture devono essere agnostici alla restrizione locale vs CI e non devono assumere il forbidden locale come oracolo fisso. Se le finestre non bastano, segnalare i dati futuri utili.
- `/data/<filename>`: aggiungere output download proprietario, file non proprietario e file DB presente ma missing su filesystem in `integration/data/test_file_download_EXT.py`.
- `/data/ready`: gia coperto acceptance e gating; se si estende la copertura, farlo in un modulo `_EXT.py` dedicato con fake Celery/SMTP e, per rami forecast reali, solo sulle finestre `lm2.2`/`lm5` documentate, usando fixture portabili tra locale e CI e segnalando esplicitamente i rami che richiederebbero piu giorni o runhour.
- `/fields`: nuovo dominio in `integration/fields/test_fields_api_EXT.py`; coprire esplicitamente sia OBS sia FOR. OBS: map mode recente con license valida, archived anonimo `401`, archived con utente senza `allowed_obs_archive` `401` se costruibile in modo portabile, network inesistente `404`, network non autorizzato `401`, license group mancante/inesistente `400`, mismatch network/license `400`, dataset osservato inesistente `404`, bbox incompleta `400`, `onlySummaryStats`, `SummaryStats=False`, `allAvailableProducts`. FOR: dataset mode autenticato con `lm5` o `lm2.2`, dataset forecast inesistente `404`, dataset multipli con categorie diverse `400`, dataset multipli con license group diversi `400`, multi `multim-forecast` non supportato `400`, happy path con `descriptions.leveltypes` e `descriptions.timerangetypes` quando `summarystats.c > 0`, `onlySummaryStats` anche sul forecast e probe esplicito per `SummaryStats=False` sul forecast, da riportare come blocco backend se riproduce il difetto del controller usando solo skip esplicito e documentato, mai `xfail`, e aggiornando il registro problemi. Per dati reali usare prima `agrmet` Arkimet `2020-03-31` o `2020-04-01`, `agrmet` DBALLE `2020-04-06` preferibilmente `00:00`, `lm5` `2021-10-19` e `lm2.2` `2019-09-10`; se queste finestre non bastano per un contratto importante, dichiararlo nel piano come gap dati futuro.
- `/observations` GET: gia coperto core; aggiungere in `test_observations_edge_cases_EXT.py` solo rami controller non gia coperti: intervallo troppo lungo anonimo/autenticato, `daily`, `last`, `interval` conflict, `stationDetails` senza `networks` `400`, `stationDetails` con piu network `400`, stazione inesistente `404` se scenario costruibile tentando sia `ident` sia `lat/lon`, `allStationProducts=false` che limita i prodotti richiesti e mismatch network/license se costruibile. Per runtime reale, fissare la finestra `agrmet` sopra e documentare se si usano i soli 4 dati delle `01:00`/`02:00`; se servisse storia piu lunga per rendere robusto `daily` o `last`, segnalarlo come dato utile futuro.
- `/observations` POST: nuovo test in `test_observations_download_EXT.py` per download JSON e BUFR, `output_format` invalido, bbox incompleta, license mandatory, license group inesistente o mismatch network/license se costruibili, `singleStation` senza `networks`, `singleStation` con piu network, `singleStation` senza coordinate/ident, archived auth, network non autorizzato e smoke `reliabilityCheck` quando sostenibile nella finestra dati ammessa.
- `/datasets/<id>/opendata`: gia coperto; aggiungere q malformata tollerata/errore deciso, variabili incoerenti -> 500, daily extraction label, dataset privato direct file in moduli `_EXT.py` dedicati.
- `/opendata/<dataset>/download`: gia coperto molto; aggiungere archived exclusion e private direct download authorization in `test_direct_download_authorization_EXT.py`.
- `/requests`: aggiungere list shape, total 206, archived filter, archive PUT, clone GET, owner mismatch, missing request in `test_requests_listing_archive_clone_EXT.py`.
- `/schedules`: aggiungere list total, create periodic non data-ready con fake RedBeat, min period forbidden, no schedule setting schema error, opendata admin-only, multidataset opendata error, observed opendata error, patch enable/disable conflicts, delete ownership, scheduled requests `last/get_total` in `test_schedule_api_contracts_EXT.py`, `test_schedule_validation_EXT.py`, `test_scheduled_requests_EXT.py`. Se il test usa runtime forecast reale, sfruttare prima `lm5` `2021-10-19` o `lm2.2` `2019-09-10`, con fixture portabili locale/CI; se servono piu date per coprire correttamente un ramo, segnalarlo come gap dati futuro.
- `/templates`: aggiungere list/get_total, max_allowed, upload grib, upload shapefile zip missing `.shx/.dbf`, quota exceeded, get existing/missing, delete removes sidecar files in `test_templates_listing_EXT.py` e `test_templates_upload_delete_EXT.py`.
- `/usage`: aggiungere empty dir and non-empty dir usage in `user_limits/test_usage_and_hourly_EXT.py`.
- `/hourly`: aggiungere no limit -> `{}`, limit with current-hour rows -> submitted/remaining nello stesso modulo `_EXT.py` dei limiti utente.
- `/outbindings`: aggiungere admin-only, exchange creation, dataset key initialization, unknown binding ignored, bind/unbind queue in eventuale modulo `_EXT.py` dedicato se la priorita viene rialzata.
- `/admin/*`: aggiungere CRUD happy path, duplicate conflict, not-found update/delete, schema empty URL/null sort_index in `admin/test_admin_*_EXT.py`.

### Tasks

- `queue_sorting`: unit deterministico in `test_queue_sorting_EXT.py` su FOR/SEA/RAD/OBS operational vs archived, naive datetime treated UTC, `reftime=None` archived.
- `create_periodic_task_with_routing` / `create_crontab_task_with_routing`: monkeypatch `RedBeatSchedulerEntry` e `celery.get_instance`, assert schedule type, args/kwargs, queue/routing in un modulo `_EXT.py` dedicato se non stanno in `test_queue_sorting_EXT.py` senza confondere lo scope.
- `automatic_cleanup`: gia copre pending stale; aggiungere completed expired archive, completed expired delete, disabled expiration ignored, archived ignored, orphan `.tmp` and orphan output deletion in `test_requests_cleanup_expiration_EXT.py`.
- `launch_all_on_data_ready_extractions`: gia copre molti skip via HTTP; aggiungere rows con zero/multiple datasets, invalid run filter decode, Celery send_task exception -> `SystemError` in `test_on_data_ready_task_edges_EXT.py`, usando dati `lm5`/`lm2.2` solo se davvero inevitabili e sempre con fixture portabili locale/CI.
- `data_extract`: non duplicare postprocessing happy path; aggiungere duplicate data-ready returns without new file, access denied, invalid license, empty output marks failure, schedule disable on quota, tmp cleanup, `force_obs_download` path in `test_data_extraction_quota_and_notifications_EXT.py`.
- Notifications: unit con fake SMTP/Rabbit, no real retry sleep; monkeypatch `time.sleep` to no-op and assert payload/body/download URL, con commenti espliciti sul motivo del fake.
- `package_data_license`: pure filesystem test tar includes output and `LICENSE`, original output removed, commentando in modo verboso il cleanup.

### Services

- `access_key_service`: unit su key missing, expired, no expiration, wrong key, request BasicAuth missing in `test_access_key_service_EXT.py` o `test_access_key_model_EXT.py`.
- `SqlApiDbManager`: service-level DB tests su `check_fileoutput`, `check_owner`, `check_request_is_pending_within_grace_period`, `create/delete_request_record`, `_get_request_response`, `_get_schedule_response`, `get_datasets`, `check_dataset_authorization`, `check_user_request_limit`, `get_user_permissions` in moduli `_EXT.py` dedicati.
- `BeArkimet`: unit parser per `parse_reftime`, `parse_matchers`, `decode_run`, invalid styles/types, `is_filter_allowed`, `get_leveltype_descriptions`, `get_trangetype_descriptions` in `test_arkimet_query_parsing_EXT.py`; runtime smoke per format/category solo se config disponibile e con date Arkimet reali documentate.
- `BeDballe`: unit parser per `from_query_to_dic`, `parse_query_for_maps`, `from_filters_to_lists`, `from_query_to_lists`, `parse_query_for_data_extraction`, `get_queries_and_dsn_list_with_itertools`, `is_query_for_pluvio_aggregations`, `get_db_type/split_reftimes` con monkeypatch clock in `test_dballe_query_parsing_EXT.py`.

### Tools

- Non duplicare `integration/postprocessing` happy path.
- Aggiungere `tools/test_tool_helpers_EXT.py` per `get_trans_type`, `format_sub_type`, `check_template_filepath`, `check_coord_filepath` missing/mismatch/corrupt shapefile.
- Aggiungere `tools/test_postprocessor_command_failures_EXT.py` solo con fake `subprocess.Popen` e file temp per assert cleanup/error wrapping.
- Aggiungere `tools/test_statistic_elaboration_helpers_EXT.py` per `run_statistic_elaboration` step string e `match_timerange` GRIB1/GRIB2 tramite monkeypatch eccodes.
- Aggiungere test su `output_formatting` passthrough non-json e unlink input, evitando dbamsg reale e mantenendo i commenti di cleanup molto espliciti.

### Altre superfici

- Customizer: `integration/customizer/test_user_customizer_EXT.py`.
- Models/access key: `integration/services/test_access_key_model_EXT.py` o nello stesso file `test_access_key_service_EXT.py`.
- Initializer: smoke idempotenza con fake SQLAlchemy solo se sostenibile in `integration/initializer/test_initializer_smoke_EXT.py`; altrimenti import/collect e copertura indiretta da startup, documentando perche non si va oltre.
- Connector S3: `integration/connectors/test_s3_connector_EXT.py` con mock `boto3.Session`.
- Migrations: `pytest --collect-only tests/custom` e, se disponibile, comando Alembic heads nel container; non creare test per ogni revision.

## Quick wins

- `queue_sorting` matrix.
- `human_size` e `package_data_license`.
- `AccessKey.generate/is_valid` e `is_access_key_valid`.
- `BeArkimet.parse_reftime`, `parse_matchers`, `decode_run`.
- `BeDballe.from_query_to_dic`, `from_filters_to_lists`, `parse_query_for_maps`.
- Tool helper `get_trans_type`, `format_sub_type`, `check_template_filepath`, `check_coord_filepath`.
- Access key DELETE revoke.
- Usage/hourly deterministic.

## High risk / high value

- `POST /data` validation/submission/queue/push/quota.
- `/fields` and observed POST download.
- Schedule API create/patch/delete/list beyond data-ready bridge.
- Request archive/clone/list total.
- Template upload/delete/get and quota.
- `data_extract` quota failure and notification side effects.
- `SqlApiDbManager` file ownership and dataset authorization helpers.
- Admin CRUD metadata because dataset/catalog behavior depends on it.

## Esclusioni motivate

- Exception classes in `exceptions.py`: no behavior besides type identity.
- `__repr__` methods and lines marked `pragma: no cover`: diagnostic only.
- `endpoints/__init__.py`: constants and typing alias; exercised indirectly.
- Full external toolchain happy paths duplicated from `integration/postprocessing`: already covered; add only edge/error/helper tests.
- Full Alembic revision-by-revision tests: high maintenance, low behavior value; prefer smoke/heads/current checks.
- Real S3/Rabbit/SMTP in deterministic tests: use fake connectors; reserve real broker only for existing or explicitly new `async_real` flows.

## Comandi di validazione

Tutti i comandi sono da repo root.

```bash
.mhub-venv/bin/rapydo shell backend 'restapi wait'
```

Fase 1:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/tasks'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/services'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/tools'
```

Fase 2:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/data'
```

Fase 3:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/observed'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/fields'
```

Fase 4:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/requests'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/schedules'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/tasks/test_on_data_ready_task_edges_EXT.py'
```

Fase 5:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/templates'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/data/test_file_download_EXT.py'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/user_limits'
```

Fase 6:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/admin'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/customizer'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/services/test_access_key_service_EXT.py'
```

Fase 7:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/tasks/test_requests_cleanup_expiration_EXT.py'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/tasks/test_data_extraction_quota_and_notifications_EXT.py'
```

Fase 8:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/arco'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/connectors'
.mhub-venv/bin/rapydo shell backend 'pytest --collect-only tests/custom -q'
```

Controllo statico complementare solo per file Python aggiunti:

```bash
.mhub-venv/bin/rapydo shell backend 'python3 -m compileall tests/custom/integration/tasks tests/custom/integration/services tests/custom/integration/tools'
```

## Sequenza operativa finale

1. Creare artefatti `_EXT.py` solo dentro `projects/mistral/backend/tests`, senza toccare `untracked_stuff` e senza modificare codice applicativo fuori dal perimetro tests; se una fase tocca `conftest.py`, creare o aggiornare anche `README_conftest_EXT.md` nella stessa cartella.
2. Non usare `xfail`: quando emerge un bug backend o uno skip forzato, usare solo skip esplicito e aggiornare `projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.
3. Implementare quick wins puri in `integration/tasks`, `integration/services`, `integration/tools` con commenti verbose, senza dataset reali e usando `conftest.py` solo se il riuso reale lo giustifica e viene documentato.
4. Validare Fase 1 e correggere solo problemi dei nuovi test `_EXT`.
5. Estendere `integration/data` per `POST /data` con fake Celery/Rabbit e contratti di validazione, lasciando intatti i file legacy esistenti e usando i dati reali forecast gia presenti solo quando aggiungono valore a costo zero.
6. Validare folder `custom/integration/data`.
7. Aggiungere observed POST download e nuovo dominio `fields`, fissando in anticipo le date `agrmet` ammesse e documentandole nei commenti dei test runtime-sensitive; se le date disponibili non bastano per un ramo importante, segnalarlo come gap dati futuro.
8. Validare observed + fields, con skip espliciti per runtime data non disponibile e senza date fuori matrice.
9. Estendere requests e schedules API, usando fake Celery/RedBeat per il deterministico e lasciando `async_real` solo a casi realmente inevitabili; per dati forecast reali usare solo `lm5` `2021-10-19` o `lm2.2` `2019-09-10`, con fixture e helper portabili tra locale e CI.
10. Validare requests/schedules/tasks edge.
11. Aggiungere templates/file/usage/hourly con cleanup filesystem rigoroso e commenti espliciti su ogni side effect.
12. Validare i file/folder specifici.
13. Aggiungere admin CRUD e customizer/models in moduli `_EXT.py` separati dalla baseline.
14. Validare admin/customizer/services.
15. Aggiungere cleanup avanzato, quota e notification/AMQP con fake connector e senza real sleep.
16. Validare i singoli file task `_EXT`.
17. Aggiungere ARCO edge, S3 connector mocked e smoke initializer/import.
18. Eseguire collect-only completo e poi `restapi tests --folder custom` solo a chiusura copertura, mantenendo sempre la tracciabilita `_EXT` dei nuovi artefatti, la documentazione `README_conftest_EXT.md` per ogni `conftest.py` toccato, la portabilita locale/CI dei test su `lm5` e `lm2.2` e l'aggiornamento del registro bug/skip ogni volta che emerge un blocco noto.

## Prompt pronti

I prompt eseguibili sono stati spezzati in file markdown sotto:

- `projects/mistral/backend/tests/docs/coverage_extension_prompts/`

Eseguirli nell'ordine numerico. Ogni prompt contiene obiettivo ristretto, target, vincoli di suite, struttura attesa, validazione minima e criterio di completamento, e ribadisce in modo tassativo sei vincoli: `_EXT` per i nuovi artefatti Python della suite con eccezione del filename speciale `conftest.py`, `README_conftest_EXT.md` per ogni cartella con `conftest.py` toccato, commenti molto verbosi, uso prioritario dei dati reali gia presenti, segnalazione dei limiti dati futuri, `untracked_stuff` off-limits e nessuna modifica fuori da `projects/mistral/backend/tests`.
