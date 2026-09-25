# Review — `test_download.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Dominio **opendata** marcato `runtime_sensitive`: tutti i **12 test** sono eseguiti senza skip dipendenti dal catalogo runtime.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/opendata/test_download.py](projects/mistral/backend/tests/integration/opendata/test_download.py)
- **Scopo**: verificare i due endpoint di download opendata: download per dataset (`/opendata/<id>/download`, con validazione `reftime`/`run`, filtri, zip multiplo vs file singolo, `404` vari) e download diretto del file (`/opendata/<filename>`).
- **Tipologia**: integrazione HTTP reale (controller + schema marshmallow + DB SQLAlchemy + **file reali** su `/opendata` + `zipfile` in memoria). Marker: `integration`, `deterministic`, `runtime_sensitive`. Nessun mock.
- **Endpoint coperti**: `OpendataDownload.get` e `OpendataDownloadFile.get`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `OpendataDownload.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L282) | Validazione query → dataset lookup (`NotFound` 404) → auth → query `args.contains` + `opendata.is_(True)` + `archived.is_(False)` → filtro reftime (**uguaglianza di data**) → `0`=404 / `1`=file diretto / `>1`=zip. |
| `OpenDataDownloadQuery` + `Reftime` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L229) | `Reftime` accetta `YYYYMMDD` o `YYYY-mm-dd` (altrimenti `ValidationError` → `reftime`); `@pre_load validate_run` esige `HH:MM` (altrimenti errore sotto `_schema`). |
| `OpendataDownloadFile.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L203) | `FileOutput` per nome → `NotFound` 404 se assente. |
| `check_dataset_authorization` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L562) | Su dataset pubblici dei test ritorna sempre `True` (non è il focus qui). |
| `db.Request` / `db.FileOutput` (JSONB) | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Righe opendata sintetiche; `args.contains(...)` per il match dei filtri. |
| `OPENDATA_DIR` (`/opendata`) | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py#L5) | File reali letti da `send_from_directory` / impacchettati nello zip. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient`; chiamate **anonime** (dataset pubblici). |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO** (righe DB + file su disco); nei quattro happy path viene eseguito esplicitamente prima della fine del test. |
| `create_test_dataset` | helper condiviso | [tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py) | Dataset pubblico isolato **senza** opendata, con attribution sintetica e teardown verificato. |
| `create_download_env` | helper locale | [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) | Dataset pubblico isolato + **3** file opendata reali (01/01@00:00, 01/01@12:00, 02/01@00:00); nessuna precondizione di skip. |
| `zip_filenames` | helper locale | [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) | Estrae/ordina i nomi nello zip di risposta. |
| `_run_teardown_and_assert_seeded_files_removed` | helper locale | `test_download.py` | Deriva i path da `OPENDATA_DIR`, verifica che tutti i seed esistano, esegue `cleanup_registry.run()` e asserisce che nessun path sopravviva. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Istanza DB usata solo dal test del dataset esistente senza opendata. |
| `BaseTests().get_content` | helper | `restapi.tests` | Decodifica body JSON (rami `400`/`404`). |
| `uuid4` | stdlib | — | Id dataset/file inesistenti. |

> Infrastruttura condivisa (non ridocumentata): `cleanup_registry` da [tests/conftest.py](projects/mistral/backend/tests/conftest.py); seeding da [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) e [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py). Cartella `runtime_sensitive`.

## 4. Analisi dettagliata di ogni test

### `test_dataset_download_unknown_dataset_returns_404`
- **Obiettivo**: download da `arkimet_id` inesistente → `404`.
- **Backend coinvolto**: `OpendataDownload.get`, ramo `if not ds_entry: raise NotFound`.
- **Flusso**: id `missing_<uuid>` → GET.
- **Setup**: nessuno. **Non usa `cleanup_registry`**.
- **Assert**: `status_code == 404`.
- **Casi coperti**: error path. **Mai skippato**.

### `test_dataset_download_rejects_invalid_reftime`
- **Obiettivo**: `reftime` non valida → `400` con chiave `reftime`.
- **Backend coinvolto**: `Reftime._deserialize` (`ValidationError`), **prima** del lookup dataset.
- **Flusso**: id dataset casuale non persistito → GET `?reftime=2020/31/01`; lo schema risponde prima del lookup.
- **Setup**: nessun record DB e nessun `cleanup_registry`.
- **Assert**: `400`; `content["reftime"]` truthy.
- **Casi coperti**: validation path su reftime, sempre eseguito.

### `test_dataset_download_rejects_invalid_run`
- **Obiettivo**: `run` non valida → `400` con messaggio sotto `_schema`.
- **Backend coinvolto**: `@pre_load validate_run` (`ValidationError`), prima del lookup dataset.
- **Flusso**: id dataset casuale non persistito → GET `?run=2500`; lo schema risponde prima del lookup.
- **Setup**: nessun record DB e nessun `cleanup_registry`.
- **Assert**: `400`; `"run format not supported" in content["_schema"][0]`.
- **Casi coperti**: validation path su run, sempre eseguito.

### `test_dataset_download_returns_404_when_no_opendata_exist`
- **Obiettivo**: dataset pubblico **senza** opendata → `404` (non un archivio vuoto).
- **Backend coinvolto**: query vuota → `filenames` vuoto → `NotFound("No opendata found...")`.
- **Flusso**: `create_test_dataset(is_public=True)` condiviso (nessun seed) → GET download.
- **Setup**: `cleanup_registry`.
- **Assert**: `404`; `"No opendata found" in content`.
- **Casi coperti**: edge case "dataset esiste ma nessun file"; nessuno skip.

### `test_dataset_download_returns_404_for_unmatched_reftime`
- **Obiettivo**: filtro reftime senza match → `404`.
- **Backend coinvolto**: filtro per **uguaglianza di data** (`reftime_from == reftime and reftime_to == reftime`).
- **Flusso**: `create_download_env` (seed 01/01 e 02/01) → GET `?reftime=20200103`.
- **Setup**: `cleanup_registry`; 3 file reali.
- **Assert**: `404`.
- **Casi coperti**: error path reftime non corrispondente.

### `test_dataset_download_returns_404_for_unmatched_run`
- **Obiettivo**: filtro run senza match → `404`.
- **Backend coinvolto**: `query["filters"]={"run":[{"desc":"MINUTE(15:00)"}]}` → containment JSONB senza match.
- **Flusso**: `create_download_env` (run 00:00/12:00/00:00) → GET `?run=15:00`.
- **Setup**: `cleanup_registry`; 3 file reali.
- **Assert**: `404`.
- **Casi coperti**: error path run non corrispondente.

### `test_dataset_download_returns_404_for_unmatched_reftime_and_run`
- **Obiettivo**: filtri **combinati** senza match → `404`.
- **Backend coinvolto**: run MINUTE(12:00) aggancia seed[1] (01/01@12:00), poi reftime `2020-01-02` lo esclude (data diversa).
- **Flusso**: `create_download_env` → GET `?reftime=2020-01-02&run=12:00`.
- **Setup**: `cleanup_registry`; 3 file reali.
- **Assert**: `404`.
- **Casi coperti**: edge case combinato (run match + reftime no-match → vuoto → 404).

### `test_dataset_download_zips_all_results`
- **Obiettivo**: nessun filtro → **tutti** i file in uno zip.
- **Backend coinvolto**: ramo `len>1` → `zipfile` in memoria → `send_file(mimetype="application/zip")`.
- **Flusso**: `create_download_env` → GET download (senza query).
- **Setup**: `cleanup_registry`; 3 file reali; `response.close` registrata dopo la GET e quindi eseguita prima della rimozione LIFO dei file.
- **Assert**: `200`; `mimetype == "application/zip"`; nome `opendata_<id>.zip`; `zip_filenames(response)` == ordinati dei 3 filename seminati; tutti i path esistono prima del teardown e nessuno esiste dopo.
- **Casi coperti**: happy path zip completo + nome archivio + cancellazione esplicita dei tre file.

### `test_dataset_download_zips_results_filtered_by_reftime`
- **Obiettivo**: filtro reftime → zip ristretto ai soli match.
- **Backend coinvolto**: filtro per data; ramo `len>1` (2 file).
- **Flusso**: `create_download_env` → GET `?reftime=2020-01-01` (match seed[0] e seed[1]).
- **Setup**: `cleanup_registry`; 3 file reali; chiusura response anteposta al cleanup dei file.
- **Assert**: `200`; `application/zip`; nome `opendata_<id>_reftime_2020-01-01.zip`; contenuto == ordinati di `seeded_results[:2]`; tutti e tre i file seedati vengono verificati assenti dopo il teardown.
- **Casi coperti**: happy path zip filtrato per reftime + nome con suffisso + cancellazione esplicita di file inclusi e non inclusi nello zip.

### `test_dataset_download_zips_results_filtered_by_run`
- **Obiettivo**: filtro run → zip ristretto ai soli match.
- **Backend coinvolto**: containment run MINUTE(00:00) (match seed[0] e seed[2]); ramo `len>1`.
- **Flusso**: `create_download_env` → GET `?run=00:00`.
- **Setup**: `cleanup_registry`; 3 file reali; chiusura response anteposta al cleanup dei file.
- **Assert**: `200`; `application/zip`; nome `opendata_<id>_run_00:00.zip`; contenuto == ordinati di `(seeded_results[0], seeded_results[2])`; tutti e tre i file seedati vengono verificati assenti dopo il teardown.
- **Casi coperti**: happy path zip filtrato per run + cancellazione esplicita di file inclusi e non inclusi nello zip.

### `test_dataset_download_returns_single_file_when_query_matches_one_result`
- **Obiettivo**: un solo match → file **streamato diretto**, non zip.
- **Backend coinvolto**: ramo `len==1` → `send_from_directory(as_attachment=True)` → `application/octet-stream`.
- **Flusso**: `create_download_env` → GET `?reftime=20200101&run=12:00` (solo seed[1]).
- **Setup**: `cleanup_registry`; 3 file reali; chiusura dello stream registrata prima del teardown dei file.
- **Assert**: `200`; `mimetype == "application/octet-stream"`; body == `seeded_results[1].content`; tutti e tre i file seedati vengono verificati assenti dopo il teardown.
- **Casi coperti**: branch a singolo file (octet-stream) vs zip; rilettura del file selezionato e cancellazione esplicita dell'intero seed.

### `test_file_download_unknown_file_returns_404`
- **Obiettivo**: download diretto di un filename inesistente → `404`.
- **Backend coinvolto**: `OpendataDownloadFile.get`, ramo `if not fileoutput_entry: raise NotFound`.
- **Flusso**: GET `/opendata/<uuid>.grib`.
- **Setup**: nessuno. **Non usa `cleanup_registry`**.
- **Assert**: `status_code == 404`.
- **Casi coperti**: error path. **Mai skippato**.

## 5. Call chain

```
GET /opendata/<id>/download?reftime=&run=
  → auth.optional → use_kwargs(OpenDataDownloadQuery)
       reftime non YYYYMMDD/YYYY-mm-dd → ValidationError → 400 {"reftime":[...]}
       run non HH:MM (pre_load)        → ValidationError → 400 {"_schema":["run format not supported..."]}
  → OpendataDownload.get
       Datasets.filter_by(arkimet_id).first → None? NotFound 404
       GroupLicense.is_public? no → check_dataset_authorization → eventuale Unauthorized 401
       query = {datasets:[id], (run? filters:{run:[{desc:MINUTE(run)}]})}
       Request.filter(args.contains(query), opendata.is_(True), archived.is_(False))
       for r: reftime? (reftime_from==reftime==reftime_to) → append fileoutput.filename ; else append
       len==0 → NotFound("No opendata found...") 404
       len==1 → file esiste? send_from_directory (octet-stream)  : NotFound 404
       len>1  → zipfile in memoria → send_file(application/zip, name opendata_<id>[_reftime_x][_run_y].zip)

GET /opendata/<filename>
  → auth.optional → OpendataDownloadFile.get
       FileOutput.filter_by(filename).first → None? NotFound 404
       Request.get → None? ServerError ; for d in datasets: check_dataset_authorization → Unauthorized 401
       file esiste? send_from_directory(as_attachment=True) : NotFound 404

quattro happy path download
     → calcola OPENDATA_DIR/<seed.filename> per tutti i 3 seed
     → assert: tutti sono file reali prima del teardown
     → cleanup_registry.run() LIFO
                response.close → unlink file (+ assert interno) → delete Request/FileOutput
                → delete utente → delete dataset/license/group/attribution
     → assert: nessun path seedato esiste dopo il teardown
```

## 6. Comportamenti nascosti

- **Nessuno skip silenzioso**: il dataset helper condiviso crea attribution e licenze sintetiche; la run completa ha eseguito tutti i 12 test.
- **La validazione precede il lookup dataset**: nei due test `400` (reftime/run) l'errore arriva dallo schema marshmallow **prima** che il dataset venga interrogato; i test usano quindi un id casuale senza creare record DB.
- **Due nomi/strutture di errore diversi**: reftime invalida → `content["reftime"]`; run invalida (sollevata in `@pre_load`) → `content["_schema"][0]`.
- **Semantica reftime del download ≠ listing**: qui il filtro è **uguaglianza di data** (`reftime_from == reftime and reftime_to == reftime` su `.date()`), non una finestra; il listing usa invece una finestra `from/to`.
- **Filtro `archived.is_(False)` solo nel download**: i pacchetti archiviati sarebbero esclusi dal download ma **non** dal listing; nessun seed è `archived`, quindi il ramo non è esercitato.
- **Tre rami di output mutuamente esclusivi**: `0` → `404`; `1` → file diretto (`octet-stream`); `>1` → zip (`application/zip`). Tutti e tre coperti.
- **Nome zip costruito per concatenazione**: `opendata_<id>{_reftime_<reftime>}{_run_<run>}.zip`; i test verificano i tre formati (nessuno / solo reftime / solo run).
- **File reali e doppia verifica del teardown**: zip e file singolo leggono davvero da `/opendata`. Nei quattro happy path il test verifica prima che tutti i path siano file, esegue esplicitamente il registry e verifica poi che non esistano; inoltre `_delete_file` esegue `unlink` e contiene un proprio assert. La response viene chiusa per prima grazie all'ordine LIFO. Il ramo che salta file mancanti nello zip (`log.warning ... continue`) non è esercitato.
- **Registry eseguito nel corpo dei quattro test**: dopo `cleanup_registry.run()` la lista dei callback è vuota; il teardown automatico della fixture lo richiama senza ripetere operazioni. Se un assert HTTP precedente fallisce, resta comunque attivo il normale teardown della fixture.
- **`reftime=20200101` vs `2020-01-01`**: entrambi i formati sono accettati da `Reftime` (test single-file usa `YYYYMMDD`, gli zip usano `YYYY-mm-dd`).

## 7. Checklist di revisione

- [x] Eliminato lo skip silenzioso usando il dataset helper condiviso con attribution sintetica.
- [x] Disaccoppiati i due test di validazione (`400` reftime/run) dal seeding DB.
- [ ] Confermare la semantica "uguaglianza di data" del filtro reftime nel download (vs finestra nel listing).
- [ ] Verificare i contratti mimetype: `application/zip` (multiplo) vs `application/octet-stream` (singolo).
- [ ] Valutare uno scenario `archived=True` per coprire il filtro `archived.is_(False)` del download.
- [x] Verificato il teardown dei file reali nei quattro happy path: esistenza prima, `cleanup_registry.run()`, assenza dopo; in aggiunta `unlink` contiene un assert interno.

## 8. Possibili criticità

- **Accoppiamento al filesystem reale**: zip e single-file dipendono dalla scrivibilità/lettura di `/opendata`; il teardown normale è verificato, ma un arresto forzato del processo può comunque impedirne l'esecuzione.
- **Coupling forte su forma JSONB**: il match dei filtri (run via containment, reftime via post-filtro) dipende dall'allineamento seed↔endpoint; un cambio lato endpoint potrebbe produrre `404`/zip "plausibili" mascherando un regresso.
- **Rami non coperti**: file mancante dentro lo zip (`continue`), `archived=True`, e (per `OpendataDownloadFile`) `ServerError` su request orfana.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture (incl. locali) | Skip silenzioso |
|---|---|---|---|---|---|
| `test_dataset_download_unknown_dataset_returns_404` | `OpendataDownload.get` (404) | `404` dataset inesistente | — | `client` | No |
| `test_dataset_download_rejects_invalid_reftime` | `Reftime._deserialize` | `400` + `reftime` | — | `client` | No |
| `test_dataset_download_rejects_invalid_run` | `pre_load validate_run` | `400` + `_schema` | — | `client` | No |
| `test_dataset_download_returns_404_when_no_opendata_exist` | query vuota | `404` "No opendata found" | — (DB+FS) | `client`, `cleanup_registry`, helper dataset condiviso | No |
| `test_dataset_download_returns_404_for_unmatched_reftime` | filtro data | `404` | — (DB+FS) | `create_download_env` | No |
| `test_dataset_download_returns_404_for_unmatched_run` | containment run | `404` | — (DB+FS) | `create_download_env` | No |
| `test_dataset_download_returns_404_for_unmatched_reftime_and_run` | run+reftime | `404` | — (DB+FS) | `create_download_env` | No |
| `test_dataset_download_zips_all_results` | ramo `len>1` zip | zip completo + nome + 3 file cancellati | — (DB+FS) | `create_download_env`, `zip_filenames`, helper teardown | No |
| `test_dataset_download_zips_results_filtered_by_reftime` | filtro data + zip | zip 2 file + nome suffix + 3 file cancellati | — (DB+FS) | `create_download_env`, `zip_filenames`, helper teardown | No |
| `test_dataset_download_zips_results_filtered_by_run` | containment run + zip | zip 2 file + nome suffix + 3 file cancellati | — (DB+FS) | `create_download_env`, `zip_filenames`, helper teardown | No |
| `test_dataset_download_returns_single_file_when_query_matches_one_result` | ramo `len==1` | file diretto `octet-stream` + 3 file cancellati | — (DB+FS) | `create_download_env`, helper teardown | No |
| `test_file_download_unknown_file_returns_404` | `OpendataDownloadFile.get` (404) | `404` file inesistente | — | `client` | No |
