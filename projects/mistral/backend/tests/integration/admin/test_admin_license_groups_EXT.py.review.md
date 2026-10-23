# Review — `test_admin_license_groups_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy, senza toccarla.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/admin/test_admin_license_groups_EXT.py](projects/mistral/backend/tests/integration/admin/test_admin_license_groups_EXT.py)
- **Scopo**: verificare il CRUD admin dei *license group*, la preservazione dei campi `is_public` e `dballe_dsn` (rilevanti per autorizzazioni e dati observed), il listing con le license figlie annidate e i rami `404`.
- **Tipologia**: test di **integrazione HTTP** (controller reale + DB SQLAlchemy). Marker: `integration`, `deterministic`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AdminLicGroups.get` | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) | `GET /api/admin/licensegroups` — lista i gruppi via `SqlApiDbManager._get_license_group_response`, annidando le license figlie. |
| `AdminLicGroups.post` | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) | `POST /api/admin/licensegroups` — crea il gruppo e ritorna l'**id scalare** (200); `Conflict` (409) su `DatabaseDuplicatedEntry`. |
| `AdminLicGroups.put` | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) | `PUT /api/admin/licensegroups/<id>` — `NotFound` (404) se assente; altrimenti `setattr` + commit → `empty_response()` (204). |
| `AdminLicGroups.delete` | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) | `DELETE /api/admin/licensegroups/<id>` — `NotFound` (404) se assente; altrimenti delete → 204. |
| `LicGroupInput` | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) | Input: `name`/`descr`/`is_public` obbligatori, `dballe_dsn` opzionale. |
| `LicGroup` (output) + `License` (nested) | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) | Serializza `id`, `name`, `descr`, `is_public`, `dballe_dsn`, `license[]`. |
| `SqlApiDbManager._get_license_group_response` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L286) | Costruisce il dict del gruppo (id, name, descr, is_public, dballe_dsn). |
| `SqlApiDbManager._get_license_response` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L297) | Costruisce il dict di ciascuna license annidata. |
| Modello `GroupLicense` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L101) | `name` indicizzato **ma non unique**; `license` (`lazy="dynamic"`), `is_public` Bool, `dballe_dsn` String(64). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**, eseguito dopo lo `yield`; non ingoia eccezioni. |
| `admin_headers_EXT` | fixture | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Importata per nome; login admin di **default** → header condivisi. |
| `license_group_payload_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Payload `LicGroupInput` con `is_public` e `dballe_dsn` espliciti (default `"DBALLE_EXT"`). |
| `create_license_group_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | POST gruppo via API (asserisce 200) + registra cleanup DB del gruppo. |
| `create_license_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | POST license figlia via API (asserisce 200) + cleanup DB. |
| `find_list_item_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Trova l'item per id normalizzato a stringa. |
| `response_content_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Decodifica body via `BaseTests().get_content`. |
| `ADMIN_LICENSE_GROUPS_ENDPOINT_EXT`, `ADMIN_MISSING_ID_EXT` | costanti | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | URL `/api/admin/licensegroups` e id sentinella `987654321`. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Accesso DB diretto per precondizioni e verifica post-delete. |

## 4. Analisi dettagliata di ogni test

### `test_admin_license_group_create_list_update_delete_EXT`
- **Obiettivo**: coprire il CRUD completo e la **preservazione** di `is_public`/`dballe_dsn` attraverso create e update.
- **Backend coinvolto**: `post`, `get` (con `_get_license_group_response`), `put`, `delete`.
- **Flusso**: crea gruppo (`is_public=False`, `dballe_dsn="DBALLE_EXT"`) via helper → GET e verifica campi → PUT (`is_public=True`, `dballe_dsn="DBALLE_EXT_UPDATED"`, nome/descr nuovi) → GET di conferma → DELETE → verifica DB.
- **Setup**: `admin_headers_EXT`; `create_license_group_via_api_EXT` con `payload` esplicito; cleanup registrato dall'helper.
- **Assert**:
  - listing: `name`/`descr` del payload, `is_public is False`, `dballe_dsn == "DBALLE_EXT"`, `license == []` (gruppo senza license) → contratto dei campi di autorizzazione OBS preservato in creazione.
  - `update_response.status_code == 204` → `empty_response()`.
  - dopo update: `is_public is True`, `dballe_dsn == "DBALLE_EXT_UPDATED"`, nome/descr aggiornati → l'update tocca davvero i campi sensibili.
  - `delete` → 204 e `GroupLicense.query.get(id) is None` → delete persistito.
- **Casi coperti**: happy path completo + verifica esplicita dei booleani/stringhe sensibili + side effect DB.
- **Nota**: `is_public` è asserito con `is False`/`is True` (identità booleana), non con `== 0/1`: protegge da serializzazioni numeriche.

### `test_admin_license_group_list_includes_nested_licenses_EXT`
- **Obiettivo**: verificare che il listing dei gruppi includa le license figlie (loop `for lic in gl.license`).
- **Backend coinvolto**: `get` → `_get_license_response` per ogni license annidata.
- **Flusso**: crea gruppo → crea license collegata a quel gruppo → GET listing → verifica che l'id della license sia tra le license annidate del gruppo.
- **Setup**: `create_license_group_via_api_EXT` + `create_license_via_api_EXT` (cleanup LIFO: license prima del gruppo).
- **Assert**: `status_code == 200` e `str(license_id) in {str(item["id"]) for item in group_item["license"]}` → la relazione gruppo→license è serializzata correttamente; confronto su id normalizzato a stringa (robusto a Int vs Str).
- **Casi coperti**: happy path / contratto relazionale annidato.

### `test_admin_license_group_missing_update_delete_return_404_EXT`
- **Obiettivo**: verificare i rami `NotFound` di `put`/`delete` su gruppo inesistente.
- **Backend coinvolto**: `put`/`delete` → `if not lgroup: raise NotFound`.
- **Flusso**: precondizione DB (`get(ADMIN_MISSING_ID_EXT) is None`) → PUT (con payload valido per superare lo schema) e DELETE sull'id mancante.
- **Setup**: `admin_headers_EXT`; **nessun dato creato** (niente `cleanup_registry`).
- **Assert**: `update_response.status_code == 404` e `delete_response.status_code == 404`.
- **Casi coperti**: error path.
- **Nota esplicita nel test**: **non** esiste un test di duplicate/409 per questo modello perché `GroupLicense.name` **non è unique** (no oracolo 409 stabile senza modificare il backend). È una scelta motivata e dichiarata, non una dimenticanza.

## 5. Call chain

```
GET    /api/admin/licensegroups       → require_all(ADMIN) → AdminLicGroups.get
                                          → db.GroupLicense.query.all()
                                          → _get_license_group_response(gl) + [ _get_license_response(lic) for lic in gl.license ]
                                          → LicGroup(many) → 200
POST   /api/admin/licensegroups       → require_all(ADMIN) → use_kwargs(LicGroupInput)
                                          → db.GroupLicense(**kwargs) → add → commit → response(id) 200
                                          → DatabaseDuplicatedEntry → Conflict 409  (non raggiungibile: name non unique)
PUT    /api/admin/licensegroups/<id>  → require_all(ADMIN) → filter_by(id).first()
                                          → None? NotFound 404  :  setattr+commit → empty_response 204
DELETE /api/admin/licensegroups/<id>  → require_all(ADMIN) → filter_by(id).first()
                                          → None? NotFound 404  :  session.delete+commit → empty_response 204
```

## 6. Comportamenti nascosti

- **Fixture `admin_headers_EXT` importata per nome** da `support_EXT.py` (niente `conftest.py` locale): login dell'admin di **default**, stato condiviso fra tutti i test del dominio.
- **Listing globale**: `get` ritorna **tutti** i gruppi; l'isolamento si basa su nomi uuid e `find_list_item_EXT`.
- **Conflict 409 deliberatamente non testato**: dichiarato nel docstring del terzo test (modello senza vincolo unique su `name`).
- **Helper con assert interni**: `create_license_group_via_api_EXT`/`create_license_via_api_EXT` asseriscono `200` e registrano cleanup; un fallimento in arrange è un assert dell'helper.
- **Cleanup LIFO relazionale**: nel secondo test la license è creata dopo il gruppo → teardown la rimuove prima del gruppo (evita violazioni FK).
- **`dballe_dsn` come stringa libera**: non c'è validazione di formato; il test verifica solo round-trip del valore.

## 7. Checklist di revisione

- [ ] Confermare che `is_public`/`dballe_dsn` siano davvero i campi che pilotano autorizzazioni/observed (commento del test) e che meritino assert dedicati.
- [ ] Verificare che `license == []` alla creazione sia garantito (gruppo nuovo senza figli).
- [ ] Controllare che la scelta di non testare il 409 resti valida (se in futuro si aggiunge unique su `name`, aggiungere il test).
- [ ] Verificare l'assenza di accoppiamento d'ordine col default user admin condiviso.
- [ ] Confermare che gli id annidati confrontati come stringa coprano il mismatch Int(modello)/Str(schema).

## 8. Possibili criticità

- **Ramo `Conflict` (409) totalmente scoperto**: corretto rispetto al modello attuale, ma resta codice non esercitato; un futuro vincolo unique passerebbe inosservato finché non si aggiunge il test.
- **Accoppiamento sull'admin condiviso**: come negli altri moduli admin, l'esecuzione parallela si regge sull'unicità uuid.
- **Assert di lista su catalogo non vuoto**: se l'ambiente avesse molti gruppi, i test restano corretti ma il body può crescere; nessun limite/paginazione verificato (l'endpoint non pagina).
- **Fixture importata per nome**: fragile rispetto a strumenti che rimuovono import “inutilizzati”.
- **`descr`/`dballe_dsn` non validati**: il test non può (e non deve) coprire validazioni che il backend non impone; eventuale aspettativa di validazione va verificata altrove.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_admin_license_group_create_list_update_delete_EXT` | `post`/`get`/`put`/`delete` | CRUD + preservazione `is_public`/`dballe_dsn` + DB side effect | — (DB diretto) | `admin_headers_EXT`, `cleanup_registry` | Media |
| `test_admin_license_group_list_includes_nested_licenses_EXT` | `get` (nested license) | license figlia presente nel gruppo | — | `admin_headers_EXT`, `cleanup_registry` | Media |
| `test_admin_license_group_missing_update_delete_return_404_EXT` | `put`/`delete` (NotFound) | 404 su id inesistente | — | `admin_headers_EXT` | Bassa |
