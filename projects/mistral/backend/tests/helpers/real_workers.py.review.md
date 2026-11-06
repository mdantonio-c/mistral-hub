# Review — `helpers/real_workers.py` (helper condiviso)

> File di review per l'helper dei test `async_real`. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/real_workers.py](projects/mistral/backend/tests/helpers/real_workers.py)
- **Scopo**: tenere nel proprio perimetro i test i cui task girano sui worker Celery reali. Nei worker `monkeypatch` non ha effetto: tutto ciò che il task fa avviene davvero.
- **Tipologia**: infrastruttura di suite, usata dai cinque test `async_real`, dall'hook di [tests/conftest.py](projects/mistral/backend/tests/conftest.py) e da `integration/data/test_real_worker_cleanup.py`.

## 2. Elementi definiti

### `FINISHED_STATES`
- `celery.states.READY_STATES`: `SUCCESS`, `FAILURE`, `REVOKED`. Sono gli stati in cui `DELETE /requests/<id>` accetta la cancellazione.

### `workers_use_smtp_mock()`, `TESTING_STACK_MARKERS`, `NO_SMTP_MOCK_REASON`
- Ritorna `True` solo se lo stack è avviato con `rapydo --testing` (senza `--production`): solo lì i worker hanno `APP_MODE=test` e usano il mock SMTP.
- Il processo dei test non vede l'ambiente dei worker e il suo `APP_MODE` vale sempre `test`, perché lo forza `restapi tests`. Il controllo usa quindi le tre variabili che lo stesso comando imposta nel container backend: `PYTHONMALLOC=debug`, `PYTHONASYNCIODEBUG=1`, `PYTHONFAULTHANDLER=1`.
- Usata dall'hook `pytest_collection_modifyitems` di `tests/conftest.py`, che salta i test `async_real` con il motivo `NO_SMTP_MOCK_REASON`.

### `read_periodic_task(schedule_id)`
- Legge da RedBeat la chiave della sola schedule indicata, tramite il connettore Celery del progetto (`get_periodic_task`).
- Ritorna la voce RedBeat oppure `None`. Sola lettura.

### `wait_for_finished_request(read_request, *, description, timeout=120, interval=2)`
- Polling (`wait_until`) finché la request restituita da `read_request` arriva a uno stato finale.
- Ritorna il payload finale qualunque sia lo stato: il test asserisce `SUCCESS` e mostra l'errore del worker negli altri casi.

### `wait_for_mock_email(address, *, timeout=30, interval=1)` e `MockEmail`
- Cerca l'email per `address` nei file `mock.mail.lastsent.json` e `mock.mail.prevsent.json` di `/logs`, condiviso da backend e worker. Ritorna destinatari, oggetto e testo.
- Un'email trovata qui è passata dal mock e non è mai uscita dallo stack.

### `held_user_tasks(user_id)`
- Interroga i worker (`inspect().active()`, `reserved()`, `scheduled()`) e ritorna gli id dei `data_extract` il cui primo argomento è `user_id`: in esecuzione, prelevati o in attesa del `countdown`.
- Ritorna `None` se nessun worker risponde: in quel caso non si può confermare nulla.

### `stop_user_tasks(user, *, timeout=30, interval=3)`
- Revoca subito, per id, i task delle request aperte dell'utente: un task ancora nel broker non compare nelle risposte dei worker, ma lo scartano appena lo ricevono.
- Poi revoca i `data_extract` dell'utente trovati nei worker, finché nessun worker ne riporta più.
- Usa `terminate=True` con `SIGKILL`: un task in esecuzione muore senza arrivare al `finally` di `data_extract`, che scriverebbe la request e invierebbe l'email.
- Se i worker non confermano, fallisce con un messaggio che indica l'utente rimasto.

### `register_wait_for_user_requests(base, client, cleanup_registry, user, *, timeout=120, interval=3, stop_timeout=30)`
- Registra un passo di cleanup che attende due condizioni: tutte le request dell'utente chiuse e nessun suo `data_extract` nei worker. La seconda copre il primo task di una schedule, che non ha ancora una request finché un worker non lo avvia.
- Va registrato **dopo** `register_data_ready_user_cleanup`: il registry è LIFO, quindi l'attesa gira prima delle cancellazioni via API.
- Allo scadere del `timeout` chiama `stop_user_tasks` e, solo dopo la conferma, cancella le request aperte dell'utente con l'ORM ed emette `RealWorkerCleanupWarning`.
- Senza conferma il passo fallisce: `CleanupRegistry.run` si ferma e righe, file e account dell'utente restano al loro posto, coerenti per un worker che completi il task più tardi.

### `RealWorkerCleanupWarning`
- Deriva da `Warning` e non da `UserWarning`. In modalità test `create_app` trasforma gli `UserWarning` in errori e pytest mantiene quei filtri fino al teardown: un `UserWarning` interromperebbe il cleanup subito dopo la cancellazione delle righe.

## 3. Comportamenti nascosti

- **Perché serve l'attesa**: `DELETE /requests/<id>` rifiuta con 403 le request non terminate nel grace period di 2 giorni. `CleanupRegistry.run` non intercetta le eccezioni: un 403 fermerebbe anche la cancellazione di schedule, utente e cartella.
- **Perché non si cancella sotto un task attivo**: un worker che trova la request, l'utente o la cartella spariti scrive su righe mancanti. Può ricreare cartelle in `/data` e, con l'utente cancellato, inviare l'email di esito all'indirizzo dell'amministratore (`SMTP_ADMIN`). Inoltre le eccezioni non gestite generano un report di errore per email all'amministratore.
- **Solo task dell'utente del test**: revoche e cancellazioni sono filtrate per gli id delle sue request e per `args[0] == user_id`; i task di altri utenti non vengono toccati.
- **Nessun fake**: l'helper non sostituisce nulla e usa lo stesso connettore Celery dell'applicazione.

## 4. Checklist di revisione

- [ ] Verificare che ogni test `async_real` registri `register_wait_for_user_requests` dopo il cleanup del proprio utente.
- [ ] Verificare che i timeout (120 s nel test, 120 s + 30 s nel cleanup) siano adeguati alla CI.
- [ ] Verificare che `read_periodic_task` venga usato solo con id di schedule creati dal test.
- [ ] Verificare, se cambia la versione di Rapydo, che `rapydo --testing` imposti ancora le tre variabili di `TESTING_STACK_MARKERS`.

## 5. Possibili criticità

- **Controllo indiretto dello stack**: le tre variabili provano come è stato avviato il container backend, non i worker. Un worker ricreato a mano con un altro `APP_MODE` non verrebbe rilevato; il test di errore in `test_data_extraction_real_worker.py` fallirebbe però, perché il mock non registrerebbe l'email.
- **Revoca in memoria**: i worker tengono in memoria l'elenco dei task revocati. Se un worker si riavvia prima di ricevere un task revocato ancora nel broker, lo esegue: trova la request cancellata e fallisce senza scrivere file, con un report di errore che negli stack `--testing` finisce nel mock.
- **Task in esecuzione**: l'arresto con `SIGKILL` è provato con worker simulati. Con i dati di test le estrazioni reali durano circa 0,1 s, quindi il test reale copre il caso più frequente: il task ancora in coda. L'estrazione Arkimet gira nello stesso processo del task e si ferma con lui; un sottoprocesso di post-processing già avviato (per esempio `grib_copy` o `vg6d_transform`) può invece finire il suo lavoro nella cartella dell'utente, che il cleanup rimuove subito dopo.
- **Costo**: ogni controllo dei worker interroga tre volte il broker con timeout di 1 s, circa 3 s per ogni teardown `async_real`.
