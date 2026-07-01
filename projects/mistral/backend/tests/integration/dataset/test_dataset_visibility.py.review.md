# Review — `test_dataset_visibility.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo runtime-sensitive: l'esito dipende dai dataset realmente presenti nel runtime.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/dataset/test_dataset_visibility.py](projects/mistral/backend/tests/integration/dataset/test_dataset_visibility.py)
- **Scopo**: verificare il **contratto anonimo** del catalogo dataset — un utente non autenticato può elencare i dataset pubblici, leggere il dettaglio di un dataset pubblico noto e riceve `404` su un id inesistente.
- **Tipologia**: test di **integrazione HTTP** (controller reale + `SqlApiDbManager` + DB SQLAlchemy), **senza autenticazione**. Marker: `integration`, `deterministic`, `runtime_sensitive`.
- **Numero di test**: 1 (`test_dataset_endpoints_expose_public_catalog_without_login`).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Datasets.get` | [endpoints/datasets.py](projects/mistral/backend/endpoints/datasets.py) | `GET /api/datasets` — `auth.optional()`; chiama `SqlApiDbManager.get_datasets(db, user=None)`; ordina per `sort_index`/`description`; **200** sempre (lista, eventualmente vuota). |
| `SingleDataset.get` | [endpoints/datasets.py](projects/mistral/backend/endpoints/datasets.py) | `GET /api/datasets/<dataset_name>` — ricarica l'intero catalogo visibile e cerca `ds["id"] == dataset_name` (l'`id` è l'`arkimet_id`); `NotFound` (**404**) se assente. |
| `SqlApiDbManager.get_datasets` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L482) | Per utente anonimo scarta i dataset il cui `GroupLicense.is_public` è falso (`if not group_license_obj.is_public: continue`). Espone `is_public` nel payload. |
| Modello `Datasets` / `GroupLicense` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L146) | `arkimet_id` unique (è l'`id` esposto), relazione `license → group_license`; `GroupLicense.is_public` governa la visibilità anonima. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test; le chiamate sono **senza header** (anonimo). |
| `faker` | fixture | `pytest-faker` | Genera l'id casuale inesistente (`faker.pystr()`) per il ramo 404. |
| `first_public_dataset_id` | helper | [tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py#L16) | Restituisce l'`id` del **primo** dataset con `is_public is True`; se nessuno esiste fa `pytest.skip`. **Importato dai helpers condivisi, non dal `support.py` locale.** |
| `API_URI` | costante | `restapi.tests` | Prefisso `/api`. |

## 4. Analisi dettagliata di ogni test

### `test_dataset_endpoints_expose_public_catalog_without_login`
- **Obiettivo**: garantire che il catalogo pubblico sia accessibile in anonimo e che gli id sconosciuti diano 404.
- **Backend coinvolto**: `Datasets.get` (lista), `SingleDataset.get` (dettaglio + 404), `get_datasets` con `user=None` (filtro `is_public`).
- **Flusso**: `GET /datasets` (no auth) → `first_public_dataset_id(list_response.json)` sceglie un id pubblico → `GET /datasets/<id_pubblico>` → `GET /datasets/<id_casuale>`.
- **Setup**: nessun arrange di stato; lo scenario riusa interamente il catalogo runtime esistente.
- **Assert**:
  - `list_response.status_code == 200` e `isinstance(list_response.json, list)`.
  - `dataset_response.status_code == 200` e `isinstance(dataset_response.json, dict)`.
  - `missing_response.status_code == 404`.
- **Casi coperti**: happy path anonimo (lista + dettaglio) + error path (id inesistente). **Non** copre dataset privati né utenti autenticati (delegati a `test_dataset_authorization.py`).

## 5. Call chain

```
GET /api/datasets                 → auth.optional() → Datasets.get(user=None)
                                    → SqlApiDbManager.get_datasets(db, None)
                                    → per ogni ds: License → GroupLicense; if not is_public: continue
                                    → sorted(...) → response(list) 200
first_public_dataset_id(payload)  → primo ds con is_public is True  |  pytest.skip se nessuno
GET /api/datasets/<id_pubblico>   → auth.optional() → SingleDataset.get
                                    → get_datasets(db, None) → next(ds.id == name) → response(dict) 200
GET /api/datasets/<id_casuale>    → SingleDataset.get → matched_ds is None → NotFound 404
```

## 6. Comportamenti nascosti

- **Skip silenzioso runtime-sensitive**: se il runtime non espone alcun dataset pubblico, `first_public_dataset_id` esegue `pytest.skip("No public dataset is available in this environment")` e il test **non verifica nulla** del ramo dettaglio. In CI senza catalogo seedato l'intero test diventa un no-op silenzioso.
- **`SingleDataset.get` non interroga il DB per id**: ricarica l'intero catalogo visibile e fa un `next(...)` in memoria; il 404 deriva dal mancato match in lista, non da una query puntuale.
- **`PUBLIC_DATASET_NAME = "lm5"` è una costante morta**: dichiarata nel modulo ma **mai usata** (il dataset pubblico è scelto dinamicamente). Residuo che potrebbe trarre in inganno il revisore.
- **`is_public` è una proprietà del gruppo licenza**, non del dataset: la visibilità anonima dipende da `GroupLicense.is_public`, valorizzato dall'initializer (`CCBY_COMPLIANT`/`CCBY-SA_COMPLIANT` sono `is_public=True`).
- **`get` non distingue 401/403**: essendo `auth.optional()`, l'anonimo riceve sempre 200 sulla lista; non esiste un ramo "login required" qui.
- **Errore infrastrutturale → 503**: se `get_datasets` solleva, l'endpoint converte in `ServiceUnavailable` (503); il test non copre questo ramo.

## 7. Checklist di revisione

- [ ] Confermare che lo `pytest.skip` su assenza di dataset pubblici sia accettabile in CI o se serva un seed deterministico (oggi il test può passare "verde" senza eseguire l'asserzione chiave).
- [ ] Verificare che il test importi `first_public_dataset_id` dai **helpers condivisi** e non dal `support.py` locale del dominio (vedi review di `support.py`).
- [ ] Valutare la rimozione della costante morta `PUBLIC_DATASET_NAME`.
- [ ] Confermare che `is_public` nel payload rispecchi `GroupLicense.is_public` e non un campo del dataset.

## 8. Possibili criticità

- **Falso verde da skip**: il test è etichettato `deterministic` ma il suo cuore (dettaglio pubblico) è subordinato alla presenza runtime di un dataset pubblico; senza, lo skip nasconde la non-verifica.
- **Accoppiamento al catalogo runtime**: nessuno stato viene preparato; il test fotografa il catalogo reale. Cambiamenti di seed o di `is_public` possono spostare il dataset scelto senza che il test se ne accorga.
- **Marker `runtime_sensitive` corretto ma silenzioso**: utile come segnale, ma non impedisce l'esecuzione in ambienti privi di dati.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Skip silenzioso |
|---|---|---|---|---|---|
| `test_dataset_endpoints_expose_public_catalog_without_login` | `Datasets.get`, `SingleDataset.get`, `get_datasets(user=None)` | Lista anonima 200, dettaglio pubblico 200, id inesistente 404 | — (DB reale) | `client`, `faker` | **Sì** — `first_public_dataset_id` → `pytest.skip` se nessun dataset pubblico |
