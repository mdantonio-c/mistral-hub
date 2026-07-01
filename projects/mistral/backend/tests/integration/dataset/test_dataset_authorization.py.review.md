# Review — `test_dataset_authorization.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo runtime-sensitive: prepara stato sintetico ma legge/riusa dataset reali del runtime.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/dataset/test_dataset_authorization.py](projects/mistral/backend/tests/integration/dataset/test_dataset_authorization.py)
- **Scopo**: verificare le **regole di autorizzazione** del catalogo dataset per un utente autenticato — dataset pubblici, dataset privati **non** assegnati (404), dataset privati **assegnati** (200), e la differenza tra accesso al catalogo pubblico (`open_dataset`) e i grant espliciti che sopravvivono allo spegnimento di `open_dataset`.
- **Tipologia**: test di **integrazione HTTP** end-to-end con manipolazione diretta del DB (creazione dataset/license/group sintetici, utente temporaneo via API admin). Marker: `integration`, `deterministic`, `runtime_sensitive`.
- **Numero di test**: 1 (`test_dataset_endpoints_respect_user_authorizations`) — scenario multi-asserzione molto denso.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Datasets.get` | [endpoints/datasets.py](projects/mistral/backend/endpoints/datasets.py) | `GET /api/datasets` con utente loggato → lista filtrata per autorizzazioni. |
| `SingleDataset.get` | [endpoints/datasets.py](projects/mistral/backend/endpoints/datasets.py) | `GET /api/datasets/<name>` → 200 se visibile, **404** se non in lista autorizzata. |
| `SqlApiDbManager.get_datasets` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L482) | Cuore dell'autorizzazione: per dataset privato (`not is_public`) richiede `ds.name in user_datasets_auth`; per dataset pubblico richiede `user.open_dataset`. |
| `AdminUsers.put` / `.delete` | endpoint admin users | `PUT /api/admin/users/<uuid>` per spegnere `open_dataset` (→ **204**); `DELETE` per il teardown utente (→ **204**). |
| Modelli `Datasets`, `License`, `GroupLicense` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L101) | m2m `Datasets.users` (associazione autorizzazioni); `GroupLicense.is_public` governa pubblico/privato. |
| Flag utente `open_dataset` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L25) | Colonna aggiunta a `User`; decide se i dataset pubblici sono visibili. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient`. |
| `faker` | fixture | `pytest-faker` | Id casuale per il ramo 404. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO**; usato **solo** per i dataset eventualmente creati. |
| `BaseTests` | classe | `restapi.tests` | `create_user`, `do_login`, `get_content` — gestione utente/login **manuale** (no fixture `auth_headers`). |
| `first_public_dataset_id` | helper | [tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py#L16) | Sceglie un dataset pubblico dalla lista vista **dall'utente**; `pytest.skip` se nessuno. |
| `_ensure_dataset_exists` (locale) | helper | nel file di test | Riusa o **crea** un dataset con `name`/`arkimet_id` dati; registra cleanup solo se crea; `pytest.skip` se mancano license/attribution. |
| `_delete_dataset` (locale) | helper | nel file di test | Stacca le associazioni m2m `dataset.users` e poi elimina la riga. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Manipolazione diretta di `Datasets`/`License`/`GroupLicense`. |

## 4. Analisi dettagliata di ogni test

### `test_dataset_endpoints_respect_user_authorizations`
- **Obiettivo**: dimostrare che (a) un dataset privato è visibile solo se assegnato all'utente, (b) il catalogo pubblico dipende da `open_dataset`, (c) i grant espliciti restano validi anche dopo `open_dataset=False`.
- **Backend coinvolto**: `Datasets.get`, `SingleDataset.get`, `get_datasets` (rami pubblico/privato + `open_dataset`), endpoint admin users (PUT/DELETE).
- **Flusso (arrange → act → assert → finally)**:
  1. **arrange**: `_ensure_dataset_exists("sa_dataset_special")` e `_ensure_dataset_exists("sa_dataset")`; salva i `license_id` originali; crea un `GroupLicense(is_public=False)` + `License` sintetici e **riassegna entrambi i dataset** a quella licenza privata (li rende privati); crea un utente con `datasets=[id(sa_dataset_special)]` e `open_dataset=True`; login utente e login admin.
  2. **act**: `GET /datasets` (utente) → sceglie `public_dataset_id` dalla lista utente; poi GET su: dataset pubblico, id casuale, `sa_dataset` (privato non autorizzato), `sa_dataset_special` (privato autorizzato); `PUT /admin/users/<uuid>` con `open_dataset=False`; di nuovo GET dataset pubblico, GET `sa_dataset_special`, GET `/datasets/error`, GET `/datasets/duplicates`.
  3. **assert** (vedi sotto).
  4. **finally**: `DELETE /admin/users/<uuid>` (==204); ripristina i `license_id` originali dei due dataset; elimina license/group sintetici.
- **Setup**: 2 dataset (creati o riusati), 1 group + 1 license sintetici privati, 1 utente temporaneo. Cleanup misto (`cleanup_registry` per i dataset creati; `finally` per utente, licenze e ripristino).
- **Assert**:
  - `list_response` 200 e `list`.
  - dataset pubblico (con `open_dataset=True`) 200 e `dict`.
  - id casuale → 404; `sa_dataset` (privato non assegnato) → **404**.
  - `sa_dataset_special` (privato assegnato) → 200 e `is_public is False`.
  - PUT admin → **204**.
  - dataset pubblico dopo `open_dataset=False` → **404** (catalogo pubblico nascosto).
  - `sa_dataset_special` ancora → **200** (grant esplicito sopravvive).
  - `/datasets/error` → 404; `/datasets/duplicates` → 404.
- **Casi coperti**: matrice autorizzativa completa pubblico/privato × `open_dataset` on/off, più due lookup per nome falliti. **Non** copra il ramo `licenceSpecs=True`.

## 5. Call chain

```
get_datasets(db, user)            → per ogni ds: License → GroupLicense
  if not is_public:                 → if ds.name not in [u.name for u in user.datasets]: continue   # privato non assegnato → escluso
  else (is_public):                 → if not user.open_dataset: continue                            # pubblico nascosto se open_dataset=False
GET /datasets/sa_dataset          → SingleDataset.get → ds non in lista autorizzata → NotFound 404
GET /datasets/sa_dataset_special  → ds privato ma assegnato → presente in lista → response 200 (is_public False)
PUT /admin/users/<uuid>           → open_dataset=False → empty_response 204
GET /datasets/<id_pubblico> (2ª)  → ora escluso da get_datasets → NotFound 404
GET /datasets/sa_dataset_special  → grant esplicito indipendente da open_dataset → 200
GET /datasets/error|duplicates    → nessun match per nome → NotFound 404
```

## 6. Comportamenti nascosti

- **Mutazione di dati reali del runtime**: se `sa_dataset`/`sa_dataset_special` **già esistono**, il test **non li crea** ma ne **riassegna il `license_id`** a una licenza privata sintetica, poi ripristina l'originale nel `finally`. Lo stato reale del catalogo viene temporaneamente alterato; il ripristino dipende dall'esecuzione del `finally`.
- **Cleanup asimmetrico**: `_ensure_dataset_exists` registra `cleanup_registry.add(_delete_dataset)` **solo quando crea** il dataset. Se i dataset preesistono, non vengono mai eliminati (solo `license_id` ripristinato) — comportamento voluto ma da conoscere.
- **Doppio skip silenzioso**:
  - `_ensure_dataset_exists` fa `pytest.skip` se non esistono **almeno una license e una attribution** nel DB.
  - `first_public_dataset_id` fa `pytest.skip` se la **lista vista dall'utente** non contiene dataset pubblici (possibile in runtime minimali) → l'intero scenario si ferma prima delle asserzioni autorizzative.
- **`/datasets/error` e `/datasets/duplicates` non sono route speciali**: per quanto risulta da [endpoints/datasets.py](projects/mistral/backend/endpoints/datasets.py) l'unica route parametrica è `/datasets/<dataset_name>`, quindi sono semplici lookup per nome falliti (→ 404), non endpoint dedicati.
- **Autorizzazione per `name`, lookup per `arkimet_id`**: `get_datasets` filtra i privati confrontando `ds.name` con `user.datasets`, mentre `SingleDataset` cerca per `id` (== `arkimet_id`). Il test funziona perché i dataset sintetici hanno `name == arkimet_id`; con dati reali dove i due differiscono il comportamento potrebbe divergere.
- **Gestione utente manuale (no `auth_headers`)**: il test crea/distrugge il proprio utente e fa `do_login(None, None)` per l'admin; non riusa la fixture condivisa.
- **`flush()` vs `commit()`**: il group/license sintetici sono creati con `flush()` e l'assegnazione finale con `commit()`; il `finally` ripristina e poi elimina con `commit()`.

## 7. Checklist di revisione

- [ ] Confermare che la mutazione temporanea del `license_id` su dataset reali sia accettabile e che il ripristino nel `finally` sia robusto anche in caso di fallimento a metà arrange.
- [ ] Verificare che i due `pytest.skip` (license/attribution assenti; nessun dataset pubblico per l'utente) non producano falsi verdi in CI.
- [ ] Valutare l'asimmetria del cleanup (dataset non eliminati se preesistenti) e l'eventuale accumulo di righe `sa_dataset*` tra run.
- [ ] Confermare la semantica `name` (autorizzazione) vs `arkimet_id` (lookup) e la sua tenuta su dataset reali dove i due campi differiscono.
- [ ] Verificare che `/datasets/error` e `/datasets/duplicates` siano effettivamente 404 e non route oscurate da altri moduli endpoint.
- [ ] Confermare che l'utente temporaneo venga sempre eliminato (assert 204 nel `finally`).

## 8. Possibili criticità

- **Rischio residui su dati reali**: se il processo viene interrotto tra l'assegnazione della licenza privata e il `finally`, i dataset reali resterebbero con un `license_id` sintetico già cancellato (FK pendente). Mitigato dall'uso di `finally`, ma non da una transazione atomica.
- **Falso verde da skip**: come per `test_dataset_visibility.py`, l'esito "verde" non garantisce che le asserzioni autorizzative siano state eseguite.
- **Test monolitico**: un singolo test concentra ~14 asserzioni eterogenee; un fallimento iniziale maschera le verifiche successive e complica la diagnosi.
- **Accoppiamento al seeding**: dipende dalla presenza di license/attribution seedate dall'initializer e dalla semantica `is_public` dei gruppi.
- **Dipendenza dall'endpoint admin users**: il cuore del test (transizione `open_dataset`) passa per `PUT /admin/users`; una regressione lì può falsare il risultato senza riguardare il dominio dataset.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture (incl. locali) | Skip silenzioso |
|---|---|---|---|---|---|
| `test_dataset_endpoints_respect_user_authorizations` | `Datasets.get`, `SingleDataset.get`, `get_datasets` (pubblico/privato/`open_dataset`), admin users PUT/DELETE | Privato non assegnato 404, privato assegnato 200, pubblico 200→404 con `open_dataset` off, grant esplicito persistente | — (DB diretto, nessun monkeypatch) | `client`, `faker`, `cleanup_registry`, `BaseTests`, `_ensure_dataset_exists`/`_delete_dataset` (locali) | **Sì** — `pytest.skip` se mancano license/attribution **o** se nessun dataset pubblico è visibile all'utente |
