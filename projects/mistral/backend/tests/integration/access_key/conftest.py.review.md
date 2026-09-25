# Review — `access_key/conftest.py` (infrastruttura di dominio)

> File di review per modulo di supporto (fixture locali). Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/access_key/conftest.py](projects/mistral/backend/tests/integration/access_key/conftest.py)
- **Scopo**: fornire fixture specifiche del dominio access-key che richiedono setup più ricco di quello condiviso.
- **Tipologia**: `conftest.py` di dominio (solo fixture locali, visibili a `integration/access_key/**`).

## 2. Backend realmente esercitato

- `AccessKeyResource.post` ([endpoints/access_key.py](projects/mistral/backend/endpoints/access_key.py)) tramite `POST /api/access-key` con `lifetime_seconds=3600`.
- `AccessKey.generate` ([models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L191)) con scadenza finita.

## 3. Elementi definiti

### Fixture `fresh_access_key_with_expiration`
- **Dipende da**: `client`, `auth_headers` (da [integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py)).
- **Cosa fa**: `POST /access-key` con `{"lifetime_seconds": 3600}`; asserisce `200`, presenza di `key` e di `expiration` non nullo; ritorna `(auth_headers, key)`.
- **Usata da**: `test_access_key_api.py::test_06_validate_expired_access_key`.
- **Effetti collaterali**: crea/rigenera la chiave del **default user** (stato condiviso).

## 4. Comportamenti nascosti

- La fixture **asserisce dentro il setup** (`assert resp.status_code == 200`, `assert "expiration" ... is not None`): se l'ambiente non emette scadenza, il fallimento appare in fase di setup, non nel corpo del test.
- Riusa `auth_headers`, quindi eredita implicitamente l'accoppiamento al default user.

## 5. Checklist di revisione

- [ ] Verificare che `lifetime_seconds=3600` sia coerente con la manipolazione `-3600s` fatta nel test che la consuma.
- [ ] Verificare che gli assert nel setup non mascherino problemi reali dell'endpoint come "errore di fixture".

## 6. Possibili criticità

- **Assert nel setup**: un fallimento dell'endpoint si presenta come errore di fixture (più difficile da diagnosticare rispetto a un assert nel test).
- **Singolo consumer**: la fixture è usata da un solo test; il valore del riuso è marginale, ma giustificato dalla località nel dominio.
