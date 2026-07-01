# Review — `helpers/datasets.py` (helper condiviso)

> File di review per l'helper di selezione dataset. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py)
- **Scopo**: rendere i test sui dataset meno dipendenti dai dati seed scegliendo "un dataset pubblico realmente presente ora".
- **Tipologia**: helper di selezione/skip condiviso.

## 2. Backend realmente esercitato

- Consuma il payload di `GET /api/datasets` ([endpoints/datasets.py](projects/mistral/backend/endpoints/datasets.py)) — campo `is_public` e `id`.

## 3. Elementi definiti

### `first_public_dataset_id(datasets) -> str`
- Scorre la lista e ritorna l'`id` del primo dataset con `is_public is True`.
- Se nessun dataset pubblico è presente → `pytest.skip`.

## 4. Comportamenti nascosti

- **`pytest.skip` se nessun dataset pubblico**: i test chiamanti possono essere saltati silenziosamente in ambienti senza dataset pubblici.
- Lavora sul payload già scaricato (non fa chiamate proprie): l'attendibilità dipende dalla risposta passata dal chiamante.

## 5. Checklist di revisione

- [ ] Verificare quali test dipendono dalla presenza di almeno un dataset pubblico (rischio skip silenzioso).

## 6. Possibili criticità

- **Skip mascherante** in ambienti privi di dataset pubblici: la copertura effettiva è runtime-dependent.
