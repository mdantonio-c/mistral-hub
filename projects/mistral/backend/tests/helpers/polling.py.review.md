# Review — `helpers/polling.py` (helper condiviso)

> File di review per l'helper di polling. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/polling.py](projects/mistral/backend/tests/helpers/polling.py)
- **Scopo**: sostituire gli `sleep()` ciechi con un retry su predicato osservabile.
- **Tipologia**: infrastruttura di suite.

## 2. Elementi definiti

### `wait_until(predicate, timeout=60, interval=2, message=...)`
- Esegue `predicate()` ripetutamente fino a valore truthy o scadenza `timeout`.
- Ritorna il **primo valore truthy** (riusabile dal chiamante).
- Allo scadere solleva `AssertionError(message)`.

## 3. Comportamenti nascosti

- **Usa `time.monotonic()`** per la deadline (robusto a cambi d'orologio).
- **Ritorna l'oggetto truthy**, non solo `True`: i chiamanti (es. `wait_for_schedule_requests`) lo usano per ottenere direttamente la lista attesa.
- **Tra un tentativo e l'altro chiama `time.sleep(interval)`**: il primo controllo è immediato, poi attende.

## 4. Checklist di revisione

- [ ] Verificare che i predicati passati siano **idempotenti** e privi di side effect indesiderati (vengono ri-eseguiti).
- [ ] Verificare che `timeout`/`interval` siano adeguati allo scenario (es. async_real vs deterministic).

## 5. Possibili criticità

- **Predicati con side effect**: alcuni predicati eseguono richieste HTTP `POST` (es. `trigger_data_ready_and_wait_accepted`), quindi ogni retry **ripete** la submission. Da valutare se accettabile per lo scenario.
