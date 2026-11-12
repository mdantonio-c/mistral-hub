# Review — `helpers/auth.py` (helper condiviso)

> File di review per helper riusabile cross-area. Non contiene test.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/helpers/auth.py`
- **Scopo**: creare utenti temporanei autenticati con permessi noti e gestirne login, directory di output e teardown.
- **Tipologia**: helper di autenticazione/utenti condiviso.

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `BaseTests.create_user` / `do_login` | `restapi.tests` | Creazione utente + login reali via API. |
| Admin users API | `DELETE {API_URI}/admin/users/<uuid>` (`projects/mistral/backend/endpoints/`) | Cancellazione utente in teardown (atteso `204`). |
| `db.User` | `projects/mistral/backend/models/sqlalchemy.py` | Lettura del record utente per ricavare `id`. |
| `DOWNLOAD_DIR` | `projects/mistral/backend/endpoints/__init__.py` | Radice della cartella output dell'utente. |

## 3. Elementi definiti

| Simbolo | Tipo | Cosa fa |
|---|---|---|
| `AuthenticatedTestUser` | dataclass frozen | Record `(uuid, user_id, headers, output_dir, email)`; `email` è valorizzata da `create_authenticated_test_user` e serve agli header BasicAuth. |
| `create_authenticated_test_user(base, client, permissions)` | funzione | Crea utente, login, legge `id` dal DB, ritorna il record. |
| `delete_test_user(base, client, uuid)` | funzione | Login admin + `DELETE /admin/users/<uuid>` (assert `204`). |
| `register_test_user_cleanup(...)` | funzione | Registra nel `cleanup_registry` la rimozione della dir e la cancellazione utente. |
| `create_dataset_test_user(client, cleanup_registry, dataset_ids=None, *, allowed_obs_archive=False, open_dataset=True)` | funzione | Crea utente con grant dataset espliciti (lista vuota = nessun grant) e flag archive, e registra il cleanup standard. Usato da `fields/support.py`, `fields/test_fields_api.py` e `observed/test_observations_download.py`. |
| `make_basic_auth(email, access_key)` | funzione | Header HTTP Basic `base64(email:key)`. |

## 4. Comportamenti nascosti

- **`output_dir = DOWNLOAD_DIR/uuid/outputs`**: la convenzione del path su disco è incapsulata qui; i test che asseriscono su file generati dipendono da questa struttura.
- **`register_test_user_cleanup` aggiunge sia la rimozione del path sia la `DELETE` admin**: il chiamante ottiene due azioni di teardown con una sola chiamata.
- **`create_authenticated_test_user` asserisce `user is not None`**: se la creazione fallisce, l'errore emerge nell'helper.
- **`make_basic_auth`** è il punto unico della codifica base64: i test non mostrano questo dettaglio. Non verifica che email e key siano validi né i permessi dell'utente.
- **`create_authenticated_test_user` non registra il cleanup**: il chiamante deve aggiungere `register_test_user_cleanup` (lo fa già `create_dataset_test_user`).
- **Ordine di registrazione**: `register_test_user_cleanup` registra prima il path e poi la `DELETE`; in LIFO l'utente viene cancellato prima della directory. Le risorse che dipendono dall'utente (request, schedule, access key) vanno registrate **dopo**, così vengono rimosse prima di lui; non affidarsi alle FK.
- **Campi non passati in `permissions`**: `BaseTests.create_user` li genera con `buildData` sullo schema admin, ruoli compresi. Non assumere ruoli o permessi non impostati esplicitamente.
- **Consumatori**: setup e teardown di access key, ARCO, admin, data, fields, observed, opendata, postprocessing, requests, schedules, tasks, templates, user_limits e degli helper `data_ready.py`, `observed_windows.py`, `real_workers.py`: un cambio qui li coinvolge tutti.

## 5. Checklist di revisione

- [ ] Verificare che chi crea utenti registri sempre il cleanup (rischio utenti orfani).
- [ ] Verificare che i permessi passati riflettano lo scenario reale del test.
- [ ] Confermare che `output_dir.parent` sia il path corretto da rimuovere (la dir utente, non solo `outputs`).

## 6. Possibili criticità

- **Teardown dipende dall'admin API**: se `DELETE /admin/users` cambia contratto (≠204), tutti i cleanup utente falliscono in blocco.
- **Accoppiamento al layout filesystem** (`DOWNLOAD_DIR/uuid/outputs`): cambi alla struttura di output impattano molti test indirettamente.
