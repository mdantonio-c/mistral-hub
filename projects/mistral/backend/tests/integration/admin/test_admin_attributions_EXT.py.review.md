# Review — `test_admin_attributions_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** aggiunta sopra la baseline legacy, senza rinominare né toccare i test storici.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/admin/test_admin_attributions_EXT.py](projects/mistral/backend/tests/integration/admin/test_admin_attributions_EXT.py)
- **Scopo**: verificare il contratto CRUD admin delle *attribution* (creazione, listing con dataset annidati, update, delete), la guardia di ruolo `ADMIN`, la normalizzazione `url=""` → `None` e i rami `404`.
- **Tipologia**: test di **integrazione HTTP** (endpoint REST reali esercitati via `FlaskClient`, DB SQLAlchemy reale). Marker di modulo: `integration`, `deterministic` (`pytestmark`).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AdminAttributions.get` | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) | `GET /api/admin/attributions` — lista tutte le attribution; per ognuna annida i dataset come `{"name": d.name, "id": d.arkimet_id}`. |
| `AdminAttributions.post` | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) | `POST /api/admin/attributions` — crea l'attribution e ritorna l'**id scalare** (200); `Conflict` (409) su `DatabaseDuplicatedEntry`. |
| `AdminAttributions.put` | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) | `PUT /api/admin/attributions/<id>` — `NotFound` (404) se assente; altrimenti `setattr` di ogni campo + commit → `empty_response()` (204). |
| `AdminAttributions.delete` | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) | `DELETE /api/admin/attributions/<id>` — `NotFound` (404) se assente; altrimenti `db.session.delete` → 204. |
| `AttributionInput` + `@pre_load null_url` | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) | Schema input: `name`/`descr` obbligatori, `url` opzionale; il `pre_load` converte `url == ""` in `None`. |
| `Attribution` (output) / `Datasets` (nested) | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) | Serializza `id`, `name`, `descr`, `url` (URL) e la lista `datasets`. |
| Modello `Attribution` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L121) | `name` indicizzato **ma non unique**, `url` String, relazione `datasets` (`lazy="dynamic"`). |
| `@decorators.auth.require_all(Role.ADMIN)` | `restapi.services.authentication` | Gate di autorizzazione su tutti i metodi: nega anonimi **e** utenti autenticati privi di ruolo admin. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` (framework) | `FlaskClient` di test; richieste reali contro l'app Flask. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Stack di teardown **LIFO**; esegue i callback dopo lo `yield`. **Non** ingoia eccezioni (un teardown rotto fa fallire il test). |
| `admin_headers_EXT` | fixture | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | **Importata per nome** nel modulo (non da `conftest.py`). Fa `BaseTests().do_login(client, None, None)` → header dell'utente **admin di default** (stato condiviso). |
| `attribution_payload_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Costruisce payload `AttributionInput` con nome uuid; `url` opzionale (passabile `""` o `None`). |
| `create_dataset_bundle_via_api_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Crea via API attribution+group+license+dataset e registra cleanup per ognuno (contiene `assert 200` interni). |
| `create_regular_user_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Crea un utente reale **non-admin** (`open_dataset`) + registra cleanup utente e directory `/data`. |
| `created_id_from_response_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Estrae l'id scalare dalla risposta POST (asserisce `int|str`). |
| `find_list_item_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Cerca l'item nel listing confrontando id **normalizzati a stringa** (gestisce Int modello vs Str schema). |
| `delete_admin_records_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Cancellazione DB difensiva/idempotente in ordine relazionale; rimuove anche associazioni m2m `dataset.users`. |
| `response_content_EXT` | helper | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | Decodifica il body via `BaseTests().get_content`. |
| `ADMIN_ATTRIBUTIONS_ENDPOINT_EXT`, `ADMIN_MISSING_ID_EXT` | costanti | [admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) | URL `/api/admin/attributions` e id sentinella `987654321` per i 404. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Accesso diretto al DB di test per verificare i side effect (precondizioni e post-delete). |

## 4. Analisi dettagliata di ogni test

### `test_admin_attributions_require_admin_role_EXT`
- **Obiettivo**: garantire che l'endpoint sia protetto dal ruolo `ADMIN`, distinguendo anonimo da autenticato-ma-non-autorizzato.
- **Backend coinvolto**: decorator `@decorators.auth.require_all(Role.ADMIN)` su `AdminAttributions.get`.
- **Flusso**: GET anonimo → poi crea un utente reale non-admin (`create_regular_user_EXT`) → GET con i suoi header → confronto status.
- **Setup**: `client`, `cleanup_registry`; l'utente temporaneo è registrato per il cleanup subito dopo la creazione.
- **Assert**: `anonymous_response.status_code == 401` (nessuna credenziale) **e** `forbidden_response.status_code == 401` (credenziali valide ma senza ruolo admin). Garantiscono che il gate scatti su entrambe le condizioni.
- **Casi coperti**: error path / **autorizzazione** (auth gate prima del CRUD).
- **Nota**: restapi restituisce **401 anche per l'utente autenticato non-admin** (non 403); è comportamento del framework, non un errore del test.

### `test_admin_attribution_create_list_update_delete_EXT`
- **Obiettivo**: coprire il ciclo CRUD completo e la normalizzazione `url=""` → `None`.
- **Backend coinvolto**: `post` (con `pre_load null_url`), `get` (serializzazione + nested datasets), `put`, `delete`.
- **Flusso**: POST `url=""` → estrae id e registra cleanup → GET e verifica normalizzazione/serializzazione → PUT (nome/descr/URL nuovi) → GET di conferma → DELETE → verifica DB diretta.
- **Setup**: `admin_headers_EXT`; istanza DB via `sqlalchemy.get_instance()`; payload sintetico con `url=""` intenzionale.
- **Assert**:
  - `create_response.status_code == 200` → POST riuscita, id scalare presente.
  - sul listing: `name`/`descr` uguali al payload, `url is None` (il `pre_load` ha normalizzato la stringa vuota), `datasets == []` (attribution senza dataset).
  - `update_response.status_code == 204` → `empty_response()` del controller; il listing riflette i nuovi `name`/`descr`/`url`.
  - `delete_response.status_code == 204` e `db.Attribution.query.get(id) is None` → il delete è realmente persistito.
- **Casi coperti**: happy path completo + **validation/normalization** (url vuota) + verifica side effect DB.

### `test_admin_attribution_list_includes_related_datasets_EXT`
- **Obiettivo**: verificare che il listing annidi correttamente i dataset collegati all'attribution.
- **Backend coinvolto**: `get` (loop `for d in a.datasets` → `{"name": d.name, "id": d.arkimet_id}`).
- **Flusso**: crea un bundle completo via API (attribution→group→license→dataset) → GET listing → cerca l'item dell'attribution → verifica la presenza del dataset annidato.
- **Setup**: `create_dataset_bundle_via_api_EXT` (4 record sintetici, cleanup LIFO automatico).
- **Assert**: `status_code == 200` e `{"id": bundle.dataset_arkimet_id, "name": bundle.dataset_name} in item["datasets"]` → conferma il **contratto di serializzazione**: l'`id` annidato è l'`arkimet_id` (non l'id numerico del dataset).
- **Casi coperti**: happy path / contratto di serializzazione relazionale.

### `test_admin_attribution_missing_update_delete_return_404_EXT`
- **Obiettivo**: verificare i rami `NotFound` di `put` e `delete` su id inesistente.
- **Backend coinvolto**: `put`/`delete` → `if not attribution: raise NotFound`.
- **Flusso**: precondizione DB (`get(ADMIN_MISSING_ID_EXT) is None`) → PUT e DELETE sullo stesso id mancante.
- **Setup**: `admin_headers_EXT`; **nessun dato creato** (niente `cleanup_registry`), così i 404 misurano il contratto e non un conflitto con stato residuo.
- **Assert**: `update_response.status_code == 404` e `delete_response.status_code == 404` → entrambi i rami NotFound sono raggiungibili e corretti.
- **Casi coperti**: error path / edge (id sentinella alto).
- **Nota**: a differenza di licenses/datasets, qui il `NotFound` è realmente esercitabile perché `put` usa correttamente `filter_by(...).first()` (con parentesi) e l'`id` è un path param libero, non soggetto a `OneOf`.

## 5. Call chain

```
GET    /api/admin/attributions        → require_all(ADMIN) → AdminAttributions.get
                                          → db.Attribution.query.all() → per ogni a: a.datasets → Attribution(many) → 200
POST   /api/admin/attributions        → require_all(ADMIN) → use_kwargs(AttributionInput[pre_load null_url])
                                          → AdminAttributions.post → db.Attribution(**kwargs) → add → commit
                                          → response(id) 200  |  DatabaseDuplicatedEntry → Conflict 409
PUT    /api/admin/attributions/<id>   → require_all(ADMIN) → use_kwargs(AttributionInput)
                                          → AdminAttributions.put → filter_by(id).first()
                                          → None? NotFound 404  :  setattr+commit → empty_response 204
DELETE /api/admin/attributions/<id>   → require_all(ADMIN) → AdminAttributions.delete → filter_by(id).first()
                                          → None? NotFound 404  :  session.delete+commit → empty_response 204
```

## 6. Comportamenti nascosti

- **`admin_headers_EXT` non è in un `conftest.py`**: è una `@pytest.fixture` definita in [support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py) e **importata per nome** in cima al modulo. pytest la risolve come fixture solo perché il simbolo è importato; non è auto-discovery di cartella. Una rimozione dell'import “non usato” la romperebbe.
- **Stato condiviso del default user**: `admin_headers_EXT` logga l'**admin di default** (come `auth_headers`). Tutti i test admin condividono quella sessione; l'isolamento si regge sui nomi uuid e su `find_list_item_EXT`, non su utenti usa-e-getta.
- **Listing globale**: `get` ritorna **tutte** le attribution del DB; i test trovano il proprio record tramite `find_list_item_EXT` (robusto rispetto a record preesistenti o paralleli).
- **`create_dataset_bundle_via_api_EXT` contiene assert interni**: ogni `create_*_via_api_EXT` asserisce `status_code == 200`. Un fallimento in arrange si manifesta come assert dell'helper, non del test, e attraversa il vero controller (non è un mock).
- **Cleanup LIFO con side effect m2m**: `delete_admin_records_EXT` rimuove anche le associazioni `dataset.users` prima del delete; l'ordine di teardown (dataset→license→group→attribution) dipende dall'ordine di creazione nel bundle.
- **Nessun `conftest.py` locale** nella cartella `admin/` (lo dichiara esplicitamente il banner di `support_EXT.py`): non esistono fixture autouse né monkeypatch in questo dominio.

## 7. Checklist di revisione

- [ ] Confermare che `401` (e non `403`) per l'utente non-admin sia il comportamento atteso/voluto di restapi e che il test debba codificarlo.
- [ ] Verificare che `url is None` nel listing dipenda davvero dal `pre_load null_url` e non da un default del modello.
- [ ] Controllare che l'`id` annidato dei dataset sia volutamente l'`arkimet_id` e non l'id numerico (contratto da preservare).
- [ ] Verificare che l'assenza di `cleanup_registry` in `..._missing_..._404_EXT` non lasci stato (non crea record: OK).
- [ ] Confermare che l'import “non usato” di `admin_headers_EXT` resti (è la fixture: non rimuovere).
- [ ] Verificare che il default user admin condiviso non crei accoppiamento d'ordine con altri moduli admin in esecuzione parallela.

## 8. Possibili criticità

- **Accoppiamento sull'admin di default**: tutti i test usano la stessa sessione admin; in esecuzione parallela o con catalogo pre-popolato la robustezza dipende interamente dall'unicità dei nomi uuid (rischio basso ma reale).
- **`Conflict` (409) non esercitato**: il modello `Attribution.name` **non è unique**, quindi il ramo `DatabaseDuplicatedEntry → Conflict` di `post` è praticamente non testabile/non raggiungibile con questo modello; il test non lo copre (corretto, ma il ramo resta scoperto).
- **Test white-box sul nested id**: l'assert sul dataset annidato dipende dal dettaglio interno `id = arkimet_id`; se cambiasse la serializzazione (es. id numerico) il test andrebbe aggiornato pur restando valido il contratto “lista dataset”.
- **Fixture importata per nome**: pratica fragile a livello di tooling (linter/auto-fix degli import potrebbe rimuoverla); meno esplicita di una fixture in `conftest.py`.
- **Dipendenza dalla traduzione errori restapi** non rilevante qui (nessun 409), ma da tenere presente se in futuro si aggiungesse un vincolo unique.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_admin_attributions_require_admin_role_EXT` | `AdminAttributions.get` + `require_all(ADMIN)` | 401 anonimo **e** non-admin | — | `client`, `cleanup_registry` | Bassa |
| `test_admin_attribution_create_list_update_delete_EXT` | `post`/`get`/`put`/`delete` + `null_url` | CRUD completo + `url=""`→None + DB side effect | — (DB diretto in assert) | `admin_headers_EXT`, `cleanup_registry` | Alta |
| `test_admin_attribution_list_includes_related_datasets_EXT` | `get` (nested datasets) | dataset annidato `{id=arkimet_id, name}` | — | `admin_headers_EXT`, `cleanup_registry` | Media |
| `test_admin_attribution_missing_update_delete_return_404_EXT` | `put`/`delete` (NotFound) | 404 su id inesistente | — | `admin_headers_EXT` | Bassa |
