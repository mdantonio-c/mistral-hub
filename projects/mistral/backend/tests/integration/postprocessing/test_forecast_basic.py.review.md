# Review — `test_forecast_basic.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/test_forecast_basic.py](projects/mistral/backend/tests/integration/postprocessing/test_forecast_basic.py)
- **Scopo**: verificare i tre scenari forecast “base” di successo su dataset `lm5`: estrazione semplice che produce un file; postprocessore **derived_variables** che emette `relhum_2m` preservando gli altri campi; postprocessore **statistic_elaboration** che produce il `stepRange` di precipitazione atteso.
- **Tipologia**: test di **integrazione end-to-end reale**. Il task `data_extract` è eseguito **sincrono/in-process** via `send_task`, quindi vengono invocati davvero estrazione Arkimet e i binari `vg6d_transform`/`eccodes`. Marker (modulo): `integration`, `deterministic`, **`runtime_sensitive`**.
- **RUNTIME-SENSITIVE**: tutti e 3 i test ereditano da `pp_forecast_env` la guardia `require_dataset(db,"lm5")` → **`pytest.skip` silenzioso** se `lm5` non è presente. La presenza di **dati** in `lm5` e dei binari non è invece coperta da skip: in loro assenza i test **falliscono**.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| Task `data_extract` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L42) | Orchestrazione: estrazione + dispatch postprocessori (ordine fisso) + size/quota + record `FileOutput`. |
| `arki.arkimet_extraction` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L355) | Estrazione forecast reale via `query_bytes` su Arkimet. |
| `arki.get_datasets_format` / `get_datasets_category` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L197) | Determina formato (`grib`) e categoria (non-`OBS`) del dataset. |
| `pp1.pp_derived_variables` | [tools/derived_variables.py](projects/mistral/backend/tools/derived_variables.py#L10) | `vg6d_transform --output-variable-list=B13003`, poi `cat input + step1` → unisce il derivato ai campi originali. |
| `pp2.pp_statistic_elaboration` | [tools/statistic_elaboration.py](projects/mistral/backend/tools/statistic_elaboration.py#L15) | Split per timerange via `eccodes`, `vg6d_transform --comp-stat-proc/--comp-step`, ricomposizione `cat`. |
| `check_user_quota` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py) | Verifica quota/size dopo il postprocessing. |
| `SqlApiDbManager.create_fileoutput_record` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py) | Crea il record `FileOutput` letto poi da `assert_success`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `pp_forecast_env` | fixture | [postprocessing/conftest.py](projects/mistral/backend/tests/integration/postprocessing/conftest.py) | Ambiente forecast su `lm5`: utente dedicato, DB, cleanup; **skip** se dataset assente. |
| `PostprocessingEnv.execute/assert_success` | helper | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Invio reale del task; assert su `status=SUCCESS`, file unico non vuoto. |
| `forecast_derived_variable_filters/postprocessor` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtri P+T+dewpoint+Q e postprocessor `derived_variables` (`["B13003"]`). |
| `forecast_statistic_elaboration_filters/postprocessor` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtri TP+P e postprocessor `statistic_elaboration` (`step=3`, `hours`). |
| `assert_grib_contains_short_name` / `…_preserves_independent_fields` / `…_contains_step_range` / `…_contains_short_name_other_than` | assert GRIB | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Leggono il GRIB prodotto via `eccodes`. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown LIFO (riga `Request`, utente, filesystem). |
| binari `vg6d_transform`, `cat`, `eccodes` | sistema | immagine backend | Eseguiti realmente dalla pipeline. |

## 4. Analisi dettagliata di ogni test

### `test_simple_forecast_extraction_creates_output`
- **Obiettivo**: una estrazione forecast “nuda” (nessun filtro, nessun postprocessore) produce un file di output.
- **Backend coinvolto**: `data_extract` → `arki.arkimet_extraction` → controllo size/quota → `create_fileoutput_record`. **Nessun** postprocessore.
- **Flusso**: `create_request()` → `execute(request_id)` (filters/postprocessors `None`/`[]`, `reftime=None`) → `assert_success`.
- **Setup**: `pp_forecast_env` (utente `lm5`).
- **Assert**: `assert_success` (status SUCCESS, `fileoutput` presente, file esistente, non vuoto, **un solo file** in `outputs/`) + `output_path.exists()`.
- **Casi coperti**: happy path minimale dell'estrazione forecast reale.

### `test_derived_variables_emit_relhum_2m`
- **Obiettivo**: il postprocessore `derived_variables` calcola `relhum_2m` (da B13003) **preservando** gli altri campi.
- **Backend coinvolto**: `data_extract` → estrazione con filtri P+T+dewpoint+Q → `pp1.pp_derived_variables` (`vg6d_transform` + `cat input+step1`).
- **Flusso**: `create_request()` → `execute(filters=forecast_derived_variable_filters(), postprocessors=[forecast_derived_variable_postprocessor()])` → `assert_success`.
- **Assert**: `assert_grib_contains_short_name(out,"relhum_2m")` (il derivato è presente) **e** `assert_grib_preserves_independent_fields(out,"relhum_2m")` (esiste almeno un campo con shortName diverso → la merge `cat` ha tenuto gli input).
- **Casi coperti**: contratto del derivato + non-distruttività della merge.

### `test_statistic_elaboration_emits_tp_step_range`
- **Obiettivo**: `statistic_elaboration` su precipitazione produce `tp` con `stepRange == "3-6"` (accumulo a 3 ore, `step=3`) mantenendo la pressione come campo indipendente.
- **Backend coinvolto**: `data_extract` → estrazione TP+P → `pp2.pp_statistic_elaboration` (split per timerange + `vg6d_transform --comp-step=…03:00:00…`).
- **Flusso**: `create_request()` → `execute(filters=forecast_statistic_elaboration_filters(), postprocessors=[forecast_statistic_elaboration_postprocessor()])` → `assert_success`.
- **Assert**: `assert_grib_contains_step_range(out,"tp","3-6")` + `assert_grib_contains_short_name_other_than(out,"tp","sp")` (verifica che `sp` sia presente; vedi §6 sul parametro ignorato).
- **Casi coperti**: contratto statistico (stepRange) + presenza campo indipendente.

## 5. Call chain

```
execute(req)               → BaseTests.send_task(app, "data_extract", user_id, ["lm5"], None, filters, pp, fmt, req, only_reliable)
  data_extract (eager)     → arki.get_datasets_format/category
                           → check user auth + query Arkimet (parse_matchers; reftime=None)
                           → arki.arkimet_extraction(datasets, query, tmp_outfile)      [forecast reale]
                           → [se postprocessors] dispatch ORDINE FISSO:
                                derived_variables → pp1.pp_derived_variables (vg6d_transform; cat input+step1)
                                statistic_elaboration → pp2.pp_statistic_elaboration (eccodes split; vg6d_transform; cat)
                           → rename → check_user_quota → create_fileoutput_record → status=SUCCESS
                           → finally: commit; (email solo se notify_on_successful_request)
assert_success(req)        → Request.status==SUCCESS, fileoutput, file unico non vuoto
assert_grib_*              → eccodes.codes_get(shortName/stepRange)
```

## 6. Comportamenti nascosti

- **Esecuzione reale dei binari**: `send_task` chiama il task come funzione → `vg6d_transform`/`cat`/`eccodes` girano davvero; l'esito dipende da dati e tool presenti.
- **`reftime=None`**: l'estrazione forecast non filtra per tempo; serve che `lm5` contenga i prodotti richiesti.
- **`derived_variables` è non distruttivo by design**: il file finale è `cat(input, step1)`, quindi contiene sia gli input sia il derivato; l'assert “preserves” sfrutta proprio questa merge.
- **`assert_grib_contains_short_name_other_than(out,"tp","sp")`**: il parametro `"tp"` (excluded) è **ignorato** dall'helper; di fatto si verifica solo che `sp` esista, non che `tp` sia escluso.
- **Un solo file in `outputs/`**: `assert_success` impone `len(glob("*"))==1`; i file `.tmp` intermedi vengono rimossi dal task prima del controllo quota.
- **Nessuna email su successo**: dipende dal default `notify_on_successful_request=False` dell'utente di test.

## 7. Checklist di revisione

- [ ] Confermare in CI la presenza di `vg6d_transform`/`eccodes` e di dati in `lm5` (altrimenti **fail**, non skip).
- [ ] Verificare che `stepRange "3-6"` sia stabile rispetto ai dati di `lm5` (dipende dai timerange realmente presenti).
- [ ] Valutare se l'assert su `sp` debba essere rafforzato per verificare davvero l'esclusione di `tp`.
- [ ] Confermare che `relhum_2m` sia lo `shortName` atteso per B13003 a 2m nell'ambiente eccodes usato.

## 8. Possibili criticità

- **Dipendenza d'ambiente forte**: scenario reale dati+binari; la guardia di skip copre solo l'assenza della *riga* dataset, non l'assenza di *dati* o *tool* → rischio di fallimenti d'ambiente scambiabili per regressioni.
- **Assert geometrico/semantico legato ai dati**: `"3-6"` e `relhum_2m` presuppongono uno specifico contenuto di `lm5`; un cambio dei dati di base rompe i test senza che il backend sia cambiato.
- **Helper di assert debole**: `…_other_than` non verifica l'esclusione, potenziale falsa sicurezza.
- **Costo/non determinismo pratico**: pur marcato `deterministic`, il test esegue subprocess esterni e I/O su filesystem; eventuali differenze di versione dei tool possono cambiare l'output.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_simple_forecast_extraction_creates_output` | `data_extract`+`arkimet_extraction` | estrazione reale → file unico non vuoto | nessuno (pipeline reale) | `pp_forecast_env` | Bassa |
| `test_derived_variables_emit_relhum_2m` | `pp1.pp_derived_variables` (`vg6d_transform`,`cat`) | `relhum_2m` emesso + campi preservati | nessuno | `pp_forecast_env` | Media |
| `test_statistic_elaboration_emits_tp_step_range` | `pp2.pp_statistic_elaboration` (`vg6d_transform`) | `tp` stepRange `3-6` + `sp` presente | nessuno | `pp_forecast_env` | Media |
