# Review — `access_key/support.py` (infrastruttura di dominio)

> File di review per modulo di supporto. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/access_key/support.py](projects/mistral/backend/tests/integration/access_key/support.py)
- **Scopo**: centralizzare le costanti URL del dominio access-key.
- **Tipologia**: modulo di supporto (sole costanti).

## 2. Elementi definiti

| Costante | Valore | Usata da |
|---|---|---|
| `ACCESS_KEY_ENDPOINT` | `{API_URI}/access-key` | test API + validation, fixture `fresh_access_key`, `fresh_access_key_with_expiration` |
| `ACCESS_KEY_VALIDATE_ENDPOINT` | `{ACCESS_KEY_ENDPOINT}/validate` | test di validazione |

- `API_URI` proviene da `restapi.tests` (prefisso `/api`).

## 3. Comportamenti nascosti

- `ACCESS_KEY_ENDPOINT` è importato anche dal `conftest` di integrazione globale ([integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py)) per la fixture `fresh_access_key`: una modifica a questa costante ha impatto **cross-dominio**, non solo locale.

## 4. Checklist di revisione

- [ ] Verificare che il riuso cross-dominio della costante sia intenzionale (accoppiamento `integration/conftest.py` → `access_key/support.py`).

## 5. Possibili criticità

- **Dipendenza inversa**: il conftest di integrazione globale importa da un `support.py` di dominio specifico, invertendo la gerarchia attesa (globale → dominio). Da tenere presente in caso di refactor del dominio access-key.
