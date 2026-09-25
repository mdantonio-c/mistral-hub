# Review — `test_arco_proxy.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/arco/test_arco_proxy.py](projects/mistral/backend/tests/integration/arco/test_arco_proxy.py)
- **Scopo**: verificare il comportamento del **proxy ARCO autenticato** (`GET /api/arco/<path:object_path>`) dal punto di vista del client: (1) l'accesso è negato senza credenziali valide; (2) un utente autenticato con access key può leggere il contenuto Zarr proxato da S3.
- **Tipologia**: test di **integrazione HTTP** (controller reale via `FlaskClient`); il backend S3 è **mockato** nel solo caso autorizzato. Marker: `pytestmark = [pytest.mark.integration, pytest.mark.deterministic]`.
- **Numero di test**: 2 funzioni.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `ArcoResource.get` | [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) | `GET /api/arco/<path:object_path>` — valida l'access key (BasicAuth), scarica l'oggetto da S3, lo restituisce come `Response` con mimetype indovinato. |
| `validate_access_key_from_request` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py#L51) | Legge `request.authorization`, recupera/valida la chiave, solleva `Unauthorized` (→ `401`) se mancante/errata/scaduta. |
| `access_key_get_by_user` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py#L30) | Recupera la `AccessKey` dall'email BasicAuth. |
| `is_access_key_valid` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py#L10) | Confronta chiave fornita/memorizzata e verifica la scadenza. |
| `guess_mime_type` | [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) | Deriva il mimetype dal nome file (non asserito qui; coperto in EXT). |
| `AccessKey` (scope `read:arco`) | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L167) | Record chiave usato dalla validazione. |
| `s3.get_instance` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py) | Connettore S3 — **mockato** nel test autorizzato. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `fresh_access_key` | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py#L29) | `POST /access-key` (login default user), asserisce `200` + `key`; ritorna `(headers, key)`. **Side effect**: crea/rigenera la access key reale del default user. |
| `auth_headers` (transitiva) | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py#L14) | Login del default user; dipendenza di `fresh_access_key`. |
| `monkeypatch` | fixture | `pytest` | Sostituisce `mistral.connectors.s3.get_instance` con un `MagicMock`; teardown automatico. |
| `make_basic_auth` | helper | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py#L114) | Codifica `email:access_key` in header `Authorization: Basic ...` (formato richiesto dal proxy). |
| `BaseAuthentication.default_user` | costante | `restapi.services.authentication` | Email del default user usata nella BasicAuth. |
| `mock_s3` (`MagicMock`) | mock locale | nel file di test | `client.get_object` → body con `read()` = `b'{"zarr_format": 2}'`. |

## 4. Analisi dettagliata di ogni test

### `test_arco_proxy_requires_authentication`
- **Obiettivo**: il proxy deve negare l'accesso (401) **prima** di servire dati remoti, applicando il controllo di sicurezza al confine Meteo-Hub.
- **Backend coinvolto**: `ArcoResource.get` → `validate_access_key_from_request()` (ramo `if not auth: raise Unauthorized`).
- **Flusso**: `GET /api/arco/ww3.zarr/.zgroup` **senza** header.
- **Setup**: solo `client`; **nessun mock S3** (non serve: la validazione fallisce prima).
- **Assert**: `status_code == 401` → conferma che il gate di autenticazione precede ogni accesso a S3.
- **Casi coperti**: error path / autorizzazione (credenziali assenti).

### `test_arco_proxy_returns_zgroup_for_authorized_user`
- **Obiettivo**: un utente autenticato con access key valida legge i metadati Zarr proxati.
- **Backend coinvolto**: `ArcoResource.get` → `validate_access_key_from_request()` (successo) → `s3.get_instance().client.get_object(...)` → `Response(body, mimetype=...)`.
- **Flusso**:
  1. `fresh_access_key` fornisce `valid_key`; `email = default_user`.
  2. `monkeypatch` su `mistral.connectors.s3.get_instance` → `mock_s3` il cui `get_object` ritorna un body `b'{"zarr_format": 2}'`.
  3. `headers = make_basic_auth(email, valid_key)`.
  4. `GET /api/arco/ww3.zarr/.zgroup` con header.
- **Setup**: `fresh_access_key`, `monkeypatch`; nessun cleanup esplicito (mock rimosso da pytest, chiave gestita dalla fixture).
- **Assert**: `status_code == 200`; `b"zarr_format" in response.data` → la validazione passa e il body S3 è propagato **invariato** al client.
- **Casi coperti**: happy path autenticato del proxy.

## 5. Call chain

```
GET /api/arco/<path:object_path>
  → ArcoResource.get
    → validate_access_key_from_request()        (BasicAuth: email:access_key)
        → access_key_get_by_user(email) → is_access_key_valid(...)
        → se mancante/errata/scaduta: raise Unauthorized → 401
    → s3.get_instance()                          [MOCK nel test autorizzato]
    → client.get_object(Bucket="arco", Key=object_path)
        → botocore ClientError "NoSuchKey" → NotFound(404)        (coperto in EXT)
        → altro ClientError → raise Exception                     (coperto/skip in EXT, ARCO-001)
    → data = body.read(); mime = guess_mime_type(Path(object_path).name)
    → Response(data, mimetype=mime) → 200
```

## 6. Comportamenti nascosti

- **Auth manuale, non da decoratore**: il proxy **non** usa `@decorators.auth.require()`; chiama `validate_access_key_from_request()` dentro il metodo. Il `401` nasce da `Unauthorized` sollevata dal service, non dal middleware standard di restapi.
- **Doppio controllo ridondante**: dopo `validate_access_key_from_request()` (che già solleva su errore), il codice fa anche `if not authorized: raise Unauthorized()`. In pratica il secondo ramo è di fatto irraggiungibile (la funzione ritorna sempre un record truthy oppure solleva).
- **Nel test 401 S3 non è mockato**: poiché la validazione fallisce prima di `s3.get_instance()`, S3 reale non viene mai contattato. Se l'ordine cambiasse, in ambiente di test il connettore reale solleverebbe (nessun S3 disponibile), non un 401 pulito.
- **`fresh_access_key` muta lo stato del default user condiviso** (crea/rigenera la chiave globale).
- **Mimetype non verificato qui**: il caso autorizzato usa `.zgroup` e asserisce solo il contenuto; la verifica di `guess_mime_type` sul filename è demandata al modulo EXT.
- **Distinzione errori S3**: il proxy cattura `botocore.exceptions.ClientError` (non `client.exceptions.NoSuchKey` come fa il catalogo). Questo ramo è coperto solo nel modulo EXT.

## 7. Checklist di revisione

- [ ] Confermare che il `401` derivi dal service `validate_access_key_from_request` e non da un decoratore (impatto su messaggi/header WWW-Authenticate).
- [ ] Valutare se il secondo `if not authorized: raise Unauthorized()` sia codice morto da rimuovere o difesa intenzionale.
- [ ] Verificare che il test autorizzato asserisca abbastanza (oggi: status + sottostringa nel body; nessun assert su mimetype/Content-Type).
- [ ] Confermare che il proxy debba restituire il body S3 **invariato** (nessuna trasformazione).
- [ ] Notare che i rami 404 (NoSuchKey) e l'errore S3 generico sono coperti nel file `*_EXT.py`, non qui.

## 8. Possibili criticità

- **Assert deboli nel caso autorizzato**: si verifica solo `status_code == 200` e `b"zarr_format" in response.data`; non si controlla il `Content-Type`/mimetype né l'uguaglianza esatta del body. Una regressione sul mimetype o una trasformazione indebita del payload potrebbe non emergere (mitigato dal modulo EXT).
- **Over-mock di S3**: il caso happy path non prova l'integrazione reale con il bucket; verifica solo la propagazione del body fornito dal mock.
- **Dipendenza dallo stato del default user**: `fresh_access_key` rigenera la chiave globale; possibile accoppiamento d'ordine con i moduli access-key in esecuzioni parallele (rischio di falso positivo/negativo).
- **Copertura parziale dei rami**: in questo file sono coperti solo 401 (no auth) e 200; i rami 404/500 e il caso "BasicAuth con chiave errata" sono altrove (`*_EXT.py`). Letto da solo, il file dà un quadro incompleto del contratto del proxy.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_arco_proxy_requires_authentication` | `ArcoResource.get` → `validate_access_key_from_request` | 401 senza credenziali, prima di S3 | — (S3 non raggiunto) | `client` | Bassa |
| `test_arco_proxy_returns_zgroup_for_authorized_user` | `ArcoResource.get` + validazione access key + S3 | 200 e body Zarr propagato per utente con key valida | `MagicMock` S3 via `monkeypatch` | `client`, `fresh_access_key`, `monkeypatch` | Media |
