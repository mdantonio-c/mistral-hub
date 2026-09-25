# Review — `postprocessing/support.py` (infrastruttura di dominio)

> File di review per modulo di supporto (builder, dataclass, helper, assert GRIB). Non contiene test.
> Struttura **ADATTATA** (modulo di supporto, non file di test).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py)
- **Scopo**: fornire ai test di postprocessing tutto ciò che serve per esercitare la pipeline reale di estrazione+postprocessing: creazione utente dedicato, creazione/cancellazione `Request`, **invio del task `data_extract`** (successo e fallimento), assert sull'esito (file prodotto o `status=FAILURE`), payload pronti di filtri/postprocessori e assert sui messaggi GRIB via `eccodes`.
- **Tipologia**: modulo di supporto locale al dominio postprocessing (nessun test al suo interno; importato da `conftest.py` e dai 5 file `test_*`).
- **Punto cruciale**: la classe `PostprocessingEnv.execute` è il **vero motore** dei test: invoca il task Celery `data_extract` in modo **sincrono/eager** tramite `BaseTests.send_task`, quindi esegue realmente estrazione Arkimet/DBALLE e i **binari esterni** (`vg6d_transform`, `v7d_transform`, `vg6d_getpoint`, `dbamsg`, `cat`, `eccodes`).

## 2. Backend realmente esercitato (tramite i builder/helper)

| Elemento backend | Path | Esercitato da |
|---|---|---|
| Task `data_extract` (intera pipeline) | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L42) | `PostprocessingEnv.execute` → `send_task("data_extract", …)`. |
| `BaseTests.send_task` | `restapi.tests` | Recupera il task registrato per nome e lo **chiama direttamente** (`task(*args, **kwargs)`): esecuzione sincrona in-process, non delega al worker. |
| Hook fallimento Celery `mark_task_as_failed` / `mark_task_as_failed_ignore` | `restapi.connectors.celery` | **Monkeypatchati a mano** dal ramo `expect_failure=True` di `execute` (vedi §3 e §4). |
| `notify_by_email` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py) | Sostituito con no-op dal ramo `expect_failure=True` per sopprimere l'email reale nel `finally` del task. |
| `SqlApiDbManager.create_request_record` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py) | `PostprocessingSupport.create_request` inserisce la riga `Request`. |
| `arki.arkimet_extraction` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L355) | Estrazione forecast reale (`lm5`). |
| `observed_extraction` → `dballe.extract_data_for_mixed` / `extract_data` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L586), [services/dballe.py](projects/mistral/backend/services/dballe.py#L2755) | Estrazione observed reale (`agrmet`). |
| `BeDballe.LASTDAYS` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L33) | Letto da `require_observed_lastdays`; sovrascritto in `pp_observed_env`. |
| `eccodes` (lettura GRIB) | libreria di sistema | Tutti gli `assert_grib_*` aprono il file prodotto e leggono `shortName`/`stepRange`/geometria. |

## 3. Elementi definiti

### Dataclass
- **`PostprocessingUser`** (`frozen`): `uuid`, `user_id`, `headers`, `output_dir`. Proprietà derivate: `root_dir` (= `output_dir.parent`, cioè `DOWNLOAD_DIR/<uuid>`) e `upload_dir` (= `root_dir/uploads`). La separazione `outputs/` vs `uploads/` è importante: i template caricati vivono in `uploads/` e **non inquinano** il conteggio dei file di output (vedi `assert_extraction_success`).
- **`PostprocessingEnv`** (mutabile): bundle `base/app/client/faker/db/cleanup_registry/dataset_name/user`. Espone i metodi operativi descritti sotto.

### `PostprocessingSupport(BaseTests)`
- **`create_request(db, user_id, request_name)`** → inserisce una `Request` (args `{}`) via `SqlApiDbManager.create_request_record`; ritorna l'id.
- **`assert_extraction_success(db, request_id, user_dir)`** → asserisce `request is not None`, `status == "SUCCESS"`, `fileoutput is not None`, che il file esista, sia **non vuoto** e che la cartella outputs contenga **esattamente un file** (`len(glob("*")) == 1`). Ritorna il `Path` prodotto.
- **`delete_request(client, headers, request_id)`** → `DELETE /api/requests/<id>` (asserisce 200): cancellazione via **API pubblica** reale.

### `PostprocessingEnv` — metodi chiave
- **`create_request()`** → crea la riga e registra **subito** il cleanup DB (`delete_request_row`) nel `cleanup_registry` (LIFO).
- **`execute(request_id, *, filters, postprocessors, output_format, only_reliable, expect_failure=False)`** → cuore del modulo:
  - `expect_failure=False`: chiama direttamente `base.send_task(app, "data_extract", user_id, [dataset_name], None, filters, postprocessors or [], output_format, request_id, only_reliable)`. **`reftime` è sempre `None`** (terzo argomento). Esecuzione reale della pipeline.
  - `expect_failure=True`: salva e **sostituisce a mano** tre simboli globali → `celery_connector.mark_task_as_failed` con una funzione che fa `raise Ignore(str(exception))`; `celery_connector.mark_task_as_failed_ignore` con una che fa `raise exception` (rilancia l'`Ignore` originale); `data_extraction_task.notify_by_email` con un no-op. Poi invia il task in `try/finally` ripristinando gli originali nel `finally`. In questo modo l'errore del postprocessing **emerge come eccezione Python** (`Ignore`) intercettabile dal test, senza far partire la gestione worker-side (update_state/send_event/email).
- **`assert_success(request_id)`** → delega a `assert_extraction_success` su `user.output_dir`.
- **`assert_failure(request_id, expected_message="Error in post-processing")`** → asserisce `status == "FAILURE"` e, se `expected_message` non è `None`, che sia contenuto in `request.error_message`.
- **`delete_request(request_id)`** → cancellazione via API pubblica (serve nei test che ricostruiscono lo scenario, es. template GI).
- **`ensure_upload_dir` / `copy_upload` / `unzip_upload`** → preparano la cartella `uploads/` e vi copiano/estraggono i template (GRIB di seed, shapefile spare-point).

### Builder di payload (filtri & postprocessori)
- Forecast: `forecast_pressure_filter`, `forecast_derived_variable_filters` (+ `…_missing_filters`), `forecast_derived_variable_postprocessor` (variabili `["B13003"]`), `forecast_statistic_elaboration_filters` (+ `…_missing_filters`), `forecast_statistic_elaboration_postprocessor` (`input/output_timerange=1`, `interval=hours`, `step=3`), `forecast_chaining_filters` (P+T+dewpoint+Q+TP).
- Spaziali: `grid_interpolation_without_template(x_min,y_min,nx)` (`x_max=20,y_max=10,ny=nx`, `inter/bilin`), `grid_interpolation_with_template(template_path)`, `grid_cropping_postprocessor(initial_lon,initial_lat)` (`flon=10,flat=5`, `zoom/coord`), `spare_point_postprocessor(template_path)` (`shp`, `inter/bilin`).
- Observed: `observed_derived_variable_*` (postprocessor `["B12103"]`), `observed_statistic_elaboration_*` (`step=1`), `observed_chaining_filters` (B12101+B13003+B13011).

### Guardie di skip (RUNTIME-SENSITIVE) e helper GRIB
- **`require_dataset(db, name)`** → `pytest.skip` se il dataset non esiste nella tabella `Datasets` (match su `name` **o** `arkimet_id`).
- **`require_observed_lastdays()`** → `pytest.skip` se le variabili `ALCHEMY_*` non sono configurate **oppure** se non ci sono dati observed reali in DBALLE; altrimenti **si connette al DB DBALLE reale** e calcola un `LASTDAYS` derivato dalla prima riga di `query_data({})`.
- **`require_spare_point_template_archive()`** → `pytest.skip` se manca `/data/templates_for_pp/template_for_spare_point.zip`.
- **`delete_request_row(db, id)`** → cancellazione diretta su DB (cleanup), no-op se la riga non esiste.
- **`iter_grib_messages` / `assert_grib_contains_short_name` / `…_preserves_independent_fields` / `…_contains_step_range` / `…_contains_short_name_other_than` / `assert_grib_geometry` / `assert_grib_messages_have_geometry`** → leggono i messaggi GRIB del file prodotto via `eccodes` e verificano contenuto/geometria.

## 4. Comportamenti nascosti

- **Pipeline 100% reale nel ramo successo**: `send_task` chiama il task registrato come funzione normale → l'estrazione e **tutti i binari esterni** vengono eseguiti davvero. Non c'è alcun mock dei tool nel percorso di successo: l'esito dipende dalla presenza dei dati e dei tool nell'ambiente.
- **`reftime` sempre `None`**: `execute` passa `None` come reftime. Per il forecast la query Arkimet usa solo `parse_matchers(filters)` (nessun filtro temporale). Per l'observed, `observed_extraction` con `reftime` falsy imposta `db_type="mixed"` **senza** chiamare `get_db_type`: l'effetto dell'override `LASTDAYS` passa quindi attraverso l'estrazione mixed / il conteggio size, non attraverso `get_db_type` (dettaglio non interamente verificabile dal solo task).
- **Monkeypatch globale manuale** (non `monkeypatch`/`test_runtime`): `execute(expect_failure=True)` riscrive attributi di modulo condivisi (`restapi.connectors.celery`, `mistral.tasks.data_extraction`). Il ripristino avviene nel `finally`; è sicuro per le normali eccezioni ma è uno stato globale (rischioso sotto esecuzione parallela/`xdist`).
- **Due hook di fallimento, due percorsi**: i test d'errore esercitano *entrambi* i rami del wrapper `@CeleryExt.task`. Postprocessore sconosciuto → `ValueError` non catturata dal primo `except` del task → ramo generico (`error_message="Failed to extract data"`, rilancio) → `mark_task_as_failed`. Input incompleti → `PostProcessingException` → primo `except` del task (`error_message=str(exc)`, `raise Ignore`) → `mark_task_as_failed_ignore`. Per questo entrambi gli hook sono patchati.
- **`error_message` persistito ≠ messaggio dell'eccezione** nel caso “postprocessore sconosciuto”: il DB salva `"Failed to extract data"`, mentre l'`Ignore` porta `"Unknown post-processor"`. (Vedi review di `test_error_handling.py`.)
- **`assert_extraction_success` impone un solo file in `outputs/`**: i test che generano un file intermedio (es. seed del template GI) devono cancellarlo (`delete_request`) prima di riasserire; i template caricati vanno in `uploads/` proprio per non contare in quel glob.
- **Email su successo non patchata**: nei test di successo `notify_by_email` non è sostituita; il `finally` del task la chiama solo se `notify_on_successful_request` dell'utente è vero. L'utente di test è creato senza quel flag, quindi (di default) nessuna email parte. È un'assunzione implicita sull'ambiente SMTP.
- **`require_observed_lastdays` apre una connessione reale a DBALLE** in fase di setup fixture: è I/O esterno dentro l'arrange, e fa `skip` (non fail) se manca configurazione/dati.
- **`assert_grib_contains_short_name_other_than(file, excluded, expected)`**: il parametro `excluded` è **ignorato**; la funzione verifica solo che `expected` sia presente. L'assert è più debole di quanto il nome suggerisca.

## 5. Checklist di revisione

- [ ] Confermare che in CI i tre binari/famiglie (`vg6d_transform`/`v7d_transform`/`vg6d_getpoint`, `dbamsg`, `cat`, `eccodes`) siano installati: senza, i test di successo **falliscono** (non skippano).
- [ ] Verificare che `lm5` e `agrmet` esistano **e contengano dati** estraibili senza reftime; la guardia `require_dataset` copre solo l'esistenza della riga, non la presenza di dati.
- [ ] Verificare che il monkeypatch manuale di `restapi.connectors.celery` non interferisca con altri test in esecuzione parallela.
- [ ] Confermare che l'assunzione “nessuna email su successo” (flag utente) sia voluta e stabile.
- [ ] Valutare se `assert_grib_contains_short_name_other_than` debba davvero verificare anche l'esclusione di `excluded`.
- [ ] Confermare che `require_observed_lastdays` debba davvero connettersi a DBALLE in setup (accoppiamento I/O nell'arrange).

## 6. Possibili criticità

- **Forte dipendenza dall'ambiente**: i test di successo sono integrazione end-to-end reale (dati + binari + filesystem). Su un runner privo di dati/tool il file singolo non viene prodotto e l'assert fallisce: il confine fra “skip atteso” e “fail d'ambiente” è sottile.
- **Over-/under-mocking nel ramo fallimento**: il ramo `expect_failure` riscrive simboli globali di un connettore condiviso a mano. Funziona, ma è fragile e nasconde quale parte della gestione errori sia realmente sotto test (gli hook reali `mark_task_as_failed*` non vengono eseguiti).
- **Assert “esattamente un file”**: accoppia i test alla pulizia esplicita degli output intermedi; un cambio di layout (es. file `.tmp` non rimossi) farebbe fallire scenari corretti.
- **Helper con assert silenziosi sull'esclusione**: `assert_grib_contains_short_name_other_than` può dare falsa sicurezza.
- **Skip silenziosi diffusi**: `require_dataset`, `require_observed_lastdays`, `require_spare_point_template_archive` possono far sparire interi file dalla copertura senza segnalazione evidente in CI.
