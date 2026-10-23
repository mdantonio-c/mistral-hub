# Review — `test_requests_cleanup_expiration_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** (prompt 07) sui rami di expiration/orphan di `automatic_cleanup`.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tasks/test_requests_cleanup_expiration_EXT.py](projects/mistral/backend/tests/integration/tasks/test_requests_cleanup_expiration_EXT.py)
- **Scopo**: verificare i rami di `automatic_cleanup` **non** coperti dal pending-stale legacy: archiviazione/cancellazione di request completate **scadute** secondo la policy utente, esclusione di request recenti / già archiviate / di utenti con expiration disabilitata, e rimozione dei **file orfani** oltre il grace period.
- **Tipologia**: test di **integrazione task** (DB di test + filesystem reale, task invocato in-process con `.run()`). Marker dichiarati: `integration`, `deterministic`.
- **Conteggio**: 3 test in `TestAutomaticCleanupExpirationEXT`. Nessun `pytest.skip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `automatic_cleanup(self)` | [tasks/requests_cleanup.py](projects/mistral/backend/tasks/requests_cleanup.py#L17) | Costruisce la mappa utenti con expiration **truthy**; per ogni request decide skip/archive/delete; poi rimuove i file orfani/`.tmp` oltre grace period. |
| `GRACE_PERIOD` | [tasks/requests_cleanup.py](projects/mistral/backend/tasks/requests_cleanup.py#L13) | `timedelta(days=GRACE_PERIOD env, default 2)`; soglia per file orfani/`.tmp` e pending stale. |
| `SqlApiDbManager.delete_request_record` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L172) | Cancella il `FileOutput` e il **file fisico** collegato alla request (non la Request). |
| `DOWNLOAD_DIR` | [endpoints/__init__.py](projects/mistral/backend/endpoints/__init__.py) | Root scandita per i file orfani (`<dir>/outputs`). |
| Modelli `Request`/`FileOutput`/`User` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py) | Stato persistito letto/scritto dal task. |

- Backend **realmente eseguito**: l'intero task in-process (query DB, `delete_request_record`, archiviazione, scansione filesystem `DOWNLOAD_DIR`).
- Backend **non** coinvolto: Celery worker/beat (chiamata diretta `.run()`).

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `create_task_test_user_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Utente reale con policy expiration/delete forzate in DB; cleanup standard. |
| `seed_request_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Request sintetica con `status`/`end_date`/`archived` controllati. |
| `seed_fileoutput_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | `FileOutput` + file fisico sotto la dir output utente; path nel `cleanup_registry`. |
| `delete_requests_for_user_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Cleanup idempotente request+fileoutput. |
| `touch_mtime_EXT` | helper | [tasks/support_EXT.py](projects/mistral/backend/tests/integration/tasks/support_EXT.py) | Imposta `st_mtime` per i file orfani (vecchi/recenti). |
| `client`, `cleanup_registry` | fixture | `restapi.tests` / [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Client di test + teardown LIFO. |
| `states` (celery) | costanti | `celery` | `states.SUCCESS` per le request seedate. |
| `requests_cleanup.GRACE_PERIOD` / `.DOWNLOAD_DIR` | simboli | [tasks/requests_cleanup.py](projects/mistral/backend/tasks/requests_cleanup.py) | Usati dal test per costruire mtime e directory orfana realistici. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | DB di test. |

## 4. Analisi dettagliata di ogni test

### `test_automatic_cleanup_archives_deletes_and_preserves_expected_requests_EXT`
- **Obiettivo**: con due utenti a policy opposta, verificare archive vs delete delle request scadute e la **preservazione** di request recenti / già archiviate.
- **Backend coinvolto**: rami `end_date > now-exp` (skip recente), `r.archived` (skip già archiviata), `delete_request_record` + `archived=True` (delete=False), `db.session.delete(r)` (delete=True).
- **Flusso**: crea `archive_user` (`expiration_days=1`, `delete=False`) e `delete_user` (`delete=True`) → seed:
  - request scaduta + fileoutput per ciascun utente,
  - request **recente** (`end_date=now`) per archive_user,
  - request **già archiviata** scaduta per archive_user → `automatic_cleanup.run()`.
- **Setup**: due utenti reali; file fisici sintetici via `seed_fileoutput_EXT`; cleanup request registrati.
- **Assert**:
  - archive_user: request scaduta **presente** ma `archived=True`, `FileOutput` rimosso e **file fisico assente**;
  - delete_user: request **cancellata** (`get is None`), `FileOutput` rimosso, file fisico assente;
  - request recente: presente, `archived=False`;
  - request già archiviata: presente, `archived=True` (invariata).
- **Casi coperti**: matrice completa archive/delete/skip-recente/skip-archiviata + side effect filesystem di `delete_request_record`.

### `test_automatic_cleanup_ignores_user_with_expiration_disabled_EXT`
- **Obiettivo**: un utente con `requests_expiration_days=0` non perde request vecchie.
- **Backend coinvolto**: costruzione mappa utenti `if exp := u.requests_expiration_days` (0 è falsy → utente escluso) → `if not (exp := users_settings.get(...)): continue`.
- **Flusso**: utente con `expiration_days=0`, `delete=True` → request SUCCESS con `end_date=now-30giorni` → `automatic_cleanup.run()`.
- **Setup**: utente reale, cleanup request registrato.
- **Assert**: request **presente**, `archived=False`, `status==SUCCESS`.
- **Casi coperti**: opt-out dell'autocleaning (valore expiration falsy). Nota: `delete=True` è volutamente impostato per dimostrare che l'esclusione avviene **prima** del ramo distruttivo.

### `test_automatic_cleanup_removes_only_old_orphan_files_EXT`
- **Obiettivo**: i file orfani (senza `FileOutput` DB) oltre grace period vengono rimossi; quelli recenti restano.
- **Backend coinvolto**: blocco finale di scansione `DOWNLOAD_DIR.iterdir() → <dir>/outputs`: ramo `.tmp` oltre grace period e ramo file senza `FileOutput` oltre grace period.
- **Flusso**: crea `DOWNLOAD_DIR/orphan-ext-<uuid>/outputs` → 3 file (`old-orphan.tmp`, `old-orphan.grib`, `recent-orphan.grib`) con mtime via `touch_mtime_EXT` (vecchi = `now - GRACE_PERIOD - 5min`, recente = `now`) → `automatic_cleanup.run()`.
- **Setup**: **nessun** utente/DB request; solo filesystem; `cleanup_registry.add_path(orphan_root)`.
- **Assert**: `.tmp` vecchio rimosso, `.grib` vecchio rimosso, `.grib` recente **presente**.
- **Casi coperti**: cleanup orfani per `.tmp` e per file senza entry DB; rispetto della soglia temporale.

## 5. Call chain

```
automatic_cleanup.run()
  → users_settings/users = { u.id: timedelta(days=exp) for u in User.query.all() if exp truthy }   # TEST 2: exp=0 escluso
  → per ogni Request (per id, ricaricata):
       → r is None? skip
       → not r.end_date? (pending) → grace-period check (legacy, non target qui)
       → users_settings.get(r.user_id) falsy? continue                                              # TEST 2
       → r.archived? continue                                                                       # TEST 1 (già archiviata)
       → r.end_date > now - exp? continue                                                           # TEST 1 (recente)
       → delete_request_record(db, user, r.id)  → unlink file + delete FileOutput                   # TEST 1 (file fisico)
       → user.requests_expiration_delete? db.session.delete(r) [deleted] : r.archived=True [archived]
  → per DOWNLOAD_DIR/<dir>/outputs/<file>:
       → .tmp e oltre grace period → unlink                                                         # TEST 3 (.tmp)
       → FileOutput.filter_by(filename).first() assente e oltre grace period → unlink               # TEST 3 (orphan)
```

## 6. Comportamenti nascosti

- **`expiration_days` falsy = opt-out**: `if exp := u.requests_expiration_days` esclude `0`/`None`. È il cuore del secondo test e va distinto dal “delete vs archive”.
- **`delete_request_record` non cancella la Request**: rimuove `FileOutput` + file fisico e fa `commit`; la decisione delete/archive della Request avviene **dopo**, nel task. I test lo verificano osservando file assente ma Request gestita separatamente.
- **Ricarica per id dentro il loop**: il task riprende `db.session.query(Request).get(r_id)` ad ogni iterazione per evitare oggetti staccati dopo i commit; rilevante se si ragiona sull'ordine degli effetti.
- **Scansione globale di `DOWNLOAD_DIR`**: il terzo test crea una dir orfana **reale** sotto `DOWNLOAD_DIR`; il task la scandisce insieme a tutte le altre dir utente presenti.
- **Grace period da env**: `GRACE_PERIOD` dipende da `Env.get_int("GRACE_PERIOD", 2)`; i test lo importano dal modulo invece di assumerne il valore, restando robusti a configurazioni diverse.
- **File recenti rimossi dal teardown**: i `.grib` recenti non toccati dal task vengono ripuliti dal `cleanup_registry`, non dal task.

## 7. Checklist di revisione

- [ ] Confermare che `requests_expiration_days=0` debba significare opt-out (semantica falsy) e non “scadenza immediata”.
- [ ] Verificare che la scansione orfani su `DOWNLOAD_DIR` reale non interferisca con dati di altri test in esecuzione concorrente/seriale (isolamento via uuid nella dir orfana).
- [ ] Confermare che `delete_request_record` debba rimuovere il file **prima** della decisione archive/delete, anche per le request archiviate.
- [ ] Verificare che il ramo pending-stale (`not r.end_date` + grace period) sia coperto altrove (qui non è il target) e non venga toccato dai seed `end_date`-completati.
- [ ] Controllare che i cleanup idempotenti coprano sia il caso “task ha cancellato” sia “task ha archiviato”.

## 8. Possibili criticità

- **Dipendenza dal filesystem reale `DOWNLOAD_DIR`**: il terzo test scrive sotto la root di download di runtime; l'isolamento si basa solo sul nome `orphan-ext-<uuid>`. Un fallimento a metà task potrebbe lasciare file (mitigato da `cleanup_registry.add_path`).
- **Accoppiamento orario con `now`/`GRACE_PERIOD`**: gli mtime sono calcolati con `now - GRACE_PERIOD - 5min`; un grace period molto piccolo o un clock skew potrebbe rendere fragile la distinzione vecchio/recente (margine 5 minuti).
- **Isolamento sul loop globale delle Request**: il primo e secondo test si fidano che le **altre** request del DB di test non cambino l'esito osservato per gli id seedati; gli assert sono mirati per id, ma il task agisce su tutto il DB.
- **Verifica indiretta del ramo `.tmp`**: il task tratta `.tmp` con un ramo dedicato (prima del check FileOutput); il test lo copre, ma un `.tmp` con FileOutput associato (caso misto) non è esercitato.
- **In-process `.run()`**: non si verifica il comportamento sotto Celery beat reale (idempotenza, scheduling), solo la logica applicativa.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `..._archives_deletes_and_preserves_expected_requests_EXT` | `automatic_cleanup` + `delete_request_record` | archive/delete/skip recente/skip archiviata + file fisico | — (DB+FS reali) | `client`, `cleanup_registry` + helper `support_EXT` | Alta |
| `..._ignores_user_with_expiration_disabled_EXT` | mappa utenti (exp falsy) | opt-out autocleaning | — | `client`, `cleanup_registry` | Bassa |
| `..._removes_only_old_orphan_files_EXT` | scansione orfani `DOWNLOAD_DIR` | `.tmp`/orphan oltre grace rimossi, recente resta | — (FS reale) | `cleanup_registry` + `touch_mtime_EXT` | Media |
