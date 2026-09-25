# Review — `test_access_key_api.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/access_key/test_access_key_api.py](projects/mistral/backend/tests/integration/access_key/test_access_key_api.py)
- **Scopo**: verificare il contratto utente del ciclo di vita delle access key (creazione, lettura, rigenerazione, gestione della scadenza, chiavi senza scadenza).
- **Tipologia**: test di **integrazione HTTP** (endpoint REST esercitato tramite `FlaskClient`). Marker: `integration`, `deterministic`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AccessKeyResource.post` | [endpoints/access_key.py](projects/mistral/backend/endpoints/access_key.py) | `POST /api/access-key` — crea o rigenera la chiave; se ne esiste già una la revoca (`db.session.delete`) e ne genera una nuova. |
| `AccessKeyResource.get` | [endpoints/access_key.py](projects/mistral/backend/endpoints/access_key.py) | `GET /api/access-key` — ritorna la chiave dell'utente; `404` se assente. |
| `AccessKeyValidationResource.get` | [endpoints/access_key.py](projects/mistral/backend/endpoints/access_key.py) | `GET /api/access-key/validate` — valida credenziali via HTTP Basic. |
| `validate_access_key_from_request` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py) | Legge `request.authorization`, recupera la chiave per email, valida e solleva `Unauthorized` (→ `401`). |
| `is_access_key_valid` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py) | Confronta chiave fornita e memorizzata; rifiuta se `expiration` è nel passato. |
| `AccessKey.generate` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L191) | Genera token `secrets.token_urlsafe(32)`; con `lifetime_seconds=None` → `expiration=None`. |
| `AccessKeySchema` | [endpoints/schemas.py](projects/mistral/backend/endpoints/schemas.py) | Schema marshmallow che serializza `key` ed `expiration` nella risposta. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` (framework) | `FlaskClient` di test; esegue richieste reali contro l'app Flask. |
| `auth_headers` | fixture | [integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | Login del test user di default → header autenticati. **Effetto nascosto**: opera sul `default_user`, non su un utente usa-e-getta. |
| `fresh_access_key` | fixture | [integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | `POST /access-key` con `auth_headers`, asserisce `200` e presenza di `key`; ritorna `(headers, key)`. |
| `fresh_access_key_with_expiration` | fixture | [access_key/conftest.py](projects/mistral/backend/tests/integration/access_key/conftest.py) | Crea chiave con `lifetime_seconds=3600`; ritorna `(headers, key)`. |
| `ACCESS_KEY_ENDPOINT`, `ACCESS_KEY_VALIDATE_ENDPOINT` | costanti | [access_key/support.py](projects/mistral/backend/tests/integration/access_key/support.py) | URL `/api/access-key` e `/api/access-key/validate`. |
| `make_basic_auth` | helper | [helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Codifica `email:key` in header `Authorization: Basic ...`. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Accesso diretto al DB di test per forzare lo stato (manipolazione `expiration`). |
| `BaseAuthentication.default_user` | costante | `restapi.services.authentication` | Email dell'utente di default usato dal login. |

## 4. Analisi dettagliata di ogni test

### `test_01_get_access_key_unauthenticated`
- **Obiettivo**: garantire che l'endpoint non risponda a chiamanti anonimi.
- **Backend coinvolto**: `AccessKeyResource.get` protetto da `@decorators.auth.require()`.
- **Flusso**: GET senza header → 401.
- **Setup**: nessuno (solo `client`).
- **Assert**: `status_code == 401` → conferma il gate di autenticazione prima di ogni dettaglio di lifecycle.
- **Casi coperti**: error path / autorizzazione.

### `test_02_get_existing_access_key`
- **Obiettivo**: una lettura successiva restituisce **esattamente** la chiave già emessa (non una nuova, non vuota).
- **Backend coinvolto**: `AccessKeyResource.get` + serializzazione `AccessKeySchema`.
- **Flusso**: fixture crea la chiave → GET → confronto token.
- **Setup**: `fresh_access_key` (headers + token).
- **Assert**: `200`; `resp.json["key"] == token` → idempotenza della lettura.
- **Casi coperti**: happy path.

### `test_03_regenerate_access_key`
- **Obiettivo**: rigenerare invalida il token precedente e la lettura espone il nuovo valore.
- **Backend coinvolto**: `AccessKeyResource.post` (ramo `if existing: db.session.delete`).
- **Flusso (arrange/act/assert)**: GET chiave attuale → POST rigenera → confronto `new != old` → GET conferma persistenza.
- **Setup**: `auth_headers`.
- **Assert**: `new_token != old_token` (rigenerazione effettiva); `resp.json["key"] == new_token` (la nuova chiave è quella persistita).
- **Casi coperti**: happy path + invalidazione implicita della vecchia chiave.

### `test_04_create_access_key_without_expiration`
- **Obiettivo**: l'API accetta una chiave senza scadenza quando richiesto esplicitamente.
- **Backend coinvolto**: `AccessKeyResource.post` con `lifetime_seconds=None` → `AccessKey.generate` con `expires=None`.
- **Flusso**: POST `{"lifetime_seconds": None}` → 200.
- **Assert**: `200`; `resp.json["expiration"] is None` → contratto "chiave long-lived".
- **Casi coperti**: edge case / variante di input.

### `test_06_validate_expired_access_key`
- **Obiettivo**: una chiave valida diventa inutilizzabile dopo la scadenza.
- **Backend coinvolto**: `validate_access_key_from_request` → `is_access_key_valid` (ramo `expiration < now`).
- **Flusso**: crea chiave con scadenza → forza `expiration` nel passato a livello DB → valida via Basic → 401.
- **Setup**: `fresh_access_key_with_expiration`; query diretta sul DB con `sqlalchemy.get_instance()`; `make_basic_auth`.
- **Assert**: `status_code == 401` → la scadenza è realmente enforced lato validazione.
- **Casi coperti**: edge case temporale / error path.

> **Nota**: la numerazione salta da `test_04` a `test_06`: `test_05` (chiave senza scadenza valida) vive in `test_access_key_validation.py`. La numerazione è quindi **cross-file** e non un buco accidentale nello stesso modulo.

## 5. Call chain

```
GET /api/access-key            → AccessKeyResource.get → user.access_key → AccessKeySchema → 200/404
POST /api/access-key           → AccessKeyResource.post → (delete existing) → AccessKey.generate → db.commit → 200
GET /api/access-key/validate   → AccessKeyValidationResource.get → validate_access_key_from_request
                                  → access_key_get_by_user → is_access_key_valid → 200 / Unauthorized(401)
```

## 6. Comportamenti nascosti

- **`auth_headers` agisce sul `default_user`**: i test che usano `auth_headers`/`fresh_access_key` modificano la chiave dell'utente condiviso di default. La rigenerazione in `test_03`/`test_04`/`test_05` **sostituisce** la chiave globale: l'ordine dei test e l'isolamento dipendono da questo.
- **`fresh_access_key_with_expiration` è in un `conftest.py` locale**: non è visibile leggendo solo il modulo di test; vive in [access_key/conftest.py](projects/mistral/backend/tests/integration/access_key/conftest.py).
- **Mutazione diretta del DB** in `test_06`: bypassa l'API e scrive `expiration` nel passato. Il test non verifica come si arriva alla scadenza, ma solo l'effetto sulla validazione.
- **Nessun cleanup esplicito**: il modulo non registra `cleanup_registry`; si appoggia al fatto che opera sul default user e che ogni POST rigenera/ revoca la chiave precedente.
- **`POST` revoca + ricrea**: la rigenerazione non è un update in-place ma `delete` + `generate` (nuovo record, nuovo `creation`).

## 7. Checklist di revisione

- [ ] Verificare che `test_02` confronti il token e non solo lo status (fa entrambi: OK).
- [ ] Verificare che la dipendenza dal `default_user` non crei accoppiamento d'ordine con altri moduli che usano lo stesso utente.
- [ ] Confermare che la manipolazione diretta di `expiration` in `test_06` rispecchi un caso reale (chiave scaduta nel tempo).
- [ ] Verificare che il salto `test_04 → test_06` sia intenzionale (la coppia `test_05` è nel file validation).
- [ ] Controllare che l'assenza di cleanup non lasci la chiave del default user in stato inatteso per i test successivi.

## 8. Possibili criticità

- **Accoppiamento sullo stato del default user**: più test rigenerano la chiave globale; un cambio d'ordine o esecuzione parallela potrebbe introdurre interferenze (rischio di falso positivo/negativo in suite parallele).
- **Numerazione cross-file** (`test_01..06` divisi su due file): rende meno ovvio che la copertura sia completa; va letta insieme a `test_access_key_validation.py`.
- **`test_06` dipende dal layout interno del modello** (`user.access_key.expiration`): è più un test white-box che contract-level; se cambia la rappresentazione della scadenza, il test va aggiornato anche se il contratto HTTP resta identico.
- **Mancanza di un test esplicito per `DELETE /access-key`** (revoca → 204) in questo file: il metodo `delete` dell'endpoint non risulta esercitato qui.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_01_get_access_key_unauthenticated` | `AccessKeyResource.get` | 401 anonimo | — | `client` | Bassa |
| `test_02_get_existing_access_key` | `AccessKeyResource.get` | lettura ritorna stessa key | — | `fresh_access_key` | Bassa |
| `test_03_regenerate_access_key` | `AccessKeyResource.post` | nuova key ≠ vecchia | — | `auth_headers` | Media |
| `test_04_create_access_key_without_expiration` | `AccessKeyResource.post` + `AccessKey.generate` | `expiration is None` | — | `auth_headers` | Bassa |
| `test_06_validate_expired_access_key` | `validate_access_key_from_request` / `is_access_key_valid` | 401 su key scaduta | — (mutazione DB diretta) | `fresh_access_key_with_expiration` | Media |
