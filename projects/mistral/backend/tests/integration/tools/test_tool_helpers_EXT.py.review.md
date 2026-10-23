# Review — `test_tool_helpers_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tools/test_tool_helpers_EXT.py](projects/mistral/backend/tests/integration/tools/test_tool_helpers_EXT.py)
- **Scopo**: verificare gli **helper puri** dei tool di post-processing spaziale — mapping dei `sub_type` in `trans_type` per interpolazione griglia (`grid_interpolation.get_trans_type`) e spare-point (`spare_point_interpol.get_trans_type`), normalizzazione `bbox→coordbb` (`grid_cropping.format_sub_type`), e le validazioni di path/template (`grid_interpolation.check_template_filepath`, `spare_point_interpol.check_coord_filepath`) compreso il bundle shapefile e il cleanup della cartella corrotta.
- **Tipologia**: **unit puri**. Nessun binario meteo viene lanciato (`vg6d_transform`, `vg6d_getpoint`, `v7d_transform`): le funzioni mutano l'input o sollevano `BadRequest` **prima** di qualsiasi `subprocess.Popen`. **Nessun monkeypatch**; le sole fixture sono la built-in `tmp_path` e `pytest.mark.parametrize`. Marker dichiarati: `integration`, `deterministic` (vedi §6 per la discrepanza marker↔natura reale).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `grid_interpolation.get_trans_type` | [tools/grid_interpolation.py](projects/mistral/backend/tools/grid_interpolation.py#L14) | `near/bilin → "inter"`; `average/min/max → "boxinter"`; muta `params["trans_type"]` (due `if` **non** esclusivi). |
| `grid_interpolation.check_template_filepath` | [tools/grid_interpolation.py](projects/mistral/backend/tools/grid_interpolation.py#L9) | `BadRequest` se il `Path` template non esiste; altrimenti ritorno implicito `None`. |
| `spare_point_interpol.get_trans_type` | [tools/spare_point_interpol.py](projects/mistral/backend/tools/spare_point_interpol.py#L10) | `near/bilin → "inter"`; `average/min/max → "polyinter"`. |
| `spare_point_interpol.check_coord_filepath` | [tools/spare_point_interpol.py](projects/mistral/backend/tools/spare_point_interpol.py#L20) | Valida esistenza file; `suffix.strip(".") == file_format`; per `shp` richiede `.shx` e `.dbf` siblings, altrimenti `shutil.rmtree(parent)` + `BadRequest`. |
| `grid_cropping.format_sub_type` | [tools/grid_cropping.py](projects/mistral/backend/tools/grid_cropping.py#L8) | `bbox → "coordbb"`; ogni altro valore **passthrough**. |
| `BadRequest` | `restapi.exceptions` | Sollevata da tutte le validazioni in errore. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `tmp_path` | fixture | `pytest` (built-in) | Directory temporanea per i check di esistenza/suffisso; pulita da pytest. |
| `pytest.mark.parametrize` | marker | `pytest` | Casi table-driven per i `sub_type` e i formati. |
| `BadRequest` | eccezione | `restapi.exceptions` | Target di `pytest.raises`. |
| `shutil.rmtree` | stdlib | (in `spare_point_interpol.check_coord_filepath`) | Cancella la cartella del bundle shapefile corrotto (effetto collaterale su filesystem). |
| `mistral.tools.{grid_cropping, grid_interpolation, spare_point_interpol}` | moduli | [tools/](projects/mistral/backend/tools) | Espongono gli helper sotto test; importati a livello di modulo. |
| `pytest.mark.integration` / `deterministic` | marker | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L9) | Solo classificazione. |

> **Nota infra**: nessun `conftest.py`/`support` locale in `integration/tools/`. Nessuna fixture condivisa: solo `tmp_path` built-in. Le fixture suite ([`test_runtime`/`cleanup_registry`](projects/mistral/backend/tests/conftest.py#L31)) non sono richieste.

## 4. Analisi dettagliata di ogni test

> Tutti i test sono metodi di `TestToolHelpers`. I primi tre usano `parametrize`; in totale **9 funzioni di test → 18 casi**.

### `test_grid_interpolation_get_trans_type_maps_known_subtypes` (parametrize ×5)
- **Obiettivo**: i `sub_type` noti mutano `params["trans_type"]` nella modalità attesa.
- **Backend coinvolto**: `grid_interpolation.get_trans_type`.
- **Flusso**: `params={"sub_type": ...}` per `near/bilin/average/min/max`.
- **Setup**: dict locale (nessun GRIB, nessun subprocess).
- **Assert**: `near/bilin → "inter"`; `average/min/max → "boxinter"`.
- **Casi coperti**: mapping completo dei sub_type noti. Non copre un sub_type **ignoto** (vedi §6).

### `test_spare_point_get_trans_type_maps_known_subtypes` (parametrize ×5)
- **Obiettivo**: i `sub_type` spare-point scelgono la modalità di interpolazione punto.
- **Backend coinvolto**: `spare_point_interpol.get_trans_type`.
- **Flusso**: come sopra, valori `near/bilin/average/min/max`.
- **Setup**: dict locale.
- **Assert**: `near/bilin → "inter"`; `average/min/max → "polyinter"` (differenza chiave vs `boxinter`).
- **Casi coperti**: mapping completo; documenta `polyinter` vs `boxinter`.

### `test_grid_cropping_format_sub_type_normalizes_bbox_only` (parametrize ×2)
- **Obiettivo**: il `sub_type` UI `bbox` è tradotto nel `coordbb` di vg6d.
- **Backend coinvolto**: `grid_cropping.format_sub_type`.
- **Flusso**: `"bbox"` e `"coord"`.
- **Setup**: stringhe pure (nessun input GRIB).
- **Assert**: `"bbox" → "coordbb"`; `"coord" → "coord"` (passthrough).
- **Casi coperti**: normalizzazione `bbox`. Non copre valori ignoti (passthrough non validato, §6).

### `test_check_template_filepath_existing_file_returns_none`
- **Obiettivo**: un template esistente è accettato senza toolchain.
- **Backend coinvolto**: `grid_interpolation.check_template_filepath`.
- **Flusso**: crea `tmp_path/template.grib` con contenuto testuale; passa il `Path`.
- **Setup**: `tmp_path`.
- **Assert**: `result is None` (ritorno implicito).
- **Casi coperti**: happy path esistenza file.

### `test_check_template_filepath_missing_file_raises_bad_request`
- **Obiettivo**: un template mancante è respinto prima del subprocess.
- **Backend coinvolto**: `check_template_filepath` (ramo `not exists → BadRequest`).
- **Flusso**: `Path` mai creato.
- **Setup**: `tmp_path`.
- **Assert**: `pytest.raises(BadRequest)`.
- **Casi coperti**: error path validazione template.

### `test_check_coord_filepath_missing_file_raises_bad_request`
- **Obiettivo**: file coordinate mancante respinto subito.
- **Backend coinvolto**: `spare_point_interpol.check_coord_filepath` (primo guard `not exists`).
- **Flusso**: `params={coord_filepath: tmp_path/missing.shp, file_format: "shp"}` senza creare il file.
- **Setup**: `tmp_path`.
- **Assert**: `pytest.raises(BadRequest)`.
- **Casi coperti**: error path esistenza. Il file non esiste → la guardia scatta prima del ramo shapefile (nessun `rmtree`).

### `test_check_coord_filepath_wrong_format_raises_bad_request`
- **Obiettivo**: suffisso reale incoerente con `file_format` dichiarato → respinto.
- **Backend coinvolto**: `check_coord_filepath` (ramo `suffix.strip(".") != file_format`).
- **Flusso**: file `points.csv` esistente ma `file_format="shp"`.
- **Setup**: `tmp_path` + file CSV reale.
- **Assert**: `pytest.raises(BadRequest)`.
- **Casi coperti**: secondo guard (coerenza formato), raggiunto perché il file esiste. Il controllo `csv != shp` precede il ramo shp → nessun `rmtree`.

### `test_check_coord_filepath_valid_shapefile_bundle_returns_none`
- **Obiettivo**: un bundle shapefile completo (placeholder) supera la preflight.
- **Backend coinvolto**: `check_coord_filepath` (ramo `shp` con `.shx`/`.dbf` presenti).
- **Flusso**: sottocartella con `points.shp` + `.shx` + `.dbf` (contenuto placeholder).
- **Setup**: `tmp_path/valid-bundle`.
- **Assert**: `result is None`.
- **Casi coperti**: happy path bundle. L'helper **non** interpreta il contenuto: verifica solo la presenza dei siblings (§6).

### `test_check_coord_filepath_corrupt_shapefile_bundle_removes_folder`
- **Obiettivo**: un bundle incompleto è respinto e la sua cartella **eliminata**.
- **Backend coinvolto**: `check_coord_filepath` (ramo `shp` con sibling mancanti → `shutil.rmtree(parent)` + `BadRequest`).
- **Flusso**: sottocartella con solo `points.shp` (mancano `.shx`/`.dbf`).
- **Setup**: `tmp_path/corrupt-bundle`.
- **Assert**: `pytest.raises(BadRequest)` **e** `not bundle_dir.exists()`.
- **Casi coperti**: error path + side effect distruttivo (cancellazione cartella). La `.shp` è in una sottocartella dedicata, quindi `rmtree` colpisce solo il bundle, non `tmp_path` (§6).

## 5. Call chain

```
grid_interpolation.get_trans_type(params)                    [test_grid_interpolation_*]
  → sub_type in (near,bilin) → params["trans_type"]="inter"
  → sub_type in (average,min,max) → params["trans_type"]="boxinter"     (due if NON esclusivi)

spare_point_interpol.get_trans_type(params)                  [test_spare_point_*]
  → sub_type in (near,bilin) → "inter"
  → sub_type in (average,min,max) → "polyinter"

grid_cropping.format_sub_type(sub_type)                      [test_grid_cropping_*]
  → sub_type=="bbox" → "coordbb" : else → sub_type   (passthrough)

grid_interpolation.check_template_filepath(template_file)    [test_check_template_*]
  → not template_file.exists() → BadRequest : (None implicito)

spare_point_interpol.check_coord_filepath(params)            [test_check_coord_*]
  → coord = Path(params["coord_filepath"])
  → not coord.exists() → BadRequest("coord-filepath does not exists")
  → coord.suffix.strip(".") != params["file_format"] → BadRequest("format ... not correct")
  → file_format=="shp" and (.shx o .dbf mancante) → shutil.rmtree(coord.parent) + BadRequest("corrupted")
  → (None implicito)
```

## 6. Comportamenti nascosti

- **Marker fuorviante**: classificati `integration` ma sono **unit puri**; nessun binario meteo, nessun DB, nessun HTTP. Le funzioni ritornano/sollevano prima di `subprocess.Popen`.
- **`get_trans_type` con due `if` non esclusivi**: un `sub_type` **ignoto** lascia `params["trans_type"]` **non impostato** (nessun default, nessun errore nella funzione) → potenziale `KeyError` a valle. Non coperto.
- **Stesso prefisso, esito diverso**: `near/bilin → "inter"` in entrambi i tool, ma il secondo ramo è `boxinter` (griglia) vs `polyinter` (spare-point).
- **`check_template_filepath` senza `return` esplicito**: ritorna `None`; il test lo asserisce.
- **`suffix.strip(".")`**: rimuove i punti **a entrambi gli estremi** del suffisso; corretto per casi normali (`.shp→shp`), ma sensibile a nomi anomali. Non testato su input degeneri.
- **Ordine dei guard in `check_coord_filepath`**: esistenza → coerenza formato → bundle `shp`. Quindi i test "missing" e "wrong format" **non** raggiungono il ramo `rmtree` (la guardia scatta prima).
- **`rmtree(parent)` distruttivo**: il ramo corrotto cancella l'**intera cartella padre** della `.shp`. I test isolano la `.shp` in una sottocartella dedicata, così la cancellazione non tocca `tmp_path`; in runtime, se la `.shp` stesse in una cartella condivisa, l'impatto sarebbe più ampio (vedi §8).
- **`format_sub_type` passthrough**: qualunque valore diverso da `bbox` passa invariato (anche valori non validi) — nessuna validazione.
- **Convenzioni di chiamata diverse**: `check_template_filepath` riceve un `Path`; `check_coord_filepath` riceve un `params` dict e costruisce il `Path` internamente.
- **Bundle shapefile non interpretato**: la validazione `shp` controlla solo l'esistenza di `.shx`/`.dbf`, non il contenuto → placeholder vuoti passano (per design).
- **Nessuno `skip`**: tutti i 18 casi eseguono sempre.

## 7. Checklist di revisione

- [ ] Confermare che la natura **unit** sia voluta nonostante marker/collocazione `integration`.
- [ ] Valutare un caso `sub_type` **ignoto** per `get_trans_type` (oggi lascia `trans_type` non impostato → `KeyError` latente a valle).
- [ ] Confermare che lo `shutil.rmtree(parent)` sul bundle corrotto abbia un raggio d'azione accettabile; eventualmente asserire che colpisca **solo** la cartella del bundle.
- [ ] Confermare che il passthrough di `format_sub_type` (nessuna validazione dei valori) sia intenzionale.
- [ ] Confermare la divergenza di firma `check_template_filepath` (`Path`) vs `check_coord_filepath` (`params` dict).
- [ ] Notare che gli shapefile placeholder superano la validazione (contenuto non ispezionato).

## 8. Possibili criticità

- **Marker mismatch (unit vs integration)**: la collocazione suggerisce flussi runtime con binari che qui non avvengono.
- **`get_trans_type` su sub_type ignoto**: silenzioso no-op che lascia `trans_type` mancante → `KeyError`/comando malformato a valle; non coperto.
- **`rmtree(parent)` potenzialmente pericoloso**: in produzione, se il file coordinate risiede in una cartella di upload condivisa, l'intera cartella verrebbe rimossa; i test lo isolano in sottocartelle, quindi il **raggio distruttivo reale non è assertito** qui.
- **`format_sub_type` senza validazione**: sub_type non validi fluiscono inalterati verso vg6d; non coperto.
- **`suffix.strip(".")` sottile**: potenziale mishandling di nomi insoliti (più punti); non testato.
- **Validazione `shp` superficiale**: solo presenza di `.shx`/`.dbf`, non integrità; placeholder vuoti passano (per design, ma da tenere presente).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_grid_interpolation_get_trans_type_maps_known_subtypes` | `grid_interpolation.get_trans_type` | sub_type → `inter`/`boxinter` | — | `parametrize` | Bassa |
| `test_spare_point_get_trans_type_maps_known_subtypes` | `spare_point_interpol.get_trans_type` | sub_type → `inter`/`polyinter` | — | `parametrize` | Bassa |
| `test_grid_cropping_format_sub_type_normalizes_bbox_only` | `grid_cropping.format_sub_type` | `bbox→coordbb`, passthrough | — | `parametrize` | Bassa |
| `test_check_template_filepath_existing_file_returns_none` | `check_template_filepath` | file esistente → `None` | — | `tmp_path` | Bassa |
| `test_check_template_filepath_missing_file_raises_bad_request` | `check_template_filepath` | file mancante → `BadRequest` | — | `tmp_path` | Bassa |
| `test_check_coord_filepath_missing_file_raises_bad_request` | `check_coord_filepath` | coord mancante → `BadRequest` | — | `tmp_path` | Bassa |
| `test_check_coord_filepath_wrong_format_raises_bad_request` | `check_coord_filepath` | suffisso ≠ formato → `BadRequest` | — | `tmp_path` | Bassa |
| `test_check_coord_filepath_valid_shapefile_bundle_returns_none` | `check_coord_filepath` | bundle `.shp/.shx/.dbf` → `None` | — | `tmp_path` | Media |
| `test_check_coord_filepath_corrupt_shapefile_bundle_removes_folder` | `check_coord_filepath` | bundle incompleto → `BadRequest` + `rmtree` | — | `tmp_path` | Media |
