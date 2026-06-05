# Prompt Pack Estensione Copertura Backend

Usare questi prompt nell'ordine numerico. Sono pensati per un agente implementativo che lavora nel repository Meteo-Hub/Rapydo 2.4 e deve aggiungere test senza rifattorizzare la suite baseline.

Regole comuni tassative:

- Leggere prima `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`, `projects/mistral/backend/tests/README.md`, `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md` e `projects/mistral/backend/tests/helpers/templates/endpoint_template.py`.
- Trattare `/home/federico/mistral/meteo-hub/untracked_stuff` come se non esistesse: niente letture, niente ricerche, niente riferimenti, niente copia di codice.
- Non modificare alcun codice fuori da `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests`.
- Ogni nuovo artefatto Python della suite introdotto dal piano deve usare il suffisso `_EXT.py`. Questo vale per moduli test, helper, factory, utility e support module, con eccezione del filename speciale `conftest.py`.
- `conftest.py` puo essere creato o modificato quando il riuso delle fixture lo giustifica davvero, ma ogni cartella toccata da questa scelta deve contenere o aggiornare `README_conftest_EXT.md` con spiegazione dettagliata di fixture, scope, cleanup, dipendenze e test consumatori.
- Non usare `xfail`: se un test mette in luce un bug backend o un comportamento anomalo non risolvibile nel perimetro della suite, usare solo `skip` esplicito, fortemente documentato e con criterio chiaro di riattivazione dell'assert.
- Ogni bug scoperto o skip forzato introdotto dal lavoro deve essere censito o aggiornato in `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.
- Ogni file `_EXT.py` deve aprirsi con un blocco commenti molto verboso che spieghi provenienza dell'estensione, scenario coperto, motivo di fake/mock, finestra dati usata o evitata, strategia di cleanup e perche la baseline legacy non e stata toccata.
- Ogni nuovo test/helper/funzione aggiunto in un file `_EXT.py` deve avere commenti introduttivi descrittivi, non minimi.
- Non aggiungere test al root di `projects/mistral/backend/tests`.
- Usare solo domini sotto `projects/mistral/backend/tests/integration`.
- Mettere fixture nel livello minimo corretto.
- Usare `helpers/polling.py` per attese osservabili.
- Validare con `rapydo shell backend 'restapi tests ...'` usando path `tests/custom/...`.

Finestre dati reali da rispettare quando il fake non basta:

- `lm2.2`: solo `2019-09-10`.
- `lm5`: solo `2021-10-19`.
- `agrmet` in Arkimet: solo `2020-03-31` e `2020-04-01`.
- `agrmet` in DBALLE: solo `2020-04-06`, principalmente `00:00`, con esattamente 4 dati alle `01:00` e `02:00`.

Regola operativa sulle date:

- Se il contratto puo essere coperto correttamente con i dati reali gia presenti nelle finestre sopra, usare prima quei dati a costo zero.
- Se il fake o il monkeypatch sono piu corretti del dato reale disponibile per quello specifico contratto, documentare il motivo e usare il fake.
- Se servono dati reali, la data deve comparire nei commenti del file `_EXT.py`, nei commenti del test e nello skip esplicito in caso di dati mancanti.
- Se le finestre disponibili non bastano per coprire bene un contratto runtime-realistic, non bloccare il lavoro: segnalare esplicitamente il limite e indicare quali dati aggiuntivi sarebbero utili in futuro.

Portabilita locale/CI per `lm5` e `lm2.2`:

- La restrizione autorizzativa su `lm5` e `lm2.2` esiste solo nel locale dell'utente; in CI quei dataset non sono inizializzati con la stessa restrizione.
- I test e le fixture devono quindi essere agnostici rispetto a questa differenza: non usare il setup locale come oracolo fisso di `401` o `403`.
- Per i casi positivi, esplicitare l'autorizzazione necessaria nel setup del test. Per i casi negativi, costruire il diniego in modo controllato e portabile, senza dipendere dalla sola configurazione locale di `lm5` o `lm2.2`.

Nota specifica per il prompt 03 (`observed` + `fields`):

- `/fields` va coperto sia nel ramo OBS sia nel ramo FOR. Per OBS usare prima `agrmet`; per FOR usare prima `lm5` `2021-10-19` o `lm2.2` `2019-09-10`, anche tramite helper in sola lettura come `helpers/dataset_window.py` quando evita duplicazione inutile.
- `/observations` non deve duplicare i GET legacy già coperti, ma deve aggiungere i branch controller-only rimasti: POST download/validation, `daily`, `last`, `interval`, varianti residue di `stationDetails`/`singleStation`, mismatch license/network e smoke `reliabilityCheck` quando sostenibile.
- Se il probe forecast di `/fields?SummaryStats=false` riproduce un difetto del controller, la mancanza va riportata esplicitamente come bug backend o blocco noto. La suite non usa `xfail`: usare solo uno skip esplicito, fortemente documentato, e aggiornare il registro problemi.

Ordine consigliato:

1. `01_quick_wins_tasks_services_tools.md`
2. `02_data_endpoint_contracts.md`
3. `03_observed_download_and_fields.md`
4. `04_requests_schedules_contracts.md`
5. `05_templates_file_usage_hourly.md`
6. `06_admin_customizer_models.md`
7. `07_data_extraction_cleanup_notifications.md`
8. `08_arco_s3_initializer_smoke.md`
