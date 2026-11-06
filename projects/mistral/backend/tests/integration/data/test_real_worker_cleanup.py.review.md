# Review — `test_real_worker_cleanup.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo deterministico: i worker sono simulati, utenti, request e API sono reali.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/test_real_worker_cleanup.py](projects/mistral/backend/tests/integration/data/test_real_worker_cleanup.py)
- **Scopo**: verificare che il cleanup dei test `async_real` ([helpers/real_workers.py](projects/mistral/backend/tests/helpers/real_workers.py)) non cancelli mai dati sotto un task che un worker può ancora eseguire.
- **Tipologia**: integrazione su DB e API reali, con il solo controllo Celery dell'helper sostituito. Marker: `integration`, `deterministic`. 3 funzioni, 4 casi (una parametrizzata).
- **Dove gira**: ovunque, anche fuori dagli stack `rapydo --testing`: nessun task raggiunge i worker reali.

## 2. Elemento sostituito

| Elemento | Dove | Come |
|---|---|---|
| `celery` nel modulo `helpers/real_workers.py` | `_install` | `monkeypatch` del solo nome nel modulo helper, non del connettore condiviso. Il fake `FakeWorkers` risponde a `inspect()` come i worker e registra le chiamate a `revoke()`. |

`FakeWorkers` può: rimuovere i task revocati (`obey_revoke`), non rispondere (`reply=False`, Celery ritorna `None`), finire da solo i task dopo un numero di interrogazioni (`finish_after`).

## 3. Analisi dettagliata di ogni test

### `test_cleanup_waits_while_workers_hold_a_task_of_the_user`
- **Scenario**: un worker tiene in coda un `data_extract` dell'utente che non ha ancora una request, come il primo task di una schedule on-data-ready.
- **Assert**: il cleanup interroga i worker finché il task non sparisce (3 interrogazioni) e non revoca nulla.

### `test_cleanup_timeout_stops_only_the_user_tasks_before_deleting_its_requests`
- **Scenario**: timeout scaduto; l'utente ha una request aperta con task ancora nel broker e un task in esecuzione; un secondo utente ha a sua volta una request aperta e un task in esecuzione.
- **Assert**: revoche con `terminate=True` e `SIGKILL`, prima per il task della request, poi per quello trovato nei worker; il task dell'altro utente resta; la request dell'utente viene cancellata, quella dell'altro resta `PENDING`; viene emesso `RealWorkerCleanupWarning`.

### `test_cleanup_timeout_deletes_nothing_without_worker_confirmation` (`task_not_stopped`, `no_worker_replies`)
- **Scenario**: timeout scaduto; il worker non ferma il task, oppure nessun worker risponde.
- **Assert**: il cleanup fallisce con un messaggio che dice che i dati restano al loro posto; la request dell'utente resta `PENDING`.

## 4. Comportamenti nascosti

- **Righe sintetiche**: le request sono create con `SqlApiDbManager.create_request_record` e un `task_id` univoco finto. Il cleanup del test le cancella con l'ORM prima dell'utente, perché l'API rifiuta di cancellare request aperte.
- **Registry locale**: il passo di cleanup sotto test è registrato in un `CleanupRegistry` creato nel test ed eseguito nell'`act`; il `cleanup_registry` della fixture resta per utenti e righe.
- **Warning dedicato**: `RealWorkerCleanupWarning` deriva da `Warning`, così non viene trasformato in errore dai filtri che `create_app` attiva in modalità test.

## 5. Checklist di revisione

- [ ] Verificare che `FakeWorkers` riproduca la forma delle risposte di Celery 5 (`args` come lista, `None` senza risposte).
- [ ] Verificare che nuovi rami di `stop_user_tasks` abbiano un caso qui.

## 6. Possibili criticità

- **Forma delle risposte simulata**: se una versione futura di Celery cambiasse il formato di `inspect()`, questi test continuerebbero a passare. Il test reale in `test_data_extraction_real_worker.py` lo rileverebbe.

## 7. Riassunto finale

| Test | Cosa verifica | Mock/Fake | Tipo |
|---|---|---|---|
| `test_cleanup_waits_while_workers_hold_a_task_of_the_user` | attesa dei task ancora senza request | `FakeWorkers` | `deterministic` |
| `test_cleanup_timeout_stops_only_the_user_tasks_before_deleting_its_requests` | revoca dei soli task dell'utente, poi cancellazione | `FakeWorkers` | `deterministic` |
| `test_cleanup_timeout_deletes_nothing_without_worker_confirmation` | nessuna cancellazione senza conferma | `FakeWorkers` | `deterministic` |
