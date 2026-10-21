# Review — `test_on_data_ready_task_edges_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** (prompt 04) sui rami edge del task data-ready, non coperti dall'happy path legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tasks/test_on_data_ready_task_edges_EXT.py](projects/mistral/backend/tests/integration/tasks/test_on_data_ready_task_edges_EXT.py)
- **Scopo**: verificare i rami di `launch_all_on_data_ready_extractions` che **saltano** una schedule (0 dataset, ≥2 dataset, run filter non decodificabile) o che **falliscono** con `SystemError` quando l'invio Celery solleva un'eccezione.
- **Tipologia**: test di **integrazione task** (schedule seedate nel DB di test + Celery fake). Marker dichiarati: `integration`, `deterministic`.
- **Conteggio**: 4 test in `TestOnDataReadyTaskEdges`. Nessun `pytest.skip`.
- **Baseline**: l'happy path data-ready è coperto inline da `test_schedule_opendata_bridge.py`; qui si coprono solo gli edge che **non** inviano l'estrazione.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `launch_all_on_data_ready_extractions(self, model, rundate)` | [tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py#L11) | Itera **tutte** le schedule; filtra per enabled/on_data_ready/dataset/run; invia `data_extract` su Celery o solleva `SystemError`. |
| `SqlApiDbManager._get_schedule_response` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L455) | Normalizza la schedule (id/name/enabled/on_data_ready/args/period/crontab_set). |
| `BeArkimet.decode_run` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py) | Decodifica il run del filtro; solleva `ValueError` su input non valido (ramo skip). |
| `@CeleryExt.task` failure hook (`mark_task_as_failed`) | `restapi.connectors.celery` | Hook eseguito quando `.run()` propaga un'eccezione (vedi §6). |

- Backend **realmente eseguito**: l'intero corpo del task fino al `send_task` (filtri, `_get_schedule_response`, `decode_run` reale, costruzione reftime/args).
- Backend **non** coinvolto: invio Celery reale, broker, esecuzione di `data_extract`.

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `seed_schedule_for_data_ready` | helper locale | nel file di test | Seed diretto di una `Schedule` con `datasets`/`run_filter` controllati; ritorna l'`id`. |
| `delete_schedule_row` | helper locale | nel file di test | Cleanup idempotente della schedule seedata. |
| `data_ready_task_user` | fixture locale | nel file di test | Crea utente reale (`allowed_schedule`) come owner della schedule; registra cleanup utente+dir. |
| `faker` | fixture | `pytest-faker` | Nome schedule pseudo-casuale (`faker.pystr()`). |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**. |
| `monkeypatch` | fixture | `pytest` | Sostituisce `celery.get_instance` e `mark_task_as_failed`. |
| `MagicMock` (`fake_celery`) | doppio | `unittest.mock` | Falso connettore Celery; `celery_app.send_task` ispezionato (`call_count`) o con `side_effect`. |
| `celery_connector.mark_task_as_failed` | hook | `restapi.connectors.celery` | Patchato per **ri-sollevare** l'eccezione originale invece di emettere l'evento Celery. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | DB di test per seed/lettura schedule. |

## 4. Analisi dettagliata di ogni test

### `test_skip_schedule_with_zero_datasets`
- **Obiettivo**: una schedule con `datasets=[]` deve essere saltata senza inviare estrazione.
- **Backend coinvolto**: ramo `if len(datasets) == 0: ... continue`.
- **Flusso**: seed schedule con 0 dataset → patch `celery.get_instance` → `launch_all_on_data_ready_extractions.run("lm5", datetime(2021,10,19))`.
- **Setup**: `data_ready_task_user`, `fake_celery` (MagicMock), cleanup schedule.
- **Assert**: `fake_celery.celery_app.send_task.call_count == 0`.
- **Casi coperti**: skip per dataset vuoto.

### `test_skip_schedule_with_multiple_datasets`
- **Obiettivo**: una schedule con ≥2 dataset (ancora non supportata) deve essere saltata.
- **Backend coinvolto**: ramo `if len(datasets) >= 2: ... continue` (precede il confronto `datasets[0] != model`).
- **Flusso**: seed schedule `datasets=["lm5","lm2.2"]` → run del task.
- **Assert**: `send_task.call_count == 0`.
- **Casi coperti**: skip multi-dataset.

### `test_skip_schedule_with_invalid_run_filter_decode`
- **Obiettivo**: una schedule con run filter malformato deve essere saltata.
- **Backend coinvolto**: `arki.decode_run(e)` **reale** solleva `ValueError` → `requested_runs` resta vuoto → `runhour not in []` → `continue`.
- **Flusso**: seed schedule `datasets=["lm5"]`, `run_filter=[{"invalid_arkimet_run":"broken"}]` → run del task con rundate ore 00:00.
- **Assert**: `send_task.call_count == 0`.
- **Casi coperti**: gestione `ValueError` nel decode del run. **Vedi §8**: l'assert è debole (non distingue il motivo dello skip).

### `test_celery_send_failure_raises_system_error`
- **Obiettivo**: se `send_task` fallisce, il task deve sollevare `SystemError`.
- **Backend coinvolto**: blocco `try/except Exception → raise SystemError("Unable to submit the data ready request extraction")`.
- **Flusso**: seed schedule valida `datasets=["lm5"]` → `fake_celery.celery_app.send_task.side_effect = Exception(...)` → patch `mark_task_as_failed` con `raise_original_task_error_EXT` (ri-solleva l'eccezione passata) → run del task.
- **Setup**: `data_ready_task_user`, `fake_celery` con side_effect, doppio patch (Celery + failure hook).
- **Assert**: `pytest.raises(SystemError, match="Unable to submit the data ready request extraction")`.
- **Casi coperti**: ramo di errore + propagazione attraverso il failure hook di restapi.

## 5. Call chain

```
launch_all_on_data_ready_extractions.run(model="lm5", rundate=2021-10-19T00:00:00)
  → db.Schedule.query.all()                       # ITERA TUTTE le schedule del DB di test
  → per ogni schedule: _get_schedule_response(row)
       → not enabled?            continue
       → not on_data_ready?      continue
       → len(datasets)==0?       continue          # TEST 1
       → len(datasets)>=2?       continue          # TEST 2
       → datasets[0]!=model?     continue
       → filters["run"]: arki.decode_run(e) → ValueError → continue → runhour not in [] → continue   # TEST 3
       → period/crontab_set?     (None qui) → salta
       → c = celery.get_instance()                 # → fake_celery (MagicMock)
       → c.celery_app.send_task("data_extract", ...)
            • TEST 1/2/3: mai raggiunto → call_count==0
            • TEST 4: side_effect Exception → except → raise SystemError
                 → @CeleryExt.task failure hook → mark_task_as_failed (patchato) → re-raise → SystemError
```

## 6. Comportamenti nascosti

- **Il task itera su TUTTE le schedule del DB** (`db.Schedule.query.all()`), non solo su quella seedata: l'isolamento dipende dallo stato globale del DB di test (vedi §8).
- **Failure hook di restapi**: chiamare `.run()` su una task decorata `@CeleryExt.task` fa passare l'eccezione attraverso `mark_task_as_failed`, che in produzione **emette un evento Celery sul broker**. Senza patch, il test misurerebbe la raggiungibilità del broker; `raise_original_task_error_EXT` ri-solleva l'eccezione originale così l'assert resta sul contratto `SystemError`.
- **`decode_run` reale**: il terzo test esercita davvero l'helper Arkimet (non è mockato), quindi dipende dalla validazione reale del run.
- **`period`/`crontab_set` assenti nei seed**: `seed_schedule_for_data_ready` non imposta `period`/`is_crontab`, quindi il blocco di scheduling periodico viene saltato e il flusso arriva diretto a `send_task`.
- **Import locali di `celery`**: ogni test reimporta `from restapi.connectors import celery` e patcha `celery.get_instance`; il modulo `celery_connector` (alias top-level) è usato solo per `mark_task_as_failed`.

## 7. Checklist di revisione

- [ ] **Isolamento**: confermare che il DB di test non contenga altre schedule `on_data_ready` che matchino `model="lm5"` con config valida — altrimenti `call_count==0` o l'attesa di `SystemError` potrebbero diventare instabili.
- [ ] Rafforzare l'assert del terzo test: oggi `call_count==0` non prova che lo skip sia dovuto al `ValueError` del run (potrebbe saltare per altri motivi).
- [ ] Verificare che il patch di `mark_task_as_failed` non mascheri altri failure hook attesi della suite (qui è confinato al singolo test e ripristinato da pytest).
- [ ] Confermare che `rundate` ore 00:00 sia coerente con il run filter del terzo test (runhour `"00:00"`).
- [ ] Verificare che i seed non lascino schedule residue tra i test (cleanup LIFO presente).

## 8. Possibili criticità

- **Assert debole sul terzo test**: `send_task.call_count == 0` non discrimina il **motivo** dello skip; lo stesso esito si avrebbe per qualunque schedule scartata. Il ramo `ValueError` del `decode_run` non è verificato direttamente (es. nessun assert sul log o sul percorso).
- **Dipendenza dallo stato globale del DB**: poiché il task itera su tutte le schedule, i test sono sensibili a dati lasciati da altri test; i tre skip-test si affidano al fatto che **nessuna** schedule preesistente matchi `lm5`.
- **Over-mock del dispatch Celery**: `send_task` è un `MagicMock`; non si verifica la correttezza di `args`/`queue`/`routing_key` realmente passati (es. l'ordine dei 12 argomenti di `data_extract`). Una regressione nella tupla di `args` passerebbe inosservata.
- **Failure hook patchato**: necessario, ma sostituisce un comportamento di produzione (evento Celery) con un re-raise; il test verifica `SystemError`, non l'effettiva segnalazione del fallimento al sistema Celery.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_skip_schedule_with_zero_datasets` | ramo `len==0` | skip, nessun send | `fake_celery` (MagicMock) | `data_ready_task_user`, `faker`, `cleanup_registry` | Bassa |
| `test_skip_schedule_with_multiple_datasets` | ramo `len>=2` | skip, nessun send | `fake_celery` | come sopra | Bassa |
| `test_skip_schedule_with_invalid_run_filter_decode` | `decode_run` ValueError | skip, nessun send | `fake_celery` | come sopra | Media |
| `test_celery_send_failure_raises_system_error` | `try/except`→`SystemError` | propagazione errore | `fake_celery` (side_effect) + patch `mark_task_as_failed` | come sopra | Media |
