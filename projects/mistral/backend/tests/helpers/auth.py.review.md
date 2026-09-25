# Review — `helpers/auth.py` (helper condiviso)

> File di review per helper riusabile cross-area. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py)
- **Scopo**: creare utenti temporanei autenticati con permessi noti e gestirne login, directory di output e teardown.
- **Tipologia**: helper di autenticazione/utenti condiviso.

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `BaseTests.create_user` / `do_login` | `restapi.tests` | Creazione utente + login reali via API. |
| Admin users API | `DELETE {API_URI}/admin/users/<uuid>` ([endpoints](projects/mistral/backend/endpoints/)) | Cancellazione utente in teardown (atteso `204`). |
| `db.User` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py) | Lettura del record utente per ricavare `id`. |
| `DOWNLOAD_DIR` | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py) | Radice della cartella output dell'utente. |

## 3. Elementi definiti

| Simbolo | Tipo | Cosa fa |
|---|---|---|
| `AuthenticatedTestUser` | dataclass frozen | Record `(uuid, user_id, headers, output_dir)`. |
| `create_authenticated_test_user(base, client, permissions)` | funzione | Crea utente, login, legge `id` dal DB, ritorna il record. |
| `delete_test_user(base, client, uuid)` | funzione | Login admin + `DELETE /admin/users/<uuid>` (assert `204`). |
| `register_test_user_cleanup(...)` | funzione | Registra nel `cleanup_registry` la rimozione della dir e la cancellazione utente. |
| `make_basic_auth(email, access_key)` | funzione | Header HTTP Basic `base64(email:key)`. |

## 4. Comportamenti nascosti

- **`output_dir = DOWNLOAD_DIR/uuid/outputs`**: la convenzione del path su disco è incapsulata qui; i test che asseriscono su file generati dipendono da questa struttura.
- **`register_test_user_cleanup` aggiunge sia la rimozione del path sia la `DELETE` admin**: il chiamante ottiene due azioni di teardown con una sola chiamata.
- **`create_authenticated_test_user` asserisce `user is not None`**: se la creazione fallisce, l'errore emerge nell'helper.
- **`make_basic_auth`** è il punto unico della codifica base64: i test non mostrano questo dettaglio.

## 5. Checklist di revisione

- [ ] Verificare che chi crea utenti registri sempre il cleanup (rischio utenti orfani).
- [ ] Verificare che i permessi passati riflettano lo scenario reale del test.
- [ ] Confermare che `output_dir.parent` sia il path corretto da rimuovere (la dir utente, non solo `outputs`).

## 6. Possibili criticità

- **Teardown dipende dall'admin API**: se `DELETE /admin/users` cambia contratto (≠204), tutti i cleanup utente falliscono in blocco.
- **Accoppiamento al layout filesystem** (`DOWNLOAD_DIR/uuid/outputs`): cambi alla struttura di output impattano molti test indirettamente.
