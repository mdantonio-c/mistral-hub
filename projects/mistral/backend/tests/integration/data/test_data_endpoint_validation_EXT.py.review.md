# Review — `test_data_endpoint_validation_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** delle validazioni HTTP di `POST /data`, sopra il baseline auth.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/test_data_endpoint_validation_EXT.py](projects/mistral/backend/tests/integration/data/test_data_endpoint_validation_EXT.py)
- **Scopo**: verificare i **rami di rifiuto** di `POST /data` prima della submission: dataset inesistente (`404`), formati misti (`400`), gruppi licenza differenti (`400`), `output_format` invalido a livello schema (`400`), `output_format` valido ma incompatibile con grib (`400`), postprocessor non autorizzato (`401`), `only_reliable` non supportato (`400`).
- **Tipologia**: test di **integrazione HTTP** (controller + schema + DB reali) con `monkeypatch` di Arkimet **solo dove il ramo lo richiede**. Marker: `integration`, `deterministic`. 7 test.
- **Invariante**: ogni ramo deve **fallire prima** di `create_request_record` → tutti gli assert includono `latest_request_for_user(...) is None`. Nessun `pytest.skip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Data.post` | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | Sequenza di guardie di validazione (vedi call chain). |
| `DataExtraction` (+ `@pre_load check_output_format`) | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | Schema Marshmallow: `output_format ∉ {json,bufr}` → `400` **a livello schema** (prima del corpo endpoint). |
| `AVProcessor` | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | Schema del postprocessor `derived_variables`; valida `processor_type` + `variables` (OneOf `DERIVED_VARIABLES`). |
| `repo.get_datasets` | [services/sqlapi_db_manager.py#L482](projects/mistral/backend/services/sqlapi_db_manager.py#L482) | Catalogo autorizzato: dataset assente → `NotFound 404`. |
| `arki.get_datasets_format` | [services/arkimet.py#L197](projects/mistral/backend/services/arkimet.py#L197) | Formato comune; `None` → `BadRequest 400` (qui **fakeato**). |
| `repo.get_license_group` | [services/sqlapi_db_manager.py#L546](projects/mistral/backend/services/sqlapi_db_manager.py#L546) | Gruppo licenza comune (reale); gruppi diversi → `None` → `400`. |
| `repo.get_user_permissions` | [services/sqlapi_db_manager.py#L665](projects/mistral/backend/services/sqlapi_db_manager.py#L665) | `allowed_postprocessing`; falsy → `Unauthorized 401`. |
| `arki.get_datasets_category` | [services/arkimet.py#L218](projects/mistral/backend/services/arkimet.py#L218) | Categoria (`OBS`/`FOR`/…); usata dal ramo `only_reliable` (qui **fakeata**). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py#L39](projects/mistral/backend/tests/conftest.py#L39) | Teardown LIFO di utenti e dataset. |
| `monkeypatch` | fixture | `pytest` | Presente **solo** nei test che fakeano Arkimet (assente nei test 1 e 4). |
| `create_synthetic_dataset` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Dataset/licenza/gruppo/attribution sintetici. |
| `create_data_endpoint_user` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Utente temporaneo (senza `allowed_postprocessing` di default). |
| `build_data_payload` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Body con `overrides` per il campo dello scenario. |
| `patch_data_endpoint_runtime` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | `monkeypatch` Arkimet (formato/categoria). |
| `latest_request_for_user` | helper | [data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py) | Asserisce assenza di request persistite. |
| `BaseTests().get_content` | util | `restapi.tests` | Decodifica body (solo test 4, per cercare `output_format`). |
| `DatasetCategories` | enum | [models/sqlalchemy.py#L132](projects/mistral/backend/models/sqlalchemy.py#L132) | Categoria del dataset sintetico (`FOR`). |

## 4. Analisi dettagliata di ogni test

### `test_post_data_returns_404_for_missing_dataset`
- **Obiettivo**: dataset non autorizzato/inesistente → `404` immediato.
- **Backend coinvolto**: `repo.get_datasets` (reale) → `NotFound`. **Niente fake**: il backend si ferma prima di Arkimet.
- **Flusso**: utente **senza** dataset collegati → payload con nome `"missing_dataset_ext"` → `POST /data`.
- **Setup**: nessun `monkeypatch`; nessun dataset creato.
- **Assert**: `404`; nessuna request creata.
- **Casi coperti**: error path / esistenza-visibilità dataset.

### `test_post_data_returns_400_for_mixed_dataset_formats`
- **Obiettivo**: set di dataset con formati incompatibili → `400`.
- **Backend coinvolto**: `arki.get_datasets_format` → `None` → `BadRequest`. (Il check formato precede quello sui gruppi licenza.)
- **Flusso**: due dataset (grib + bufr) visibili all'utente → `patch_data_endpoint_runtime(dataset_format=None)` → `POST /data`.
- **Setup**: `monkeypatch` con `dataset_format=None` (segnatura del caso misto).
- **Assert**: `400`; nessuna request.
- **Casi coperti**: error path / formato. Isola il ramo formato (anche se i gruppi licenza differiscono, il 400 scatta prima).

### `test_post_data_returns_400_for_different_license_groups`
- **Obiettivo**: dataset di gruppi licenza diversi → `400`.
- **Backend coinvolto**: `repo.get_license_group` (**reale**) → `None`. Il formato è fakeato a `"grib"` per superare il ramo precedente.
- **Flusso**: due dataset, **ciascuno con il proprio gruppo licenza** (`group_name` default univoco) → `patch_data_endpoint_runtime(dataset_format="grib")` → `POST /data`.
- **Setup**: `monkeypatch` formato/categoria; gruppi licenza distinti via helper.
- **Assert**: `400`; nessuna request.
- **Casi coperti**: error path / licenze. Il controllo licenze gira sul repository reale.

### `test_post_data_returns_400_for_invalid_output_format_schema`
- **Obiettivo**: `output_format` non ammesso → `400` **a livello schema**.
- **Backend coinvolto**: `DataExtraction.@pre_load check_output_format` (durante `use_kwargs`), **prima** del corpo `Data.post`. **Niente fake**.
- **Flusso**: dataset valido + utente → payload con `output_format="csv"` → `POST /data`.
- **Setup**: nessun `monkeypatch` (non si arriva ad Arkimet né al DB applicativo).
- **Assert**: `400`; `"output_format" in str(content)`; nessuna request.
- **Casi coperti**: validazione schema Marshmallow. L'assert su stringa è robusto rispetto al wrapper restapi.

### `test_post_data_returns_400_when_output_format_is_incompatible_with_grib`
- **Obiettivo**: `output_format` valido per schema (`json`) ma incompatibile con grib → `400` **applicativo**.
- **Backend coinvolto**: ramo `if output_format is not None:` → `dataset_format=="grib"` e `"spare_point_interpolation"` assente → `BadRequest`.
- **Flusso**: dataset grib → `patch_data_endpoint_runtime(dataset_format="grib")` → payload con `output_format="json"` → `POST /data`.
- **Setup**: `monkeypatch` formato grib.
- **Assert**: `400`; nessuna request.
- **Casi coperti**: error path applicativo. Distingue il `400` schema (`csv`) dal `400` logica (`json` su grib).

### `test_post_data_returns_401_for_unauthorized_postprocessor_usage`
- **Obiettivo**: uso di postprocessor senza permesso → `401`.
- **Backend coinvolto**: `if postprocessors:` → `repo.get_user_permissions(allowed_postprocessing)` falsy → `Unauthorized`.
- **Flusso**: utente **senza** `allowed_postprocessing` → payload con postprocessor `derived_variables` (variabile `B12194`, valida per schema `AVProcessor`) → `POST /data`.
- **Setup**: `patch_data_endpoint_runtime(format="grib", category="FOR")`; il postprocessor passa la validazione schema per **raggiungere** il controllo autorizzativo.
- **Assert**: `401`; nessuna request.
- **Casi coperti**: error path / autorizzazione applicativa (distinta dal `401` di autenticazione del baseline).

### `test_post_data_returns_400_when_only_reliable_is_not_supported`
- **Obiettivo**: `only_reliable` su dataset non `OBS`/non `multim-forecast` → `400`.
- **Backend coinvolto**: `data_type = arki.get_datasets_category` (fakeato `"FOR"`) → `if only_reliable and data_type!="OBS" and "multim-forecast" not in dataset_names:` → `BadRequest`.
- **Flusso**: dataset `FOR`/grib → `patch_data_endpoint_runtime(format="grib", category="FOR")` → payload con `only_reliable=True` → `POST /data`.
- **Setup**: `monkeypatch` formato/categoria.
- **Assert**: `400`; nessuna request.
- **Casi coperti**: error path / opzione non supportata.

## 5. Call chain

```
POST /api/data  → auth.require()
  → use_kwargs(DataExtraction)
       └ @pre_load check_output_format   → output_format ∉ {json,bufr} → 400   [TEST 4]
       └ Postprocessors._deserialize / AVProcessor.load (schema postprocessor)
  → Data.post:
      1. repo.check_user_request_limit
      2. repo.get_datasets → ds_name ∉ catalogo → 404                          [TEST 1]
      3. arki.get_datasets_format → None → 400                                  [TEST 2]   (FAKE=None)
      4. repo.get_license_group → None → 400                                    [TEST 3]   (FAKE format="grib")
      7. postprocessors? → get_user_permissions(allowed_postprocessing) → 401   [TEST 6]
      8. output_format & dataset_format=="grib" & no SPI → 400                  [TEST 5]
     10. data_type = arki.get_datasets_category                                  (FAKE="FOR")
     11. only_reliable & data_type!="OBS" & no multim-forecast → 400            [TEST 7]
     (... mai raggiunti: push, quota OBS, create_request_record, send_task)
```

## 6. Comportamenti nascosti

- **Due `400` di natura diversa**: il test 4 colpisce il `@pre_load` dello schema (fuori dal corpo endpoint, nessun DB/Arkimet); il test 5 colpisce la logica applicativa `Data.post`. La distinzione è il punto di valore della coppia.
- **Test 1 e 4 senza `monkeypatch`**: si fermano prima di Arkimet (rispettivamente a `get_datasets` reale e al `pre_load` schema), quindi non importano `monkeypatch`. Negli altri test l'assenza del patch farebbe chiamare la config Arkimet reale (inesistente per dataset sintetici).
- **Ordine dei rami come oracolo implicito**: i test isolano ciascun ramo facendo passare i precedenti (es. test 3 fakeia il formato a grib per arrivare al check licenze). Un riordino delle guardie in `data.py` sposterebbe il punto di fallimento e potrebbe rendere ambigui questi test.
- **`get_license_group` reale (test 3)**: a differenza del formato (fakeato), il controllo licenze gira sul repository reale; la separazione dei gruppi è ottenuta creando dataset con `group_name` distinti.
- **Postprocessor valido per schema ma bloccato dopo (test 6)**: serve un postprocessor **sintatticamente valido** (`B12194` ∈ `DERIVED_VARIABLES`) per superare `AVProcessor.load` e raggiungere il controllo `allowed_postprocessing`. Un postprocessor malformato avrebbe dato un 400 schema, non il 401 voluto.
- **Invariante “no request”**: ogni test asserisce `latest_request_for_user(...) is None`, verificando che il rifiuto preceda `create_request_record`.
- **Nessun `pytest.skip`**: stato interamente sintetico → nessun test saltabile silenziosamente.

## 7. Checklist di revisione

- [ ] Confermare che il `400` “output_format invalido” sia atteso a **livello schema** (`pre_load`) e non applicativo; il test 4 ne dipende.
- [ ] Verificare che l'ordine delle guardie in `Data.post` (formato → licenze → postprocessor → output_format → only_reliable) resti quello assunto dai test.
- [ ] Confermare che `get_user_permissions("allowed_postprocessing")` ritorni falsy per l'utente di default creato dall'helper (nessun `allowed_postprocessing`).
- [ ] Verificare che la distinzione `400` schema vs `400` applicativo resti significativa anche se `OUTPUT_FORMATS` cambia.
- [ ] Confermare che la separazione dei gruppi licenza (test 3) dipenda dal `group_name` univoco di `create_synthetic_dataset`.

## 8. Possibili criticità

- **Fragilità all'ordine delle guardie**: isolare un ramo richiede di far passare i precedenti; un refactor che riordini i controlli può cambiare lo status atteso senza che il comportamento sia “sbagliato”.
- **Copertura mista reale/fakeata**: formato e categoria sono fakeati, mentre catalogo e licenze sono reali; un reviewer deve sapere quale parte è effettivamente esercitata (Arkimet **non** lo è).
- **Assert su sottostringa (test 4)**: `"output_format" in str(content)` è robusto ma poco specifico: passerebbe anche con un messaggio d'errore diverso che cita lo stesso campo.
- **Ramo `multim-forecast` non testato (test 7)**: si verifica solo il rifiuto su `FOR`; il caso ammesso (`OBS`/`multim-forecast`) non è coperto qui.
- **Disciplina di patch**: come per il modulo submission, l'isolamento da Arkimet non è `autouse`; nuovi test devono ricordarsi del patch dove serve.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_post_data_returns_404_for_missing_dataset` | `repo.get_datasets` | dataset assente → 404 | — (DB reale) | `client`, `cleanup_registry` | Bassa |
| `test_post_data_returns_400_for_mixed_dataset_formats` | `arki.get_datasets_format` | formati misti → 400 | `patch_data_endpoint_runtime` (format=None) | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `test_post_data_returns_400_for_different_license_groups` | `repo.get_license_group` | gruppi licenza diversi → 400 | `patch_...` (format="grib") | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `test_post_data_returns_400_for_invalid_output_format_schema` | `DataExtraction` pre_load | output_format invalido → 400 schema | — | `client`, `cleanup_registry` | Bassa |
| `test_post_data_returns_400_when_output_format_is_incompatible_with_grib` | `Data.post` (output_format) | json su grib → 400 applicativo | `patch_...` (format="grib") | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `test_post_data_returns_401_for_unauthorized_postprocessor_usage` | `repo.get_user_permissions` | postprocessor senza permesso → 401 | `patch_...` (format/category) | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `test_post_data_returns_400_when_only_reliable_is_not_supported` | `arki.get_datasets_category` | only_reliable su FOR → 400 | `patch_...` (category="FOR") | `client`, `cleanup_registry`, `monkeypatch` | Media |
