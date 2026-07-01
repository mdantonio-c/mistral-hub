# Review — `helpers/runtime.py` (helper condiviso)

> File di review per il runtime di sessione condiviso. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/runtime.py](projects/mistral/backend/tests/helpers/runtime.py)
- **Scopo**: singleton di sessione che cache-a risorse riusabili (id dataset) e offre un context manager per override temporanei di attributi.
- **Tipologia**: infrastruttura di suite (usata dalla fixture `test_runtime`).

## 2. Backend realmente esercitato

- `db.Datasets` ([models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py)) per risolvere `name`/`arkimet_id` → `id` numerico.

## 3. Elementi definiti

### Classe `TestRuntime` (singleton via `__new__` + `RLock`)
| Metodo | Cosa fa |
|---|---|
| `dataset_id(db, name)` | Risolve l'id del dataset (per `name` o `arkimet_id`), lo cache-a in `_dataset_cache`; `LookupError` se assente. |
| `override_attr(target, attr, value)` | Context manager: imposta un attributo, lo `yield`a e **ripristina** l'originale a fine blocco. |

## 4. Comportamenti nascosti

- **Singleton di sessione**: `_dataset_cache` **persiste tra tutti i test** della sessione. Un id risolto resta valido per l'intera run.
- **`override_attr` è thread-safe** (`RLock`) e garantisce ripristino in `finally`: usato per patchare attributi env-dependent senza leak tra test.
- **`dataset_id` accetta sia `name` sia `arkimet_id`**: la stessa stringa può matchare due colonne diverse (query con `OR`).

## 5. Checklist di revisione

- [ ] Considerare la natura di sessione della cache: nessun reset tra test.
- [ ] Verificare che `override_attr` sia sempre usato come context manager (altrimenti niente ripristino).

## 6. Possibili criticità

- **Stato globale mutabile** condiviso da tutta la sessione: una cache stantia introdurrebbe accoppiamento d'ordine difficile da diagnosticare.
- **`dataset_id` con `OR name/arkimet_id`**: se due dataset hanno collisione tra `name` e `arkimet_id`, il `.first()` potrebbe restituire un id ambiguo.
