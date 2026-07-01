# Review — `test_forecast_chaining.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/test_forecast_chaining.py](projects/mistral/backend/tests/integration/postprocessing/test_forecast_chaining.py)
- **Scopo**: verificare il **concatenamento** di più postprocessori forecast in una sola request su `lm5`: (1) derived + statistic + interpolazione + cropping preservano derivato, statistica e geometria; (2) catena derived + statistic + spare-point con **export finale JSON**.
- **Tipologia**: integrazione **end-to-end reale**; `data_extract` sincrono via `send_task` → esecuzione reale di `vg6d_transform`, `vg6d_getpoint`, `dbamsg`, `cat`, `eccodes`. Marker (modulo): `integration`, `deterministic`, **`runtime_sensitive`**.
- **RUNTIME-SENSITIVE — skip silenziosi**: entrambi i test → `require_dataset(db,"lm5")`; il secondo → in più `require_spare_point_template_archive()` (zip template).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| Task `data_extract` (dispatch **ordine fisso**) | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L42) | Applica i postprocessori in sequenza fissa: derived → statistic → **crop → interp** → spare-point; ogni stadio prende in input l'output del precedente (`pp_output or tmp_outfile`). |
| `pp1.pp_derived_variables` | [tools/derived_variables.py](projects/mistral/backend/tools/derived_variables.py#L10) | Derivato `relhum_2m` + merge. |
| `pp2.pp_statistic_elaboration` | [tools/statistic_elaboration.py](projects/mistral/backend/tools/statistic_elaboration.py#L15) | Accumulo precipitazione (`step=3`). |
| `pp3_1.pp_grid_interpolation` | [tools/grid_interpolation.py](projects/mistral/backend/tools/grid_interpolation.py#L24) | Re-griglia (ultimo stadio spaziale → geometria finale). |
| `pp3_2.pp_grid_cropping` | [tools/grid_cropping.py](projects/mistral/backend/tools/grid_cropping.py#L17) | Crop (eseguito **prima** dell'interp). |
| `pp3_3.pp_sp_interpolation` | [tools/spare_point_interpol.py](projects/mistral/backend/tools/spare_point_interpol.py#L44) | Spare-point → BUFR. |
| `output_formatting.pp_output_formatting` | [tools/output_formatting.py](projects/mistral/backend/tools/output_formatting.py#L7) | `dbamsg dump --json` per il secondo test; rimuove il file di input nel `finally`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `pp_forecast_env` | fixture | [postprocessing/conftest.py](projects/mistral/backend/tests/integration/postprocessing/conftest.py) | Ambiente `lm5` + skip su dataset assente. |
| `forecast_chaining_filters` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtri combinati P+T+dewpoint+Q+TP (coprono derived **e** statistic). |
| `forecast_derived_variable_postprocessor` / `forecast_statistic_elaboration_postprocessor` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Payload derived/statistic. |
| `grid_interpolation_without_template` / `grid_cropping_postprocessor` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Payload spaziali. |
| `spare_point_postprocessor` / `require_spare_point_template_archive` | builder/guardia | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Spare-point + **skip** se manca lo zip. |
| `assert_grib_contains_short_name` / `…_contains_step_range` / `assert_grib_messages_have_geometry` | assert GRIB | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Verificano derivato, stepRange e geometria **di tutti** i messaggi. |
| `env.unzip_upload` | helper | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Estrae lo shapefile in `uploads/`. |

## 4. Analisi dettagliata di ogni test

### `test_combined_postprocessors_keep_derived_statistic_and_geometry`
- **Obiettivo**: una catena di 4 postprocessori preserva il derivato (`relhum_2m`), la statistica (`tp` `3-6`) e impone la geometria finale (`y_min=-10`, `nx=12`) su **tutti** i messaggi.
- **Backend coinvolto**: `data_extract` → derived → statistic → crop → interp (ordine fisso del task).
- **Flusso**: `create_request()` → lista postprocessori `[derived, statistic, grid_interpolation(x_min=-15,y_min=-10,nx=12), grid_cropping(initial_lon=-10,initial_lat=-5)]` → `execute(filters=forecast_chaining_filters(), postprocessors=…)` → `assert_success`.
- **Assert**: `assert_grib_contains_short_name(out,"relhum_2m")`; `assert_grib_contains_step_range(out,"tp","3-6")`; `assert_grib_messages_have_geometry(out,-10,12)` (geometria uguale su **ogni** messaggio).
- **Casi coperti**: composizione multi-stadio non distruttiva + geometria finale.
- **Hidden behavior cruciale**: la lista passa **interp prima di crop**, ma il backend applica **crop prima di interp** (dispatch a ordine fisso da dict). La geometria finale asserita (`-10`,`12`) è quella dell'**interpolazione** proprio perché è l'ultimo stadio spaziale eseguito. Il test passa *grazie* all'ordine del backend, non a quello della lista (vedi §6/§8).

### `test_combined_postprocessors_can_export_json_after_spare_point`
- **Obiettivo**: una catena derived + statistic + spare-point può esportare il risultato finale in **JSON**.
- **Backend coinvolto**: `data_extract` → derived → statistic → spare-point (→ BUFR) → `output_formatting` (`dbamsg dump --json`).
- **Flusso**: `create_request()` → `archive = require_spare_point_template_archive()` (**skip** se assente) → `unzip_upload(archive)` → `template = uploads/template_for_spare_point.shp` → `execute(filters=forecast_chaining_filters(), postprocessors=[derived, statistic, spare_point(template)], output_format="json")` → `assert_success`.
- **Assert**: `output_path.suffix == ".json"` e `"grib" not in output_path.name`.
- **Casi coperti**: catena mista grid→punto + conversione formato finale BUFR→JSON.

## 5. Call chain

```
execute(req)              → send_task("data_extract", user, ["lm5"], None, forecast_chaining_filters, [pp...], fmt, req, None)
  data_extract (eager)    → arki.arkimet_extraction(...)                          [estrazione reale]
                          → dispatch ORDINE FISSO (da dict, NON dalla lista):
                               1 derived_variables → pp1 (vg6d_transform; cat)
                               2 statistic_elaboration → pp2 (vg6d_transform; cat)
                               3 grid_cropping → pp3_2 (vg6d_transform zoom)
                               4 grid_interpolation → pp3_1 (vg6d_transform inter)   ← geometria finale
                               5 spare_point_interpolation → pp3_3 (vg6d_getpoint → .bufr)
                          → [output_format=json] output_formatting.pp_output_formatting (dbamsg dump --json)
                          → check_user_quota → create_fileoutput_record → SUCCESS
assert_grib_*             → eccodes (relhum_2m, tp/3-6, geometria su tutti i messaggi)
```

## 6. Comportamenti nascosti

- **Ordine di esecuzione ≠ ordine della lista**: `requested_postprocessors` è un **dict** per `processor_type`; il task li applica in sequenza fissa (derived, statistic, crop, interp, spare-point). Nel test 1 la lista è `[…, interp, crop]` ma l'esecuzione reale è `… crop, interp`. L'assert geometrico funziona *perché* interp è l'ultimo stadio spaziale del backend.
- **Chaining via filesystem**: ogni stadio usa `pp_output or tmp_outfile` come input; i `.tmp` intermedi sono accumulati in `tmp_file_list` e rimossi prima del controllo quota.
- **Spare-point cambia il formato** a BUFR; `output_format="json"` poi converte con `dbamsg`. `output_formatting` **rimuove il file di input** nel suo `finally`.
- **`assert_grib_messages_have_geometry`** verifica **ogni** messaggio (più stringente del singolo-messaggio usato in `test_forecast_spatial.py`).
- **Filtri combinati**: `forecast_chaining_filters` include i 5 prodotti necessari a derived **e** statistic; un sottoinsieme incompleto manderebbe la catena su un ramo di fallimento.

## 7. Checklist di revisione

- [ ] **Decidere se il test 1 debba dipendere dall'ordine fisso del backend**: oggi nasconde che l'ordine in lista è ignorato. Valutare un commento/asserzione esplicita o un test dedicato all'ordinamento.
- [ ] Confermare in CI `vg6d_transform`, `vg6d_getpoint`, `dbamsg`, `eccodes` e dati completi in `lm5` per i 5 prodotti.
- [ ] Verificare lo zip template spare-point (.shp/.shx/.dbf) per il test 2.
- [ ] Confermare che `"grib" not in name` sia un controllo sufficiente per “non è più GRIB” (oltre a `.json`).

## 8. Possibili criticità

- **Accoppiamento implicito all'ordinamento interno**: il test 1 “passa” per via dell'ordine fisso del dispatch; se il backend rispettasse l'ordine della lista (interp→crop), la geometria finale sarebbe quella del crop e l'assert cambierebbe. È una dipendenza non dichiarata e potenzialmente fuorviante in revisione.
- **Catena reale lunga**: 4–5 subprocess esterni in sequenza aumentano costo, tempo e superficie di fallimento d'ambiente.
- **Skip silenziosi**: dataset e/o template assenti rimuovono i test dalla copertura senza segnale evidente.
- **Geometria non distruttiva non garantita per stadi intermedi**: si verifica solo l'output finale; eventuali perdite di campi negli stadi intermedi non sono osservate direttamente.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_combined_postprocessors_keep_derived_statistic_and_geometry` | pp1+pp2+pp3_2+pp3_1 | derivato + stepRange + geometria (tutti i msg) | nessuno (pipeline reale) | `pp_forecast_env` | Alta |
| `test_combined_postprocessors_can_export_json_after_spare_point` | pp1+pp2+pp3_3+`output_formatting` | catena + export JSON | nessuno | `pp_forecast_env` + template (skip) | Alta |
