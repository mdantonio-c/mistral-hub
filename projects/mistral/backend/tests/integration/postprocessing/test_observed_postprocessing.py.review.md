# Review — `test_observed_postprocessing.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/test_observed_postprocessing.py](projects/mistral/backend/tests/integration/postprocessing/test_observed_postprocessing.py)
- **Scopo**: verificare gli scenari **observed** di successo su dataset `agrmet`: estrazione semplice; postprocessore `derived_variables`; postprocessore `statistic_elaboration`; catena derived + statistic con export **JSON** e filtro qualità (`only_reliable=True`).
- **Tipologia**: integrazione **end-to-end reale** su dati DBALLE; `data_extract` sincrono via `send_task` → esecuzione reale di `observed_extraction` (DBALLE), `v7d_transform` (BUFR), `dbamsg`, filtro qualità. Marker (modulo): `integration`, `deterministic`, **`runtime_sensitive`**.
- **RUNTIME-SENSITIVE — skip silenziosi (doppia guardia)**: tutti i 4 test usano `pp_observed_env`, che può **skippare** sia per `require_dataset(db,"agrmet")` sia per `require_observed_lastdays()` (variabili `ALCHEMY_*` mancanti **o** nessun dato observed in DBALLE).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| Task `data_extract` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L42) | Ramo `OBS`: stima size observed (solo senza postprocessori) + `observed_extraction` + dispatch postprocessori. |
| `observed_extraction` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L586) | `parse_query_for_data_extraction`; con `reftime=None` imposta `db_type="mixed"` → `extract_data_for_mixed`. |
| `dballe.parse_query_for_data_extraction` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2615) | Costruisce `fields/queries` dai filtri + reti del dataset. |
| `dballe.extract_data_for_mixed` / `extract_data` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2655) | Estrazione BUFR reale da DBALLE/Arkimet. |
| `pp1.pp_derived_variables` (BUFR) | [tools/derived_variables.py](projects/mistral/backend/tools/derived_variables.py#L10) | Per BUFR usa `v7d_transform --input/output-format=BUFR`. |
| `pp2.pp_statistic_elaboration` (BUFR) | [tools/statistic_elaboration.py](projects/mistral/backend/tools/statistic_elaboration.py#L15) | Ramo non-grib: split via `dballe.Importer/Exporter`; `v7d_transform`. |
| `qc.pp_quality_check_filter` | [tools/quality_check_filter.py](projects/mistral/backend/tools/quality_check_filter.py#L7) | Solo `only_reliable=True`: `BeDballe.filter_messages(quality_check=True)`. |
| `output_formatting.pp_output_formatting` | [tools/output_formatting.py](projects/mistral/backend/tools/output_formatting.py#L7) | `dbamsg dump --json`. |
| `BeDballe.LASTDAYS` (override) | [services/dballe.py](projects/mistral/backend/services/dballe.py#L33) | Sovrascritto dalla fixture per la durata del test. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `pp_observed_env` | fixture (**yield**) | [postprocessing/conftest.py](projects/mistral/backend/tests/integration/postprocessing/conftest.py) | Ambiente `agrmet`; override `BeDballe.LASTDAYS` attivo per tutto il test; **skip** su dataset/`ALCHEMY_*`/dati assenti. |
| `observed_derived_variable_filters/postprocessor` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtri B12101+B13003; postprocessor `["B12103"]`. |
| `observed_statistic_elaboration_filters/postprocessor` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtri B12101+B13011; `step=1`, `hours`. |
| `observed_chaining_filters` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | B12101+B13003+B13011 (coprono derived **e** statistic). |
| `env.execute/assert_success` | helper | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Invio reale del task; assert su SUCCESS + file unico non vuoto. |
| `cleanup_registry`, `test_runtime` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown LIFO; gestione override `LASTDAYS`. |
| binari `v7d_transform`, `dbamsg`, libreria `dballe` | sistema | immagine backend | Eseguiti realmente. |

## 4. Analisi dettagliata di ogni test

### `test_simple_observed_extraction_creates_output`
- **Obiettivo**: estrazione observed nuda → file prodotto.
- **Backend coinvolto**: `data_extract` (ramo OBS, **senza** postprocessori → stima size observed via `data.get_observed_data_size_count`) → `observed_extraction` → `extract_data_for_mixed`.
- **Flusso**: `create_request()` → `execute(request_id)` (filters/postprocessors vuoti, `reftime=None`) → `assert_success` + `exists()`.
- **Assert**: SUCCESS, file unico non vuoto.
- **Casi coperti**: happy path estrazione observed reale (con ramo di stima size attivo perché niente postprocessori).

### `test_observed_derived_variables_create_output`
- **Obiettivo**: derived observed (`B12103`, dew-point) riesce con gli input richiesti.
- **Backend coinvolto**: `observed_extraction` (BUFR) → `pp1.pp_derived_variables` con `v7d_transform`.
- **Flusso**: `create_request()` → `execute(filters=observed_derived_variable_filters(), postprocessors=[observed_derived_variable_postprocessor()])` → `assert_success` + `exists()`.
- **Assert**: SUCCESS + file presente (**nessun** controllo sul contenuto BUFR del derivato — vedi §8).
- **Casi coperti**: happy path derived observed.

### `test_observed_statistic_elaboration_creates_output`
- **Obiettivo**: statistic elaboration observed riesce con gli input richiesti.
- **Backend coinvolto**: `pp2.pp_statistic_elaboration` ramo BUFR (`dballe.Importer/Exporter` + `v7d_transform`).
- **Flusso**: `create_request()` → `execute(filters=observed_statistic_elaboration_filters(), postprocessors=[observed_statistic_elaboration_postprocessor()])` → `assert_success` + `exists()`.
- **Assert**: SUCCESS + file presente.
- **Casi coperti**: happy path statistic observed.

### `test_combined_observed_postprocessors_export_json`
- **Obiettivo**: catena derived + statistic con export **JSON** e `only_reliable=True` (filtro qualità).
- **Backend coinvolto**: `observed_extraction` con `only_reliable` → `qc.pp_quality_check_filter` → `pp1` → `pp2` → `output_formatting` (`dbamsg dump --json`).
- **Flusso**: `create_request()` → `execute(filters=observed_chaining_filters(), postprocessors=[derived, statistic], output_format="json", only_reliable=True)` → `assert_success`.
- **Assert**: `output_path.suffix == ".json"`.
- **Casi coperti**: catena observed + QC + conversione formato finale.
- **Nota**: con `only_reliable=True`, `observed_extraction` estrae in un file `_to_be_qcfiltered.tmp`, applica `pp_quality_check_filter` (scarta i dati senza flag qualità validi) e rimuove il tmp; è un percorso reale aggiuntivo non esercitato dagli altri test del file.

## 5. Call chain

```
execute(req)             → send_task("data_extract", user, ["agrmet"], None, filters, [pp], fmt, req, only_reliable)
  data_extract (eager)   → arki.get_datasets_category == "OBS"
                         → [se NON postprocessors] data.get_observed_data_size_count(...) + check_user_quota_for_observed_data
                         → observed_extraction:
                              parse_query_for_data_extraction(...)
                              reftime=None → db_type="mixed" → dballe.extract_data_for_mixed(...)   [DBALLE reale]
                              [only_reliable] qc.pp_quality_check_filter(...)  (BeDballe.filter_messages)
                         → dispatch ORDINE FISSO: derived_variables → statistic_elaboration (rami BUFR/v7d_transform)
                         → [output_format=json] output_formatting (dbamsg dump --json)
                         → check_user_quota → create_fileoutput_record → SUCCESS
assert_success(req)      → Request.status==SUCCESS, fileoutput, file unico non vuoto
```

## 6. Comportamenti nascosti

- **`reftime=None` ⇒ `db_type="mixed"` diretto**: `observed_extraction` non chiama `get_db_type`; l'override `BeDballe.LASTDAYS` agisce attraverso l'estrazione mixed / il conteggio size, non tramite `get_db_type`. Il percorso esatto che consuma `LASTDAYS` con reftime nullo **non è interamente verificabile dal solo codice del task**.
- **Override `LASTDAYS` derivato dai dati reali**: la fixture observed apre una connessione DBALLE reale in setup; quindi i test sono accoppiati allo stato del DB e alla configurazione `ALCHEMY_*` (skip se assenti).
- **Stima size solo senza postprocessori**: il primo test (no postprocessori) attiva `get_observed_data_size_count` + `check_user_quota_for_observed_data`; gli altri (con postprocessori) saltano la stima a monte.
- **`only_reliable` aggiunge uno stadio reale**: il quarto test esercita `pp_quality_check_filter` (filtra messaggi via flag QC `B33007/B33192`); gli altri no.
- **Postprocessori BUFR usano `v7d_transform`** (non `vg6d_transform`) e il ramo `dballe.Importer/Exporter` per lo split statistico — codice diverso dal forecast pur con gli stessi `processor_type`.
- **Assert solo di esito** per derived/statistic observed: si verifica SUCCESS + file, **non** il contenuto (a differenza dei test forecast che leggono il GRIB).

## 7. Checklist di revisione

- [ ] Confermare in CI `ALCHEMY_*`, dati observed in DBALLE per `agrmet`, e i binari `v7d_transform`/`dbamsg` (altrimenti **skip** o **fail** a seconda del punto).
- [ ] Verificare che l'override `LASTDAYS` renda davvero visibile la fetta di dati estratta con `reftime=None`/mixed.
- [ ] Valutare se i test derived/statistic observed debbano asserire anche il **contenuto** BUFR (oggi solo esito).
- [ ] Confermare che `only_reliable=True` produca comunque un output non vuoto dopo il filtro QC (rischio `EmptyOutputFile` se i dati non hanno flag validi).

## 8. Possibili criticità

- **Assert deboli (solo esito)**: derived e statistic observed verificano solo SUCCESS+file; un postprocessore che “riesce” ma non aggiunge/calcola nulla passerebbe comunque.
- **Forte dipendenza d'ambiente**: doppia guardia di skip (dataset + `ALCHEMY_*`/dati); inoltre il filtro QC e l'estrazione mixed dipendono dallo stato reale del DB → possibili `EmptyOutputFile` (fail) su dati poveri.
- **`LASTDAYS` non chiaramente in gioco con `reftime=None`**: l'override è derivato dai dati ma il suo effetto sul percorso mixed non è esplicito dal codice del task; rischio di falsa sicurezza sul controllo della finestra temporale.
- **Skip silenziosi**: un ambiente senza DBALLE configurato rende l'intero file “skipped” senza segnalazione evidente.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_simple_observed_extraction_creates_output` | `observed_extraction`+stima size | estrazione observed → file | nessuno | `pp_observed_env` | Bassa |
| `test_observed_derived_variables_create_output` | `pp1` BUFR (`v7d_transform`) | derived → file (solo esito) | nessuno | `pp_observed_env` | Bassa |
| `test_observed_statistic_elaboration_creates_output` | `pp2` BUFR (`dballe`+`v7d_transform`) | statistic → file (solo esito) | nessuno | `pp_observed_env` | Media |
| `test_combined_observed_postprocessors_export_json` | `qc`+`pp1`+`pp2`+`output_formatting` | catena + QC + export JSON | nessuno | `pp_observed_env` | Alta |
