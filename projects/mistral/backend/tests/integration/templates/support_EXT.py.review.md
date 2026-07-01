# Review — `templates/support_EXT.py` (infrastruttura di dominio, ADATTATA)

> File di review per modulo di supporto. Non contiene test e non modifica codice.
> Struttura **adattata**: descrive costanti, builder, seeding su filesystem e wiring di cleanup.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py)
- **Scopo**: centralizzare URL, creazione utenti con quota/limiti, seeding di file template sintetici e costruzione di zip shapefile in memoria per i due moduli di test del dominio templates.
- **Tipologia**: modulo di supporto locale (costanti + builder + seeding filesystem). **Non** crea fixture globali né `conftest.py` locali.
- **Usato da**: [test_templates_listing_EXT.py](projects/mistral/backend/tests/integration/templates/test_templates_listing_EXT.py) e [test_templates_upload_delete_EXT.py](projects/mistral/backend/tests/integration/templates/test_templates_upload_delete_EXT.py).

## 2. Elementi definiti

| Elemento | Tipo | Ruolo |
|---|---|---|
| `TEMPLATES_ENDPOINT_EXT` | costante | `{API_URI}/templates` (da `restapi.tests`). |
| `create_templates_user_EXT` | builder | Crea utente via API admin con `max_templates`/`disk_quota` espliciti; registra cleanup. |
| `uploads_root_EXT` | helper path | `DATA_PATH/<uuid>/uploads`. |
| `template_folder_EXT` | helper path | `DATA_PATH/<uuid>/uploads/<grib|shp>`. |
| `seed_template_file_EXT` | seeding FS | Scrive un file sintetico nella cartella dedotta dall'estensione; registra `uploads`. |
| `seed_shapefile_sidecars_EXT` | seeding FS | Crea `.shp/.shx/.dbf/.prj` con stesso stem in `uploads/shp`. |
| `build_shapefile_zip_EXT` | builder | Zip **in memoria** con `.shp` + opzionali `.shx`/`.dbf`. |
| `upload_payload_EXT` | builder | Payload multipart `{"file": (stream, filename)}`. |
| `listed_filenames_EXT` | helper | Estrae i soli `name` dai `Path` serializzati come stringhe assolute. |

- Import chiave: `DOWNLOAD_DIR` da [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py) (`Path("/data")`), `DATA_PATH` da `restapi.config`, e gli helper di auth da [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py).

## 3. Builder e seeding: dettaglio

### `create_templates_user_EXT(client, cleanup_registry, *, max_templates=5, disk_quota=1073741824)`
- Imposta `permissions = {disk_quota, max_output_size=disk_quota, max_templates, open_dataset=True}` e crea l'utente via `create_authenticated_test_user` (canale **API admin** reale).
- Registra `register_test_user_cleanup` con `root_path = Path(DOWNLOAD_DIR, user.uuid)` ⇒ cancellazione utente (admin) + rimozione ricorsiva di `/data/<uuid>`.
- **Non** scrive direttamente nel DB: i valori `max_templates`/`disk_quota` dipendono da come l'admin customizer li applica.

### `seed_template_file_EXT(cleanup_registry, user, filename, *, content=b"...")`
- Deduce il sottofolder dall'estensione: `.grib` → `uploads/grib`, **qualsiasi altra** → `uploads/shp`.
- `mkdir(parents=True, exist_ok=True)` della cartella e `cleanup_registry.add_path(uploads_root_EXT(user))` **prima** della scrittura.
- Scrive `content` (byte sintetici) e ritorna il `Path` creato.

### `seed_shapefile_sidecars_EXT(cleanup_registry, user, stem="shape_ext", *, suffixes=(".shp",".shx",".dbf",".prj"))`
- Crea i sidecar con lo stesso stem in `uploads/shp`; registra `uploads` nel cleanup prima di scrivere; ritorna la lista dei `Path`.
- Serve a verificare il `glob(f"{stem}*")` del `Template.delete`.

### `build_shapefile_zip_EXT(stem="shape_ext", *, include_shx=True, include_dbf=True)`
- Costruisce un `io.BytesIO` con `ZipFile`; scrive sempre `<stem>.shp` e, su flag, `<stem>.shx`/`<stem>.dbf` (byte sintetici).
- Esegue `seek(0)`; **nessun file temporaneo** su disco fuori dalla directory utente.

### `upload_payload_EXT(content, filename)`
- Normalizza `bytes`/`BytesIO` in `BytesIO`, `seek(0)`, e ritorna `{"file": (stream, filename)}` per il client Flask.

### `listed_filenames_EXT(files)`
- `{Path(str(f)).name for f in files}` → confronti stabili indipendenti dal prefisso `/data`.

## 4. Filesystem toccato e cleanup

- **Radici toccate**: `DATA_PATH/<uuid>/uploads/grib`, `DATA_PATH/<uuid>/uploads/shp` (scrittura seed) e — via endpoint — l'intera `/data/<uuid>` (upload, estrazione zip, `du -sb`).
- **Doppia registrazione**: `register_test_user_cleanup` registra `/data/<uuid>`; i seeding registrano anche `uploads`. Poiché `DOWNLOAD_DIR == Path("/data")` e `DATA_PATH` coincide con la stessa radice del container, le due voci puntano allo stesso sottoalbero: il LIFO rimuove prima `uploads`, poi `/data/<uuid>` (ridondante ma sicuro).
- **`CleanupRegistry`** ([tests/helpers/cleanup.py](projects/mistral/backend/tests/helpers/cleanup.py)) usa `shutil.rmtree(..., ignore_errors=True)` ⇒ rimozione **best-effort**, non fallisce se il path è già assente.
- **Nessun dato reale**: tutti i contenuti sono byte/stringhe sintetiche; nessun dataset meteo, nessun shapefile valido, nessun GDAL.

## 5. Comportamenti nascosti

- **Regola di estensione del seeding**: `seed_template_file_EXT` instrada in `uploads/shp` **tutto** ciò che non è `.grib` (anche estensioni inattese): coerente con il backend ma da tenere presente se si seedano nomi atipici.
- **`DATA_PATH` da `restapi.config`**: il sorgente di `restapi` non è nel workspace; il valore effettivo non è ispezionabile qui, ma per coerenza con l'endpoint (che scrive/legge sotto la stessa radice misurata da `du`) deve coincidere con `/data` (= `DOWNLOAD_DIR`). **Parzialmente non verificabile dal codice**.
- **`cleanup_registry.add_path` registra la radice `uploads`**, non i singoli file: la rimozione è dell'intero sottoalbero utente, quindi anche i file lasciati dal backend (es. zip non rimosso su errore) vengono ripuliti.
- **Cleanup registrato prima della scrittura**: garantisce rimozione anche se un assert successivo fallisce a metà.
- **Lo zip è sintetico**: non rappresenta uno shapefile reale; valido solo per i rami del controller che ispezionano nomi/estensioni.

## 6. Checklist di revisione

- [ ] Confermare che `DATA_PATH` (da `restapi.config`) e `DOWNLOAD_DIR` (`/data`) coincidano nel runtime: i seeding scrivono sotto `DATA_PATH/<uuid>/uploads`, mentre il cleanup utente registra `DOWNLOAD_DIR/<uuid>`.
- [ ] Verificare che la regola “tutto ciò che non è `.grib` va in `uploads/shp`” sia voluta anche per estensioni non canoniche.
- [ ] Confermare che `create_templates_user_EXT` non necessiti di forzare il DB (a differenza del supporto user_limits) perché i valori passano dall'admin customizer.
- [ ] Verificare che la doppia registrazione di cleanup (`/data/<uuid>` + `uploads`) resti coerente se i path divergessero in futuro.

## 7. Possibili criticità

- **Affidamento all'admin customizer**: `disk_quota`/`max_templates` sono applicati dall'endpoint admin, non forzati su DB; un'eventuale normalizzazione lato customizer cambierebbe i valori attesi dai test di quota/limite.
- **Accoppiamento a `restapi.config.DATA_PATH`**: assunzione (non verificabile dal workspace) che la radice dei file coincida con `/data`; un mismatch romperebbe sia il seeding sia il cleanup.
- **Builder con effetti su disco reali**: ogni seeding crea cartelle e file sotto `/data`; la robustezza dipende dal `CleanupRegistry` (best-effort, LIFO).
- **Nessuna fixture/`conftest` locale**: l'estensione resta confinata al dominio templates (positivo), ma i due moduli di test devono importare esplicitamente ciascun helper.
