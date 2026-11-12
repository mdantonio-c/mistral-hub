# Review — `opendata/support.py` (infrastruttura di dominio opendata)

> File di review per modulo di supporto. Non contiene test. Struttura **ADATTATA** (niente sezioni "Call chain" o "Analisi per test").
> A differenza di un `support.py` di sole costanti, questo modulo è **attivo**: scrive righe reali su DB e **file reali su disco**.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/integration/opendata/support.py`
- **Scopo**: centralizzare il seeding dello scenario opendata usato dai tre file di test del dominio:
  - dataset temporanei pubblici o privati creati dall'helper condiviso `tests/helpers/datasets.py`;
  - utenti temporanei autenticati;
  - righe `Request` opendata sintetiche (`status="SUCCESS"`, `opendata=True`) con il relativo `FileOutput`;
  - **file scaricabili reali** scritti in `OPENDATA_DIR` (`/opendata`);
  - i cleanup associati e le utility di asserzione (`zip_filenames`).
- **Tipologia**: modulo di supporto **attivo** (DB + filesystem reali, **nessun mock**).
- **Nota trasversale**: l'intero dominio opendata resta marcato `runtime_sensitive` per DB e filesystem reali, ma il setup non contiene più alcun `pytest.skip`.

## 2. Backend realmente esercitato

Il modulo non passa quasi mai dagli endpoint HTTP: costruisce lo stato **direttamente** sui modelli SQLAlchemy e sul filesystem (eccetto la creazione utente, che usa l'API admin tramite gli helper condivisi).

| Elemento backend | Path | Come viene esercitato |
|---|---|---|
| `db.Attribution` | `projects/mistral/backend/models/sqlalchemy.py` | **Creato** per ogni dataset dall'helper condiviso, senza dipendere dal catalogo runtime. |
| `db.GroupLicense` / `db.License` | `projects/mistral/backend/models/sqlalchemy.py` | **Creati** dall'helper condiviso; `is_public` decide pubblico/privato. |
| `db.Datasets` | `projects/mistral/backend/models/sqlalchemy.py` | **Creato** dall'helper condiviso con nome/`arkimet_id` univoci, categoria OBS e formato BUFR. |
| `db.Request` | `projects/mistral/backend/models/sqlalchemy.py` | **Creato** come riga opendata sintetica; `args` (JSONB) prodotto da `_build_opendata_args`. |
| `db.FileOutput` | `projects/mistral/backend/models/sqlalchemy.py` | **Creato** e collegato alla `Request`; `filename` unique. |
| associazione m2m `user.datasets` | `projects/mistral/backend/models/sqlalchemy.py` | **Scritta** in `authorize_user_for_dataset` (append + commit). |
| `OPENDATA_DIR` (`/opendata`) | `projects/mistral/backend/endpoints/__init__.py` | **Scrittura/cancellazione file reali** (`.grib` di testo). |
| `DatasetCategories.OBS` | `projects/mistral/backend/models/sqlalchemy.py` | Enum reale usato come `category`. |
| `create_authenticated_test_user` / `register_test_user_cleanup` | `projects/mistral/backend/tests/helpers/auth.py` | Creazione utente via **API admin** + login reale; teardown FS + utente. |

## 3. Elementi definiti

| Nome | Tipo | Ruolo / effetti |
|---|---|---|
| `OpendataSeedSpec` | dataclass (frozen) | Descrizione dichiarativa di un pacchetto opendata da seminare: `reftime`, `content`, `run`, `archived`, `submission_date`. |
| `FakeOpendataResult` | dataclass (frozen) | Metadati della riga/file seminati: `request_id`, `filename`, `content`, `reftime`, `run`. |
| `create_opendata_user` | helper | Crea utente autenticato con permessi opendata (`open_dataset=True`, quote, `datasets=[...]`, opz. `allowed_schedule`). **Non** crea cleanup. |
| `register_user_cleanup` | helper | Registra cleanup FS (`output_dir.parent`) + delete utente via API admin. |
| `create_test_dataset` | helper condiviso importato | Crea `Attribution`+`GroupLicense`+`License`+`Datasets` isolati e registra il teardown completo; non può saltare per dati runtime mancanti. |
| `authorize_user_for_dataset` | helper | Collega (m2m) un utente esistente a un dataset esistente (idempotente). |
| `create_fake_opendata_result` | helper | Crea `Request`+`FileOutput` + **file reale** su `/opendata`; registra 2 cleanup (riga + file). |
| `seed_opendata_results` | helper | Applica `create_fake_opendata_result` a una sequenza di `OpendataSeedSpec`. |
| `create_private_opendata_env` | env builder | Dataset **privato** + utente (non autorizzato) + 1 risultato (`run="00:00"`). Ritorna `(db, dataset, user, result)`. |
| `create_listing_env` | env builder | Dataset **pubblico** + 2 risultati (run 00:00 / 12:00, reftime 1 gen / 2 gen). Ritorna `(dataset, seeded_results)`. |
| `create_download_env` | env builder | Dataset **pubblico** + 3 risultati (01/01@00:00, 01/01@12:00, 02/01@00:00). Ritorna `(dataset, seeded_results)`. |
| `zip_filenames` | utility | Estrae e ordina i nomi file contenuti nello zip di risposta. |
| `_build_opendata_args` | privato | Costruisce il JSONB `Request.args`: `{filters, reftime{from,to}, datasets}`. |
| `_build_run_filter` | privato | Converte `"HH:MM"` nella struttura `MINUTE` con `value` **intero** (minuti totali). |
| `_delete_request_row` / `_delete_file` | privati | Cleanup difensivi; verificano rispettivamente che la request e il file su disco non esistano più. Il bundle dataset è rimosso dall'helper condiviso. |

## 4. Comportamenti nascosti

- **Nessuno skip per catalogo incompleto**: `create_test_dataset` proviene da `tests/helpers/datasets.py` e crea anche una `Attribution` sintetica. Tutti i test opendata vengono quindi raccolti ed eseguiti anche con catalogo runtime vuoto.
- **Side effect su filesystem reale, con teardown verificato**: `create_fake_opendata_result` scrive `OPENDATA_DIR/<uuid>.grib` con `write_text(...)` e registra subito `_delete_file`, prima di creare il `FileOutput`. Il callback esegue `unlink` e asserisce `not path.exists()`, quindi un residuo rende visibile l'errore di teardown.
- **Registrazione immediata delle risorse**: il cleanup della `Request` viene registrato subito dopo il relativo commit e quello del file subito dopo la scrittura. Un errore nelle fasi successive del setup non lascia queste risorse prive di callback.
- **Accoppiamento JSONB ↔ endpoint**: il matching avviene via `db.Request.args.contains(query)` (containment JSONB). La forma prodotta da `_build_opendata_args`/`_build_run_filter` deve combaciare con la query costruita dall'endpoint, altrimenti il filtro non aggancia nulla. In particolare il formato reftime salvato è `"%Y-%m-%dT%H:%M:%S.%fZ"`, identico a quanto l'endpoint riparserà.
- **Dipendenza reale da `BeArkimet.decode_run`**: nel listing il `run` viene **decodificato** (`projects/mistral/backend/services/arkimet.py`); pretende `style="MINUTE"` e `value` **intero**. `_build_run_filter` fornisce proprio `value` intero: se cambiasse forma, il listing run-filtrato darebbe `500` invece del risultato atteso.
- **Permessi ≠ autorizzazione m2m**: `create_opendata_user` imposta il permesso `open_dataset` e una lista `datasets` (vuota negli env attuali), ma l'autorizzazione effettiva sui dataset privati passa dalla relazione m2m `user.datasets`, popolata solo da `authorize_user_for_dataset`. Se il permesso `datasets` popoli o meno la m2m alla creazione **non è verificabile da questo modulo**.
- **Capacità latenti non usate**: i parametri `dataset_ids` e `allow_schedule` di `create_opendata_user`, e i campi `archived`/`submission_date` di `OpendataSeedSpec`, non sono esercitati dagli env builder attuali (tutti seminano `archived=False`).
- **Cleanup LIFO con dipendenze rispettate**: le response streamate vengono chiuse prima dei file, poi spariscono `Request`/`FileOutput`, utenti e infine il bundle dataset completo (inclusa l'attribution) tramite l'helper condiviso.
- **`register_user_cleanup` cancella l'albero utente**: usa `user.output_dir.parent` come `root_path`, cioè `DOWNLOAD_DIR/<uuid>` (non solo `outputs`).
- **Nessuna fixture**: il modulo non dichiara fixture; i tre moduli di test chiamano esplicitamente gli env builder e gli helper.
- **Percorso comune ai tre moduli del dominio** (`test_authorization.py`, `test_download.py`, `test_listing_filters.py`, tutti con marker `integration`/`deterministic`/`runtime_sensitive`): SQL e filesystem reali con contenuti testuali controllati, **nessuna estrazione meteorologica**. Sorgenti: `OpendataFileList`, `OpendataDownload`, `OpendataDownloadFile` in `projects/mistral/backend/endpoints/opendata.py` e `SqlApiDbManager.check_dataset_authorization` in `projects/mistral/backend/services/sqlapi_db_manager.py`.
  - Listing: dataset assente → `self.response(code=404)`, privato non autorizzato → `self.response(code=401)`; filtro run via containment JSONB e `BeArkimet.decode_run`, reftime filtrato in Python; nessun match → `200` con lista vuota.
  - Download per dataset: `OpenDataDownloadQuery` valida `reftime`/`run` **prima** del lookup del dataset; poi `NotFound` per dataset assente, autorizzazione, filtro `archived.is_(False)` e reftime per uguaglianza di data. Zero file → 404 "No opendata found"; un file → `send_from_directory` (404 se il file fisico manca); più file → ZIP in memoria (`ZIP_DEFLATED`, file fisici mancanti saltati con `log.warning`) chiamato `opendata_<id>[_reftime_<x>][_run_<y>].zip`.
  - Download per filename: `FileOutput` assente → 404; `Request` collegata assente → `ServerError`; autorizzazione verificata per ogni dataset della `Request`; file fisico assente → 404.
  - **Proprietà della request ≠ grant**: in `create_private_opendata_env` l'utente è il proprietario della `Request` seminata ma riceve comunque 401 finché non esiste la relazione m2m con il dataset privato.
- **File sintetici, non GRIB**: il `.grib` contiene il testo di `content`; nessun test può dimostrare la validità del formato. `zip_filenames` restituisce solo i nomi ordinati dei membri, senza confrontarne il contenuto.
- **Cleanup mirati, mai la root**: `_delete_request_row` cancella la `Request` e il `FileOutput` sparisce per la relazione `cascade="delete"`; `_delete_file` scollega solo il file UUID. I file stanno nella root applicativa reale `OPENDATA_DIR`, non in `tmp_path`: non registrare mai la root intera nel cleanup.

## 5. Checklist di revisione

- [x] Eliminata la precondizione di skip creando un'attribution sintetica per ogni dataset.
- [x] Verificata la rimozione dei file reali in `OPENDATA_DIR` con asserzione nel callback e run completa del dominio.
- [ ] Verificare l'allineamento JSONB `_build_opendata_args`/`_build_run_filter` ↔ query degli endpoint (containment) dopo eventuali refactor dell'endpoint.
- [ ] Confermare che `value` resti intero per `decode_run` (rischio `500` nel listing run-filtrato).
- [ ] Valutare se la distinzione permesso `open_dataset`/lista `datasets` vs m2m `user.datasets` debba essere documentata o coperta.
- [x] Il teardown condiviso stacca la m2m e verifica la cancellazione di dataset, license, group license e attribution.

## 6. Possibili criticità

- **Effetti collaterali su `/opendata` condiviso**: scritture/cancellazioni restano reali; un arresto forzato del processo può impedire qualsiasi teardown pytest, mentre il normale percorso di fixture è ora auto-verificante.
- **Forte coupling sulla forma JSONB**: la correttezza dei test di filtro dipende interamente dall'aderenza tra seed e query dell'endpoint; un cambio di formato lato endpoint romperebbe i test in modo non ovvio (match vuoto → 404/lista vuota "plausibili").
- **Dipendenza non mockata da arkimet** (`decode_run`) nel listing run-filtrato: introduce un punto di rottura esterno rispetto al puro contratto HTTP.
- **Comportamenti latenti non testati** (`archived=True`, `dataset_ids`, `allow_schedule`): l'asimmetria download (`archived.is_(False)`) vs listing (nessun filtro archived) non è coperta da alcuno scenario.
