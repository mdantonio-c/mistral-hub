# Meteo-Hub Backend Test Suite Manual

## Parti da qui

Questa cartella contiene la suite custom del backend Meteo-Hub dopo il refactor strutturale.

La documentazione mantenuta della suite e concentrata solo in questi file:

1. `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
   - overview corrente, struttura finale e metodo di validazione;
2. `projects/mistral/backend/tests/README.md`
   - mappa pratica della cartella `tests`, cioe questo file;
3. `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`
   - mappa esplicita `legacy -> nuova suite` per i contratti migrati;
4. `projects/mistral/backend/tests/docs/piano_refactoring_suite_test.md`
   - rationale storico del refactor, utile solo quando serve ricostruire il percorso fatto.

## Stato corrente della suite

Lo stato corrente e questo:

- il refactor strutturale della suite e validato;
- i test reali vivono sotto `integration/` e sono separati per dominio;
- `helpers/` contiene solo riuso cross-area o infrastruttura di suite;
- il root della cartella `tests` non contiene piu moduli `test_*.py`: oggi espone solo infrastruttura di suite, documentazione e lo smoke script `test_arpaesimc.sh`;
- la fase successiva, fuori scope rispetto a questo lavoro, e l'eventuale estensione della copertura verso endpoint, services e task non ancora coperti dai test storici.

## Modello mentale in cinque minuti

La suite si legge bene se la dividi in quattro strati:

1. `conftest.py` globale
   - espone solo fixture davvero trasversali come `test_runtime` e `cleanup_registry`;
2. `helpers/`
   - contiene building block riusabili tra piu aree, non test veri;
3. `integration/`
   - contiene i test reali organizzati per dominio funzionale;
4. `integration/<area>/conftest.py` e `integration/<area>/support.py`
   - contengono rispettivamente fixture locali e logica di supporto di dominio singolo.

Se ti stai chiedendo dove vive davvero un comportamento, la risposta corretta quasi sempre non e nel root della cartella, ma in `integration/<area>/`.

## Path host e path container

Percorso host nel repository:

- `projects/mistral/backend/tests/...`

Percorso visto dal container backend durante l'esecuzione:

- `tests/custom/...`

La differenza conta: quando lanci i test con `rapydo`, i comandi devono quasi sempre usare il path `tests/custom/...`, anche se nel repository i file stanno sotto `projects/mistral/backend/tests/...`.

## Il giro che fanno i test

Il flusso reale della suite e questo:

1. Si lancia pytest attraverso il wrapper di progetto, di solito con `.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/...''`.
2. `restapi tests` esegue pytest dentro il container backend, con l'ambiente Meteo-Hub gia pronto e con i servizi richiesti collegati nel modo previsto dal progetto.
3. Pytest parte dalla radice della suite custom e carica subito `tests/custom/conftest.py`, che nel repository corrisponde a `projects/mistral/backend/tests/conftest.py`.
4. Quel `conftest.py` registra il marker `integration` e mette a disposizione solo fixture globali di suite: `test_runtime`, `cleanup_registry`.
5. Pytest colleziona i moduli Python trovati sotto la cartella dei test. I test veri della suite corrente vivono sotto `integration/`, mentre il root contiene infrastruttura e documentazione di suite.
6. Quando un test si trova sotto `integration/`, pytest carica anche `integration/conftest.py`, che espone le fixture condivise tra i test HTTP integrati, come `auth_headers` e le fixture legate alle access key.
7. Se il test appartiene a un sottoalbero con un suo `conftest.py`, per esempio `integration/observed/conftest.py` o `integration/postprocessing/conftest.py`, pytest aggiunge anche quelle fixture locali solo a quel dominio.
8. Il test usa le fixture per preparare utenti, dataset, schedule, richieste, file di output o override temporanei. La logica ripetibile viene tenuta nei moduli `helpers/` se serve a piu aree, oppure in moduli locali come `integration/<area>/support.py` se resta confinata a un solo dominio.
9. A fine test, il cleanup avviene in teardown tramite `cleanup_registry.run()`, in modo centralizzato e coerente.

## Come funziona pytest in questa suite

### Regola piu importante: visibilita dei `conftest.py`

Pytest non tratta tutti i `conftest.py` allo stesso modo. Ogni `conftest.py` vale per la directory in cui si trova e per le sue sottodirectory.

In questa suite la scelta corretta e:

- `tests/conftest.py`: solo fixture davvero globali, valide per tutta la suite.
- `tests/integration/conftest.py`: fixture condivise da tutti i test di integrazione HTTP.
- `tests/integration/<dominio>/conftest.py`: fixture valide solo per quel dominio.

Questa e la risposta pratica al dubbio iniziale: il punto di divisione corretto e `root` contro `integration`, non `root` contro un singolo dominio.

### Fixture globali

`projects/mistral/backend/tests/conftest.py` espone due mattoni di base:

- `test_runtime`: singleton di sessione per cache e override temporanei di attributi.
- `cleanup_registry`: registro LIFO di callback e path da ripulire in teardown.

### Fixture di integrazione

`projects/mistral/backend/tests/integration/conftest.py` espone fixture usate da molti test API:

- `auth_headers`: login del test user di default.
- `fresh_access_key`: genera una access key appena creata.

Le fixture access-key usate solo da quel dominio, come `fresh_access_key_with_expiration`, stanno invece in `projects/mistral/backend/tests/integration/access_key/conftest.py`.

### Marker e parametrizzazione

La suite rifattorizzata espone ora questi marker:

- `integration`: tutti i test veri della suite nuova sotto `integration/`.
- `deterministic`: il controllo del flusso resta nel runtime del test e non aspetta latenze reali di beat, broker o worker.
- `async_real`: il test aspetta davvero la catena asincrona `celerybeat -> broker -> worker`.
- `runtime_sensitive`: il contratto e stabile, ma dipende anche dallo stato del runtime, dai dataset presenti o da servizi infrastrutturali vivi.

Mappa pratica attuale:

- `access_key`, `arco`, `data`, `requests`: `integration`, `deterministic`.
- `dataset`, `data_ready`, `observed`, `opendata`, `postprocessing`: `integration`, `deterministic`, `runtime_sensitive`.
- `integration/schedules/test_schedule_opendata_bridge.py::test_on_data_ready_schedule_publishes_opendata_package`: `integration`, `deterministic`, `runtime_sensitive`.
- `integration/schedules/test_schedule_opendata_bridge.py::test_crontab_schedule_publishes_opendata_package`: `integration`, `async_real`, `runtime_sensitive`.

L'aggiunta dei marker non cambia da sola il comportamento della CI attuale: il workflow backend continua a eseguire l'intera suite finche non usa esplicitamente selezioni `-m`.

In alcuni domini, come `observed`, i test usano `pytest.mark.parametrize(...)` con il nome di una fixture e poi recuperano la fixture con `request.getfixturevalue(...)`. Questo pattern permette di riutilizzare la stessa batteria di assert su scenari diversi (`dballe`, `arkimet`, `mixed`) senza duplicare il test body.

## Come leggere la nuova modulazione

La suite e organizzata in tre strati.

### 1. Root della suite

Qui stanno solo i pezzi che devono essere visibili ovunque e la documentazione locale della suite.

- `README.md`: manuale pratico della cartella `tests`.
- `docs/`: guida finale, matrice `legacy -> nuova suite` e piano storico del refactor.
- `__init__.py`: marca la cartella come package Python della suite custom.
- `conftest.py`: definisce le fixture globali e registra il marker `integration`.
- `helpers/`: helper riusabili e infrastruttura condivisa.
- `integration/`: test reali organizzati per dominio.
- `test_arpaesimc.sh`: smoke script shell per verificare la presenza dei tool meteo di base (`arki-query`, `dballe`, `vg6d_transform`, `v7d_transform`, `dbadb`).

### 2. Helper riusabili

I moduli sotto `helpers/` non sono test. Contengono solo setup, polling, builder di payload, assertion specializzate, factory di utenti e infrastruttura che servono davvero a piu aree.

Quando builder, parser, seed o assert servono solo a un dominio, vivono invece in moduli locali importabili sotto `integration/<area>/`, per esempio `integration/observed/support.py` o `integration/postprocessing/support.py`.

### 3. Domini di integrazione

Ogni cartella sotto `integration/` raggruppa un contratto funzionale:

- `access_key`: ciclo di vita e validazione delle API key.
- `arco`: proxy e catalogo ARCO.
- `data`: autorizzazione dell'endpoint dati.
- `data_ready`: trigger `/data/ready` e interazione con le schedule.
- `dataset`: visibilita e autorizzazione dei dataset.
- `observed`: query osservate, filtri e dettagli stazione.
- `opendata`: listing, download e autorizzazioni sui package opendata.
- `postprocessing`: esecuzione dei postprocessor forecast e observed.
- `requests`: cancellazione di richieste pendenti e cleanup automatico.
- `schedules`: bridge tra schedule on-data-ready e pubblicazione opendata.

## Come lanciare i test

Esempi pratici consigliati:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/access_key/test_access_key_api.py'
```

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/observed/test_observations_filters.py'
```

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/observed'
```

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom'
```

```bash
.mhub-venv/bin/rapydo shell backend 'pytest tests/custom -m "integration and not async_real" -q -rs'
```

```bash
.mhub-venv/bin/rapydo shell backend 'pytest tests/custom -m "async_real" -q -rs'
```

Regola pratica:

- partire sempre dal file o dal dominio toccato;
- allargare a una cartella solo se il cambiamento tocca fixture o helper condivisi;
- evitare regressioni larghe quando esiste una verifica piu stretta.

## Come aggiungere nuovi test senza rompere la struttura

Linee guida operative:

1. Se una fixture serve a tutta la suite, mettila in `tests/conftest.py`.
2. Se una fixture serve a piu domini di integrazione ma non alla suite intera, mettila in `tests/integration/conftest.py`.
3. Se una fixture serve a un solo dominio, mettila nel `conftest.py` del dominio.
4. Se una logica e riusabile ma non e una fixture, mettila in `helpers/` solo se serve a piu aree; se resta di un solo dominio, mettila in `integration/<area>/support.py` o in un modulo locale equivalente.
5. Non reintrodurre moduli root `test_*.py`: i nuovi test vanno direttamente sotto `integration/<area>/`.
6. Mantieni i test in forma `arrange / act / assert`.
7. Per attese asincrone usa `helpers/polling.py`, non `sleep` sparsi.
8. Per setup o cleanup di oggetti creati al volo usa `cleanup_registry` o helper dedicati.

## Mappa file per file

### Root della suite

- `README.md`: manuale pratico della suite custom backend.
- `docs/`: documentazione mantenuta della suite.
- `__init__.py`: marca la cartella come package Python della suite custom.
- `conftest.py`: definisce le fixture globali e registra il marker `integration`.
- `helpers/`: infrastruttura e helper condivisi tra domini.
- `integration/`: test reali organizzati per dominio funzionale.
- `test_arpaesimc.sh`: smoke script shell per i tool meteo di base.

### Helpers condivisi

- `helpers/__init__.py`: marca la cartella dei helper riusabili.
- `helpers/auth.py`: crea utenti temporanei autenticati, compone header auth e centralizza il cleanup condiviso degli utenti di test.
- `helpers/celery_fakes.py`: espone finti wrapper Celery per tenere alcuni test completamente locali o inline senza dipendere dal broker reale.
- `helpers/cleanup.py`: implementa il registro di cleanup LIFO per callback e percorsi filesystem.
- `helpers/data_ready.py`: contiene l'infrastruttura condivisa del cluster `data_ready/schedules`, inclusi helper per utenti dedicati, payload `/data/ready`, creazione schedule, polling delle richieste schedule e cleanup collegati.
- `helpers/datasets.py`: aiuta i test che hanno bisogno di trovare un dataset pubblico realmente disponibile nel runtime corrente.
- `helpers/dataset_window.py`: legge `/fields` e normalizza finestra temporale e filtri run di un dataset.
- `helpers/polling.py`: utility generica `wait_until` per attese osservabili.
- `helpers/runtime.py`: contiene `TestRuntime`, cioe il runtime condiviso di sessione per cache e override temporanei.
- `helpers/schedules.py`: costruisce payload JSON per schedule on-data-ready, crontab e periodiche condivisi tra `integration/data_ready/` e `integration/schedules/`.

### Template di riferimento

- `helpers/templates/endpoint_template.py`: file guida non collezionato da pytest che mostra la forma canonica di un modulo di test Meteo-Hub.

### Integrazione condivisa

- `integration/conftest.py`: fixture condivise dai test HTTP integrati, oggi limitate a autenticazione base e creazione della access key standard.

### Dominio `access_key`

- `integration/access_key/conftest.py`: fixture usate solo dai test access key, come la chiave con scadenza esplicita.
- `integration/access_key/support.py`: centralizza gli endpoint access key usati dai test e dalle fixture locali.
- `integration/access_key/test_access_key_api.py`: testa il ciclo di vita della access key, inclusi recupero, rigenerazione, chiave senza scadenza e chiave scaduta.
- `integration/access_key/test_access_key_validation.py`: testa l'endpoint di validazione della access key con credenziali mancanti, email errata, chiave errata e casi validi.

### Dominio `arco`

- `integration/arco/test_arco_catalog.py`: verifica il comportamento del catalogo ARCO.
- `integration/arco/test_arco_proxy.py`: verifica il proxy ARCO e le sue risposte integrate.

### Dominio `data`

- `integration/data/test_data_endpoint_auth.py`: verifica regole di autenticazione e autorizzazione sull'endpoint dati.

### Dominio `data_ready`

- `integration/data_ready/conftest.py`: prepara fixture locali per data-ready, inclusi override dei dataset abilitati, base test, header admin, accesso al DB e utente dedicato.
- `integration/data_ready/test_base_cases.py`: copre accettazione base di `/data/ready`, dataset non abilitati e schedule da ignorare per flag o inattivita.
- `integration/data_ready/test_crontab.py`: verifica che una schedule on-data-ready non parta quando il crontab non combacia.
- `integration/data_ready/test_periodic.py`: verifica la logica periodica, cioe quando una nuova richiesta deve o non deve essere rigenerata in base al tempo trascorso.
- `integration/data_ready/test_run_mismatch.py`: verifica che modello e run-hour non coerenti non attivino la schedule.

### Dominio `dataset`

- `integration/dataset/support.py`: tiene helper locali del dominio dataset per scegliere in modo robusto un dataset pubblico realmente disponibile nel runtime corrente.
- `integration/dataset/test_dataset_authorization.py`: verifica quali dataset sono accessibili in base ai permessi utente.
- `integration/dataset/test_dataset_visibility.py`: verifica la visibilita dei dataset nelle diverse condizioni di esposizione.

### Dominio `observed`

- `integration/observed/conftest.py`: crea scenari osservati validi per `dballe`, `arkimet` e `mixed`, applicando anche eventuali override a `BeDballe.LASTDAYS`.
- `integration/observed/support.py`: scopre parametri validi dal backend osservato corrente, costruisce endpoint e query, espone i casi parametrizzati condivisi e le utility di parsing stazione/prodotti.
- `integration/observed/test_observations_auth.py`: verifica gli errori di validazione base quando mancano porzioni obbligatorie della query osservata.
- `integration/observed/test_observations_filters.py`: verifica filtri per reftime, network, bounding box, product e combinazioni di filtri sui tre backend osservati.
- `integration/observed/test_observations_station_details.py`: verifica `onlyStations`, `stationDetails`, coordinate richieste e casi con network non valido.

### Dominio `opendata`

- `integration/opendata/support.py`: semina dataset, utenti, record di richiesta e file opendata fittizi, oltre ai piccoli builder di scenario riusati tra authorization, listing e download.
- `integration/opendata/test_authorization.py`: verifica accesso negato o consentito ai package opendata di dataset privati.
- `integration/opendata/test_download.py`: verifica download dataset, validazione di query `reftime` e `run`, zip multiple, file singolo e file mancanti.
- `integration/opendata/test_listing_filters.py`: verifica il listing dei package opendata con filtri `run` e `reftime`.

### Dominio `postprocessing`

- `integration/postprocessing/conftest.py`: crea gli ambienti forecast e observed per i test di postprocessing.
- `integration/postprocessing/support.py`: espone ambienti di test forecast/observed, builder dei postprocessor, helper per template e assert specialistici su output GRIB/JSON/BUFR.
- `integration/postprocessing/test_error_handling.py`: verifica i fallimenti attesi per postprocessor sconosciuti o input incompleti.
- `integration/postprocessing/test_forecast_basic.py`: verifica estrazione forecast semplice, derived variables e statistic elaboration.
- `integration/postprocessing/test_forecast_chaining.py`: verifica concatenazioni di piu postprocessor forecast e output JSON dopo spare point.
- `integration/postprocessing/test_forecast_spatial.py`: verifica interpolazione, cropping, uso di template e output BUFR per spare point.
- `integration/postprocessing/test_observed_postprocessing.py`: verifica estrazione observed semplice e chaining observed con output JSON.

### Dominio `requests`

- `integration/requests/conftest.py`: tiene solo le fixture locali per le richieste pending.
- `integration/requests/support.py`: contiene i seed helper locali del dominio requests senza promuoverli a helper globali.
- `integration/requests/test_delete_pending_request.py`: verifica la cancellazione manuale delle richieste in base al grace period e il comportamento del task `automatic_cleanup`.

### Dominio `schedules`

- `integration/schedules/conftest.py`: prepara fixture locali per i test schedule che fanno ponte con il data-ready e l'opendata.
- `integration/schedules/test_schedule_opendata_bridge.py`: verifica il flusso completo in cui una schedule on-data-ready genera una richiesta, pubblica un package opendata e rende quel file scaricabile.

## In sintesi

La modularizzazione nuova separa in modo netto:

- infrastruttura globale di suite;
- helper riusabili;
- test veri, organizzati per dominio.

La regola chiave da ricordare e questa: in pytest la posizione del `conftest.py` decide chi vede una fixture. In questa suite, quindi, il punto di divisione corretto e `root` contro `integration`, non `root` contro un singolo dominio.

## Documentazione mantenuta della suite

Per il lavoro quotidiano usa solo questi file:

- `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
- `projects/mistral/backend/tests/README.md`
- `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`
- `projects/mistral/backend/tests/docs/piano_refactoring_suite_test.md`

Non ci sono piu riferimenti operativi mantenuti verso altre cartelle `docs/` del repository per capire lo stato corrente della suite backend.