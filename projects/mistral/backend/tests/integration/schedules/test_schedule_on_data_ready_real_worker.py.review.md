# Review — `test_schedule_on_data_ready_real_worker.py`

> File di review per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `async_real`: la prima estrazione della schedule gira su un worker Celery reale, senza fake.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/integration/schedules/test_schedule_on_data_ready_real_worker.py`
- **Scopo**: verificare che `POST /schedules` con `on-data-ready` invii il primo `data_extract` a un worker reale, che la request termini in `SUCCESS` e che la `DELETE` rimuova la schedule.
- **Tipologia**: integrazione HTTP + broker + worker reali. Marker di modulo: `integration`, `async_real`, `runtime_sensitive`. 1 test.
- **Dataset reale**: `lm5`, con finestra e prima run lette da `/api/fields`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `SingleSchedule.post` | `projects/mistral/backend/endpoints/schedules.py` | Salva la schedule solo on-data-ready, senza voce RedBeat, e invia subito il primo `data_extract` (`countdown=1`). |
| task `data_extract` | `projects/mistral/backend/tasks/data_extraction.py` | Eseguito dal worker reale con `schedule_id` e `data_ready=True`: crea la `Request`, estrae, scrive il file nella cartella dell'utente. |
| `ScheduledRequests.get` | `projects/mistral/backend/endpoints/schedules.py` | `GET /schedules/<id>/requests`, letto in polling. |
| `SingleSchedule.delete` / `get` | `projects/mistral/backend/endpoints/schedules.py` | `DELETE` con Celery reale; `GET` successivo → 404. |
| `FileDownload.get` | `projects/mistral/backend/endpoints/file.py` | `GET /data/<filename>`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `schedules_base` | fixture conftest | `projects/mistral/backend/tests/integration/schedules/conftest.py` | Override di `SingleSchedule.ON_DATA_READY_DATASETS` su `lm5`. |
| `schedules_user` | fixture conftest | `projects/mistral/backend/tests/integration/schedules/conftest.py` | `create_data_ready_user` (nessuna email reale) + cleanup di request, schedule, utente e cartella. |
| `register_wait_for_user_requests`, `wait_for_finished_request`, `read_periodic_task` | helper | `projects/mistral/backend/tests/helpers/real_workers.py` | Attesa dei worker nel test e nel cleanup, compreso il primo task della schedule ancora senza request; se scade, arresto dei soli task dell'utente prima di cancellare. Lettura RedBeat della sola schedule del test. |
| `create_schedule`, `list_schedule_requests` | helper | `projects/mistral/backend/tests/helpers/data_ready.py` | Creazione e listing via API. |
| `build_on_data_ready_schedule` | helper | `projects/mistral/backend/tests/helpers/schedules.py` | Body con `opendata=False`. |
| `fetch_dataset_window` | helper | `projects/mistral/backend/tests/helpers/dataset_window.py` | Finestra reale di `lm5`; `pytest.skip` su 404. |

## 4. Analisi dettagliata di ogni test

### `test_on_data_ready_schedule_first_extraction_runs_on_real_worker`
- **Obiettivo**: il primo `data_extract` di una schedule on-data-ready viene eseguito da un worker reale.
- **Flusso**: attesa dei worker registrata nel cleanup → finestra `lm5` → `POST /schedules` (`on-data-ready`, `opendata=False`) → lettura RedBeat → polling della request della schedule → download → `DELETE /schedules/<id>` → `GET /schedules/<id>`.
- **Assert**: nessuna voce RedBeat per la schedule, né dopo la creazione né dopo la cancellazione; request `SUCCESS` con `task_id` valorizzato; file nella cartella dell'utente; download 200 con lunghezza pari a `filesize`; `DELETE` 200 e `GET` 404.
- **Casi coperti**: catena reale endpoint → broker → worker per le schedule on-data-ready, e cancellazione con Celery reale.

## 5. Call chain

```
POST /api/schedules (on-data-ready, opendata=False)  → 202 {schedule_id}
   nessuna voce RedBeat; RabbitMQ reale → worker reale → data_extract(schedule_id, data_ready=True)
poll GET /api/schedules/<id>/requests                → SUCCESS, fileoutput, filesize, task_id
GET /api/data/<file>                                 → 200
DELETE /api/schedules/<id>                           → 200 (Celery reale)
GET /api/schedules/<id>                              → 404
cleanup: attesa worker → DELETE /requests/<id> → DELETE utente → rimozione cartella
```

## 6. Comportamenti nascosti

- **È il caso che i test `data_ready` producevano per errore**: prima del fake nel loro conftest, ogni schedule on-data-ready inviava questo `data_extract` reale. Il worker lo eseguiva dopo la cancellazione della schedule e falliva con "Cannot find schedule reference". Qui il test aspetta l'esito e lo verifica.
- **`task_id` come prova del worker**: `data_extract` lo scrive con l'id del task Celery; eseguito in-process resterebbe `None`.
- **Output fuori da opendata**: con `opendata=False` il file finisce nella cartella dell'utente temporaneo, rimossa dal cleanup, e non nella cartella opendata condivisa.
- **Nessuna email reale**: il test gira solo sugli stack `rapydo --testing`, dove i worker usano il mock SMTP; altrove `tests/conftest.py` lo salta. L'utente ha inoltre `notify_on_successful_request=False` e indirizzo `@example.invalid`.
- **Prima estrazione vuota**: con `data_ready=True` una request senza dati viene cancellata dal task; il polling scadrebbe con il messaggio di timeout.

## 7. Checklist di revisione

- [ ] Verificare che la finestra di `lm5` produca dati anche nell'ambiente CI.
- [ ] Verificare che nessun `launch_all_on_data_ready_extractions` reale giri durante il test, altrimenti la schedule potrebbe avere più di una request.

## 8. Possibili criticità

- **Richiede l'infrastruttura reale**: senza broker o worker il test fallisce per timeout.
- **Stack condiviso**: un data-ready reale ricevuto durante il test potrebbe lanciare altre estrazioni della schedule. Il test va eseguito solo su uno stack di test dedicato.
- **Skippabile**: senza `lm5` il test viene saltato.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/Fake | Fixture | Tipo |
|---|---|---|---|---|---|
| `test_on_data_ready_schedule_first_extraction_runs_on_real_worker` | `SingleSchedule.post/delete` + broker + worker + `data_extract` | prima estrazione reale, nessuna voce RedBeat, cancellazione | nessuno | `schedules_base`, `schedules_user` | `async_real` + `runtime_sensitive` |
