# Review — `test_access_key_validation.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/access_key/test_access_key_validation.py](projects/mistral/backend/tests/integration/access_key/test_access_key_validation.py)
- **Scopo**: verificare quali combinazioni di `email` + `access key` sono accettate o rifiutate dall'endpoint di validazione via HTTP Basic.
- **Tipologia**: test di **integrazione HTTP**. Marker: `integration`, `deterministic`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AccessKeyValidationResource.get` | [endpoints/access_key.py](projects/mistral/backend/endpoints/access_key.py) | `GET /api/access-key/validate` — entry point pubblico (no `auth.require`), delega al service. |
| `validate_access_key_from_request` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py) | Estrae `request.authorization`; senza credenziali → `Unauthorized`. |
| `access_key_get_by_user` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py) | Risolve la chiave dall'email; email inesistente → `None` → `401`. |
| `is_access_key_valid` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py) | Confronto chiave + controllo scadenza. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | Client HTTP di test. |
| `auth_headers` | fixture | [integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | Header autenticati del default user (usato solo da `test_05`). |
| `fresh_access_key` | fixture | [integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | Crea una chiave per il default user. |
| `make_basic_auth` | helper | [helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Costruisce header Basic `email:key`. |
| `BaseAuthentication.default_user` | costante | `restapi.services.authentication` | Email del default user. |
| `ACCESS_KEY_ENDPOINT` / `ACCESS_KEY_VALIDATE_ENDPOINT` | costanti | [access_key/support.py](projects/mistral/backend/tests/integration/access_key/support.py) | URL endpoint. |

## 4. Analisi dettagliata di ogni test

### `test_01_missing_credentials`
- **Obiettivo**: validazione senza credenziali → 401.
- **Backend**: `validate_access_key_from_request` ramo `if not auth`.
- **Assert**: `401`. Garantisce che l'endpoint non sia aperto.
- **Casi coperti**: error path.

### `test_02_invalid_email`
- **Obiettivo**: email inesistente → 401.
- **Backend**: `access_key_get_by_user` ritorna `None`.
- **Setup**: `make_basic_auth("nonexistent@example.com", "whatever")`.
- **Assert**: `401`. Distingue "utente non trovato" da chiave errata, ma il contratto HTTP è lo stesso 401.
- **Casi coperti**: error path / validazione input.

### `test_03_invalid_access_key`
- **Obiettivo**: email valida ma chiave errata → 401.
- **Backend**: `is_access_key_valid` ritorna `False` sul confronto `key == provided_key`.
- **Setup**: crea chiave reale via `fresh_access_key`, poi presenta `"WRONG-KEY"`.
- **Assert**: `401`. Prova che il confronto della chiave è effettivo.
- **Casi coperti**: error path.

### `test_04_valid_access_key`
- **Obiettivo**: email + chiave corretti → 200 con `status == "OK"`.
- **Backend**: catena completa di validazione con esito positivo.
- **Setup**: `fresh_access_key` fornisce la chiave valida.
- **Assert**: `200`; `resp.json["status"] == "OK"`. Happy path end-to-end.
- **Casi coperti**: happy path.

### `test_05_validate_access_key_without_expiration`
- **Obiettivo**: una chiave creata senza scadenza resta accettabile alla validazione.
- **Backend**: `is_access_key_valid` ramo `expiration is None` → sempre valida.
- **Setup**: `POST` con `lifetime_seconds=None`, poi valida la chiave ottenuta.
- **Assert**: `200`; `status == "OK"`. Complementa il `test_04` lato creazione (in `test_access_key_api.py`) col comportamento lato validazione.
- **Casi coperti**: edge case (chiave senza scadenza) / happy path.

## 5. Call chain

```
GET /api/access-key/validate
  → AccessKeyValidationResource.get
  → validate_access_key_from_request()
       ├─ no auth                → Unauthorized (401)   [test_01]
       ├─ access_key_get_by_user → None (email) (401)   [test_02]
       └─ is_access_key_valid
            ├─ key mismatch (401)                       [test_03]
            ├─ match           → 200 {"status":"OK"}    [test_04]
            └─ expiration None → 200                    [test_05]
```

## 6. Comportamenti nascosti

- **Endpoint pubblico**: `AccessKeyValidationResource.get` **non** ha `@decorators.auth.require()`; l'autorizzazione è interamente delegata al service via HTTP Basic. La sicurezza è quindi tutta dentro `validate_access_key_from_request`.
- **`401` ambiguo per scelta**: "email inesistente", "chiave errata" e "credenziali mancanti" producono lo stesso `401`, evitando user-enumeration. È un comportamento di sicurezza voluto, non un bug.
- **`test_05` rigenera la chiave del default user** (POST con `lifetime_seconds=None`): muta lo stato condiviso, come nei test del file gemello.
- **`make_basic_auth` nasconde la codifica base64**: il test non mostra la costruzione dell'header.

## 7. Checklist di revisione

- [ ] Verificare che il 401 indistinto (email vs key) sia una scelta di sicurezza documentata e non una svista.
- [ ] Confermare che `test_04`/`test_05` verifichino davvero il body (`status == "OK"`) e non solo lo status.
- [ ] Verificare l'isolamento rispetto a `test_access_key_api.py` (entrambi mutano la chiave del default user).
- [ ] Controllare che non manchi un caso "chiave valida ma utente diverso" (cross-user).

## 8. Possibili criticità

- **Copertura cross-user assente**: non esiste un test che presenti email corretta + chiave appartenente a un altro utente; il confronto è solo "chiave giusta/sbagliata sullo stesso utente".
- **Accoppiamento sullo stato del default user** condiviso con `test_access_key_api.py`: potenziale fragilità in esecuzione parallela.
- **Asserzioni solo su status/`status` field**: non viene verificato lo `scope` della chiave (`read:arco`), che è parte del modello.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_01_missing_credentials` | `validate_access_key_from_request` | 401 senza credenziali | — | `client` | Bassa |
| `test_02_invalid_email` | `access_key_get_by_user` | 401 email inesistente | — | `client` | Bassa |
| `test_03_invalid_access_key` | `is_access_key_valid` | 401 chiave errata | — | `fresh_access_key` | Bassa |
| `test_04_valid_access_key` | catena validazione | 200 + `status OK` | — | `fresh_access_key` | Bassa |
| `test_05_validate_access_key_without_expiration` | `is_access_key_valid` (no exp) | 200 chiave senza scadenza | — | `auth_headers` | Bassa |
