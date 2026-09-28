# Review — `test_data_extraction_quota_and_notifications_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** (prompt 07) sui rami ad alto rischio di `tasks.data_extraction` non esercitati dagli happy path postprocessing.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tasks/test_data_extraction_quota_and_notifications_EXT.py](projects/mistral/backend/tests/integration/tasks/test_data_extraction_quota_and_notifications_EXT.py)
- **Scopo**: proteggere i rami di quota utente (`MaxOutputSizeExceeded`/`DiskQuotaException`), la disabilitazione schedule su quota, il **duplicate data-ready**, le notifiche **email** (con retry) e **AMQP**, e il package license, **senza** rieseguire estrazioni meteo reali.
- **Tipologia**: mista — **integrazione task** per quota/data-ready (DB reale: User/Schedule/Request/FileOutput) e **unità con fake** per le notifiche e il package (request come `SimpleNamespace`, sistemi esterni monkeypatchati). Marker: `integration`, `deterministic`.
- **Conteggio**: 8 test in 4 classi (`TestCheckUserQuotaEXT`×4, `TestDataExtractDataReadyEXT`×1, `TestDataExtractionNotificationsEXT`×2, `TestPackageDataLicenseEXT`×1). Nessun `pytest.skip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `check_user_quota(...)` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L494) | Stima dimensione (Arkimet) → confronta con `max_output_size` e disk quota; disabilita schedule periodica su quota; bypass per `opendata`. |
| `data_extract` (ramo duplicate data-ready) | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L44) | Early-return se l'ultima request SUCCESS ha la stessa `reftime` (no nuovo output). |
| `notify_by_email(db, user_id, request, extra_msg)` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L694) | Costruisce body via template, invia via SMTP con **retry** (`MAX_RETRIES`/`SLEEP_TIME`). |
| `notify_by_amqp_queue(amqp_queue, request)` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L725) | Pubblica JSON (status/reftime/filename/download_url) sulla routing key e `disconnect`. |
| `package_data_license(...)` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L860) | tar.gz output+LICENSE + unlink sorgente. |
| `SqlApiDbManager.get_user_permissions` / `update_schedule_status` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L665) / [#L427](projects/mistral/backend/services/sqlapi_db_manager.py#L427) | `max_output_size`; disabilitazione schedule. |
| `CeleryExt.delete_periodic_task` | `restapi.connectors.celery` | Rimozione periodic task (qui **fake**). |
| Template `data_extraction_result.html` | [models/emails/data_extraction_result.html](projects/mistral/backend/models/emails/data_extraction_result.html) | Riferito dal `get_html_template` (qui **fake**). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `create_task_test_user_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Utente reale con quota/limiti forzati in DB. |
| `seed_schedule_EXT` / `delete_schedule_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Schedule DB (no RedBeat) + cleanup idempotente. |
| `seed_request_EXT` / `delete_requests_for_user_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Request precedente per duplicate check + cleanup. |
| `RetryThenSuccessSmtpFactoryEXT` | fake | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Fake SMTP: fallisce 1 volta poi invia; registra invii/kwargs. |
| `RecordingRabbitFactoryEXT` | fake | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Fake RabbitMQ: registra payload+routing_key e `disconnect`. |
| `RecordingPeriodicTaskDeletionEXT` | fake | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Fake `delete_periodic_task`: registra `calls`, ritorna True. |
| `monkeypatch` | fixture | `pytest` | Patcha `arki.estimate_data_size`, `subprocess.check_output`, `CeleryExt.delete_periodic_task`, `get_html_template`, `smtp.get_instance`, `time.sleep`, `rabbitmq.get_instance`, `get_backend_url`. |
| `client`, `cleanup_registry`, `tmp_path` | fixture | `restapi.tests` / [tests/conftest.py](projects/mistral/backend/tests/conftest.py) / `pytest` | Client, teardown LIFO, dir temporanea. |
| `DiskQuotaException`, `MaxOutputSizeExceeded` | eccezioni | [mistral/exceptions.py](projects/mistral/backend/exceptions.py) | Effetto osservabile dei rami quota. |
| `states` (celery) | costanti | `celery` | `SUCCESS`/`FAILURE` per request sintetiche. |

## 4. Analisi dettagliata di ogni test

### `test_check_user_quota_raises_when_estimate_exceeds_max_output_size_EXT`
- **Obiettivo**: stima > `max_output_size` → `MaxOutputSizeExceeded` ("single request").
- **Backend coinvolto**: `check_user_quota` dal confronto `max_output_size` (Arkimet stub).
- **Flusso**: utente `max_output_size=128` → `arki.estimate_data_size` → `129` → chiamata diretta a `check_user_quota`.
- **Setup**: utente reale, `output_dir` creata, `estimate_data_size` monkeypatchato.
- **Assert**: `pytest.raises(MaxOutputSizeExceeded, match="single request")`.
- **Casi coperti**: ramo limite per singola request. **Arkimet completamente bypassato** (la stima è sintetica).

### `test_check_user_quota_raises_when_disk_quota_is_insufficient_EXT`
- **Obiettivo**: `used + stima > disk_quota` → `DiskQuotaException`.
- **Backend coinvolto**: secondo controllo (`max_output_size=None` salta il primo) con `du -sb` stub.
- **Flusso**: `disk_quota=1000`, `max_output_size=None`, stima `200`, `du` → `b"900\t...\n"` → `900+200>1000`.
- **Setup**: utente reale; `estimate_data_size` e `subprocess.check_output` monkeypatchati.
- **Assert**: `pytest.raises(DiskQuotaException, match="Disk quota exceeded")`.
- **Casi coperti**: ramo disk quota; calcolo free space come in produzione (ma `du` e Arkimet finti).

### `test_check_user_quota_disables_periodic_schedule_on_quota_failure_EXT`
- **Obiettivo**: su quota error, schedule periodica disabilitata e periodic task rimosso.
- **Backend coinvolto**: ramo `schedule_id is not None` → `on_data_ready is False` → `CeleryExt.delete_periodic_task(name=str(schedule_id))` → `update_schedule_status(False)`.
- **Flusso**: utente `max_output_size=10`, schedule `on_data_ready=False`, stima `64`, fake `delete_periodic_task` → `check_user_quota(..., schedule_id=...)`.
- **Setup**: utente+schedule reali, fake periodic deletion, cleanup schedule.
- **Assert**: `MaxOutputSizeExceeded` sollevata; `schedule.is_enabled is False`; `fake_delete_periodic.calls == [{"args":(),"kwargs":{"name":str(schedule_id)}}]`; messaggio contiene `"temporary disabled"`.
- **Casi coperti**: ramo side-effect heavy (DB + Celery fake) sul limite per singola request.

### `test_check_user_quota_skips_user_limits_for_opendata_EXT`
- **Obiettivo**: con `opendata=True` i limiti personali non si applicano.
- **Backend coinvolto**: `if not opendata:` saltato; ritorna la stima senza eccezioni.
- **Flusso**: utente `max_output_size=1`, `disk_quota=1`, stima `4096`; `du` monkeypatchato per **fallire** se chiamato.
- **Setup**: `fail_if_du_is_used_EXT` (AssertionError) come guardia del ramo filesystem.
- **Assert**: `estimated_size == 4096` (nessuna eccezione, `du` mai chiamato).
- **Casi coperti**: bypass opendata di entrambi i controlli quota; prova **negativa** che `du` non viene consultato.

### `test_data_extract_duplicate_data_ready_returns_without_new_output_EXT`
- **Obiettivo**: se l'ultima request SUCCESS ha la stessa reftime, il task ritorna senza creare output.
- **Backend coinvolto**: `data_extract` ramo `if data_ready:` → `last_request.args["reftime"] == reftime` → `return` (prima di auth dataset/Arkimet/output_dir).
- **Flusso**: utente, schedule `on_data_ready=True`, request precedente SUCCESS con `reftime=duplicate_reftime` → `data_extract.run(...)` con `data_ready=True`, stessa reftime.
- **Setup**: utente+schedule+request reali; cleanup schedule e request.
- **Assert**: nessuna **nuova** Request per la schedule (`after == before == {previous_id}`); `FileOutput.count()==0`; `output_dir` vuota se esiste.
- **Casi coperti**: idempotenza data-ready. Poiché `data_ready=True`, `adapt_reftime` **non** è invocata (la reftime resta quella passata, confrontata tale e quale).

### `test_notify_by_email_retries_with_sleep_noop_and_sends_payload_EXT`
- **Obiettivo**: primo errore SMTP → retry senza sleep reale → invio riuscito.
- **Backend coinvolto**: `notify_by_email` (query email DB reale, `get_html_template`, loop retry `MAX_RETRIES`/`SLEEP_TIME`).
- **Flusso**: utente reale (per l'email), `get_html_template` fake (registra `title/status/message`), `smtp.get_instance` → fake che fallisce 1 volta, `time.sleep` → no-op che registra → `notify_by_email(db, user_id, request, " after retry")` con `request` `SimpleNamespace(status=FAILURE, error_message="synthetic failure")`.
- **Setup**: utente reale; resto del percorso notification **fake**.
- **Assert**: `send_attempts==2`; 1 messaggio inviato; subject fisso `"MeteoHub: data extraction completed"`; `recipient==db_user.email`; `body=="html:FAILURE:synthetic failure after retry"`; `plain_body=="plain-body-ext"`; `captured_template` esatto; `sleep_calls==[SLEEP_TIME]`; `get_instance_calls==[{"retries":5,"retry_wait":10}]×2`.
- **Casi coperti**: assemblaggio body + retry SMTP (1 fallimento). **Vedi §8**: il ramo “tutti i retry falliscono” (eccezione silenziata) **non** è coperto.

### `test_notify_by_amqp_queue_sends_success_payload_with_download_url_EXT`
- **Obiettivo**: notifica AMQP success include status/reftime/filename/download_url.
- **Backend coinvolto**: `notify_by_amqp_queue` (costruzione dict + `send_json` + `disconnect`).
- **Flusso**: `rabbitmq.get_instance` → fake, `get_backend_url` → `"https://backend.example.invalid"`, `request` `SimpleNamespace(status=SUCCESS, args={"reftime":...}, fileoutput=SimpleNamespace(filename=...))` → `notify_by_amqp_queue("queue.notification.ext", request)`.
- **Setup**: **nessun** DB; solo fake e `SimpleNamespace`.
- **Assert**: `sent_messages` con payload esatto (`request_name`, `status`, `reftime`, `filename`, `download_url="https://backend.example.invalid/api/data/synthetic-output.grib"`) su `routing_key="queue.notification.ext"`; `disconnected is True`.
- **Casi coperti**: payload success completo. **Vedi §8**: ramo `error_message` (non-success) non coperto; solo costruzione dict (broker finto).

### `test_package_data_license_archives_license_and_removes_original_EXT`
- **Obiettivo**: tar contiene output+LICENSE, file output originale sparisce.
- **Backend coinvolto**: `package_data_license` completo.
- **Flusso**: `tmp_path` con `task-output.grib` + `license.txt` → `package_data_license(...)`.
- **Setup**: `tmp_path` registrata anche in `cleanup_registry.add_path`.
- **Assert**: tar esiste; `out_file` assente; `license_file` presente; membri `["LICENSE","task-output.grib"]`; contenuti verificati.
- **Casi coperti**: duplica volutamente il contratto già visto nei quick wins, accanto ai side effect di `data_extraction`.

## 5. Call chain

```
check_user_quota(user_id, user_dir, db, datasets, query, schedule_id?, opendata?)
  → esti = arki.estimate_data_size(...)            # STUB sintetico
  → max_output_size = get_user_permissions(user, "output_size")
  → if not opendata:                               # opendata=True → ritorna esti
       → esti > max_output_size? → [schedule? on_data_ready False → CeleryExt.delete_periodic_task(name) (FAKE)
                                                    → update_schedule_status(False)] → raise MaxOutputSizeExceeded
       → used = du -sb user_dir (STUB) ; used+esti > disk_quota? → raise DiskQuotaException
  → return esti

data_extract.run(... data_ready=True, schedule_id ...)
  → schedule = Schedule.query.get(schedule_id)
  → data_ready: last_request = Request.filter_by(schedule_id, status=SUCCESS).order_by(submission_date desc).first()
  → last_request.args["reftime"] == reftime? → return        # nessun create_request_record / Arkimet / output_dir

notify_by_email(db, user_id, request, extra)
  → email = User.email (DB reale) ; body,plain = get_html_template(...) (FAKE)
  → for i in range(MAX_RETRIES): smtp.get_instance(retries=5, retry_wait=10) (FAKE) → send(...) ; break
       → except → log + time.sleep(SLEEP_TIME) (no-op) → continue

notify_by_amqp_queue(queue, request)
  → rabbitmq.get_instance() (FAKE) → send_json({request_name,status,reftime,[error_message],filename,download_url}, routing_key=queue) → disconnect()
       → download_url = get_backend_url() (STUB) + "/api/data/" + filename
```

## 6. Comportamenti nascosti

- **Test che iniziano “dopo la stima”**: in tutti i test quota, `arki.estimate_data_size` è uno stub; l'estrazione Arkimet reale **non** è esercitata. Il contratto verificato parte dal confronto con i limiti utente.
- **`opendata` bypassa l'intero blocco quota**: il quarto test usa `du` come **trappola** (AssertionError) per provare che il ramo filesystem non viene mai toccato.
- **Duplicate data-ready prima di tutto il resto**: l'early-return avviene **prima** di `create_request_record`, auth dataset, output_dir e Arkimet; per questo il test non deve mockare nulla di esterno.
- **`adapt_reftime` saltata con `data_ready=True`**: nel task, `adapt_reftime` è chiamata solo `if reftime and not data_ready`; il confronto duplicate usa la reftime **non** adattata.
- **Retry SMTP: condizione sempre vera e nessun re-raise**: nel loop `for i in range(MAX_RETRIES)` la guardia `if i < MAX_RETRIES` è **sempre** vera (i∈{0,1,2}, MAX_RETRIES=3) → l'ultimo tentativo dorme comunque; e se **tutti** i tentativi falliscono l'eccezione viene **silenziata** (nessun `raise`). Il test copre solo 1 fallimento, quindi questi due comportamenti restano scoperti.
- **`notify_by_email` legge l'email reale dal DB**: l'unico pezzo non-fake del percorso email è la query `User.email`.
- **AMQP payload condizionale**: `error_message` è aggiunto solo se valorizzato; `filename`/`download_url` solo se `status==SUCCESS`. Il test copre il ramo SUCCESS senza error_message.
- **`get_backend_url` importato nel modulo**: pur essendo `from restapi.config import get_backend_url`, è patchabile come `data_extraction.get_backend_url`.

## 7. Checklist di revisione

- [ ] Confermare che bypassare `estimate_data_size` sia accettabile: i test quota non esercitano la stima Arkimet, solo la logica di confronto.
- [ ] Verificare la robustezza del retry email: documentare/decidere se l'eccezione “tutti i retry falliti” debba essere silenziata e se l'ultimo `sleep` sia voluto (`i < MAX_RETRIES` sempre vero).
- [ ] Aggiungere copertura del ramo AMQP con `error_message` (non-success) e del ramo email “tutti i retry falliti”.
- [ ] Confermare che l'uso di `SimpleNamespace` per `request` nelle notifiche non diverga dagli attributi reali (`name`, `status`, `error_message`, `args["reftime"]`, `fileoutput.filename`).
- [ ] Verificare che il fake `delete_periodic_task` rifletta la firma reale (`name=` kwarg) e che il valore di ritorno True/False copra anche il ramo `DeleteScheduleException`.

## 8. Possibili criticità

- **Over-mocking elevato (rischio segnalato dal prompt)**:
  - quota: Arkimet (`estimate_data_size`) e `du` (`subprocess.check_output`) sono stub → si testa solo la **logica di confronto**, non l'integrazione reale;
  - notifiche: SMTP, RabbitMQ, `get_html_template`, `get_backend_url`, `time.sleep` sono tutti fake **e** la `request` è un `SimpleNamespace` → per `notify_by_amqp_queue` si verifica di fatto solo l'assemblaggio di un dict;
  - schedule disabling: `CeleryExt.delete_periodic_task` è un fake → non si verifica la rimozione reale in RedBeat.
- **Rami di errore scoperti**: `DeleteScheduleException` (quando `delete_periodic_task` ritorna False), email “tutti i retry falliti” (eccezione silenziata), AMQP con `error_message`.
- **Bug latente non testato nel retry email**: la guardia `if i < MAX_RETRIES` è sempre vera e non c'è `raise` finale; il test con 1 fallimento non lo evidenzia. Un reviewer potrebbe concludere erroneamente che il retry sia robusto.
- **Asserzioni su costanti duplicate**: `{"retries":5,"retry_wait":10}` e `SLEEP_TIME` sono verificati a specchio dei valori hardcoded nel task; vanno mantenuti sincronizzati a mano.
- **Isolamento DB sul duplicate test**: l'assert conta le request `filter_by(schedule_id)`; corretto perché la schedule è dedicata, ma dipende dal fatto che nessun'altra request usi quella schedule.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/Fake | Fixture | Complessità |
|---|---|---|---|---|---|
| `..._raises_when_estimate_exceeds_max_output_size_EXT` | `check_user_quota` (max_output_size) | `MaxOutputSizeExceeded` | `estimate_data_size` stub | `client`, `cleanup_registry`, `monkeypatch` | Media |
| `..._raises_when_disk_quota_is_insufficient_EXT` | `check_user_quota` (disk quota) | `DiskQuotaException` | `estimate_data_size`+`du` stub | come sopra | Media |
| `..._disables_periodic_schedule_on_quota_failure_EXT` | quota + `delete_periodic_task` + `update_schedule_status` | schedule disabilitata, periodic rimosso | `delete_periodic_task` fake | + `seed_schedule_EXT` | Alta |
| `..._skips_user_limits_for_opendata_EXT` | `check_user_quota` (bypass opendata) | nessuna eccezione, `du` non usato | `estimate_data_size` stub + `du` trap | come sopra | Media |
| `..._duplicate_data_ready_returns_without_new_output_EXT` | `data_extract` (duplicate) | nessun nuovo output | — (DB reale) | + `seed_schedule_EXT`/`seed_request_EXT` | Alta |
| `..._notify_by_email_retries_with_sleep_noop..._EXT` | `notify_by_email` | retry+body+recipient | SMTP/template/sleep fake | `client`, `cleanup_registry`, `monkeypatch` | Alta |
| `..._notify_by_amqp_queue_sends_success_payload..._EXT` | `notify_by_amqp_queue` | payload+routing+disconnect | Rabbit/`get_backend_url` fake | `monkeypatch` | Media |
| `..._package_data_license_archives_license_and_removes_original_EXT` | `package_data_license` | tar+unlink sorgente | — (FS reale) | `tmp_path`, `cleanup_registry` | Bassa |
