# Review — `test_requests_listing_archive_clone_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline. La baseline ([test_delete_pending_request.py](projects/mistral/backend/tests/integration/requests/test_delete_pending_request.py)) copre già `DELETE /requests/<id>`; questo modulo copre listing, archiviazione e clone.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py](projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py)
- **Scopo**: verificare le superfici di gestione delle richieste rimaste fuori dalla baseline — forma e filtri di `GET /requests` (paginazione, `get_total`, `archived`), `PUT /requests/<id>` (archiviazione, request pendente vietata, owner mismatch) e `GET /requests/<id>/clone` (clone con espansione dataset, request mancante, request altrui).
- **Tipologia**: test di **integrazione HTTP** (controller reale + DB SQLAlchemy), con **seeding diretto delle righe `Request`** per evitare la dipendenza dai worker di estrazione. Marker: `integration`, `deterministic`.
- **Numero di test**: 10, in tre classi: `TestRequestsListing` (4), `TestRequestsArchive` (3), `TestRequestsClone` (3).
- **Helper/fixture locali al modulo**: `seed_request_row`, `dataset_ids_for_user`, `delete_request_row` e la fixture `requests_user` (definiti **nel file stesso**, non in `conftest.py`).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `UserRequests.get` | [endpoints/requests.py](projects/mistral/backend/endpoints/requests.py) | `GET /api/requests` — `get_total` → `count_user_requests` + `pagination_total` (**206**); altrimenti `filter_by(user_id, archived)` + `joinedload(fileoutput)` + `paginate` + rename `datasets`→`dataset_names` → `200`. |
| `UserRequests.put` | [endpoints/requests.py](projects/mistral/backend/endpoints/requests.py) | `PUT /api/requests/<id>` — `check_request`/`check_owner`/`check_request_is_pending_within_grace_period`, poi `delete_request_record` + `archived = True`. |
| `CloneUserRequests.get` | [endpoints/requests.py](projects/mistral/backend/endpoints/requests.py) | `GET /api/requests/<id>/clone` — `check_request`/`check_owner`, `get_user_request_by_id`, sostituisce `args["datasets"]` con le spec complete via `get_datasets`. |
| `repo.count_user_requests` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L96) | `count()` filtrato per `user_id` + `archived`. |
| `repo.check_request` / `check_owner` / `check_request_is_pending_within_grace_period` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L69) | Guardie `404` / `401` / `403`. |
| `repo.delete_request_record` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L172) | Chiamata da `put` **prima** di archiviare (rimuove l'eventuale fileoutput). |
| `repo.get_user_request_by_id` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L377) | `db.Request.query.get(request_id)` per il clone. |
| `repo.get_datasets` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L482) | Lista dataset visibili all'utente (`licenceSpecs=True`); espone `id = arkimet_id`. |
| Modello `Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | `user_id`, `name`, `args` (JSONB), `submission_date`, `status`, `archived`. |
| Modello `Datasets` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L146) | `arkimet_id` (lookup in `dataset_ids_for_user` e match nel clone). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `faker` | fixture | plugin `faker` | `faker.pystr()` per i nomi delle richieste. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L37) | Teardown **LIFO**; ogni riga seed registra la propria delete. |
| `requests_user` | fixture **locale al modulo** | [questo file](projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py) | Utente temporaneo con `open_dataset=True` e accesso esplicito al dataset `agrmet`; cleanup utente/cartelle. |
| `seed_request_row` | helper **locale** | [questo file](projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py) | Inserisce una `Request` con età/stato/archived controllati; `args = {"datasets": [...]}`. |
| `dataset_ids_for_user` | helper **locale** | [questo file](projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py) | Traduce `arkimet_id`→`Datasets.id` (JSON) per i permessi utente; **asserisce** che il dataset esista. |
| `delete_request_row` | helper **locale** | [questo file](projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py) | Cancella una riga seed se ancora presente. |
| `create_authenticated_test_user` / `register_test_user_cleanup` / `AuthenticatedTestUser` | helper | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Creazione/login/teardown utenti (anche del secondo utente "altrui"). |
| `Env.get_int("GRACE_PERIOD", 2)` | config | `restapi.env` | `grace_period_days`/`GRACE_PERIOD` per l'età delle richieste negli scenari di archiviazione. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Seeding e verifica diretti sul DB. |

> Nota: questo modulo **non** usa `conftest.py`/`support.py` locali (che servono ai test di *delete*); definisce in proprio fixture e helper di seeding.

## 4. Analisi dettagliata di ogni test

### `TestRequestsListing`

#### `test_get_requests_returns_expected_shape`
- **Obiettivo**: `GET /requests` ritorna una lista con i campi standard della richiesta.
- **Backend coinvolto**: `get` (ramo non-total, `archived=False` default) + rename `datasets`→`dataset_names`.
- **Flusso**: seed 1 `Request` `SUCCESS` → `GET /requests`.
- **Setup**: `requests_user`; cleanup riga registrato.
- **Assert**: `200`; `data` è `list` con `len >= 1`; trova l'item per `id`; presenza chiavi `id`/`name`/`args`/`submission_date`/`status` e `args["dataset_names"]`.
- **Casi coperti**: contratto di forma del listing (incluso il rename del campo dataset).

#### `test_get_total_returns_206_with_count`
- **Obiettivo**: `GET /requests?get_total=true` ritorna `206` con `total`.
- **Backend coinvolto**: ramo `get_total` → `count_user_requests(db, user.id, archived=False)` → `pagination_total` (`TotalSchema`, code 206).
- **Flusso**: seed 3 richieste `SUCCESS` → `GET ?get_total=true`.
- **Setup**: `requests_user`; cleanup di ogni riga con **binding esplicito** `lambda rid=request_id:` (cattura corretta nel loop).
- **Assert**: `206`; `"total" in data`; `data["total"] >= 3`.
- **Casi coperti**: convenzione partial-content del conteggio totale.

#### `test_archived_false_excludes_archived_requests`
- **Obiettivo**: `?archived=false` esclude le richieste archiviate.
- **Backend coinvolto**: `get` con `filter_by(..., archived=False)`.
- **Flusso**: seed 1 attiva + 1 archiviata → `GET ?archived=false`.
- **Assert**: `200`; l'attiva è presente, l'archiviata no.
- **Casi coperti**: filtro `archived=false`.

#### `test_archived_true_returns_only_archived_requests`
- **Obiettivo**: `?archived=true` ritorna solo le archiviate.
- **Backend coinvolto**: `get` con `filter_by(..., archived=True)`.
- **Flusso**: seed 1 attiva + 1 archiviata → `GET ?archived=true`.
- **Assert**: `200`; l'archiviata è presente, l'attiva no.
- **Casi coperti**: filtro `archived=true` (complementare al precedente).

### `TestRequestsArchive`

#### `test_archive_success_for_old_completed_request`
- **Obiettivo**: `PUT /requests/<id>` archivia una richiesta completata fuori dal grace period.
- **Backend coinvolto**: `put` → guardie ok → `delete_request_record` → `archived = True` → `200`.
- **Flusso**: seed `SUCCESS`, `age_days = grace_period_days + 1` → `PUT`.
- **Assert**: `200`; `db.Request.query.get(id).archived is True`.
- **Casi coperti**: happy path dell'archiviazione + effetto persistito.

#### `test_archive_pending_request_forbidden`
- **Obiettivo**: archiviare una richiesta pendente recente è vietato.
- **Backend coinvolto**: `put` → `check_request_is_pending_within_grace_period` **True** (`PENDING`, `age_days=0`) → `Forbidden`.
- **Flusso**: seed `PENDING`, `age_days=0` → `PUT`.
- **Assert**: `403`.
- **Casi coperti**: protezione grace period sull'archiviazione.

#### `test_archive_owner_mismatch_unauthorized`
- **Obiettivo**: archiviare la richiesta di un altro utente è negato.
- **Backend coinvolto**: `put` → `check_owner` su request di `other_user` → `None` (falsy) → `Unauthorized` (**401**).
- **Flusso**: crea `other_user`, seed richiesta posseduta da `other_user` (`SUCCESS`, vecchia) → `PUT` con header di `requests_user`.
- **Setup**: doppio utente; cleanup di entrambi gli utenti e della riga.
- **Assert**: `401`.
- **Casi coperti**: distinzione **401 (owner)** vs **403 (grace)**.

### `TestRequestsClone`

#### `test_clone_returns_args_with_dataset_specs`
- **Obiettivo**: `GET /requests/<id>/clone` ritorna gli `args` con i dataset espansi.
- **Backend coinvolto**: `CloneUserRequests.get` → `get_user_request_by_id` → `args["datasets"] = [ds for ds in get_datasets(user, licenceSpecs=True) if ds["id"] in args_datasets]`.
- **Flusso**: seed `SUCCESS` con `dataset_names=["agrmet"]` → `GET .../clone`.
- **Setup**: `requests_user` con accesso esplicito ad `agrmet` (necessario perché `get_datasets` filtra per visibilità utente).
- **Assert**: `200`; `data["datasets"]` è una lista non vuota; il primo elemento ha `id` e `name`.
- **Casi coperti**: arricchimento dataset nel clone (match `args_datasets`↔`arkimet_id`).

#### `test_clone_missing_request_not_found`
- **Obiettivo**: clone di una richiesta inesistente → `404`.
- **Backend coinvolto**: `check_request` **False** → `NotFound`.
- **Flusso**: `GET /requests/999999/clone` (id **hardcoded** inesistente).
- **Setup**: solo `requests_user`; **nessun seeding, nessun cleanup**.
- **Assert**: `404`.
- **Casi coperti**: error path "richiesta mancante".

#### `test_clone_foreign_request_unauthorized`
- **Obiettivo**: clone della richiesta di un altro utente → `401`.
- **Backend coinvolto**: `check_request` ok → `check_owner` falsy → `Unauthorized`.
- **Flusso**: crea `other_user`, seed richiesta di `other_user` → `GET .../clone` con header di `requests_user`.
- **Assert**: `401`.
- **Casi coperti**: error path "richiesta altrui".

## 5. Call chain

```
GET  /api/requests[?get_total|archived]  → auth.require() → get_pagination → marshal_with(TotalSchema, 206)
                                           → use_kwargs(archived: Bool=False, location=query)
                                           → get_total? → repo.count_user_requests(db, user.id, archived) → pagination_total → 206 {total}
                                           → else → Request.query.filter_by(user_id, archived)
                                                    .options(joinedload(fileoutput)).order_by(submission_date desc).paginate(page,size).items
                                                    → per item: filtra args None + rename datasets→dataset_names → response(list) 200
PUT  /api/requests/<id>                   → auth.require()
                                           → check_request?  no  → NotFound 404
                                           → check_owner?    no  → Unauthorized 401
                                           → check_request_is_pending_within_grace_period? yes → Forbidden 403
                                           → delete_request_record → request.archived = True → commit → 200
GET  /api/requests/<id>/clone             → auth.require()
                                           → check_request?  no  → NotFound 404
                                           → check_owner?    no  → Unauthorized 401
                                           → get_user_request_by_id
                                           → args["datasets"] = [ds for ds in get_datasets(user, licenceSpecs=True) if ds["id"] in args_datasets]
                                           → response(args) 200
```

## 6. Comportamenti nascosti

- **Seeding che bypassa l'endpoint di creazione**: `seed_request_row` scrive direttamente la riga `Request`; il percorso `POST` (validazione, dispatch worker, visibilità dataset in creazione) **non** è esercitato. Il modulo isola listing/archive/clone dal runtime di estrazione.
- **Il listing richiede sempre la chiave `args["datasets"]`**: l'endpoint fa `filtered_args.pop("datasets")`; una riga senza quella chiave provocherebbe `KeyError`/500. L'helper la fornisce sempre (default `["agrmet"]`), mascherando questa precondizione implicita.
- **"Archiviare" cancella prima il fileoutput**: `put` chiama `delete_request_record` (rimozione file/DB) **prima** di settare `archived=True`. Le righe seed non hanno fileoutput, quindi quel ramo è no-op e non viene coperto.
- **Il clone dipende dalla visibilità dataset dell'utente**: `requests_user` è creato con `open_dataset=True` **e** accesso esplicito ad `agrmet` proprio perché `get_datasets` filtra per autorizzazione; senza questi permessi `data["datasets"]` sarebbe vuoto e il test fallirebbe (coupling forte fra fixture e clone).
- **`id` dataset = `arkimet_id`** (non l'id numerico): il match nel clone è `ds["id"] in args_datasets` con `args_datasets=["agrmet"]`; `dataset_ids_for_user`, al contrario, usa l'id **numerico** per i permessi utente. Due "id" diversi convivono nello stesso flusso.
- **401 vs 403**: owner mismatch → `Unauthorized` (401); pendente entro grace → `Forbidden` (403). `check_owner` ritorna `None` (non `False`) quando non è owner, ma il `if not ...` lo tratta correttamente come falsy.
- **`data["total"] >= 3` (non `== 3`)**: assert difensivo; l'utente temporaneo è fresco quindi il valore atteso è 3, ma il `>=` tollera eventuali residui.
- **Binding del cleanup nel loop**: in `test_get_total...` la lambda usa `rid=request_id` per catturare il valore corretto; negli altri test le variabili (`active_id`/`archived_id`) sono distinte, quindi la cattura per closure è sicura.

## 7. Checklist di revisione

- [ ] Confermare che il dataset `agrmet` esista nel DB di test (altrimenti `dataset_ids_for_user` fallisce in setup) e che i permessi concessi a `requests_user` siano sufficienti per vederlo nel clone.
- [ ] Verificare che il seeding diretto rispetti il contratto del listing (presenza di `args["datasets"]`), dato che l'endpoint vi fa `pop`.
- [ ] Confermare la semantica `200` (non `204`) per `PUT` archive e `200` per il clone.
- [ ] Verificare che `age_days = grace_period_days + 1` collochi davvero la richiesta fuori dal grace period per qualunque valore di `GRACE_PERIOD`.
- [ ] Valutare il rischio dell'id **hardcoded** `999999` nel test "missing" (vedi §8).
- [ ] Confermare che i due utenti (owner reale vs `requests_user`) siano entrambi ripuliti nei test di mismatch/foreign.

## 8. Possibili criticità

- **Id hardcoded `999999`** in `test_clone_missing_request_not_found`: presuppone che nessuna `Request` abbia quell'id; in un DB con molti dati storici l'assunzione è fragile e renderebbe il test falso-negativo.
- **Coupling fixture↔clone via dataset**: il successo del clone dipende dai permessi dataset di `requests_user`; un cambio nella policy di visibilità o nel seed `agrmet` rompe il test in modo non ovvio (la causa è nella fixture, non nel test).
- **Bypass del path di creazione**: il seeding diretto non valida che una richiesta *reale* (creata via API) produca `args` compatibili con il `pop("datasets")`; eventuali divergenze fra formato seed e formato prodotto dai worker non emergono qui.
- **Ramo file di `delete_request_record` non coperto**: l'archiviazione di una richiesta **con** fileoutput (e quindi la cancellazione del file) non è esercitata.
- **Filtri non parametrizzati**: solo `archived=true/false` e `get_total`; paginazione (`page`/`size`), `sort_by`/`sort_order` e `input_filter` dell'endpoint restano non coperti.
- **Effetti collaterali su disco**: `delete_request_record` accede a `DOWNLOAD_DIR`/`OPENDATA_DIR`; con seed privi di fileoutput è innocuo, ma resta una dipendenza dal filesystem in `put`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_get_requests_returns_expected_shape` | `get` (listing) | forma lista + rename `dataset_names` | — (DB seed) | `requests_user`, `cleanup_registry`, `faker` | Bassa |
| `test_get_total_returns_206_with_count` | `get` + `count_user_requests` | `206` + `total` | — | `requests_user`, `cleanup_registry`, `faker` | Bassa |
| `test_archived_false_excludes_archived_requests` | `get` (filter archived) | esclude archiviate | — | `requests_user`, `cleanup_registry`, `faker` | Bassa |
| `test_archived_true_returns_only_archived_requests` | `get` (filter archived) | solo archiviate | — | `requests_user`, `cleanup_registry`, `faker` | Bassa |
| `test_archive_success_for_old_completed_request` | `put` (archive) | `200` + `archived=True` | — | `requests_user`, `cleanup_registry`, `faker` | Media |
| `test_archive_pending_request_forbidden` | `put` + grace check | `403` su pendente recente | — | `requests_user`, `cleanup_registry`, `faker` | Bassa |
| `test_archive_owner_mismatch_unauthorized` | `put` + `check_owner` | `401` su request altrui | — | `requests_user` + utente "altrui", `cleanup_registry` | Media |
| `test_clone_returns_args_with_dataset_specs` | `clone get` + `get_datasets` | `args` con dataset espansi | — | `requests_user` (con accesso `agrmet`), `cleanup_registry` | Media |
| `test_clone_missing_request_not_found` | `clone get` + `check_request` | `404` (id `999999`) | — | `requests_user` | Bassa |
| `test_clone_foreign_request_unauthorized` | `clone get` + `check_owner` | `401` su request altrui | — | `requests_user` + utente "altrui", `cleanup_registry` | Media |
