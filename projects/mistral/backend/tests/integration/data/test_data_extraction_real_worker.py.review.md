# Review — `test_data_extraction_real_worker.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `async_real`: l'estrazione gira su un worker Celery reale, senza fake.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/test_data_extraction_real_worker.py](projects/mistral/backend/tests/integration/data/test_data_extraction_real_worker.py)
- **Scopo**: verificare il flusso più usato, `POST /data`, fino al worker reale: estrazione riuscita, estrazione fallita con email di esito, cleanup di una request che il worker non ha ancora eseguito.
- **Tipologia**: integrazione HTTP + broker + worker reali. Marker di modulo: `integration`, `async_real`, `runtime_sensitive`. 3 test.
- **Dove gira**: solo sugli stack avviati con `rapydo --testing`, dove i worker usano il mock SMTP; altrove [tests/conftest.py](projects/mistral/backend/tests/conftest.py) salta il modulo.
- **Dataset reale**: `lm5`, con finestra e prima run lette da `/api/fields`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Data.post` | [endpoints/data.py](projects/mistral/backend/endpoints/data.py#L328) | Valida la richiesta, crea la `Request` e invia `data_extract` al broker (`countdown=1`). |
| task `data_extract` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py) | Eseguito dal worker reale: estrazione Arkimet, file e `FileOutput`, oppure `FAILURE` per quota con email di esito (`notify_by_email`). |
| `UserRequests.get` | [endpoints/requests.py](projects/mistral/backend/endpoints/requests.py#L44) | `GET /requests`, letto in polling. |
| `FileDownload.get` | [endpoints/file.py](projects/mistral/backend/endpoints/file.py) | `GET /data/<filename>`, download del file prodotto dal worker. |
| revoca Celery | `celery_app.control.revoke` | Usata dal cleanup per fermare il task dell'utente prima di cancellarne la request. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `real_worker_user`, `_create_real_worker_user` | fixture e helper locali | questo file | `create_data_ready_user` su `lm5` (nessuna email reale), `pytest.skip` se `lm5` manca; registra il cleanup dell'utente e poi l'attesa dei worker. |
| `create_data_ready_user`, `register_data_ready_user_cleanup`, `list_user_requests` | helper | [tests/helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) | Utente temporaneo (anche con `max_output_size` ridotto), cleanup di request, schedule, utente e cartella, listing delle request. |
| `register_wait_for_user_requests`, `wait_for_finished_request`, `wait_for_mock_email`, `RealWorkerCleanupWarning` | helper | [tests/helpers/real_workers.py](projects/mistral/backend/tests/helpers/real_workers.py) | Attesa dei worker, cleanup che ferma i task dell'utente, lettura delle email del mock SMTP. |
| `fetch_dataset_window` | helper | [tests/helpers/dataset_window.py](projects/mistral/backend/tests/helpers/dataset_window.py) | Finestra reale di `lm5`; `pytest.skip` su 404. |

## 4. Analisi dettagliata di ogni test

### `test_data_request_is_extracted_by_real_worker`
- **Obiettivo**: una richiesta `POST /data` viene eseguita da un worker reale e produce un file scaricabile.
- **Flusso**: `POST /data` con la prima run di `lm5` → 202 → polling di `GET /requests` fino allo stato finale → `GET /data/<file>`.
- **Assert**: stato `SUCCESS` (altrimenti mostra l'errore del worker); `task_id` uguale a quello restituito dall'endpoint; request non opendata; file nella cartella dell'utente; download 200 con lunghezza pari a `filesize` e filename nel `Content-Disposition`.

### `test_failed_data_request_notifies_owner_through_smtp_mock`
- **Obiettivo**: l'email che il worker invia quando un'estrazione fallisce finisce nel mock SMTP, non in un server reale.
- **Flusso**: utente con `max_output_size=1` → `POST /data` → il worker stima l'output, lo trova oltre il limite e segna `FAILURE` → `notify_by_email` → mock.
- **Assert**: `FAILURE` con il messaggio di quota; `task_id` dell'endpoint; nessun `fileoutput` e nessun file nella cartella; email registrata dal mock per il solo indirizzo `@example.invalid` dell'utente, con oggetto `MeteoHub: data extraction completed`, nome della request, stato `FAILURE` e messaggio di errore nel testo.
- **Perché prova l'isolamento**: il mock scrive l'email solo se il worker gira in modalità test. Con l'SMTP reale non ci sarebbe nulla da leggere e il test fallirebbe.

### `test_cleanup_timeout_revokes_queued_request_on_real_workers`
- **Obiettivo**: con worker troppo lenti, il cleanup ferma il task dell'utente e solo dopo ne cancella la request.
- **Flusso**: `POST /data` → `register_wait_for_user_requests(..., timeout=0)` su un registry locale, eseguito subito. Il task ha `countdown=1`, quindi è ancora in coda come con un worker occupato. Il cleanup lo revoca, attende la conferma dei worker e cancella la request.
- **Assert**: `RealWorkerCleanupWarning` emesso; stato Celery del task `REVOKED`, quindi scartato e non eseguito; request cancellata; nessun `FileOutput` e nessun file dell'utente.

## 5. Call chain

```
POST /api/data (utente temporaneo)        → 202 {request_id, task_id}
   RabbitMQ reale → worker reale → data_extract
      ├─ successo: /data/<uuid>/outputs/<file> + FileOutput
      └─ quota superata: FAILURE + email di esito → mock SMTP (/logs/mock.mail.*.json)
poll GET /api/requests                    → stato finale
GET /api/data/<file>                      → 200 + Content-Disposition (solo successo)
cleanup scaduto: revoke(task_id, SIGKILL) → conferma dei worker → cancellazione della request
cleanup: attesa worker → DELETE /requests/<id> → DELETE utente → rimozione cartella
```

## 6. Comportamenti nascosti

- **Nessuna email reale**: oltre allo skip fuori da `rapydo --testing`, l'utente ha `notify_on_successful_request=False` e un indirizzo `@example.invalid`.
- **Prova che ha lavorato il worker**: lo stato passa da `PENDING` a uno stato finale solo se qualcuno esegue `data_extract`, e nessun fake è installato.
- **Estrazione piccola**: il filtro sulla prima run limita il volume; la finestra resta quella reale del dataset.
- **Mock condiviso**: il mock conserva solo le ultime due email inviate nello stack. Il test cerca l'indirizzo univoco del proprio utente in entrambi i file.

## 7. Checklist di revisione

- [ ] Verificare che la CI avvii i worker della coda `archived_forecast` usata dai reftime storici.
- [ ] Verificare che i timeout (120 s per la request, 30 s per email e revoca) siano adeguati al carico della CI.

## 8. Possibili criticità

- **Richiede l'infrastruttura reale**: senza broker o worker i test falliscono per timeout; il cleanup prova a fermare i task dell'utente e, senza conferma dei worker, fallisce senza cancellare.
- **Skippabile**: senza `lm5`, o fuori dagli stack `rapydo --testing`, i test vengono saltati.
- **Stack condiviso**: i worker eseguono anche i task di altri. I test vanno eseguiti solo su uno stack di test dedicato; due email inviate da altri tra il fallimento e la lettura farebbero uscire quella del test dal mock.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/Fake | Fixture | Tipo |
|---|---|---|---|---|---|
| `test_data_request_is_extracted_by_real_worker` | `Data.post` + broker + worker + `data_extract` + download | estrazione reale scaricabile | nessuno | `real_worker_user` | `async_real` + `runtime_sensitive` |
| `test_failed_data_request_notifies_owner_through_smtp_mock` | `Data.post` + worker + quota + `notify_by_email` | email di errore nel mock SMTP | mock SMTP di Rapydo nel worker | `_create_real_worker_user` | `async_real` + `runtime_sensitive` |
| `test_cleanup_timeout_revokes_queued_request_on_real_workers` | `Data.post` + revoca Celery + cleanup | revoca prima della cancellazione | nessuno | `real_worker_user` | `async_real` + `runtime_sensitive` |
