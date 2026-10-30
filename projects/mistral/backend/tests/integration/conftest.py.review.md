# Review — `tests/integration/conftest.py` (infrastruttura di integrazione)

> File di review per il `conftest.py` condiviso dai test di integrazione HTTP. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py)
- **Scopo**: baseline autenticato minimo riusabile da tutti i sottoalberi di `integration/`, più il perimetro del task globale di cleanup.
- **Tipologia**: `conftest.py` di area (visibile a `integration/**`).

## 2. Elementi definiti

### `auth_headers` — fixture
- Esegue `BaseTests().do_login(client, None, None)` → login del **default user**.
- Ritorna gli header autenticati.
- **Usata da**: domini che leggono dati con l'account predefinito (es. `observed`); non va usata per creare o ruotare access key.

### `access_key_owner` — fixture
- Crea un utente temporaneo con [helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) e registra il cleanup standard (utente + directory).
- Registra **dopo** l'utente la revoca `DELETE /access-key` (204 o 404): in LIFO gira prima della cancellazione utente, necessaria perché `AccessKey.user_id` non ammette `NULL`.
- Ritorna `AuthenticatedTestUser`, incluso `email` per gli header BasicAuth.

### `fresh_access_key` — fixture
- Dipende da `client` + `access_key_owner`.
- `POST {API_URI}/access-key` (costante importata da [access_key/support.py](projects/mistral/backend/tests/integration/access_key/support.py)) con gli header del proprietario temporaneo; asserisce `200` e presenza di `key`; ritorna `(access_key_owner.headers, key)`.
- **Usata da**: domini `access_key` e `arco`, abbinata a `access_key_owner.email` nei test BasicAuth.

### `requests_cleanup_perimeter` — fixture
- Chiama `confine_requests_cleanup` di [helpers/task_perimeter.py](projects/mistral/backend/tests/helpers/task_perimeter.py) con una root download in `tmp_path`.
- Il test registra con `allow(user_ids=..., request_ids=...)` le sole righe che `automatic_cleanup` può processare.

## 3. Comportamenti nascosti

- **`auth_headers` opera sul default user**, non su un utente usa-e-getta: tutti i test che la usano condividono lo stesso account. Le access key non passano più da questo account.
- **Ordine di teardown**: il cleanup del proprietario usa le API reali. Se un test sostituisce globalmente `restapi.connectors.sqlalchemy.get_instance`, il ripristino del `monkeypatch` avviene dopo `cleanup_registry` (pytest-flask istanzia `monkeypatch` in anticipo) e il cleanup riceve `401`.
- **Dipendenza inversa**: questo conftest globale importa `ACCESS_KEY_ENDPOINT` da un `support.py` di dominio specifico (`access_key`). Accoppiamento da tenere presente.
- **Assert nel setup** di `fresh_access_key`: un endpoint rotto appare come errore di fixture.

## 4. Checklist di revisione

- [ ] Verificare che i test che richiedono isolamento NON usino `auth_headers` (default user condiviso) ma utenti dedicati.
- [ ] Verificare che i test con `access_key_owner` non sostituiscano globalmente il connettore SQLAlchemy.
- [ ] Verificare la dipendenza `integration/conftest.py → access_key/support.py` in caso di refactor.

## 5. Possibili criticità

- **Stato condiviso del default user**: fixture comoda ma fonte di accoppiamento d'ordine tra domini; limitata alle letture.
- **Import cross-dominio** della costante endpoint: inverte la gerarchia attesa globale→dominio.
