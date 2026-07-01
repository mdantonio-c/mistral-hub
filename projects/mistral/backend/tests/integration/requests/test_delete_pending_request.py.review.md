# Review — `test_delete_pending_request.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo *baseline* (non `*_EXT`): copre il contratto di **cancellazione** delle richieste e il **cleanup automatico** delle richieste stagnanti.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/requests/test_delete_pending_request.py](projects/mistral/backend/tests/integration/requests/test_delete_pending_request.py)
- **Scopo**: verificare le regole di `DELETE /api/requests/<id>` attorno al *grace period* (cancellazione consentita oltre la finestra → `200`; negata dentro la finestra → `403`) e il comportamento del task Celery `automatic_cleanup` che marca come `FAILURE` le richieste stagnanti lasciando intatte quelle recenti.
- **Tipologia**: test di **integrazione HTTP + task Celery** (controller reale + DB SQLAlchemy + task registrato). Marker: `integration`, `deterministic`.
- **Numero di test**: 3, in un'unica classe `TestDeletePendingRequests(BaseTests)`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `UserRequests.delete` | [endpoints/requests.py](projects/mistral/backend/endpoints/requests.py) | `DELETE /api/requests/<id>` — sequenza `check_request` → `check_owner` → `check_request_is_pending_within_grace_period` → `delete_request_record` + `db.session.delete(request)` → `200`. |
| `repo.check_request` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L69) | `True` se la `Request` esiste, altrimenti `False` → `NotFound`. |
| `repo.check_owner` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L50) | `True` se `request.user_id == user.id`; altrimenti ritorna `None` (falsy) → `Unauthorized`. |
| `repo.check_request_is_pending_within_grace_period` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L80) | `True` se `submission_date > now - GRACE_PERIOD` **e** `status not in READY_STATES` → `Forbidden`. |
| `repo.delete_request_record` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L172) | Rimuove l'eventuale `fileoutput` su disco/DB poi `commit` (non cancella la `Request`, lo fa l'endpoint). |
| `automatic_cleanup` | [tasks/requests_cleanup.py](projects/mistral/backend/tasks/requests_cleanup.py#L18) | Task Celery: per ogni `Request` senza `end_date`, se `status not in READY_STATES` e `now - GRACE_PERIOD > submission_date` setta `end_date`, `error_message`, `status = FAILURE`. |
| Modello `Request` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Colonne usate negli assert: `id`, `status`, `submission_date`, `archived`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `app` | fixture | `restapi.tests` | App Flask di test; passata a `send_task` per il task di cleanup. |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L37) | Teardown **LIFO**; usata **transitivamente** dalle fixture locali. |
| `pending_request_user` | fixture **locale** | [requests/conftest.py](projects/mistral/backend/tests/integration/requests/conftest.py) | Utente temporaneo autenticato (senza permessi speciali) + cleanup utente/cartelle. |
| `pending_delete_requests` | fixture **locale** | [requests/conftest.py](projects/mistral/backend/tests/integration/requests/conftest.py) | Crea **due** `Request` (una vecchia/`STARTED`, una recente/`PENDING`) e registra il cleanup; ritorna `(deletable_id, undeletable_id)`. |
| `create_pending_delete_requests` / `delete_request_rows` | helper | [requests/support.py](projects/mistral/backend/tests/integration/requests/support.py) | Seeding/cleanup diretto delle righe `Request` (usati dalla fixture locale). |
| `faker` | fixture | plugin `faker` | Nomi randomici delle richieste (via la fixture locale). |
| `AuthenticatedTestUser` | dataclass | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Record `uuid`/`user_id`/`headers`/`output_dir`. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Accesso diretto al DB per gli assert di stato. |
| `BaseTests.send_task` | helper | `restapi.tests` | Dispatcher del task Celery registrato per nome (`"automatic_cleanup"`). |
| `READY_STATES` | costante | `celery.states` | Insieme degli stati terminali (`SUCCESS`/`FAILURE`/`REVOKED`); usata nell'assert finale. |

## 4. Analisi dettagliata di ogni test

### `test_delete_request_before_grace_period_returns_200`
- **Obiettivo**: una richiesta **più vecchia** del grace period è cancellabile manualmente.
- **Backend coinvolto**: `delete` → `check_request`/`check_owner` ok → `check_request_is_pending_within_grace_period` **False** (la `submission_date` è fuori finestra) → cancellazione.
- **Flusso**: prende `deletable_request_id` (primo elemento della tupla) → `DELETE /requests/<id>` con gli header dell'owner.
- **Setup**: `pending_request_user` + `pending_delete_requests`; la richiesta cancellabile ha `status="STARTED"` e `submission_date = now - GRACE_PERIOD - 1g`.
- **Assert**: `status_code == 200`; `db.Request.query.get(deletable_request_id) is None` (effetto persistito sul DB).
- **Casi coperti**: happy path della cancellazione fuori grace period + side effect DB.

### `test_delete_request_within_grace_period_returns_403`
- **Obiettivo**: una richiesta **pendente e recente** è protetta dalla cancellazione manuale.
- **Backend coinvolto**: `delete` → `check_request`/`check_owner` ok → `check_request_is_pending_within_grace_period` **True** → `Forbidden`.
- **Flusso**: prende `undeletable_request_id` (secondo elemento) → `DELETE /requests/<id>`.
- **Setup**: la richiesta non cancellabile ha `status="PENDING"` e `submission_date = now - GRACE_PERIOD + 1g` (dentro la finestra).
- **Assert**: `status_code == 403`; la richiesta è **ancora presente** (`get(...) is not None`).
- **Casi coperti**: error path / protezione grace period.

### `test_requests_cleanup_marks_stale_request_as_failure`
- **Obiettivo**: il cleanup automatico marca come `FAILURE` la richiesta stagnante e lascia pendente quella recente.
- **Backend coinvolto**: task `automatic_cleanup` (ramo "richiesta senza `end_date` oltre grace period").
- **Flusso**: `self.send_task(app, "automatic_cleanup")` → poi rilettura delle due righe dal DB.
- **Setup**: stesse due righe della fixture (`STARTED` vecchia, `PENDING` recente). **Non** usa `client` né `pending_request_user` direttamente (l'utente è creato in modo transitivo).
- **Assert**:
  - `deletable_request is not None` e `status == "FAILURE"` (marcata, **non** cancellata: il ramo "stagnante" setta solo lo stato e fa `continue`).
  - `undeletable_request is not None` e `status not in READY_STATES` (resta `PENDING`).
- **Casi coperti**: comportamento del task su una richiesta oltre grace period vs una dentro.

## 5. Call chain

```
DELETE /api/requests/<id>            → auth.require()
                                       → repo.check_request?  no  → NotFound 404
                                       → repo.check_owner?    no  → Unauthorized 401
                                       → repo.check_request_is_pending_within_grace_period? yes → Forbidden 403
                                       → repo.delete_request_record(db,user,id)   (rimuove fileoutput se presente)
                                       → db.session.delete(request) → commit → response 200

send_task(app, "automatic_cleanup")  → CeleryExt task automatic_cleanup
                                       → for r in tutte le Request:
                                           if not r.end_date and r.status not in READY_STATES and now-GRACE_PERIOD > r.submission_date:
                                               r.end_date=now; r.error_message=...; r.status=FAILURE; commit
                                       → (+ rami: archive/delete richieste completate per-utente, pulizia file orfani/.tmp)
```

## 6. Comportamenti nascosti

- **Discriminante = `submission_date`, non lo `status`**: la riga cancellabile è `STARTED` e quella protetta è `PENDING`, ma a decidere è l'età rispetto al grace period (entrambi gli stati sono fuori da `READY_STATES`). Il significato dei nomi di test ("before/within grace period") si riferisce all'**età** della richiesta.
- **Ordine della tupla**: `pending_delete_requests` ritorna `(deletable_id, undeletable_id)`; i test fanno unpacking posizionale (`deletable, _` / `_, undeletable`). Tupla e nomi delle variabili nella fixture/`support.py` devono restare allineati.
- **`delete_request_record` non cancella la `Request`**: rimuove solo l'eventuale `fileoutput`; la `db.session.delete(request)` è nell'endpoint. Sulle righe seed (senza `fileoutput`) il ramo file è no-op.
- **Il task di cleanup ha effetti GLOBALI**: itera **tutte** le `Request` del DB e **tutte** le cartelle sotto `DOWNLOAD_DIR` (file `.tmp` e orfani). L'esecuzione nel test tocca quindi anche dati non legati allo scenario.
- **`send_task` esegue il task nel runtime di test**: gli assert leggono subito gli effetti, quindi il task gira in modo sincrono; il meccanismo esatto (Celery eager) vive in `restapi` e **non è verificabile da questo workspace**.
- **Commento fuorviante** sul wrapper `delete_pending_request`: il commento "Rimuoviamo lo stato creato dal test…" descrive un cleanup, ma la funzione **chiama l'endpoint** sotto test (non pulisce nulla).
- **Login dell'owner**: i test usano `pending_request_user.headers` (utente temporaneo dedicato), non il default user condiviso.

## 7. Checklist di revisione

- [ ] Confermare che `STARTED` e `PENDING` non appartengano a `READY_STATES` (presupposto dei tre test).
- [ ] Verificare l'allineamento ordine-tupla ↔ unpacking nei due test di delete (un'inversione li renderebbe entrambi verdi "per caso" o entrambi rotti).
- [ ] Confermare che il task `automatic_cleanup` sia eseguito sincronamente nel runtime di test (altrimenti gli assert leggerebbero stato non aggiornato).
- [ ] Considerare l'impatto degli **effetti globali** del task sugli altri test della stessa sessione (ordine/isolamento).
- [ ] Verificare che il teardown della fixture cancelli entrambe le righe anche dopo che il task ha mutato lo stato della riga cancellabile.

## 8. Possibili criticità

- **Effetti globali del cleanup**: `automatic_cleanup` non è scopato sull'utente del test; marcando `FAILURE` qualunque richiesta stagnante e cancellando file `.tmp`/orfani, può interagire con dati di altri test o residui → potenziale fonte di non-determinismo in suite condivisa.
- **Dipendenza dal tempo wall-clock**: gli scenari si basano su `now()`; il margine ±1 giorno assorbe gli skew ordinari, ma resta una dipendenza dall'orologio (e dal valore di `GRACE_PERIOD`).
- **`now()` naive vs `submission_date` default `utcnow`**: i seed impostano `submission_date` esplicitamente con `datetime.now()` locale, coerente con i controlli (anch'essi `now()` locale); il default del modello (`utcnow`) non viene usato qui, ma la discrepanza naive/UTC merita attenzione.
- **Test cleanup accoppiato alla fixture di delete**: riusa `pending_delete_requests` (pensata per i test di delete); un cambio della fixture impatta sia delete sia cleanup.
- **Verifica solo il ramo "stagnante" del task**: i rami "richieste completate" (archiviazione/cancellazione per `requests_expiration_*`) e "file orfani" del task non sono coperti qui.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_delete_request_before_grace_period_returns_200` | `delete` + repo grace/owner | delete consentita fuori grace + riga rimossa | — (DB diretto) | `client`, `pending_request_user`, `pending_delete_requests` | Bassa |
| `test_delete_request_within_grace_period_returns_403` | `delete` + `check_request_is_pending_within_grace_period` | delete negata dentro grace + riga intatta | — | `client`, `pending_request_user`, `pending_delete_requests` | Bassa |
| `test_requests_cleanup_marks_stale_request_as_failure` | task `automatic_cleanup` | stagnante→`FAILURE`, recente→resta pending | — (task reale) | `app`, `pending_delete_requests` | Media |
