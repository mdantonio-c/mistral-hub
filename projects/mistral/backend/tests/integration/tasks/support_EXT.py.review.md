# Review — `tasks/support_EXT.py` (infrastruttura di dominio, ADATTATA)

> File di review per modulo di supporto dei test task. Non contiene test e non modifica codice.
> Modulo `*_EXT.py`: infrastruttura **di estensione** aggiunta dal prompt 07, usata solo dai nuovi test task.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py)
- **Scopo**: centralizzare i **fake** di SMTP/RabbitMQ/Celery e i **seed DB** (utente, request, schedule, fileoutput) usati dai test su `requests_cleanup` e `data_extraction`. I fake riproducono **solo** i metodi osservati dai task, così la verifica resta sui side effect (quota, cleanup, notification) e non sull'infrastruttura esterna reale.
- **Tipologia**: modulo di supporto (dataclass + fake/double + builder DB + helper filesystem). Nessun marker, nessun test.
- **Runtime dichiarato**: nessuna connessione SMTP/RabbitMQ/Celery/tool meteo reale; il DB è quello di test Rapydo; i file fisici vivono sotto la directory dell'utente temporaneo o sotto `tmp_path`.

## 2. Elementi definiti

| Elemento | Tipo | Ruolo |
|---|---|---|
| `SentEmailEXT` | dataclass | Cattura `body`/`subject`/`recipient`/`plain_body` di una mail per assert espliciti. |
| `RetryThenSuccessSmtpFactoryEXT` | fake factory | Sostituisce `smtp.get_instance`; conta `send_attempts`, registra `get_instance_calls` e `sent_messages`. |
| `RetryThenSuccessSmtpClientEXT` | fake context manager | Implementa solo `send`/`__enter__`/`__exit__`; fallisce `failures_before_success` volte poi accetta il payload. |
| `RecordingRabbitFactoryEXT` | fake factory | Sostituisce `rabbitmq.get_instance`; espone `connection`. |
| `RecordingRabbitConnectionEXT` | fake context manager | Implementa `send_json`/`disconnect`/`__enter__`/`__exit__`; registra `sent_messages` e `disconnected`. |
| `RecordingPeriodicTaskDeletionEXT` | fake callable | Sostituisce `CeleryExt.delete_periodic_task`; registra `calls` e ritorna `return_value`. |
| `create_task_test_user_EXT` | builder | Crea utente via API e poi **forza in DB** i campi task (quota, expiration, notify). |
| `seed_request_EXT` | seed DB | Inserisce una `Request` sintetica (status/end_date/schedule_id/archived/opendata). |
| `seed_fileoutput_EXT` | seed DB+FS | Crea `FileOutput` **e** file fisico nella dir output dell'utente. |
| `seed_schedule_EXT` | seed DB | Inserisce una `Schedule` minimale (no RedBeat). |
| `delete_schedule_EXT` | cleanup | Rimozione idempotente di una schedule. |
| `delete_requests_for_user_EXT` | cleanup | Rimozione `FileOutput`+`Request` di un utente. |
| `touch_mtime_EXT` | helper FS | Imposta `st_mtime` via `os.utime` per i rami orphan-cleanup. |

## 3. Fake e doppi di test (cosa è davvero simulato)

| Fake | Sistema esterno reale sostituito | Metodi simulati | Cosa NON viene esercitato |
|---|---|---|---|
| `RetryThenSuccessSmtpFactoryEXT` + `...ClientEXT` | connettore SMTP `restapi.connectors.smtp` usato in [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L694) (`notify_by_email`) | `get_instance(**kwargs)`, `send(...)`, `__enter__`/`__exit__` | apertura connessione SMTP reale, invio TLS, retry/backoff del connettore reale. |
| `RecordingRabbitFactoryEXT` + `...ConnectionEXT` | connettore `rabbitmq` usato in [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L725) (`notify_by_amqp_queue`) | `get_instance()`, `send_json(payload, routing_key=...)`, `disconnect()` | pubblicazione reale su broker, canali, serializzazione AMQP. |
| `RecordingPeriodicTaskDeletionEXT` | `CeleryExt.delete_periodic_task` usato in [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L494) (`check_user_quota`) | `__call__(*args, **kwargs)` → `return_value` | rimozione reale del periodic task da RedBeat / worker Celery. |

- **Punto di iniezione coerente con il reale**: i metodi dei factory si chiamano `get_instance_EXT`, ma vengono **monkeypatchati** sui simboli reali (`smtp.get_instance`, `rabbitmq.get_instance`). Il suffisso `_EXT` serve solo a marcare l'origine “estensione”.
- **Semantica context manager preservata**: `__exit__` ritorna `False` in entrambi i fake → eventuali eccezioni si propagano come col connettore reale (importante per il test di retry SMTP).

## 4. Builder e seed DB (cosa tocca davvero il database)

- **`create_task_test_user_EXT`**: passa dalla creazione utente reale ([tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) → `create_authenticated_test_user`), poi **scrive direttamente** in DB `requests_expiration_days`, `requests_expiration_delete`, `disk_quota`, `max_output_size`, `notify_on_successful_request`. Registra il cleanup standard (utente + dir output) via `register_test_user_cleanup`. Permessi: `allowed_schedule`, `open_dataset`.
- **`seed_request_EXT`**: inserisce una `Request` con `args` minimi (`datasets`/`reftime`/`filters`); default `status="SUCCESS"`, `submission_date=utcnow()`. Restituisce l'`id`.
- **`seed_fileoutput_EXT`**: crea la dir `output_dir`, **scrive un file fisico** (`.grib` sintetico) sotto `DOWNLOAD_DIR/<uuid>/outputs`, inserisce `FileOutput(size=len(content))`, e **aggiunge il path al `cleanup_registry`**. È il ponte DB↔filesystem usato dal cleanup test.
- **`seed_schedule_EXT`**: inserisce una `Schedule` non-crontab (`PeriodEnum.days`, `every=1`, `time_delta=1h`), `is_enabled`/`on_data_ready` configurabili. **Non** registra nulla in RedBeat.
- **`delete_schedule_EXT` / `delete_requests_for_user_EXT`**: cleanup **idempotenti** (controllano l'esistenza prima di cancellare), pensati per non fallire se il ramo sotto test ha già modificato lo stato.
- **`touch_mtime_EXT`**: riscrive il file e poi forza `os.utime(path, (ts, ts))` (import `os` locale alla funzione) per spostare l'mtime nel passato/presente, così il ramo orphan di `automatic_cleanup` decide in base alla soglia temporale.

## 5. Comportamenti nascosti

- **DB reale, servizi esterni fake**: i seed usano il vero DB di test (i rami da coprire persistono `User`/`Schedule`/`Request`/`FileOutput`), mentre SMTP/Rabbit/Celery sono doppi locali. Mix consapevole: utile a isolare i side effect, ma sposta la fiducia sui fake (vedi §7).
- **Fake “parziali” per costruzione**: implementano **solo** il sottoinsieme di API osservato. Se il task reale iniziasse a chiamare un altro metodo (es. un secondo `send`, o un `ack`), i fake **non** lo intercetterebbero e il test potrebbe passare ignorando una regressione.
- **Accoppiamento sui kwargs di connessione**: `RetryThenSuccessSmtpFactoryEXT.get_instance_calls` registra i kwargs (`retries`, `retry_wait`) attesi dal task: un cambio di firma del connettore reale **non** romperebbe il fake, ma il test che vi si appoggia sì.
- **Side effect filesystem confinati**: i path vivono sotto l'utente temporaneo o `tmp_path`; `seed_fileoutput_EXT` registra anche il parent dir nel `cleanup_registry`. Nessuna scrittura in aree runtime non controllate.
- **`touch_mtime_EXT` riscrive il contenuto** del file prima di settare l'mtime: l'mtime finale è quello imposto, ma il file viene comunque toccato due volte.

## 6. Dipendenze esterne

| Dipendenza | Origine | Note |
|---|---|---|
| `create_authenticated_test_user`, `register_test_user_cleanup`, `AuthenticatedTestUser` | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Creazione utente reale + cleanup standard. |
| `sqlalchemy.get_instance()` | `restapi.connectors` | Sessione DB di test. |
| `BaseTests`, `FlaskClient` | `restapi.tests` | Helper di creazione utente. |
| `PeriodEnum`, `Schedule`/`Request`/`FileOutput`/`User` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py) | Modelli persistiti dai seed. |

## 7. Checklist di revisione

- [ ] Verificare che i fake coprano **tutti** i metodi che il task reale invoca oggi (SMTP `send`, Rabbit `send_json`/`disconnect`, `delete_periodic_task`): un'API aggiunta lato task richiederebbe di aggiornare il fake.
- [ ] Confermare che `create_task_test_user_EXT` debba forzare i campi DB **dopo** la creazione API (l'endpoint non li espone tutti) e che non rimanga divergenza con i default di produzione.
- [ ] Verificare che `seed_*` restino allineati al formato `args` prodotto dagli endpoint reali (schedule/request), per non testare un contratto JSON divergente.
- [ ] Controllare che i cleanup idempotenti coprano l'ordine `FileOutput → Request` anche quando il task ha già cancellato parte dello stato.

## 8. Possibili criticità

- **Over-mocking strutturale**: il modulo esiste per sostituire interi sistemi esterni con fake che riproducono il “percorso felice osservato”. È adeguato a test di ramo, ma **non** verifica l'integrazione reale con SMTP/RabbitMQ/RedBeat: un cambio del connettore reale può passare inosservato.
- **Doppia fonte di verità sui kwargs**: i valori `retries=5, retry_wait=10` sono codificati sia nel task sia nelle aspettative dei test che leggono `get_instance_calls`; vanno mantenuti sincronizzati a mano.
- **Seed che bypassano la validazione applicativa**: inserendo `Request`/`Schedule` direttamente in DB si evita la validazione degli endpoint; uno schema `args` non più valido per la produzione potrebbe restare “verde” nei test.
- **Dipendenza dal layout filesystem**: `seed_fileoutput_EXT` assume `DOWNLOAD_DIR/<uuid>/outputs`; un refactor del path di output romperebbe sia il task sia i seed, ma il fallimento si manifesterebbe solo qui.
