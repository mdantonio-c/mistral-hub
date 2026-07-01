# Review — `test_forecast_spatial.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/test_forecast_spatial.py](projects/mistral/backend/tests/integration/postprocessing/test_forecast_spatial.py)
- **Scopo**: verificare i postprocessori **spaziali** forecast su `lm5`: interpolazione di griglia senza template (riscrive la geometria), interpolazione con template (riusa la geometria da un GRIB), cropping di griglia (completa con successo) e **spare-point interpolation** (output BUFR).
- **Tipologia**: integrazione **end-to-end reale**; `data_extract` eseguito sincrono via `send_task`, con esecuzione reale di `vg6d_transform` / `vg6d_getpoint` e lettura GRIB via `eccodes`. Marker (modulo): `integration`, `deterministic`, **`runtime_sensitive`**.
- **RUNTIME-SENSITIVE — skip silenziosi**:
  - tutti i 4 test → `require_dataset(db,"lm5")` (da `pp_forecast_env`) può **skippare**;
  - `test_spare_point_interpolation_outputs_bufr` → in più `require_spare_point_template_archive()` **skippa** se manca `/data/templates_for_pp/template_for_spare_point.zip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| Task `data_extract` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L42) | Estrazione + dispatch postprocessori (**ordine fisso**: crop *prima* di interp). |
| `pp3_1.pp_grid_interpolation` | [tools/grid_interpolation.py](projects/mistral/backend/tools/grid_interpolation.py#L24) | `vg6d_transform --trans-type/--sub-type` con `--x/y-min/max,--nx/ny` **oppure** `--output-format=grib_api:<template>`. |
| `pp3_2.pp_grid_cropping` | [tools/grid_cropping.py](projects/mistral/backend/tools/grid_cropping.py#L17) | `vg6d_transform --trans-mode=s --trans-type=zoom --sub-type=coord --ilon/ilat/flon/flat`. |
| `pp3_3.pp_sp_interpolation` | [tools/spare_point_interpol.py](projects/mistral/backend/tools/spare_point_interpol.py#L44) | `vg6d_getpoint`(grib) con shapefile `--coord-file`; output **BUFR**. |
| `arki.arkimet_extraction` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L355) | Estrazione forecast (filtro `forecast_pressure_filter`). |
| `eccodes` | sistema | `assert_grib_geometry` legge `latitudeOfFirstGridPointInDegrees` e `Ni`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `pp_forecast_env` | fixture | [postprocessing/conftest.py](projects/mistral/backend/tests/integration/postprocessing/conftest.py) | Ambiente `lm5` + skip su dataset assente. |
| `forecast_pressure_filter` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtro singolo prodotto P (pressione). |
| `grid_interpolation_without_template(x_min,y_min,nx)` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Boundings inline (`x_max=20,y_max=10`), `nx=ny`. |
| `grid_interpolation_with_template(path)` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Riusa geometria dal GRIB `template`. |
| `grid_cropping_postprocessor(initial_lon,initial_lat)` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | `flon=10,flat=5`, `zoom/coord`. |
| `spare_point_postprocessor(path)` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Shapefile `shp`, `inter/bilin`. |
| `require_spare_point_template_archive` | guardia | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | **skip** se manca lo zip template. |
| `env.unzip_upload/copy_upload/delete_request` | helper | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Preparano `uploads/`, copiano il GRIB di seed, ripuliscono lo scenario. |
| `assert_grib_geometry` | assert GRIB | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Verifica geometria del **primo** messaggio. |

## 4. Analisi dettagliata di ogni test

### `test_grid_interpolation_without_template_updates_geometry`
- **Obiettivo**: l'interpolazione senza template riscrive la geometria come richiesto (`y_min=-10`, `nx=12`).
- **Backend coinvolto**: `data_extract` → estrazione P → `pp3_1.pp_grid_interpolation` (`vg6d_transform` con boundings/nodi inline).
- **Flusso**: `create_request()` → `execute(filters=forecast_pressure_filter(), postprocessors=[grid_interpolation_without_template(x_min=-15,y_min=-10,nx=12)])` → `assert_success` → `assert_grib_geometry(out,-10,12)`.
- **Assert**: primo messaggio con `latitudeOfFirstGridPointInDegrees == -10` e `Ni == 12`.
- **Casi coperti**: happy path interpolazione “a parametri”.

### `test_grid_interpolation_with_template_reuses_template_geometry`
- **Obiettivo**: l'interpolazione con template copia la geometria dal GRIB fornito.
- **Backend coinvolto**: due esecuzioni reali di `data_extract`/`pp3_1`.
- **Flusso (a due fasi)**:
  1. **Seed**: crea una request, esegue interpolazione *senza* template (`y_min=-10,nx=12`), `assert_success` → ottiene un GRIB; lo **copia in `uploads/`** come `gi_template.grib` (`copy_upload`); **cancella la seed request** (`delete_request`) per liberare `outputs/`.
  2. **Test**: nuova request → `execute(filters=forecast_pressure_filter(), postprocessors=[grid_interpolation_with_template(template_path)])` → `assert_success` → `assert_grib_geometry(out,-10,12)`.
- **Assert**: la geometria finale coincide con quella del template (stessi `-10`/`12`).
- **Casi coperti**: ramo `--output-format=grib_api:<template>` dell'interpolazione; riuso geometria.
- **Coupling chiave**: la `delete_request` della seed è **necessaria** per l'invariante “un solo file in `outputs/`” di `assert_success`; il template vive in `uploads/` (cartella sorella) e non conta nel glob.

### `test_grid_cropping_completes_successfully`
- **Obiettivo**: il cropping completa con successo (verifica di esito, non di geometria).
- **Backend coinvolto**: `pp3_2.pp_grid_cropping` (`vg6d_transform --trans-type=zoom`).
- **Flusso**: `create_request()` → `execute(filters=forecast_pressure_filter(), postprocessors=[grid_cropping_postprocessor(initial_lon=-10,initial_lat=-5)])` → `assert_success` + `output_path.exists()`.
- **Assert**: solo successo + file presente (**nessun** assert sui bounding del crop).
- **Casi coperti**: happy path crop; **nota**: la correttezza geometrica del crop **non** è verificata (vedi §8).

### `test_spare_point_interpolation_outputs_bufr`
- **Obiettivo**: la spare-point interpolation esporta output **BUFR**.
- **Backend coinvolto**: `pp3_3.pp_sp_interpolation` (`vg6d_getpoint` + shapefile).
- **Flusso**: `create_request()` → `archive = require_spare_point_template_archive()` (**skip** se assente) → `unzip_upload(archive)` → `template = uploads/template_for_spare_point.shp` → `execute(filters=forecast_pressure_filter(), postprocessors=[spare_point_postprocessor(template)])` → `assert_success` → `assert output_path.suffix == ".bufr"`.
- **Assert**: il file finale ha estensione `.bufr` (il task NON rinomina a `.grib` perché l'output non è grib né `.tmp`).
- **Casi coperti**: happy path spare-point; cambio formato output GRIB→BUFR.

## 5. Call chain

```
execute(req)             → send_task("data_extract", user, ["lm5"], None, forecast_pressure_filter, [pp], fmt, req, None)
  data_extract (eager)   → arki.arkimet_extraction(...)                         [estrazione P reale]
                         → dispatch ORDINE FISSO: grid_cropping → grid_interpolation → spare_point
                              pp3_2.pp_grid_cropping            (vg6d_transform zoom/coord)
                              pp3_1.pp_grid_interpolation       (vg6d_transform inter/bilin | grib_api:<template>)
                              pp3_3.pp_sp_interpolation         (vg6d_getpoint + shp → .bufr)
                         → rename: se output è grib/.tmp → outfile.grib; altrimenti outfile = pp_output (.bufr)
                         → check_user_quota → create_fileoutput_record → SUCCESS
assert_grib_geometry     → eccodes.codes_get(latitudeOfFirstGridPointInDegrees, Ni)
```

## 6. Comportamenti nascosti

- **Ordine fisso dei postprocessori**: il task applica **crop prima di interp** indipendentemente dall'ordine in lista (qui ogni test usa un solo postprocessore spaziale, quindi l'ordine non incide; diventa rilevante in `test_forecast_chaining.py`).
- **Rinomina condizionale dell'output**: in `data_extract`, se `pp_output` contiene `grib` o è `.tmp` viene rinominato a `outfile` (grib); altrimenti `outfile = pp_output`. Per questo la spare-point resta `.bufr` e l'interp/crop restano grib.
- **`assert_grib_geometry` guarda solo il PRIMO messaggio** (`return` dopo il primo `gid`): non garantisce uniformità su tutti i messaggi (a differenza di `assert_grib_messages_have_geometry`).
- **Template via filesystem reale**: il GRIB di seed è scritto/letto su disco in `uploads/`; il path assoluto è passato a `vg6d_transform` (`grib_api:<path>`).
- **`delete_request` come prerequisito d'invariante**: senza la cancellazione della seed, `assert_success` fallirebbe per via del conteggio `==1`.

## 7. Checklist di revisione

- [ ] Confermare presenza in CI di `vg6d_transform` **e** `vg6d_getpoint`, oltre a dati P in `lm5`.
- [ ] Per spare-point: verificare lo zip `/data/templates_for_pp/template_for_spare_point.zip` (.shp + .shx + .dbf): la mancanza di .shx/.dbf produce `BadRequest` con **rimozione della cartella** (vedi `check_coord_filepath`).
- [ ] Valutare se `test_grid_cropping_completes_successfully` debba asserire anche la geometria risultante (oggi non lo fa).
- [ ] Verificare che la seed del test template sia sempre cancellata anche in caso di fallimento intermedio (oggi è sequenziale, non in teardown).

## 8. Possibili criticità

- **Crop “smoke test”**: `test_grid_cropping_completes_successfully` verifica solo successo+esistenza; un crop che produce una geometria errata ma un file valido **passerebbe** comunque.
- **Geometria sul solo primo messaggio**: `assert_grib_geometry` non copre file multi-messaggio non omogenei.
- **Doppia esecuzione reale** nel test con template: costo e fragilità raddoppiati (due estrazioni + due interpolazioni reali).
- **Dipendenza da artefatto esterno** per spare-point: lo zip template è uno stato d'ambiente non versionato qui; la sua assenza maschera la copertura (skip silenzioso).
- **Confine skip/fail**: come per gli altri file, lo skip copre solo l'assenza della riga dataset/template, non dati o tool mancanti.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_grid_interpolation_without_template_updates_geometry` | `pp3_1` (`vg6d_transform`) | geometria riscritta (`-10`,`12`) | nessuno | `pp_forecast_env` | Media |
| `test_grid_interpolation_with_template_reuses_template_geometry` | `pp3_1` template + seed | geometria copiata dal template | nessuno | `pp_forecast_env` | Alta (2 fasi) |
| `test_grid_cropping_completes_successfully` | `pp3_2` (`vg6d_transform zoom`) | solo successo + file presente | nessuno | `pp_forecast_env` | Bassa |
| `test_spare_point_interpolation_outputs_bufr` | `pp3_3` (`vg6d_getpoint`) | output `.bufr` | nessuno | `pp_forecast_env` + template (skip) | Media |
