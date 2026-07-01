# Review — `tests/integration/conftest.py` (infrastruttura di integrazione)

> File di review per il `conftest.py` condiviso dai test di integrazione HTTP. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py)
- **Scopo**: baseline autenticato minimo riusabile da tutti i sottoalberi di `integration/`.
- **Tipologia**: `conftest.py` di area (visibile a `integration/**`).

## 2. Elementi definiti

### `auth_headers` — fixture
- Esegue `BaseTests().do_login(client, None, None)` → login del **default user**.
- Ritorna gli header autenticati.
- **Usata da**: quasi tutti i domini di integrazione.

### `fresh_access_key` — fixture
- Dipende da `client` + `auth_headers`.
- `POST {API_URI}/access-key` (costante importata da [access_key/support.py](projects/mistral/backend/tests/integration/access_key/support.py)); asserisce `200` e presenza di `key`; ritorna `(auth_headers, key)`.
- **Usata da**: dominio `access_key`, e ovunque serva un default user + chiave.

## 3. Comportamenti nascosti

- **`auth_headers` opera sul default user**, non su un utente usa-e-getta: tutti i test che la usano condividono lo stesso account. I domini che vogliono isolamento creano invece utenti dedicati via [helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py).
- **Dipendenza inversa**: questo conftest globale importa `ACCESS_KEY_ENDPOINT` da un `support.py` di dominio specifico (`access_key`). Accoppiamento da tenere presente.
- **Assert nel setup** di `fresh_access_key`: un endpoint rotto appare come errore di fixture.

## 4. Checklist di revisione

- [ ] Verificare che i test che richiedono isolamento NON usino `auth_headers` (default user condiviso) ma utenti dedicati.
- [ ] Verificare la dipendenza `integration/conftest.py → access_key/support.py` in caso di refactor.

## 5. Possibili criticità

- **Stato condiviso del default user**: fixture comoda ma fonte di accoppiamento d'ordine tra domini.
- **Import cross-dominio** della costante endpoint: inverte la gerarchia attesa globale→dominio.
