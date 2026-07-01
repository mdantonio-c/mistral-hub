# Review — `test_authorization.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Dominio **opendata** marcato `runtime_sensitive`: **entrambi** i test di questo file sono **silenziosamente skippabili** (vedi §6).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/opendata/test_authorization.py](projects/mistral/backend/tests/integration/opendata/test_authorization.py)
- **Scopo**: verificare le regole di **autorizzazione** sui tre endpoint opendata quando il dataset è **privato** (`group_license.is_public == False`): rifiuto di anonimi **e** di utenti autenticati ma non autorizzati (`401`); accesso consentito all'utente esplicitamente collegato al dataset.
- **Tipologia**: test di **integrazione HTTP reale** (controller + DB SQLAlchemy + filesystem `/opendata`). Marker: `integration`, `deterministic`, `runtime_sensitive`. Nessun mock.
- **Endpoint coperti**: listing (`/datasets/<id>/opendata`), download dataset (`/opendata/<id>/download`), download file diretto (`/opendata/<filename>`).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `OpendataFileList.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L36) | `GET /datasets/<id>/opendata` — `auth.optional`; se dataset privato e non autorizzato → `self.response(..., code=401)`. |
| `OpendataDownload.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L282) | `GET /opendata/<id>/download` — privato e non autorizzato → `raise Unauthorized` (401). |
| `OpendataDownloadFile.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L203) | `GET /opendata/<filename>` — risale alla `Request`, itera i `datasets` e per ognuno verifica l'autorizzazione → non autorizzato → `Unauthorized` (401). |
| `check_dataset_authorization` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L562) | Cuore della regola: `is_public → True`; anonimo+privato → `False`; autenticato+privato → `True` solo se `arkimet_id ∈ [d.arkimet_id for d in user.datasets]`. |
| m2m `user.datasets` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L139) | Tabella `auth_association`; popolata da `authorize_user_for_dataset` nel secondo test. |
| `OPENDATA_DIR` (`/opendata`) | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py#L5) | File reale letto/streamato in caso di accesso autorizzato. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test; chiamate HTTP reali. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**; non ingoia eccezioni. |
| `create_private_opendata_env` | helper locale | [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) | Crea dataset **privato** + utente (non autorizzato) + 1 file opendata reale; **può `pytest.skip`** se manca `Attribution`. |
| `authorize_user_for_dataset` | helper locale | [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) | Collega (m2m) l'utente al dataset (solo 2° test). |
| `create_opendata_user` (indiretto) | helper locale | [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) | Utente con `open_dataset=True` ma **senza** dataset collegati. |
| `BaseTests().get_content` | helper | `restapi.tests` | Decodifica il body JSON (listing autorizzato). |
| `sqlalchemy.get_instance()` (indiretto) | connettore | `restapi.connectors` | Istanza DB usata dagli helper di seeding. |

> Infrastruttura condivisa (non ridocumentata): `cleanup_registry` da [tests/conftest.py](projects/mistral/backend/tests/conftest.py); helper utente da [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py). La cartella è marcata `runtime_sensitive`.

## 4. Analisi dettagliata di ogni test

### `test_private_dataset_endpoints_reject_unauthorized_access`
- **Obiettivo**: tutti e tre gli endpoint, su dataset **privato**, devono rispondere `401` sia all'**anonimo** sia all'utente **autenticato ma non autorizzato**.
- **Backend coinvolto**: `OpendataFileList.get` (ramo `code=401`), `OpendataDownload.get` (`Unauthorized`), `OpendataDownloadFile.get` (loop datasets → `Unauthorized`), tutti via `check_dataset_authorization`.
- **Flusso**: `create_private_opendata_env` → costruisce i 3 URL (listing per `arkimet_id`, download per `arkimet_id`, file per `result.filename`) → esegue **6** GET (anon/loggato × 3 endpoint).
- **Setup**: `cleanup_registry`; dataset privato, utente con `user.datasets` **vuoto** (autenticato ma non collegato), 1 risultato opendata reale.
- **Assert**: i sei status sono tutti `401`.
- **Casi coperti**: error path/authorization su **tutti** gli endpoint privati; dimostra la distinzione **autenticato ≠ autorizzato** (il login da solo non basta: serve l'aggancio m2m).

### `test_private_dataset_endpoints_allow_authorized_user`
- **Obiettivo**: l'utente **esplicitamente autorizzato** sul dataset privato può elencare e scaricare i contenuti.
- **Backend coinvolto**: stessi tre `get`, ma con `check_dataset_authorization → True`; download a **singolo file** (`len==1`) → `send_from_directory` (octet-stream); listing → serializzazione del pacchetto; file diretto → stream del file reale.
- **Flusso**: `create_private_opendata_env` → `authorize_user_for_dataset(db, user.uuid, dataset.id)` (append m2m + commit) → 3 GET autenticate (listing, download, file).
- **Setup**: come sopra, ma con l'utente collegato al dataset.
- **Assert**:
  - listing: `200`, `len(content) == 1`, `content[0]["filename"] == result.filename`;
  - download dataset: `200`, body `== result.content` (singolo file servito diretto, non zip);
  - download file: `200`, body `== result.content`.
- **Casi coperti**: happy path autorizzato end-to-end su tutti e tre gli endpoint, inclusa la **rilettura del file reale** da `/opendata`.

## 5. Call chain

```
GET /datasets/<id>/opendata        → auth.optional → OpendataFileList.get
                                      → Datasets.filter_by(arkimet_id).first → None? 404
                                      → License → GroupLicense → is_public?
                                          no → check_dataset_authorization(db, arkimet_id, user)
                                                 anonimo → False  |  user senza m2m → False  →  response(code=401)
                                                 user con m2m → True → query Request.args.contains({datasets}) → lista
GET /opendata/<id>/download        → auth.optional → OpendataDownload.get (use_kwargs OpenDataDownloadQuery)
                                      → Datasets.filter_by(arkimet_id).first → None? NotFound 404
                                      → GroupLicense.is_public? no → check_dataset_authorization
                                          non autorizzato → raise Unauthorized 401
                                          autorizzato → filtra → len==1 → send_from_directory (octet-stream)
GET /opendata/<filename>           → auth.optional → OpendataDownloadFile.get
                                      → FileOutput.filter_by(filename).first → None? NotFound 404
                                      → Request.get(request_id) → None? ServerError
                                      → for d in args["datasets"]: check_dataset_authorization
                                          non autorizzato → raise Unauthorized 401
                                          autorizzato → file esiste? → send_from_directory
```

## 6. Comportamenti nascosti

- **Entrambi i test sono silenziosamente skippabili**: passano da `create_private_opendata_env` → `create_test_dataset`, che fa `pytest.skip` se `db.Attribution.query.first() is None`. In un ambiente senza attribution, **tutta** la verifica di autorizzazione opendata sparisce senza fallire.
- **Asimmetria di status code "nascosta"**: il listing produce il 401 con `self.response(..., code=401)`, mentre i due download lo producono con `raise Unauthorized`. Il risultato osservabile è identico (`401`), ma i percorsi interni sono diversi.
- **Autenticato ≠ autorizzato**: l'utente del primo test ha `open_dataset=True` ma `user.datasets` vuoto; il `401` da loggato dimostra che la decisione dipende dalla m2m, **non** dal permesso.
- **`OpendataDownloadFile` itera tutti i dataset della richiesta**: basta **un** dataset non autorizzato per ottenere `401`. Qui la `Request` ha un solo dataset, quindi il loop non è stressato con liste eterogenee.
- **Ramo `ServerError` non raggiunto**: nel file-download, il caso "request mancante" non è esercitato (il `FileOutput` seminato ha sempre la sua `Request`).
- **File reale**: il secondo test rilegge davvero il contenuto scritto su `/opendata`; non è un mock di `send_file`.

## 7. Checklist di revisione

- [ ] **Segnalare in CI** lo skip silenzioso: confermare che esista almeno un `Attribution` nell'ambiente, o i due test non vengono eseguiti.
- [ ] Confermare che il `401` da utente loggato derivi dalla m2m vuota e non da altri permessi.
- [ ] Verificare che il download autorizzato a singolo file resti `octet-stream` (ramo `len==1`) e non zip.
- [ ] Valutare l'aggiunta di uno scenario file-download con `Request` multi-dataset (uno autorizzato + uno no) per coprire il loop in `OpendataDownloadFile`.
- [ ] Verificare che il teardown rimuova il file reale da `/opendata` e l'utente temporaneo.

## 8. Possibili criticità

- **Skip silenzioso = falso senso di sicurezza**: i test di sicurezza/autorizzazione sono proprio quelli che non si vuole veder saltati senza preavviso; la dipendenza da un `Attribution` preesistente è una precondizione fragile.
- **Copertura parziale del loop multi-dataset** in `OpendataDownloadFile`: il contratto "un solo dataset non autorizzato basta a negare" non è verificato.
- **Ramo `ServerError` del file-download non coperto** (request orfana): resta latente.
- **Accoppiamento al filesystem reale**: il secondo test dipende dalla scrivibilità/lettura di `/opendata`; un ambiente con permessi diversi potrebbe far fallire il download autorizzato per motivi non legati all'autorizzazione.
- **Dipendenza dalla creazione utente via API admin** (login di default): un eventuale cambio del flusso admin impatterebbe indirettamente questi test.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture (incl. locali) | Skip silenzioso |
|---|---|---|---|---|---|
| `test_private_dataset_endpoints_reject_unauthorized_access` | 3 `get` opendata + `check_dataset_authorization` | `401` per anonimo e loggato-non-autorizzato su listing/download/file | — (DB+FS reali) | `client`, `cleanup_registry`, `create_private_opendata_env` | **Sì** (no `Attribution`) |
| `test_private_dataset_endpoints_allow_authorized_user` | 3 `get` opendata (rami autorizzati) | `200` + contenuti corretti dopo aggancio m2m | — (DB+FS reali) | `client`, `cleanup_registry`, `create_private_opendata_env`, `authorize_user_for_dataset` | **Sì** (no `Attribution`) |
