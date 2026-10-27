# Review — `test_admin_licenses_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/admin/test_admin_licenses_EXT.py](projects/mistral/backend/tests/integration/admin/test_admin_licenses_EXT.py)
- **Scopo**: verificare il CRUD admin delle *license* (create con group, cambio di group in update, normalizzazione `url=""`→`None`), il listing con `group_license` e `datasets` annidati, i rami `404` per license mancante e il `400` di validazione su `group_license` inesistente senza creare license (ADMIN-001).
- **Tipologia**: test di **integrazione HTTP** (controller reale + schema dinamica + DB SQLAlchemy). Marker: `integration`, `deterministic`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AdminLicenses.get` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) | `GET /api/admin/licenses` — lista via `_get_license_response`, aggiunge `group_license` (id/name/descr) e `datasets[]` (`{name, id=arkimet_id}`). |
| `AdminLicenses.post` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) | `POST /api/admin/licenses` — crea la license, collega `group_license_id`, ritorna l'**id** (200); `Conflict` (409) su dup. |
| `AdminLicenses.put` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) | `PUT /api/admin/licenses/<id>` — `NotFound` (404) se license assente; `setattr`; eventuale cambio `group_license_id` → `empty_response()` (**204**). |
| `AdminLicenses.delete` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) | `DELETE /api/admin/licenses/<id>` — `NotFound` (404) se assente; delete → **204**. |
| `getInputSchema` / `getPOSTInputSchema` / `getPUTInputSchema` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) | **Schema dinamica valutata a runtime**: `group_license` è una `OneOf` costruita sugli id dei gruppi **esistenti** nel DB. |
| `LicenseInput` + `@pre_load null_url` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) | Converte `url == ""` in `None`. |
| `SqlApiDbManager._get_license_response` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L297) | Dict base della license (id, name, descr, url). |
| Modello `License` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L111) | `group_license_id` FK, `name` indicizzato **non unique**, `url` String, `datasets` (`lazy="dynamic"`). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**; non ingoia eccezioni. |
| `admin_headers_EXT` | fixture | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Importata per nome; login admin di **default**. |
| `license_payload_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Payload license; `group_license` inviato come **stringa** (per la `OneOf`); `url` opzionale (`""`/`None`). |
| `create_license_group_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | POST gruppo (asserisce 200) + cleanup; necessario perché la `OneOf` di `group_license` esista. |
| `create_license_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | POST license (asserisce 200) + cleanup. |
| `create_dataset_bundle_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Crea attribution+group+license+dataset per il test di listing annidato. |
| `find_list_item_EXT`, `response_content_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Ricerca item per id stringa; decodifica body. |
| `ADMIN_LICENSES_ENDPOINT_EXT`, `ADMIN_MISSING_ID_EXT` | costanti | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | URL `/api/admin/licenses` e id sentinella. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Precondizioni DB, verifica post-delete e assenza di license dopo il 400. |

## 4. Analisi dettagliata di ogni test

### `test_admin_license_create_list_update_delete_EXT`
- **Obiettivo**: CRUD license + **cambio di group_license** in update + `url=""`→`None`.
- **Backend coinvolto**: `post`, `get` (group + datasets annidati), `put` (con ramo `group_license_id`), `delete`.
- **Flusso**: crea **due** gruppi → crea license nel primo → GET e verifica gruppo originale e `datasets == []` → PUT (sposta al secondo gruppo, `url=""`) → GET di conferma → DELETE → verifica DB.
- **Setup**: `admin_headers_EXT`; due gruppi creati **prima** della license (cleanup LIFO sicuro).
- **Assert**:
  - listing post-create: `name`/`descr`/`url` del payload, `group_license.id == original_group_id`, `datasets == []`.
  - `update_response.status_code == 204` (`empty_response`), poi `url is None` (pre_load) e `group_license.id == updated_group_id` → il cambio relazione è persistito.
  - `delete` → 204 e `License.query.get(id) is None`.
- **Casi coperti**: happy path completo + validation/normalization (url) + cambio FK + side effect DB.

### `test_admin_license_list_includes_group_and_datasets_EXT`
- **Obiettivo**: verificare lo schema list con `group_license` e `datasets` annidati.
- **Backend coinvolto**: `get` (dict `group_license` + loop `for d in lic.datasets`).
- **Flusso**: crea bundle completo (attribution+group+license+dataset) → GET → trova la license → verifica gruppo e dataset annidato.
- **Setup**: `create_dataset_bundle_via_api_EXT` (cleanup LIFO).
- **Assert**: `status_code == 200`; `group_license.id == bundle.group_license_id`; `{"id": bundle.dataset_arkimet_id, "name": bundle.dataset_name} in datasets` → conferma il doppio annidamento (gruppo + dataset con `id=arkimet_id`).
- **Casi coperti**: happy path / contratto relazionale annidato.

### `test_admin_license_missing_license_returns_404_EXT`
- **Obiettivo**: `NotFound` per `put`/`delete` su license inesistente.
- **Backend coinvolto**: `put`/`delete` → `if not license: raise NotFound`.
- **Flusso**: precondizione DB (`License.query.get(ADMIN_MISSING_ID_EXT) is None`) → crea un gruppo valido (serve solo a far passare la `OneOf` del PUT) → PUT e DELETE sull'id mancante.
- **Setup**: `admin_headers_EXT`, `cleanup_registry` (per il gruppo creato).
- **Assert**: `update_response.status_code == 404` e `delete_response.status_code == 404`.
- **Casi coperti**: error path. Il gruppo valido isola il test dal ramo di validazione: il 404 misura la ricerca della **license** path, non il body.

### `test_admin_license_missing_group_returns_400_EXT` — **ADMIN-001 (contratto di validazione)**
- **Obiettivo**: verificare il `400` di validazione quando si tenta di creare una license con `group_license` **inesistente**, senza persistenza.
- **Backend coinvolto**: `getPOSTInputSchema` (`OneOf` dinamica) **prima** del ramo applicativo `post`.
- **Flusso**: precondizione DB (`GroupLicense.query.get(ADMIN_MISSING_ID_EXT) is None`) → POST con `group_license = ADMIN_MISSING_ID_EXT`.
- **Setup**: `admin_headers_EXT`; **nessun cleanup** (la create non deve riuscire).
- **Assert**: `status_code == 400`; `"group_license" in response_content_EXT(response)`; `License.query.filter_by(name=payload["name"]).count() == 0`.
- **Casi coperti**: edge/contract negativo. La `OneOf` rifiuta l'id mancante con **400** prima del controller; il ramo `NotFound` non viene raggiunto via HTTP. Il test non usa skip.
- **Doppio problema di backend dietro ADMIN-001** (vedi §8): anche se l'input superasse lo schema, il controllo `if not lic_group:` userebbe `db.GroupLicense.query.filter_by(...).first` **senza parentesi** → un *bound method* sempre truthy → il `raise NotFound("This license group")` è **codice morto**.

## 5. Call chain

```
GET    /api/admin/licenses        → require_all(ADMIN) → AdminLicenses.get
                                      → db.License.query.all()
                                      → _get_license_response(lic) + group_license{id,name,descr} + [ {name, id=arkimet_id} for d in lic.datasets ]
                                      → get_output_schema(many) → 200
POST   /api/admin/licenses        → require_all(ADMIN) → use_kwargs(getPOSTInputSchema[OneOf group_license])
                                      → (OneOf reietta id inesistente → 400, errore group_license, nessuna license creata)  ← ADMIN-001
                                      → pop group_license → License(**kwargs) → add → commit
                                      → lic_group = filter_by(id).first   (BUG: senza () → sempre truthy → NotFound morto)
                                      → set group_license_id → commit → response(id) 200
PUT    /api/admin/licenses/<id>   → require_all(ADMIN) → use_kwargs(getPUTInputSchema)
                                      → filter_by(id).first()  → None? NotFound 404
                                      → setattr+commit → (eventuale set group_license_id) → empty_response 204
DELETE /api/admin/licenses/<id>   → require_all(ADMIN) → filter_by(id).first()
                                      → None? NotFound 404  :  delete+commit → empty_response 204
```

## 6. Comportamenti nascosti

- **Schema dinamica a runtime**: `group_license` è una `OneOf` ricostruita ad ogni richiesta dagli id dei gruppi presenti; genera anche le opzioni del form. Un id mancante è **400 (validation)**, non `404`: questo è il contratto HTTP verificato per ADMIN-001, insieme all'errore sul campo e all'assenza di persistenza.
- **Nessuno skip per ADMIN-001**: il quarto test esegue sempre gli assert sul `400`; non pretende di coprire il `NotFound` del controller, irraggiungibile via HTTP.
- **Bug `.first` senza `()`**: in `post` e `put`, `db.GroupLicense.query.filter_by(...).first` è un metodo non invocato → sempre truthy → i rami `NotFound("This license group")` sono **irraggiungibili** (dead code).
- **Mismatch doc/impl sugli status**: l'endpoint dichiara `responses={200: "License successfully modified"}` e `{200: "License successfully deleted"}`, ma `put`/`delete` ritornano `empty_response()` → **204**. I test asseriscono correttamente 204.
- **`admin_headers_EXT` importata per nome** (niente `conftest.py` locale); login admin di default condiviso.
- **Helper con assert e cleanup interni**: la create delle dipendenze attraversa il vero controller e registra cleanup; un fallimento in arrange è un assert dell'helper.
- **`datasets` annidati con `id = arkimet_id`** (non id numerico) — stesso contratto degli altri endpoint metadata.

## 7. Checklist di revisione

- [x] **ADMIN-001**: adottato il contratto HTTP `400` della `OneOf`, con errore su `group_license` e nessuna license creata. Nessuno skip; il bug `.first` senza `()` resta separato e non viene corretto qui.
- [ ] Verificare nel backend i due `db...filter_by(...).first` **senza parentesi** in `post`/`put` di licenses: sono bug che rendono morto il ramo NotFound.
- [ ] Confermare che 204 (non 200) sia il contratto reale di `put`/`delete` e aggiornare la doc OpenAPI dell'endpoint.
- [ ] Verificare che `url is None` derivi dal `pre_load null_url`.
- [ ] Confermare che il cambio `group_license` in PUT sia coperto end-to-end (lo è).
- [ ] Verificare che il gruppo creato nel test 404-license sia volutamente “solo per lo schema” (non collegato).

## 8. Possibili criticità

- **Perimetro ADMIN-001**: il test verifica il rifiuto HTTP `400` e l'assenza di persistenza, non il ramo `NotFound` del controller, non raggiungibile attraverso la `OneOf`.
- **Bug di backend ancora aperto**: il `.first` senza `()` rende il `NotFound` di group morto sia in `post` sia in `put`; resta da correggere separatamente. La validazione `400` è invece il contratto HTTP adottato.
- **Doc/implementazione divergenti**: `responses` dichiara 200 dove il codice ritorna 204; test corretti ma contratto OpenAPI fuorviante.
- **`Conflict` (409) non testato**: `License.name` non è unique → ramo dup non esercitabile/non coperto.
- **Dipendenza dalla schema dinamica**: i test devono creare i gruppi *prima*, altrimenti la `OneOf` sarebbe vuota; accoppiamento forte fra setup e validazione runtime.
- **Accoppiamento sull'admin condiviso**: come negli altri moduli admin.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_admin_license_create_list_update_delete_EXT` | `post`/`get`/`put`/`delete` + `null_url` | CRUD + cambio group + `url=""`→None + DB | — (DB diretto) | `admin_headers_EXT`, `cleanup_registry` | Alta |
| `test_admin_license_list_includes_group_and_datasets_EXT` | `get` (group + datasets nested) | gruppo e dataset annidati | — | `admin_headers_EXT`, `cleanup_registry` | Media |
| `test_admin_license_missing_license_returns_404_EXT` | `put`/`delete` (NotFound) | 404 su license inesistente | — | `admin_headers_EXT`, `cleanup_registry` | Bassa |
| `test_admin_license_missing_group_returns_400_EXT` | `getPOSTInputSchema` (OneOf) | 400, errore group_license, nessuna license creata (ADMIN-001) | — (DB diretto) | `admin_headers_EXT` | Bassa |
