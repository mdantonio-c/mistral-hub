# Review — `tests/conftest.py` (infrastruttura di suite globale)

> File di review per il `conftest.py` radice della suite. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/conftest.py](projects/mistral/backend/tests/conftest.py)
- **Scopo**: configurazione pytest valida per **tutta** la suite custom: registrazione marker e fixture davvero trasversali.
- **Tipologia**: `conftest.py` globale (visibile a tutti i test sotto `tests/`).

## 2. Elementi definiti

### `pytest_configure(config)` — hook
Registra 4 marker custom usati per categorizzare i test:
- `integration` — test di integrazione;
- `deterministic` — flusso deterministico nel runtime di test (no attese reali);
- `async_real` — il test attende la catena reale beat → broker → worker;
- `runtime_sensitive` — l'esito dipende da dati/infrastruttura runtime.

### `test_runtime` — fixture (scope **session**)
- Ritorna l'istanza singleton `TestRuntime` ([helpers/runtime.py](projects/mistral/backend/tests/helpers/runtime.py)).
- **Usata da**: domini `data_ready`, `schedules`, `observed`, ecc. per cache `dataset_id` e override temporanei di attributi.

### `cleanup_registry` — fixture (scope funzione)
- Crea un `CleanupRegistry` ([helpers/cleanup.py](projects/mistral/backend/tests/helpers/cleanup.py)), lo `yield`a e a teardown chiama `registry.run()`.
- **Usata da**: praticamente ogni dominio che crea utenti/schedule/file temporanei.

## 3. Comportamenti nascosti

- **Teardown centralizzato**: il `yield` + `registry.run()` garantisce cleanup LIFO **anche se il test fallisce a metà**. Tutti i test che chiamano `cleanup_registry.add(...)` dipendono da questo punto.
- **`test_runtime` è un singleton di sessione**: lo stato (cache dataset) **persiste tra i test**. Un dataset risolto in un test resta in cache per tutti i successivi (vedi rischi sotto).
- **`CleanupRegistry.run()` non ingoia eccezioni**: un teardown rotto fa fallire il test in modo visibile (scelta deliberata).

## 4. Checklist di revisione

- [ ] Verificare che ogni risorsa creata nei test sia registrata nel `cleanup_registry`.
- [ ] Considerare che `test_runtime` è di sessione: la cache dei dataset non si resetta tra i test.
- [ ] Verificare che i marker dichiarati siano effettivamente applicati nei moduli (`pytestmark`).

## 5. Possibili criticità

- **Cache di sessione condivisa** (`TestRuntime._dataset_cache`): se un dataset cambia id durante la sessione, i test successivi userebbero un id stantio (improbabile in pratica, ma è uno stato globale mutabile).
- **Teardown "strict"**: un singolo cleanup fallito propaga l'errore; utile per igiene, ma può mascherare il vero motivo di fallimento di un test.
