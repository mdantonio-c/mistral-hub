# Review — `test_file_download.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo: copertura del contratto `GET /data/<filename>` (download output).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/test_file_download.py](projects/mistral/backend/tests/integration/data/test_file_download.py)
- **Scopo**: verificare i tre livelli di controllo di `GET /data/<filename>` in [endpoints/file.py](projects/mistral/backend/endpoints/file.py): download del file **posseduto** (`200` + contenuto), negazione **non-disclosure** del file non posseduto (`404`), e `404` quando il record `FileOutput` esiste ma il file fisico manca dal filesystem utente.
- **Tipologia**: test di **integrazione HTTP** (controller + `SqlApiDbManager.check_fileoutput` + DB + filesystem reali). **Nessun** fake Celery/Arkimet/Rabbit, **nessun** `monkeypatch`. Marker: `integration`, `deterministic`. 3 test.
- **Isolamento**: stato interamente sintetico (request/FileOutput/file scritti nell'area del solo utente temporaneo); nessun `pytest.skip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `FileDownload.get` | [endpoints/file.py](projects/mistral/backend/endpoints/file.py) | `GET /data/<filename>`: delega a `check_fileoutput`, poi `send_from_directory(..., as_attachment=True)`. |
| `SqlApiDbManager.check_fileoutput` | [services/sqlapi_db_manager.py#L21](projects/mistral/backend/services/sqlapi_db_manager.py#L21) | (1) lookup `FileOutput` per `filename` → `NotFound` se assente; (2) `check_owner` → `NotFound` se non proprietario; (3) ramo `opendata`; (4) `path.exists()` → `NotFound` se file mancante; ritorna `file_dir`. |
| `SqlApiDbManager.check_owner` | [services/sqlapi_db_manager.py#L50](projects/mistral/backend/services/sqlapi_db_manager.py#L50) | `True` se `FileOutput.user_id == user.id`, altrimenti `None` (falsy) → `NotFound`. |
| Modelli `FileOutput` / `Request` | [models/sqlalchemy.py#L59](projects/mistral/backend/models/sqlalchemy.py#L59) | `FileOutput.filename` (unique), `request_id`; `Request.opendata=False` → `file_dir = DOWNLOAD_DIR/<uuid>/outputs`. |
| `DOWNLOAD_DIR` | [endpoints/\_\_init\_\_.py](projects/mistral/backend/endpoints/__init__.py) | Radice del path di output utente usata sia dal backend sia dall'helper di setup. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py#L59](projects/mistral/backend/tests/conftest.py#L59) | Teardown LIFO: utenti, directory output, request sintetiche. |
| `create_data_endpoint_user` | helper | [data/support.py](projects/mistral/backend/tests/integration/data/support.py) | Utente temporaneo autenticato (qui senza dataset). |
| `create_file_download_record` | helper | [data/support.py](projects/mistral/backend/tests/integration/data/support.py) | Crea `Request(SUCCESS, opendata=False)` + `FileOutput` e — se `content` non è `None` — scrive il file fisico in `DOWNLOAD_DIR/<uuid>/outputs/<filename>`. |
| `API_URI` | costante | `restapi.tests` | Prefisso `/api`. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Istanza DB per il setup del record. |

## 4. Analisi dettagliata di ogni test

### `test_file_download_returns_owned_output_content`
- **Obiettivo**: il proprietario scarica il proprio output → `200` con contenuto esatto come attachment.
- **Backend coinvolto**: `check_fileoutput` (tutti e tre i livelli OK) → `send_from_directory(as_attachment=True)`.
- **Flusso**: `owner` temporaneo → `create_file_download_record(content="owned-file-download-ext")` (record DB + file fisico) → `GET /data/<filename>` con header del proprietario.
- **Setup**: un solo utente; file scritto nel suo `outputs`.
- **Assert**: `200`; `mimetype == "application/octet-stream"`; `get_data(as_text=True) == "owned-file-download-ext"`; `response.close()`.
- **Casi coperti**: happy path completo (lookup DB + ownership + presenza file + consegna contenuto).

### `test_file_download_denies_non_owned_output`
- **Obiettivo**: un utente diverso dal proprietario riceve `404` (non-disclosure dell'ownership).
- **Backend coinvolto**: `check_owner` → `False`/`None` → `NotFound` (il file esiste su disco ma è mascherato).
- **Flusso**: `owner` crea il file → `other_user` (secondo utente temporaneo) esegue `GET /data/<filename>` con le **proprie** credenziali.
- **Setup**: due utenti temporanei; nessuna autorizzazione condivisa.
- **Assert**: `404`.
- **Casi coperti**: error path / sicurezza. Il `404` (anziché `403`) è volutamente indistinguibile dal “file inesistente” per non rivelare l'esistenza di output altrui.

### `test_file_download_returns_404_when_db_row_exists_but_file_is_missing`
- **Obiettivo**: record `FileOutput` presente ma file fisico assente → `404` sul controllo finale di esistenza path.
- **Backend coinvolto**: `check_fileoutput` supera lookup DB + ownership, poi `path.exists()` → `False` → `NotFound`.
- **Flusso**: `owner` → `create_file_download_record(content=None)` (record DB **senza** file su disco) → `GET /data/<filename>` con il proprietario.
- **Setup**: proprietario corretto (così il `404` deriva **solo** dall'assenza del file, non da auth/ownership).
- **Assert**: `404`.
- **Casi coperti**: error path / coerenza DB↔filesystem.

## 5. Call chain

```
GET /api/data/<filename>  → auth.require() (401 anonimo)
  → FileDownload.get
      → SqlApiDbManager.check_fileoutput(user, filename):
            FileOutput.query.filter(filename==...).first()  → None → NotFound 404   [non testato direttamente]
            check_owner(user.id, file_id)  → not owner → NotFound 404               [TEST 2]
            request.opendata ? OPENDATA_DIR : DOWNLOAD_DIR/<uuid>/outputs           (qui opendata=False)
            path.exists() == False → NotFound 404                                   [TEST 3]
            return file_dir
      → send_from_directory(file_dir, filename, as_attachment=True) → 200           [TEST 1]
```

## 6. Comportamenti nascosti

- **`404` come non-disclosure**: per il file non posseduto il backend solleva `NotFound`, non `Forbidden`. È una scelta di sicurezza (non rivelare l'esistenza di output altrui); il test 2 la protegge esplicitamente.
- **Tre `404` con cause diverse**: lookup DB mancante, ownership negata, file fisico assente. I test coprono **ownership** (test 2) e **file mancante** (test 3); il `404` da lookup DB inesistente **non è testato direttamente** (richiederebbe un filename mai inserito).
- **Setup a doppio livello DB/filesystem**: `create_file_download_record` con `content=None` crea il record ma **non** scrive il file e **non** registra `add_path`, isolando il ramo `path.exists()` (vedi review di `support.py`).
- **Ramo `opendata` non esercitato**: la request è creata con `opendata=False`, quindi `file_dir = DOWNLOAD_DIR/<uuid>/outputs`; il ramo `OPENDATA_DIR` non è coperto.
- **`mimetype` da `as_attachment`**: il `application/octet-stream` deriva da `send_from_directory(..., as_attachment=True)` di Flask, non da logica applicativa.
- **`response.close()`** nel test 1: chiude lo stream del file inviato come attachment (buona pratica con `send_from_directory`).
- **Nessun fake, nessun `monkeypatch`**: il contratto di `file.py` dipende solo da DB, ownership e filesystem reali; nessun servizio esterno coinvolto.

## 7. Checklist di revisione

- [ ] Confermare che il `404` (e non `403`) per file non posseduto sia il contratto di sicurezza voluto (non-disclosure) e che non cambi nel tempo.
- [ ] Valutare se aggiungere copertura per il `404` da **lookup DB mancante** (filename mai inserito) e per il ramo **`opendata=True`** (`OPENDATA_DIR`).
- [ ] Verificare che il path di scrittura dell'helper (`DOWNLOAD_DIR/<uuid>/outputs`) coincida sempre con quello calcolato da `check_fileoutput` (accoppiamento setup↔backend).
- [ ] Confermare che `cleanup_registry` rimuova sia la directory output sia la request sintetica (no residui su disco/DB).

## 8. Possibili criticità

- **Accoppiamento al layout filesystem**: l'helper replica la convenzione `DOWNLOAD_DIR/<uuid>/outputs` del backend; un cambio di tale convenzione in `check_fileoutput` romperebbe i test pur con logica corretta.
- **`404` da DB-miss non coperto**: il primo ramo di `check_fileoutput` (FileOutput inesistente) resta scoperto; tutti i `404` testati nascono dopo un lookup riuscito.
- **Ramo `opendata` scoperto**: il download di output opendata da `OPENDATA_DIR` non è esercitato.
- **Asserzioni minime sui rami negativi**: i test 2 e 3 verificano solo lo status `404`, non il messaggio; accettabile per non-disclosure ma non distingue le due cause di `404` (ownership vs file mancante).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_file_download_returns_owned_output_content` | `check_fileoutput` + `send_from_directory` | 200 + contenuto + octet-stream | — | `client`, `cleanup_registry` | Media |
| `test_file_download_denies_non_owned_output` | `check_owner` | file non posseduto → 404 (non-disclosure) | — | `client`, `cleanup_registry` | Media |
| `test_file_download_returns_404_when_db_row_exists_but_file_is_missing` | `check_fileoutput` (`path.exists`) | record presente, file assente → 404 | — | `client`, `cleanup_registry` | Media |
