# Review — `opendata/support.py` (infrastruttura di dominio opendata)

> File di review per modulo di supporto. Non contiene test. Struttura **ADATTATA** (niente sezioni "Call chain" o "Analisi per test").
> A differenza di un `support.py` di sole costanti, questo modulo è **attivo**: scrive righe reali su DB e **file reali su disco**.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py)
- **Scopo**: centralizzare il seeding dello scenario opendata usato dai tre file di test del dominio:
  - dataset temporanei (con relativi `License` + `GroupLicense`, pubblici o privati);
  - utenti temporanei autenticati;
  - righe `Request` opendata sintetiche (`status="SUCCESS"`, `opendata=True`) con il relativo `FileOutput`;
  - **file scaricabili reali** scritti in `OPENDATA_DIR` (`/opendata`);
  - i cleanup associati e le utility di asserzione (`zip_filenames`).
- **Tipologia**: modulo di supporto **attivo** (DB + filesystem reali, **nessun mock**).
- **Nota trasversale**: l'intero dominio opendata è marcato `runtime_sensitive`; l'**unico** punto di skip vive proprio qui (vedi §4).

## 2. Backend realmente esercitato

Il modulo non passa quasi mai dagli endpoint HTTP: costruisce lo stato **direttamente** sui modelli SQLAlchemy e sul filesystem (eccetto la creazione utente, che usa l'API admin tramite gli helper condivisi).

| Elemento backend | Path | Come viene esercitato |
|---|---|---|
| `db.Attribution` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L121) | **Letto** (`query.first()`); se assente → `pytest.skip` (vedi §4). |
| `db.GroupLicense` / `db.License` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L101) | **Creati** in `create_test_dataset`; `is_public` decide pubblico/privato. |
| `db.Datasets` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L146) | **Creato** con `arkimet_id == name == "<prefix>_<token>"`, `category=DatasetCategories.OBS`, `fileformat="bufr"`, `bounding=DEFAULT_BOUNDING`. |
| `db.Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | **Creato** come riga opendata sintetica; `args` (JSONB) prodotto da `_build_opendata_args`. |
| `db.FileOutput` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L59) | **Creato** e collegato alla `Request`; `filename` unique. |
| associazione m2m `user.datasets` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L139) | **Scritta** in `authorize_user_for_dataset` (append + commit). |
| `OPENDATA_DIR` (`/opendata`) | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py#L5) | **Scrittura/cancellazione file reali** (`.grib` di testo). |
| `DatasetCategories.OBS` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L132) | Enum reale usato come `category`. |
| `create_authenticated_test_user` / `register_test_user_cleanup` | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Creazione utente via **API admin** + login reale; teardown FS + utente. |

## 3. Elementi definiti

| Nome | Tipo | Ruolo / effetti |
|---|---|---|
| `DEFAULT_BOUNDING` | costante | WKT `POLYGON` usato come `bounding` di ogni dataset di test. |
| `TestDataset` | dataclass (frozen) | Espone `id` (numerico) e `arkimet_id` (stringa) del dataset creato. |
| `OpendataSeedSpec` | dataclass (frozen) | Descrizione dichiarativa di un pacchetto opendata da seminare: `reftime`, `content`, `run`, `archived`, `submission_date`. |
| `FakeOpendataResult` | dataclass (frozen) | Metadati della riga/file seminati: `request_id`, `filename`, `content`, `reftime`, `run`. |
| `create_opendata_user` | helper | Crea utente autenticato con permessi opendata (`open_dataset=True`, quote, `datasets=[...]`, opz. `allowed_schedule`). **Non** crea cleanup. |
| `register_user_cleanup` | helper | Registra cleanup FS (`output_dir.parent`) + delete utente via API admin. |
| `create_test_dataset` | helper | Crea `GroupLicense`+`License`+`Datasets` (commit) + cleanup; **`pytest.skip` se nessun `Attribution`**. |
| `authorize_user_for_dataset` | helper | Collega (m2m) un utente esistente a un dataset esistente (idempotente). |
| `create_fake_opendata_result` | helper | Crea `Request`+`FileOutput` + **file reale** su `/opendata`; registra 2 cleanup (riga + file). |
| `seed_opendata_results` | helper | Applica `create_fake_opendata_result` a una sequenza di `OpendataSeedSpec`. |
| `create_private_opendata_env` | env builder | Dataset **privato** + utente (non autorizzato) + 1 risultato (`run="00:00"`). Ritorna `(db, dataset, user, result)`. |
| `create_listing_env` | env builder | Dataset **pubblico** + 2 risultati (run 00:00 / 12:00, reftime 1 gen / 2 gen). Ritorna `(dataset, seeded_results)`. |
| `create_download_env` | env builder | Dataset **pubblico** + 3 risultati (01/01@00:00, 01/01@12:00, 02/01@00:00). Ritorna `(dataset, seeded_results)`. |
| `zip_filenames` | utility | Estrae e ordina i nomi file contenuti nello zip di risposta. |
| `_build_opendata_args` | privato | Costruisce il JSONB `Request.args`: `{filters, reftime{from,to}, datasets}`. |
| `_build_run_filter` | privato | Converte `"HH:MM"` nella struttura `MINUTE` con `value` **intero** (minuti totali). |
| `_delete_dataset_bundle` / `_delete_request_row` / `_delete_file` | privati | Cleanup difensivi (rimuovono m2m users, riga richiesta, file su disco). |

## 4. Comportamenti nascosti

- **Unico punto di `pytest.skip` dell'intero dominio**: `create_test_dataset` salta lo scenario se `db.Attribution.query.first() is None` (`"At least one attribution is required..."`). Di conseguenza **ogni** test che costruisce un dataset (direttamente o via `create_*_env`) è **silenziosamente skippabile** quando il DB di runtime non ha alcun `Attribution`. **Non** è invece legato all'esistenza di pacchetti opendata: quelli vengono sempre auto-seminati.
- **Side effect su filesystem reale**: `create_fake_opendata_result` scrive `OPENDATA_DIR/<uuid>.grib` con `write_text(...)`; i download li rileggono davvero (`send_from_directory`/zip). Il cleanup `_delete_file` li rimuove. Un teardown saltato lascia file orfani in `/opendata`.
- **Accoppiamento JSONB ↔ endpoint**: il matching avviene via `db.Request.args.contains(query)` (containment JSONB). La forma prodotta da `_build_opendata_args`/`_build_run_filter` deve combaciare con la query costruita dall'endpoint, altrimenti il filtro non aggancia nulla. In particolare il formato reftime salvato è `"%Y-%m-%dT%H:%M:%S.%fZ"`, identico a quanto l'endpoint riparserà.
- **Dipendenza reale da `BeArkimet.decode_run`**: nel listing il `run` viene **decodificato** ([services/arkimet.py](projects/mistral/backend/services/arkimet.py#L621)); pretende `style="MINUTE"` e `value` **intero**. `_build_run_filter` fornisce proprio `value` intero: se cambiasse forma, il listing run-filtrato darebbe `500` invece del risultato atteso.
- **Permessi ≠ autorizzazione m2m**: `create_opendata_user` imposta il permesso `open_dataset` e una lista `datasets` (vuota negli env attuali), ma l'autorizzazione effettiva sui dataset privati passa dalla relazione m2m `user.datasets`, popolata solo da `authorize_user_for_dataset`. Se il permesso `datasets` popoli o meno la m2m alla creazione **non è verificabile da questo modulo**.
- **Capacità latenti non usate**: i parametri `dataset_ids` e `allow_schedule` di `create_opendata_user`, e i campi `archived`/`submission_date` di `OpendataSeedSpec`, non sono esercitati dagli env builder attuali (tutti seminano `archived=False`).
- **Cleanup LIFO con rimozione m2m**: `_delete_dataset_bundle` stacca prima gli utenti dalla m2m, poi elimina dataset→license→group; il `cleanup_registry` esegue in ordine inverso di registrazione.
- **`register_user_cleanup` cancella l'albero utente**: usa `user.output_dir.parent` come `root_path`, cioè `DOWNLOAD_DIR/<uuid>` (non solo `outputs`).

## 5. Checklist di revisione

- [ ] Confermare che la precondizione di skip (almeno un `Attribution`) sia accettabile o se debba diventare un seeding esplicito per non perdere copertura silenziosamente.
- [ ] Verificare che `OPENDATA_DIR` punti a un percorso scrivibile/isolato nell'ambiente di test (i file sono reali).
- [ ] Verificare l'allineamento JSONB `_build_opendata_args`/`_build_run_filter` ↔ query degli endpoint (containment) dopo eventuali refactor dell'endpoint.
- [ ] Confermare che `value` resti intero per `decode_run` (rischio `500` nel listing run-filtrato).
- [ ] Valutare se la distinzione permesso `open_dataset`/lista `datasets` vs m2m `user.datasets` debba essere documentata o coperta.
- [ ] Verificare che `_delete_dataset_bundle` non lasci righe orfane in `auth_association`.

## 6. Possibili criticità

- **Copertura fragile per assenza di `Attribution`**: lo skip silenzioso può azzerare quasi tutta la suite opendata senza segnalazione evidente in CI (passerebbe come "verde con skip").
- **Effetti collaterali su `/opendata` condiviso**: scritture/cancellazioni reali su una directory potenzialmente condivisa con il runtime; un teardown parziale può inquinare scenari successivi o lasciare residui.
- **Forte coupling sulla forma JSONB**: la correttezza dei test di filtro dipende interamente dall'aderenza tra seed e query dell'endpoint; un cambio di formato lato endpoint romperebbe i test in modo non ovvio (match vuoto → 404/lista vuota "plausibili").
- **Dipendenza non mockata da arkimet** (`decode_run`) nel listing run-filtrato: introduce un punto di rottura esterno rispetto al puro contratto HTTP.
- **Comportamenti latenti non testati** (`archived=True`, `dataset_ids`, `allow_schedule`): l'asimmetria download (`archived.is_(False)`) vs listing (nessun filtro archived) non è coperta da alcuno scenario.
