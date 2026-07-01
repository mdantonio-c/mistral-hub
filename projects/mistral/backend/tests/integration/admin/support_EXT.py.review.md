# Review — `admin/support_EXT.py` (infrastruttura di dominio)

> File di review per modulo di supporto. Non contiene test (`*_EXT.py` di supporto, nessuna funzione `test_*`).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/admin/support_EXT.py](projects/mistral/backend/tests/integration/admin/support_EXT.py)
- **Scopo**: centralizzare costanti URL, payload builder, helper di creazione via API (con cleanup registrato) e cleanup DB per i quattro moduli `test_admin_*_EXT.py`. Evita duplicazione e tiene fuori dalla baseline legacy l'infrastruttura dei nuovi test admin.
- **Tipologia**: modulo di supporto (costanti + dataclass + una fixture + helper). Importato **per nome** dai test (niente `conftest.py` locale nella cartella `admin/`).

## 2. Backend realmente esercitato (indirettamente)

| Via | Endpoint / Modello | Path |
|---|---|---|
| `create_attribution_via_api_EXT` → POST | `AdminAttributions.post` | [endpoints/admin_attributions.py](projects/mistral/backend/endpoints/admin_attributions.py) |
| `create_license_group_via_api_EXT` → POST | `AdminLicGroups.post` | [endpoints/admin_license_groups.py](projects/mistral/backend/endpoints/admin_license_groups.py) |
| `create_license_via_api_EXT` → POST | `AdminLicenses.post` | [endpoints/admin_licenses.py](projects/mistral/backend/endpoints/admin_licenses.py) |
| `create_dataset_via_api_EXT` → POST | `AdminDatasets.post` | [endpoints/admin_datasets.py](projects/mistral/backend/endpoints/admin_datasets.py) |
| `admin_headers_EXT` → login | `BaseTests().do_login` (admin di default) | `restapi.tests` |
| `create_regular_user_EXT` → utente reale | `create_authenticated_test_user` / `register_test_user_cleanup` | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) |
| `delete_admin_records_EXT` → DB diretto | modelli `Datasets`, `License`, `GroupLicense`, `Attribution` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L101) |
| `DOWNLOAD_DIR` | directory output utente da pulire | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py) (via `mistral.endpoints`) |

## 3. Elementi definiti

| Elemento | Tipo | Cosa fa / note |
|---|---|---|
| `ADMIN_ATTRIBUTIONS_ENDPOINT_EXT` … `ADMIN_DATASETS_ENDPOINT_EXT` | costanti URL | `{API_URI}/admin/...` per i quattro domini metadata. |
| `ADMIN_MISSING_ID_EXT` | costante | `987654321` — id sentinella per i test `404`; i test verificano via DB che non esista prima di usarlo. |
| `AdminDatasetBundle_EXT` | `@dataclass(frozen=True)` | Record immutabile con gli id di attribution/group/license/dataset + `dataset_arkimet_id`/`dataset_name`; usato dai test di listing annidato. |
| `admin_headers_EXT` | **fixture** | `BaseTests().do_login(client, None, None)` → header dell'**admin di default**; `assert headers is not None`. Locale al support, **importata per nome** dai moduli. |
| `unique_admin_token_EXT(prefix)` | helper | `f"{prefix}_{uuid4().hex[:12]}"` — nomi unici per evitare collisioni col catalogo runtime. |
| `attribution_payload_EXT(...)` | builder | Payload `AttributionInput`; `url` passabile `""` (per il `pre_load null_url`) o `None`. |
| `license_group_payload_EXT(...)` | builder | Payload `LicGroupInput`; `is_public` e `dballe_dsn` (default `"DBALLE_EXT"`) sempre espliciti. |
| `license_payload_EXT(group_license_id, ...)` | builder | Payload license; `group_license` inviato come **stringa** (per la `OneOf`); `url` opzionale. |
| `dataset_payload_EXT(license_id, attribution_id, ...)` | builder | Payload dataset; default `arkimet_id == name == token`, `sort_index=10`, `supports_variable_browsing=True`; `license`/`attribution` come stringhe. |
| `response_content_EXT(response)` | helper | Decodifica il body via `BaseTests().get_content` (gestisce scalari/list/dict in modo uniforme). |
| `created_id_from_response_EXT(response)` | helper | Estrae l'id scalare dalla POST; `assert isinstance(content, (int, str))` poi `int(...)`. |
| `find_list_item_EXT(items, item_id)` | helper | Trova l'item confrontando id **normalizzati a stringa** (Int modello vs Str schema); `AssertionError` se assente. |
| `create_regular_user_EXT(client, cleanup_registry)` | helper | Crea un utente reale **non-admin** (`{"open_dataset": True}`) e registra cleanup utente + directory `Path(DOWNLOAD_DIR, uuid)`. |
| `create_attribution_via_api_EXT(...)` | helper | POST attribution (asserisce 200) + registra cleanup DB; ritorna l'id. |
| `create_license_group_via_api_EXT(...)` | helper | POST group license (asserisce 200) + cleanup DB. |
| `create_license_via_api_EXT(..., group_license_id, ...)` | helper | POST license collegata a un gruppo (asserisce 200) + cleanup DB. |
| `create_dataset_via_api_EXT(..., license_id, attribution_id, ...)` | helper | POST dataset (asserisce 200) + cleanup DB. |
| `create_dataset_bundle_via_api_EXT(...)` | helper | Crea attribution→group→license→dataset in ordine; ritorna `AdminDatasetBundle_EXT`. Il dataset è creato per ultimo → teardown LIFO lo elimina per primo. |
| `delete_admin_records_EXT(db, ...)` | helper | Cleanup DB **idempotente** in ordine dataset→license→group→attribution; per i dataset rimuove anche le associazioni m2m `dataset.users` e fa `flush()` per passo, `commit()` finale. |

## 4. Comportamenti nascosti

- **Fixture in un `support.py`, non in `conftest.py`**: `admin_headers_EXT` è una `@pytest.fixture` che diventa disponibile **solo perché importata per nome** in ciascun modulo di test. Non è auto-discovery: rimuovere l'import “inutilizzato” romperebbe i test.
- **Stato condiviso del default user**: `admin_headers_EXT` logga l'admin di **default** della suite (stessa logica di `auth_headers`). Tutti i test admin condividono quella sessione; l'isolamento poggia sui nomi uuid e su `find_list_item_EXT`.
- **Helper “che fanno più del nome”**: i `create_*_via_api_EXT` **contengono `assert status_code == 200`** e **registrano cleanup**. Quindi (a) un fallimento in fase di arrange si manifesta come assert dell'helper, non del test; (b) attraversano il **vero controller** (non sono mock) e dipendono dalla schema dinamica (la `OneOf` richiede che le dipendenze esistano già).
- **`delete_admin_records_EXT` con side effect m2m**: prima di cancellare un dataset svuota `dataset.users` (tabella `auth_association`), comportamento non evidente dal nome “delete records”.
- **Cleanup LIFO dipendente dall'ordine di creazione**: la correttezza relazionale del teardown dipende dal fatto che il bundle crei il dataset per ultimo; il `CleanupRegistry` esegue in ordine inverso ([helpers/cleanup.py](projects/mistral/backend/tests/helpers/cleanup.py)).
- **`find_list_item_EXT` maschera un mismatch di tipo**: confronta id come stringa perché gli schema admin dichiarano `id` come `Str` mentre i modelli sono `Integer`; un assert “ingenuo” su id numerico sarebbe fragile.
- **`created_id_from_response_EXT` codifica un'assunzione di contratto**: gli endpoint POST ritornano un **id scalare** (non un JSON annidato); se cambiasse il contratto, l'assert `isinstance` fallirebbe qui e non nel test.
- **Nessun fake/monkeypatch/worker**: il banner del file lo dichiara; tutto passa per Flask + SQLAlchemy reali (deterministico).

## 5. Checklist di revisione

- [ ] Confermare che la scelta di mettere `admin_headers_EXT` in `support_EXT.py` (anziché in un `conftest.py` locale) sia voluta e che gli import “non usati” della fixture restino.
- [ ] Verificare che l'ordine di cleanup in `delete_admin_records_EXT` (dataset→license→group→attribution) copra tutte le FK reali e che lo svuotamento di `dataset.users` non lasci righe orfane in `auth_association`.
- [ ] Controllare che `ADMIN_MISSING_ID_EXT` resti realisticamente “mai esistente” negli ambienti di test (id molto alto).
- [ ] Verificare che i builder mantengano `arkimet_id == name` per i dataset solo dove serve (il 409 si basa su entrambi i vincoli unique).
- [ ] Confermare che `create_regular_user_EXT` pulisca davvero sia l'utente sia la directory `DOWNLOAD_DIR/uuid`.
- [ ] Verificare che l'uso del default admin condiviso non introduca accoppiamento d'ordine fra i quattro moduli in esecuzione parallela.

## 6. Possibili criticità

- **Fixture importata per nome**: pratica fragile rispetto a linter/auto-fix che rimuovono import non referenziati esplicitamente; meno scopribile di una fixture in `conftest.py`.
- **Helper con assert “nascosti”**: spostare le asserzioni di setup dentro gli helper rende i fallimenti di arrange meno leggibili (lo stack punta a `support_EXT.py`, non al test che ha fallito).
- **Accoppiamento setup↔schema dinamica**: poiché `license`/`attribution`/`group_license` sono `OneOf` runtime, ogni helper deve creare le dipendenze nell'ordine giusto; un riordino del codice di test può rompere silenziosamente la validazione (400 inattesi).
- **Cleanup idempotente ma “rumoroso”**: `delete_admin_records_EXT` fa `flush()` ad ogni passo e `commit()` finale; in caso di FK non previste il `flush` solleva qui, mescolando errori di teardown con errori di test (il `CleanupRegistry` **non** ingoia eccezioni).
- **Stato condiviso del default admin**: come per `auth_headers`, l'esecuzione parallela o un catalogo pre-popolato si reggono solo sull'unicità uuid e su `find_list_item_EXT`.
- **Dipendenza inversa di visibilità**: l'integrazione globale importa già costanti da `support.py` di dominio (pattern visto in access-key); qui il rischio è speculare se in futuro un `conftest` globale importasse da questo support specifico del dominio admin.
