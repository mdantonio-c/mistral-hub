# Review — `test_admin_datasets_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/admin/test_admin_datasets_EXT.py](projects/mistral/backend/tests/integration/admin/test_admin_datasets_EXT.py)
- **Scopo**: verificare il CRUD admin dei *dataset* catalografici, il cambio delle relazioni `license`/`attribution` in update, la normalizzazione `sort_index=""`→`None`, il **409 su vincoli unique** (`arkimet_id`/`name`) e i rami `404`.
- **Tipologia**: test di **integrazione HTTP** (controller reale + schema dinamica + DB SQLAlchemy). Marker: `integration`, `deterministic`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AdminDatasets.get` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | `GET /api/admin/datasets` — lista tutti i dataset; `category` serializzata come `d.category.name`; `license` e `attribution` annidati (`{id,name,descr}`). |
| `AdminDatasets.post` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | `POST /api/admin/datasets` — crea il dataset, collega `license_id`/`attribution_id`, ritorna l'**id** (200); `Conflict` (409) su `DatabaseDuplicatedEntry`. |
| `AdminDatasets.put` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | `PUT /api/admin/datasets/<id>` — `NotFound` (404) se assente; `setattr`; eventuale cambio `license_id`/`attribution_id` → `empty_response()` (**204**). |
| `AdminDatasets.delete` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | `DELETE /api/admin/datasets/<id>` — `NotFound` (404) se assente; delete → **204**. |
| `getInputSchema` (POST/PUT) | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | **Schema dinamica a runtime**: `license`/`attribution` sono `OneOf` sugli id esistenti; `category`/`source` `OneOf` su valori fissi; `source` default `arkimet`, `supports_variable_browsing` default `False`. |
| `DatasetInput` + `@pre_load null_sort_index` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | Converte `sort_index == ""` in `None`. |
| `get_output_schema` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) | Output: `sort_index` `Int(allow_none=True)`, `license`/`attribution` nested, ecc. |
| Modello `Datasets` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L146) | `arkimet_id` **unique** (nullable), `name` **unique** (not null), `category` `Enum(DatasetCategories)`, `sort_index` Int nullable, m2m `users`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**; non ingoia eccezioni. |
| `admin_headers_EXT` | fixture | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Importata per nome; login admin di **default**. |
| `dataset_payload_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Payload dataset sintetico; default `arkimet_id == name == token`, `sort_index=10`, `supports_variable_browsing=True`; `license`/`attribution` come stringhe. |
| `create_attribution_via_api_EXT` / `create_license_group_via_api_EXT` / `create_license_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Creano le dipendenze relazionali (ognuno asserisce 200 + cleanup) necessarie per le `OneOf` dinamiche. |
| `create_dataset_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | POST dataset (asserisce 200) + cleanup DB. |
| `delete_admin_records_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Cleanup; per i dataset rimuove anche le associazioni m2m `dataset.users` prima del delete. |
| `find_list_item_EXT`, `response_content_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Ricerca item per id stringa; decodifica body. |
| `ADMIN_DATASETS_ENDPOINT_EXT`, `ADMIN_MISSING_ID_EXT` | costanti | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | URL `/api/admin/datasets` e id sentinella. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Precondizioni DB, verifica post-delete e conteggio dopo il 409. |

## 4. Analisi dettagliata di ogni test

### `test_admin_dataset_create_list_update_delete_EXT`
- **Obiettivo**: CRUD dataset + **cambio relazioni** license/attribution + `sort_index=""`→`None`.
- **Backend coinvolto**: `post`, `get` (relazioni nested), `put` (rami `license_id`/`attribution_id`), `delete`, `pre_load null_sort_index`.
- **Flusso**: crea **due** coppie license/attribution (per coprire create + cambio in PUT) → crea dataset sul primo set → GET e verifica schema/relazioni iniziali → PUT (secondo set, `sort_index=""`, `supports_variable_browsing=False`) → GET di conferma → DELETE → verifica DB.
- **Setup**: `admin_headers_EXT`, `cleanup_registry`; 6 record dipendenza + 1 dataset, tutti sintetici e con cleanup.
- **Assert**:
  - create: `arkimet_id`/`name`/`category`/`source`/`sort_index` uguali al payload, `supports_variable_browsing is True`, `license.id`/`attribution.id` = primo set.
  - `update_response.status_code == 204`; poi `name`/`description` aggiornati, `sort_index is None` (pre_load), `supports_variable_browsing is False`, `license.id`/`attribution.id` = **secondo** set → la PUT è un replace completo con cambio FK.
  - `delete` → 204 e `Datasets.query.get(id) is None`.
- **Casi coperti**: happy path completo + validation/normalization (`sort_index`) + cambio FK + side effect DB.

### `test_admin_dataset_duplicate_unique_fields_return_conflict_EXT`
- **Obiettivo**: verificare il **409** sul duplicato, dove esistono **vincoli unique reali** (`arkimet_id`/`name`).
- **Backend coinvolto**: `post` → `db.session.commit()` viola unique → `DatabaseDuplicatedEntry` → `rollback` → `Conflict`.
- **Flusso**: crea dipendenze + primo dataset → reinvia lo **stesso** payload → verifica 409 + che resti un solo record.
- **Setup**: `admin_headers_EXT`, `cleanup_registry`; payload identico riusato.
- **Assert**: `duplicate_response.status_code == 409`; `Datasets.query.get(first_dataset_id) is not None`; `filter_by(arkimet_id=...).count() == 1` → il conflitto non crea un secondo record e l'originale sopravvive.
- **Casi coperti**: error path / **conflict** (l'unico endpoint admin dove il 409 è genuinamente esercitabile).
- **Dipendenza implicita**: il 409 richiede che restapi traduca l'`IntegrityError` SQLAlchemy in `DatabaseDuplicatedEntry`; il test verifica indirettamente anche questo ponte.

### `test_admin_dataset_missing_update_delete_return_404_EXT`
- **Obiettivo**: `NotFound` per `put`/`delete` su dataset inesistente.
- **Backend coinvolto**: `put`/`delete` → `if not dataset: raise NotFound`.
- **Flusso**: precondizione DB (`Datasets.query.get(ADMIN_MISSING_ID_EXT) is None`) → crea license/attribution valide (solo per superare la `OneOf` del PUT) → PUT e DELETE sull'id mancante.
- **Setup**: `admin_headers_EXT`, `cleanup_registry` (per le dipendenze).
- **Assert**: `update_response.status_code == 404` e `delete_response.status_code == 404`.
- **Casi coperti**: error path. Le dipendenze valide isolano il test dal ramo di validazione: il 404 misura la ricerca del **dataset** path.

## 5. Call chain

```
GET    /api/admin/datasets        → require_all(ADMIN) → AdminDatasets.get
                                      → db.Datasets.query.all() → category=d.category.name + license{} + attribution{} → get_output_schema(many) → 200
POST   /api/admin/datasets        → require_all(ADMIN) → use_kwargs(getPOSTInputSchema[OneOf license/attribution/category/source, pre_load null_sort_index])
                                      → pop license/attribution → Datasets(**kwargs) → add → commit
                                      → IntegrityError → DatabaseDuplicatedEntry → rollback → Conflict 409
                                      → license/attribution = filter_by(id).first  (BUG: senza () → NotFound morto)
                                      → set license_id/attribution_id → commit → response(id) 200
PUT    /api/admin/datasets/<id>   → require_all(ADMIN) → use_kwargs(getPUTInputSchema)
                                      → filter_by(id).first() → None? NotFound 404
                                      → setattr+commit → (eventuale set license_id/attribution_id) → empty_response 204
DELETE /api/admin/datasets/<id>   → require_all(ADMIN) → filter_by(id).first()
                                      → None? NotFound 404  :  delete+commit → empty_response 204
```

## 6. Comportamenti nascosti

- **Schema dinamica a runtime**: `license`/`attribution` sono `OneOf` sugli id esistenti; per questo i test creano sempre le dipendenze **prima** del dataset. Un id mancante sarebbe **400 (validation)**, non 404.
- **Bug `.first` senza `()`** (stesso pattern di `admin_licenses.py`): in `post`/`put`, `db.License.query.filter_by(...).first` e `db.Attribution...first` sono *bound method* sempre truthy → i rami `NotFound("This license"/"This attribution")` sono **codice morto**. Questi test **non** li esercitano (testano solo dataset id mancante), quindi il bug resta latente e non coperto.
- **Mismatch doc/impl sugli status**: l'endpoint dichiara `responses={200: "Dataset successfully modified"}` / `{200: "Dataset successfully deleted"}`, ma `put`/`delete` ritornano `empty_response()` → **204** (asserito correttamente dai test).
- **`category` via Enum reale**: il payload invia la stringa `"FOR"`; il modello la mappa su `DatasetCategories` e il GET rilegge `d.category.name`. Il round-trip passa per l'enum SQLAlchemy, non per una semplice stringa.
- **`source`/`supports_variable_browsing` hanno default di schema** (`arkimet`/`False`): compaiono nei kwargs anche se non inviati; nel test sono comunque espliciti nel payload.
- **Cleanup con side effect m2m**: `delete_admin_records_EXT` rimuove le associazioni `dataset.users` prima del delete del dataset; ordine LIFO dataset→license→group→attribution.
- **`admin_headers_EXT` importata per nome**; login admin di default condiviso; listing globale + `find_list_item_EXT` per l'isolamento.

## 7. Checklist di revisione

- [ ] Confermare che `409` derivi dai vincoli unique `arkimet_id`/`name` e che restapi traduca davvero l'`IntegrityError` in `DatabaseDuplicatedEntry`.
- [ ] Verificare che 204 (non 200) sia il contratto reale di `put`/`delete` e correggere la doc OpenAPI dell'endpoint.
- [ ] Segnalare il bug `.first` senza `()` per license/attribution in `post`/`put` (rami NotFound morti); valutare un test dedicato dopo il fix.
- [ ] Verificare che `sort_index is None` derivi dal `pre_load null_sort_index` e non da altro default.
- [ ] Confermare che il cambio license/attribution in PUT sia coperto end-to-end (lo è).
- [ ] Verificare che il cleanup m2m `dataset.users` non lasci righe orfane in `auth_association`.

## 8. Possibili criticità

- **Bug di backend non coperto**: il `.first` senza `()` per license/attribution rende morti i rami NotFound in `post`/`put`; il test missing-404 verifica solo il dataset id, quindi il difetto resta invisibile alla suite (rischio falso negativo su quel contratto).
- **Doc/implementazione divergenti**: `responses` dichiara 200 dove il codice ritorna 204; i test sono corretti ma l'OpenAPI è fuorviante.
- **Dipendenza dalla traduzione errori restapi**: se cambiasse il mapping `IntegrityError → DatabaseDuplicatedEntry`, il test 409 diventerebbe fragile (potrebbe emergere un 500 non gestito).
- **Setup pesante**: il primo test crea 7 record sintetici; la robustezza del teardown dipende interamente dal cleanup LIFO e dalla rimozione m2m. Un fallimento a metà arrange potrebbe lasciare residui (mitigato dall'idempotenza di `delete_admin_records_EXT`).
- **Accoppiamento sulla schema dinamica**: i test devono pre-creare license/attribution o la `OneOf` sarebbe vuota; forte coupling setup↔validazione.
- **Accoppiamento sull'admin condiviso**: come negli altri moduli admin.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_admin_dataset_create_list_update_delete_EXT` | `post`/`get`/`put`/`delete` + `null_sort_index` | CRUD + cambio license/attribution + `sort_index=""`→None + DB | — (DB diretto) | `admin_headers_EXT`, `cleanup_registry` | Alta |
| `test_admin_dataset_duplicate_unique_fields_return_conflict_EXT` | `post` (unique → Conflict) | 409 su duplicato + un solo record | — | `admin_headers_EXT`, `cleanup_registry` | Media |
| `test_admin_dataset_missing_update_delete_return_404_EXT` | `put`/`delete` (NotFound) | 404 su dataset inesistente | — | `admin_headers_EXT`, `cleanup_registry` | Bassa |
