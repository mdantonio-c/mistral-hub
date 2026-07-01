# Review — `helpers/schedules.py` (helper condiviso)

> File di review per i builder di payload schedule. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/schedules.py](projects/mistral/backend/tests/helpers/schedules.py)
- **Scopo**: costruire i body JSON per schedule on-data-ready, crontab e periodic.
- **Tipologia**: builder di payload condiviso.

## 2. Backend realmente esercitato

- `POST /api/schedules` ([endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py)) — i body prodotti definiscono il contratto di input dello scheduler.

## 3. Elementi definiti

| Builder | Produce |
|---|---|
| `build_on_data_ready_schedule(...)` | body con `on-data-ready: True`, `reftime`, `dataset_names`, `filters.run`, `opendata`. |
| `build_crontab_schedule(...)` | body con `crontab-settings` (solo i campi temporali forniti) + `on-data-ready` opzionale. |
| `build_periodic_schedule(...)` | body con `period-settings` (`every`, `period`) + `on-data-ready`. |

## 4. Comportamenti nascosti

- **Inclusione condizionale dei campi**: `build_crontab_schedule` aggiunge solo i campi crontab esplicitamente passati (None → omesso). Il payload risultante può essere parziale.
- **`filters` = `{"run": run_filter}` solo se `run_filter`**, altrimenti `{}`: la forma del filtro cambia in base all'input.
- **`opendata=True` di default** in tutti i builder: gli scenari pubblicano opendata salvo override esplicito.

## 5. Checklist di revisione

- [ ] Verificare che la forma del payload generato corrisponda esattamente allo schema atteso da [endpoints/schedules.py](projects/mistral/backend/endpoints/schedules.py).
- [ ] Confermare che `opendata=True` di default sia coerente con l'intento dei test (non sempre vogliono pubblicare).

## 6. Possibili criticità

- **Default `opendata=True`**: i test che non si occupano di opendata pubblicano comunque, con possibili side effect non rilevanti allo scenario.
