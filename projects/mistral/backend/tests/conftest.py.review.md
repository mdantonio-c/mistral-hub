# Review — `tests/conftest.py` (infrastruttura di suite globale)

> File di review per il `conftest.py` radice della suite. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/conftest.py](projects/mistral/backend/tests/conftest.py)
- **Scopo**: configurazione pytest valida per **tutta** la suite custom: registrazione marker, fixture davvero trasversali e skip dei test `async_real` fuori dagli stack `rapydo --testing`.
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

### `pytest_collection_modifyitems(config, items)` — hook
- Se `workers_use_smtp_mock()` ([helpers/real_workers.py](projects/mistral/backend/tests/helpers/real_workers.py)) è falso, aggiunge `skip` a ogni test con marker `async_real`, con il motivo `NO_SMTP_MOCK_REASON`.
- Motivo: i task di quei test girano sui worker reali, dove `monkeypatch` non arriva. Solo negli stack `rapydo --testing` i worker usano il mock SMTP; altrove un'estrazione fallita invierebbe email vere all'utente e all'amministratore.

## 3. Comportamenti nascosti

- **Teardown centralizzato**: il `yield` + `registry.run()` garantisce cleanup LIFO **anche se il test fallisce a metà**. Tutti i test che chiamano `cleanup_registry.add(...)` dipendono da questo punto.
- **`test_runtime` è un singleton di sessione**: lo stato (cache dataset) **persiste tra i test**. Un dataset risolto in un test resta in cache per tutti i successivi (vedi rischi sotto).
- **`CleanupRegistry.run()` non ingoia eccezioni**: un teardown rotto fa fallire il test in modo visibile (scelta deliberata).
- **Skip dei test `async_real` già in collection**: fuori dagli stack `rapydo --testing` le loro fixture non partono, quindi non vengono creati utenti né inviati task ai worker. Con `-rs` il motivo compare nel riepilogo.

## 4. Checklist di revisione

- [ ] Verificare che ogni risorsa creata nei test sia registrata nel `cleanup_registry`.
- [ ] Considerare che `test_runtime` è di sessione: la cache dei dataset non si resetta tra i test.
- [ ] Verificare che i marker dichiarati siano effettivamente applicati nei moduli (`pytestmark`).
- [ ] Verificare che in CI, avviata con `rapydo --testing`, i test `async_real` risultino eseguiti e non saltati.

## 5. Possibili criticità

- **Cache di sessione condivisa** (`TestRuntime._dataset_cache`): se un dataset cambia id durante la sessione, i test successivi userebbero un id stantio (improbabile in pratica, ma è uno stato globale mutabile).
- **Teardown "strict"**: un singolo cleanup fallito propaga l'errore; utile per igiene, ma può mascherare il vero motivo di fallimento di un test.
- **Skip silenzioso in CI**: se Rapydo smettesse di impostare le variabili usate da `workers_use_smtp_mock`, i test `async_real` verrebbero saltati anche in CI. Il riepilogo `-rs` lo renderebbe visibile.
