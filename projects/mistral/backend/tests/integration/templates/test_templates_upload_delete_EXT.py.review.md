# Review — `test_templates_upload_delete_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/templates/test_templates_upload_delete_EXT.py](projects/mistral/backend/tests/integration/templates/test_templates_upload_delete_EXT.py)
- **Scopo**: verificare `POST /api/templates` (upload grib, zip shapefile completo/incompleto, estensione non ammessa, quota disco superata, limite `max_templates`), `GET /api/templates/<name>` (file esistente/mancante) e `DELETE /api/templates/<name>` (file assente, rimozione sidecar con stesso stem).
- **Tipologia**: test di **integrazione HTTP** con **scrittura/cancellazione reale su disco** sotto `/data/<uuid>/uploads`. Marker: `integration`, `deterministic`.
- **Dati reali**: nessuno. Grib e shapefile sono **byte sintetici**; gli zip sono costruiti in memoria. Nessun GDAL/worker/broker viene esercitato (il ramo `geojson`→`convert_to_shapefile` non viene toccato).
- **Skip documentati**: **TEMPLATES-001** (2 test su `GET <name>`, bug di esistenza invertita) e **TEMPLATES-002** (1 test su estensione errata, body mascherato). Vedi §6/§8.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Template.post` | [endpoints/templates.py#L116](projects/mistral/backend/endpoints/templates.py#L116) | Upload multipart; whitelist estensioni; validazione zip; limite `max_templates`; `Uploader.upload`; estrazione zip; **controllo quota** finale. |
| `Template.check_files_to_upload` | [endpoints/templates.py#L291](projects/mistral/backend/endpoints/templates.py#L291) | Per gli zip shapefile pretende `.shx` e `.dbf` con stesso stem; altrimenti `BadRequest`. |
| Limite `max_templates` (POST) | [endpoints/templates.py#L161](projects/mistral/backend/endpoints/templates.py#L161) | `Unauthorized` (401) quando `len(template_list) == int(max_templates)` (**uguaglianza esatta**). |
| Controllo quota (POST) | [endpoints/templates.py#L219](projects/mistral/backend/endpoints/templates.py#L219) | `du -sb /data/<uuid>` vs `User.disk_quota`; se eccede → cancella i file dello stem → `Forbidden` (403). |
| `Template.get` (singolo) | [endpoints/templates.py#L249](projects/mistral/backend/endpoints/templates.py#L249) | **Controllo di esistenza INVERTITO**: `if filepath.exists(): raise NotFound` ([#L256](projects/mistral/backend/endpoints/templates.py#L256)) → 404 sul file presente, 200 sul file assente (TEMPLATES-001). |
| `Template.delete` | [endpoints/templates.py#L272](projects/mistral/backend/endpoints/templates.py#L272) | Controllo **corretto** `if not filepath.exists(): raise NotFound` ([#L279](projects/mistral/backend/endpoints/templates.py#L279)); poi `glob(f"{stem}*")` + `unlink`. |
| `Uploader.upload` / `set_allowed_exts` | `restapi.services.uploader` | Whitelist `shp,shx,geojson,dbf,zip,grib`; rifiuta estensioni fuori lista (**sorgente non presente nel workspace**). |
| `SqlApiDbManager.get_user_permissions` | [services/sqlapi_db_manager.py#L665](projects/mistral/backend/services/sqlapi_db_manager.py#L665) | `param="templates"` → `user.max_templates`. |
| `User.disk_quota` / `User.max_templates` | [models/sqlalchemy.py#L11](projects/mistral/backend/models/sqlalchemy.py#L11) | Quota disco (BigInteger, default 1 GB) e numero massimo template ([#L27](projects/mistral/backend/models/sqlalchemy.py#L27)). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py#L39](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**; non ingoia eccezioni. |
| `TEMPLATES_ENDPOINT_EXT` | costante | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | URL `{API_URI}/templates`. |
| `create_templates_user_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Crea utente con `max_templates`/`disk_quota`; cleanup utente + `/data/<uuid>`. |
| `upload_payload_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Payload multipart `{"file": (stream, filename)}` (dimostra che si passa dall'HTTP reale). |
| `build_shapefile_zip_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Zip **in memoria** con `.shp` + opzionali `.shx`/`.dbf` (byte sintetici). |
| `seed_template_file_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Scrive un file sintetico nella cartella del tipo; registra `uploads` nel cleanup. |
| `seed_shapefile_sidecars_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Crea `.shp/.shx/.dbf/.prj` con stesso stem in `uploads/shp`. |
| `template_folder_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Restituisce `/data/<uuid>/uploads/<grib|shp>` (verifica fisica dei file). |
| `pytest.skip` | meccanismo | `pytest` | **Skip espliciti** TEMPLATES-001 (×2) e TEMPLATES-002 (×1). |

> Il dettaglio dei builder è in [support_EXT.py.review.md](projects/mistral/backend/tests/integration/templates/support_EXT.py.review.md).

## 4. Analisi dettagliata di ogni test

### `test_template_upload_accepts_valid_grib_file_EXT`
- **Obiettivo**: un grib valido viene salvato in `uploads/grib` e la risposta espone `format`/`filepath`.
- **Backend coinvolto**: `Template.post` ramo grib; `Uploader.upload`; controllo quota (sotto soglia).
- **Flusso**: utente `max_templates=5` (quota default 1 GB) → POST multipart `b"GRIB EXT"` come `valid_grib_ext.grib`.
- **Setup**: `create_templates_user_EXT`.
- **Assert**: `200`; `content["format"]=="grib"`; `Path(content["filepath"]).name == filename`; il file **esiste** in `template_folder_EXT(user,"grib")`.
- **Filesystem**: scrive `/data/<uuid>/uploads/grib/valid_grib_ext.grib`.
- **Casi coperti**: happy path upload grib + side effect su disco.

### `test_template_upload_accepts_complete_shapefile_zip_EXT`
- **Obiettivo**: zip shapefile completo (`.shp/.shx/.dbf`) viene accettato ed estratto in `uploads/shp`.
- **Backend coinvolto**: `Template.post` ramo zip → `check_files_to_upload` → `upload` → `extractall` → `unlink` dello zip; quota sotto soglia.
- **Flusso**: utente `max_templates=5` → `build_shapefile_zip_EXT("complete_zip_ext")` → POST come `complete_zip_ext.zip`.
- **Setup**: `create_templates_user_EXT`.
- **Assert**: `200`; presenza dei **tre** sidecar `complete_zip_ext.{shp,shx,dbf}` in `uploads/shp`.
- **Filesystem**: zip salvato, estratto e rimosso; restano i tre file estratti sotto `/data/<uuid>/uploads/shp`.
- **Casi coperti**: happy path zip completo + estrazione. La risposta `filepath`/`format` non è asserita (l'ultimo file iterato è il `.dbf`); il contratto verificato è HTTP 200 + presenza fisica.

### `test_template_upload_rejects_incomplete_shapefile_zip_EXT` — **parametrizzato (×2)**
- **Obiettivo**: zip senza `.shx` o senza `.dbf` → `400` con messaggio specifico.
- **Backend coinvolto**: `check_files_to_upload` (rami `"file .shx is missing"` / `"file .dbf is missing"`), **prima** di scrivere su disco.
- **Flusso**: per ogni combinazione `(include_shx, include_dbf)` costruisce lo zip incompleto → POST.
- **Setup**: `max_templates=5`.
- **Assert**: `400`; `get_content == expected_message`.
- **Filesystem**: nessuna scrittura persistente (il controllo precede l'upload).
- **Casi coperti**: due error path di validazione zip distinti per messaggio.

### `test_template_upload_rejects_wrong_extension_EXT` — **TEMPLATES-002 (skippabile)**
- **Obiettivo**: estensione fuori whitelist (`.txt`) → `400`.
- **Backend coinvolto**: `Uploader.allowed_file` (via `self.upload`) dopo `set_allowed_exts`; in caso di errore, il ramo `except Exception` di `post` itera `subfolder.iterdir()`.
- **Flusso**: utente valido → POST `b"not a template"` come `wrong_ext.txt`.
- **Setup**: `max_templates=5`.
- **Assert / Skip**: `status_code == 400` (asserito incondizionatamente); se `content != "File extension not allowed"` → `pytest.skip("TEMPLATES-002: ...")`; altrimenti `content == "File extension not allowed"`.
- **Filesystem**: `uploads/shp` può non esistere quando `iterdir()` viene invocato sul ramo di errore.
- **Casi coperti**: error path estensione. **Può essere silenziosamente saltato**: nel backend attuale il body viene mascherato (vedi §6/§8). La meccanica esatta con cui lo status resta `400` dipende da `restapi.services.uploader.Uploader`, **non incluso nel workspace** → **non completamente verificabile dal codice**.

### `test_template_upload_returns_403_when_disk_quota_is_exceeded_EXT`
- **Obiettivo**: ramo `Forbidden` quando l'upload supera `disk_quota`.
- **Backend coinvolto**: `Template.post` fino al controllo quota `du -sb` vs `User.disk_quota` → cancellazione file dello stem → `Forbidden`.
- **Flusso**: utente con `disk_quota=1` → zip shapefile completo → POST.
- **Setup**: `create_templates_user_EXT(..., disk_quota=1)`. **Non** forza il DB: si affida all'admin customizer che deve accettare `disk_quota=1`.
- **Assert**: `403`; `get_content == "Disk quota exceeded"`.
- **Filesystem**: il backend estrae poi cancella i file dello stem; il residuo eventuale resta sotto `/data/<uuid>` ed è coperto dal cleanup.
- **Casi coperti**: error path quota. La quota minima rende il superamento deterministico senza scrivere file grandi.

### `test_template_upload_returns_401_when_max_templates_is_reached_EXT`
- **Obiettivo**: il secondo template dello stesso tipo è rifiutato con `401`.
- **Backend coinvolto**: blocco `max_templates` ([#L161](projects/mistral/backend/endpoints/templates.py#L161)) con **uguaglianza esatta** (`==`).
- **Flusso**: utente `max_templates=1`, seed di `already_present_ext.grib` → POST `second_ext.grib`.
- **Setup**: `seed_template_file_EXT` per portare il conteggio grib a 1.
- **Assert**: `401`; `get_content == "user has reached the max number of templates of this kind"`.
- **Filesystem**: il secondo file **non** viene scritto.
- **Casi coperti**: error path limite. Il seed porta `len==1` esattamente uguale al limite `1` (vedi nota su `==` in §6).

### `test_template_get_existing_file_returns_filepath_and_format_EXT` — **TEMPLATES-001 (skippabile)**
- **Obiettivo**: documentare il contratto atteso di `GET <name>` su file **esistente** (atteso 200).
- **Backend coinvolto**: `Template.get` con controllo invertito ([#L256](projects/mistral/backend/endpoints/templates.py#L256)).
- **Flusso**: seed di `get_existing_ext.grib` → GET `/<name>`.
- **Setup**: `seed_template_file_EXT`.
- **Assert / Skip**: se `404` → `pytest.skip("TEMPLATES-001: ...")`; altrimenti `200` + `filepath.name`/`format`.
- **Stato attuale**: con il bug presente il file esiste ⇒ `404` ⇒ **il test fa skip**. L'assert 200 è copertura **sospesa**, non verificata.

### `test_template_get_missing_file_returns_404_EXT` — **TEMPLATES-001 (skippabile)**
- **Obiettivo**: documentare il contratto atteso di `GET <name>` su file **mancante** (atteso 404).
- **Backend coinvolto**: `Template.get` (stesso controllo invertito).
- **Flusso**: solo utente, nessun file → GET `/missing_template_ext.grib`.
- **Setup**: `create_templates_user_EXT`.
- **Assert / Skip**: se `200` → `pytest.skip("TEMPLATES-001: ...")`; altrimenti `404`.
- **Stato attuale**: con il bug il file non esiste ⇒ `200` (con `filepath` inesistente) ⇒ **il test fa skip**.

### `test_template_delete_missing_file_returns_404_EXT`
- **Obiettivo**: `DELETE <name>` su file assente → `404`.
- **Backend coinvolto**: `Template.delete` controllo **corretto** `if not filepath.exists()`.
- **Flusso**: solo utente → DELETE `/missing_delete_ext.shp`.
- **Setup**: `create_templates_user_EXT`.
- **Assert**: `404`; `get_content == "The template doesn't exist"`.
- **Casi coperti**: error path delete (non affetto dal bug di `get`).

### `test_template_delete_removes_shapefile_sidecars_with_same_stem_EXT`
- **Obiettivo**: `DELETE <stem>.shp` rimuove **tutti** i file `stem*` (sidecar).
- **Backend coinvolto**: `Template.delete` → `glob(f"{stem}*")` + `unlink`.
- **Flusso**: seed di `delete_ext.{shp,shx,dbf,prj}` → DELETE `/delete_ext.shp`.
- **Setup**: `seed_shapefile_sidecars_EXT`.
- **Assert**: `200`; `get_content == "File delete_ext.shp succesfully deleted"` (nota: refuso “succesfully” **nel backend**); tutti i sidecar **non esistono** più.
- **Filesystem**: rimuove fisicamente i quattro file in `uploads/shp`.
- **Casi coperti**: happy path delete + side effect su disco (cancellazione per stem).

## 5. Call chain

```
POST   /api/templates             → auth.require()
                                    → request.files["file"]; set_allowed_exts([shp,shx,geojson,dbf,zip,grib])
                                    → ext == zip? → check_files_to_upload(...)  → BadRequest 400 (shx/dbf mancante)
                                    → max_templates? len(glob)==max → Unauthorized 401
                                    → try: Uploader.upload(subfolder)
                                        except Exception: iterdir(subfolder)*  → ServerError  (*TEMPLATES-002 se dir assente)
                                    → ext==zip? extractall + unlink zip
                                    → du -sb /data/<uuid> vs User.disk_quota → Forbidden 403
                                    → response({filepath, format}) 200   (la doc dichiara 202)
GET    /api/templates/<name>      → auth.require()
                                    → filepath = /data/<uuid>/uploads/<ext>/<name>
                                    → if filepath.exists(): raise NotFound  ← INVERTITO (TEMPLATES-001)
                                    → response({filepath, format}) 200
DELETE /api/templates/<name>      → auth.require()
                                    → if not filepath.exists(): NotFound 404
                                    → glob(f"{stem}*") → unlink → response("File ... succesfully deleted") 200
```

## 6. Comportamenti nascosti

- **`Template.get` invertito (TEMPLATES-001)**: `if filepath.exists(): raise NotFound` ([#L256](projects/mistral/backend/endpoints/templates.py#L256)) restituisce `404` per file presenti e `200` (con `filepath` inesistente) per file assenti. **Entrambi** i test su `GET <name>` fanno quindi `skip` nel backend attuale.
- **TEMPLATES-002 (body mascherato)**: sul rifiuto di estensione, il ramo `except Exception` di `post` esegue `subfolder.iterdir()` su una cartella che può non esistere; ciò può sollevare `FileNotFoundError` e mascherare il messaggio `"File extension not allowed"`. Il test mantiene l'assert sullo status `400` e fa `skip` solo sul body.
- **Limite `max_templates` con `==`**: il POST blocca solo quando `len(template_list) == max` (uguaglianza esatta), mentre il listing usa `>=`. Con `len > max` (es. file pre-esistenti oltre il limite) il POST **non** bloccherebbe. Il test usa `len==1, max==1`.
- **Doc/impl divergenti sullo status di upload**: `@decorators.endpoint(responses={202: "File uploaded", ...})` ma `post` ritorna `self.response(r)` → **200**. I test asseriscono correttamente `200`.
- **Refuso nel messaggio di delete**: il backend ritorna `"... succesfully deleted"` (manca una “s”); il test riproduce esattamente la stringa del backend.
- **Glob per stem nel delete**: cancella **tutti** i file che iniziano con lo stem (`stem*`), non solo i sidecar shapefile canonici; potenzialmente più ampio del previsto.
- **Rami non esercitati**: `geojson`→`convert_to_shapefile` (GDAL) e i controlli `shx/shp/dbf does not match` di `check_files_to_upload` non sono coperti.
- **Zip in memoria**: gli archivi non sono shapefile reali; il controller in questi rami valida solo nomi/estensioni, non geometrie.

## 7. Checklist di revisione

- [ ] **TEMPLATES-001**: correggere `Template.get` (condizione invertita) per riattivare i due test `GET <name>` oggi in `skip`; finché il bug resta, quella copertura è **sospesa** (verde per skip).
- [ ] **TEMPLATES-002**: correggere il cleanup del ramo `except` (`iterdir` su cartella assente) per riabilitare l'assert sul messaggio `"File extension not allowed"`.
- [ ] Confermare che il limite POST debba usare `==` o `>=` (coerenza con il listing) — possibile bypass se il conteggio supera il limite.
- [ ] Allineare la doc OpenAPI dell'upload (dichiara 202, ritorna 200).
- [ ] Valutare il refuso `succesfully` nel messaggio di delete (impatto su client che parsano la stringa).
- [ ] Verificare che il `glob(f"{stem}*")` del delete non rimuova file non correlati con prefisso comune.

## 8. Possibili criticità

- **Tre test che possono sparire dalla copertura**: 2× TEMPLATES-001 + 1× TEMPLATES-002 fanno `skip` nel backend corrente → **falso senso di copertura** su `GET <name>` e sul messaggio di estensione errata. Onesti e documentati, ma di fatto **non verificati** finché i bug restano.
- **Dipendenza da `restapi.services.uploader`**: la dinamica esatta di `self.upload` (status 400 vs 500 sul ramo di errore) non è verificabile dal workspace; la review si basa sul comportamento osservato dall'autore e sull'assert dello status.
- **Affidamento all'admin customizer per `disk_quota=1`**: a differenza dei test usage/hourly, qui la quota non viene forzata via DB; se il customizer normalizzasse il valore, il ramo 403 non sarebbe più deterministico.
- **Side effect su disco reali**: i test scrivono/cancellano sotto `/data/<uuid>`; correttezza del cleanup LIFO essenziale per non lasciare residui in CI.
- **Asimmetria `==`/`>=`**: incoerenza fra POST e listing sul confronto con `max_templates`, non coperta da test dedicati.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/Skip | Fixture | Complessità |
|---|---|---|---|---|---|
| `..._accepts_valid_grib_file_EXT` | `post` (grib) | upload grib + file su disco | — | `client`, `cleanup_registry` | Media |
| `..._accepts_complete_shapefile_zip_EXT` | `post` (zip) + `check_files_to_upload` | estrazione 3 sidecar | — | `client`, `cleanup_registry` | Media |
| `..._rejects_incomplete_shapefile_zip_EXT` (×2) | `check_files_to_upload` | 400 shx/dbf mancante | — (parametrizzato) | `client`, `cleanup_registry` | Bassa |
| `..._rejects_wrong_extension_EXT` | `Uploader`/`post` except | 400 estensione | **skip TEMPLATES-002** | `client`, `cleanup_registry` | Media (skippabile) |
| `..._returns_403_when_disk_quota_is_exceeded_EXT` | `post` (quota) | 403 quota | — | `client`, `cleanup_registry` | Media |
| `..._returns_401_when_max_templates_is_reached_EXT` | `post` (`max_templates`) | 401 limite | — | `client`, `cleanup_registry` | Media |
| `..._get_existing_file_..._EXT` | `Template.get` | atteso 200 file presente | **skip TEMPLATES-001** | `client`, `cleanup_registry` | Bassa (skippabile) |
| `..._get_missing_file_returns_404_EXT` | `Template.get` | atteso 404 file assente | **skip TEMPLATES-001** | `client`, `cleanup_registry` | Bassa (skippabile) |
| `..._delete_missing_file_returns_404_EXT` | `Template.delete` | 404 file assente | — | `client`, `cleanup_registry` | Bassa |
| `..._delete_removes_shapefile_sidecars_..._EXT` | `Template.delete` | rimozione `stem*` su disco | — | `client`, `cleanup_registry` | Media |
