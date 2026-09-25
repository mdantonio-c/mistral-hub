# Review — `requests/support.py` (infrastruttura di dominio)

> File di review per modulo di supporto (helper locali). Non contiene test né fixture.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/requests/support.py](projects/mistral/backend/tests/integration/requests/support.py)
- **Scopo**: fornire gli helper di **seeding** e **cleanup** delle righe `Request` usati dalle fixture di [requests/conftest.py](projects/mistral/backend/tests/integration/requests/conftest.py) per costruire lo scenario "una richiesta cancellabile + una protetta" dei test sul grace period.
- **Tipologia**: modulo di supporto puramente di dominio (nessuna chiamata HTTP, solo `db.session`).
- **Consumatori**: [requests/conftest.py](projects/mistral/backend/tests/integration/requests/conftest.py) (`pending_delete_requests`). **Non** importato dal modulo `*_EXT`.

## 2. Backend realmente esercitato

- Solo il modello `Request` ([models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36)) via `db.session.add/delete/commit`. Nessun endpoint, nessun task.
- Le date riproducono **manualmente** la soglia di [check_request_is_pending_within_grace_period](projects/mistral/backend/services/sqlapi_db_manager.py#L80): la finestra `now - GRACE_PERIOD`.

## 3. Elementi definiti

| Elemento | Tipo | Cosa fa | Usato da |
|---|---|---|---|
| `grace_period_days` / `GRACE_PERIOD` | costanti | Leggono `Env.get_int("GRACE_PERIOD", 2)` e ne derivano un `timedelta`; replicano i valori usati da endpoint e task. | Calcolo delle `submission_date` qui sotto. |
| `create_pending_delete_requests(faker, db, user_id)` | helper | Crea **due** `Request`: la **cancellabile** (`status="STARTED"`, `submission_date = now - GRACE_PERIOD - 1g`, fuori finestra) e la **protetta** (`status="PENDING"`, `submission_date = now - GRACE_PERIOD + 1g`, dentro finestra); `args={}`; `commit`; ritorna `(deletable_id, undeletable_id)`. | `pending_delete_requests`. |
| `delete_request_rows(db, *request_ids)` | helper | Cancella le righe seed ancora presenti (`get` → `if is not None` → `delete`), poi un singolo `commit`. | Cleanup registrato da `pending_delete_requests`. |

## 4. Comportamenti nascosti

- **Nomi delle variabili-data vs ruolo**: `allowed_delete_time` (vecchia) è assegnata alla richiesta **cancellabile**; `forbidden_delete_time` (recente) alla richiesta **protetta**. I nomi seguono la prospettiva "delete consentita/vietata", non l'ordine della tupla — facile da confondere.
- **Discriminante reale = `submission_date`**: entrambi gli stati (`STARTED`, `PENDING`) sono fuori da `READY_STATES`; a rendere una richiesta cancellabile o protetta è l'**età** rispetto a `GRACE_PERIOD`, non lo stato.
- **`args={}` (minimale e non list-safe)**: le righe non hanno la chiave `datasets`; sono adatte ai soli test di delete/cleanup (che non leggono `args`) ma provocherebbero `KeyError` in `GET /requests` (che fa `pop("datasets")`).
- **`commit` unico nel cleanup**: `delete_request_rows` accumula le `delete` e fa **un solo** `commit` finale; se una riga è già stata rimossa altrove, viene semplicemente saltata.
- **`datetime.now()` naive**: le date sono calcolate con l'ora locale (come i controlli backend), mentre il default del modello è `datetime.utcnow`; qui `submission_date` è sempre impostata esplicitamente, quindi il default non interviene.

## 5. Checklist di revisione

- [ ] Confermare che `now - GRACE_PERIOD - 1g` cada davvero **fuori** dalla finestra e `now - GRACE_PERIOD + 1g` **dentro**, per qualunque valore di `GRACE_PERIOD`.
- [ ] Verificare che `STARTED` e `PENDING` non siano in `READY_STATES` (presupposto della logica grace period).
- [ ] Confermare che l'ordine della tupla `(deletable_id, undeletable_id)` corrisponda all'uso nei test.
- [ ] Verificare che `delete_request_rows` sia idempotente (gestione del caso "riga già assente").

## 6. Possibili criticità

- **Margine temporale a ±1 giorno**: robusto verso piccoli skew, ma se `GRACE_PERIOD` fosse impostato a `0` o a valori anomali la classificazione cancellabile/protetta potrebbe degenerare.
- **Naming potenzialmente fuorviante**: `allowed_/forbidden_delete_time` non rispecchia l'ordine della tupla; un refactor distratto può invertire i due casi senza errori sintattici.
- **Seed non rappresentativo del path reale**: `args={}` non riflette ciò che producono i worker; va bene per i test di delete, ma non valida la forma reale degli `args`.
- **Dipendenza dal wall-clock e dalla configurazione `GRACE_PERIOD`**: lo scenario non è ermetico rispetto al tempo né all'ambiente.
