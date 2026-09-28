# Review — `test_initializer_smoke_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: smoke deterministico **di estensione** su `mistral.initialization.Initializer`, superficie finora coperta solo indirettamente dallo startup.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/initializer/test_initializer_smoke_EXT.py](projects/mistral/backend/tests/integration/initializer/test_initializer_smoke_EXT.py)
- **Scopo**: proteggere invarianti **sostenibili** dell'initializer senza replicarne il seeding: (a) importabilità del modulo senza side effect, (b) importabilità strutturale delle revisioni Alembic, (c) **nessuna creazione duplicata** quando le righe esistono già + **ricreazione** del cron `requests_cleanup`.
- **Tipologia**: smoke **deterministico** con **fake totali** (SQLAlchemy/Celery/Arkimet) e import-only delle migrazioni. **Nessun** DB/Celery/Arkimet reale, **nessun** dato meteo. Marker: `integration`, `deterministic` (**non** `runtime_sensitive`).
- **Numero di test**: 3, nella classe `TestInitializerSmoke_EXT`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Initializer.__init__` | [initialization.py](projects/mistral/backend/initialization.py#L7) | Seed idempotente di `GroupLicense`/`License`/`Attribution`/`Datasets` + ricreazione cron `requests_cleanup`. **Esercitato solo via fake** nel test 3. |
| Seed `GroupLicense`/`License`/`Attribution` | [initialization.py](projects/mistral/backend/initialization.py#L11) | Per ogni voce: `filter_by(name=...).first()` → se `None` crea, altrimenti aggiorna solo su differenza. 2 `commit()` complessivi (gruppi; licenze+attribution). |
| Seed `Datasets` | [initialization.py](projects/mistral/backend/initialization.py#L296) | `arki.load_datasets()` → per ogni ds `filter_by(arkimet_id=...).first()`; update solo su differenza. 3° `commit()`. |
| Cron `requests_cleanup` | [initialization.py](projects/mistral/backend/initialization.py#L347) | `get_periodic_task` → se presente `delete_periodic_task` → `create_crontab_task(task="automatic_cleanup", hour=3, minute=45, args=[])`. |
| Revisioni Alembic | `migrations/versions/*.py` | Importate come moduli isolati; **mai** eseguite (`upgrade`/`downgrade` solo verificate come callable). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `monkeypatch` | fixture | pytest | Sostituisce `initialization.sqlalchemy.get_instance`, `...celery.get_instance`, `...arki.load_datasets` (solo test 3). |
| `_FakeSqlAlchemy_EXT` | fake locale | nel file | Espone `session` + model fake (`GroupLicense`/`License`/`Attribution`/`Datasets`). |
| `_FakeSession_EXT` | fake locale | nel file | Registra `added` e conta `commit()` senza persistere. |
| `_Query_EXT` / `_FilteredQuery_EXT` | fake locale | nel file | `filter_by(...).first()` ritorna **sempre** una riga esistente; `.all()` ritorna `[]`. |
| `_ExistingSeedRow_EXT` | fake locale | nel file | Riga "già presente"; campi sentinella `_AlwaysMatchingValue_EXT`. |
| `_AlwaysMatchingValue_EXT` | fake locale | nel file | `__eq__→True`, `__ne__→False`, `__bool__→True`: neutralizza i rami di update. |
| `_NoDuplicateModel_EXT` | fake locale | nel file | Il costruttore **solleva `AssertionError`**: ogni tentativo di creare una riga fa fallire il test. |
| `_FakeCelery_EXT` | fake locale | nel file | `get_periodic_task` ritorna truthy → forza il ramo delete+recreate; registra le chiamate. |
| `_fake_arkimet_datasets_EXT` | fake locale | nel file | Ritorna **un** dataset sintetico `synthetic-dataset` già rappresentato dal DB fake. |
| `_load_migration_module_EXT` | helper locale | nel file | `importlib.util.spec_from_file_location` per importare una revision senza eseguirla. |

## 4. Analisi dettagliata di ogni test

### `test_initializer_module_imports_without_running_seed_EXT`
- **Obiettivo**: il modulo `mistral.initialization` è importabile senza avviare il seeding.
- **Backend coinvolto**: import del modulo (non il costruttore).
- **Flusso**: `importlib.import_module("mistral.initialization")` → `assert hasattr(initialization, "Initializer")`.
- **Setup**: nessuno.
- **Assert**: presenza dell'attributo `Initializer`.
- **Casi coperti**: smoke di import. **⚠️ Può "passare in modo banale"**: l'asserzione è un semplice `hasattr`; il valore aggiunto è solo verificare che l'import non colleghi DB/Celery/Arkimet (assenza di side effect a import time), ma ciò **non è asserito esplicitamente** — è garantito solo dal fatto che il modulo non esegue logica a livello top.

### `test_migration_versions_import_without_running_upgrade_EXT`
- **Obiettivo**: ogni revisione Alembic è importabile e strutturalmente valida, senza toccare il DB.
- **Backend coinvolto**: file `migrations/versions/*.py` (solo import).
- **Flusso**: deriva `versions_dir` dal path del modulo initializer importato → importa ogni file con `_load_migration_module_EXT` (mai `upgrade`/`downgrade`).
- **Setup**: nessun fake; usa il filesystem reale del backend.
- **Assert**: lista non vuota; `revision` **univoche**; ogni `revision` è stringa non vuota; `upgrade`/`downgrade` presenti e **callable**; almeno una `down_revision is None` (base); almeno una revision **non** referenziata come `down_revision` (head).
- **Casi coperti**: integrità strutturale della catena migrazioni. **Non** verifica la correttezza dello schema né esegue le migrazioni (delegate al runtime Alembic/CI). Non banale (asserzioni reali), ma puramente **strutturale**.

### `test_initializer_recreates_cleanup_cron_without_duplicate_seed_EXT`
- **Obiettivo**: con righe già presenti, l'initializer **non crea duplicati** e **reinstalla** il cron cleanup.
- **Backend coinvolto**: `Initializer.__init__` completo, eseguito contro fake.
- **Flusso**: monkeypatch di `sqlalchemy.get_instance→fake_sql`, `celery.get_instance→fake_celery`, `arki.load_datasets→_fake_arkimet_datasets_EXT` → `initialization.Initializer()`.
- **Setup**: fake SQLAlchemy (tutto "già presente"), fake Celery (cron preesistente), un dataset Arkimet sintetico.
- **Assert**:
  - `initializer is not None`;
  - `fake_sql.session.added == []` → **nessun add** (né create né update);
  - `fake_sql.session.commit_count >= 3` → i 3 `commit()` del costruttore (gruppi; licenze+attribution; dataset);
  - `fake_celery.requested_tasks == ["requests_cleanup"]`;
  - `fake_celery.deleted_tasks == ["requests_cleanup"]`;
  - `fake_celery.created_crontab_tasks == [{name, task="automatic_cleanup", hour="3", minute="45", args=[]}]`.
- **Casi coperti**: idempotenza del seed (nessun duplicato/aggiornamento spurio) + sequenza esatta di ricreazione del cron. **Doppia guardia** contro le creazioni: oltre a `added == []`, il costruttore dei model fake (`_NoDuplicateModel_EXT`) **solleverebbe `AssertionError`** se l'initializer provasse a istanziare una riga.

## 5. Call chain

```
Initializer()                       → sqlalchemy.get_instance() == fake_sql
  GroupLicense: filter_by(name).first() → _ExistingSeedRow_EXT (mai None)
                if descr/is_public/dballe_dsn != ... → _AlwaysMatchingValue_EXT.__ne__ == False → nessun add
  session.commit()                   → commit_count = 1
  License/Attribution: idem          → nessun add → session.commit() → commit_count = 2
  Datasets: arki.load_datasets() == [synthetic-dataset]
            filter_by(arkimet_id).first() → riga; ds_entry.name("synthetic-dataset") != ds["name"]("synthetic-dataset") == False
            (altri campi via _AlwaysMatchingValue_EXT) → nessun add → session.commit() → commit_count = 3
  celery.get_instance() == fake_celery
  get_periodic_task("requests_cleanup") → truthy → delete_periodic_task("requests_cleanup")
  create_crontab_task(name, task="automatic_cleanup", hour=3, minute=45, args=[])
```

## 6. Comportamenti nascosti

- **`_AlwaysMatchingValue_EXT` neutralizza i rami di update**: ogni confronto `campo != valore_atteso` restituisce `False`, quindi l'initializer non chiama mai `session.add(row)` sulle righe esistenti. L'invariante `added == []` dipende interamente da questo fake.
- **Coupling fragile sul nome dataset**: per i `Datasets` l'initializer usa il confronto **reale** `ds_entry.name != ds["name"]`. Il fake funziona solo perché `_ExistingSeedRow_EXT` ha `name` di default `"synthetic-dataset"` **uguale** al `name` ritornato da `_fake_arkimet_datasets_EXT`. Se i due divergessero, scatterebbe un `add` e il test fallirebbe — non per un bug reale, ma per disallineamento dei fake.
- **`_NoDuplicateModel_EXT` come seconda guardia**: i model fake ereditano un costruttore che solleva `AssertionError`; qualunque creazione (anche legittima in un DB vuoto) viene trasformata in fallimento. Lo smoke modella **esplicitamente** un DB "già seedato".
- **`get_periodic_task` truthy forza un solo ramo**: il fake ritorna `{"name": ...}`, quindi il test copre **solo** il caso "cron già esistente → delete + recreate", **non** il caso "cron assente → solo create".
- **`.all()` ritorna `[]` di proposito**: silenzia i warning diagnostici dell'initializer su righe extra nel DB; quei rami di logging non sono oggetto dello smoke.
- **`commit_count >= 3` è una soglia, non un'uguaglianza**: ammette commit aggiuntivi; oggi i commit sono esattamente 3, ma il test non si rompe se ne venissero aggiunti.
- **Le migrazioni non vengono eseguite**: `upgrade`/`downgrade` sono solo verificate come `callable`; nessuna operazione DDL viene applicata.
- **`initialize_testing_environment` non è coperto**: è un no-op (`pass`) e non viene chiamato.

## 7. Checklist di revisione

- [ ] Prendere atto che il **test 1 può passare banalmente** (`hasattr`): valutare se aggiungere un'asserzione esplicita sull'assenza di side effect all'import.
- [ ] Confermare che il **coupling sul nome `synthetic-dataset`** sia intenzionale e documentato (rischio falso-rosso su refactor dei fake).
- [ ] Verificare che lo smoke copra **solo** il ramo "cron già presente"; valutare un caso complementare "cron assente → create".
- [ ] Confermare che `commit_count >= 3` rifletta i 3 commit reali e non mascheri eventuali commit mancanti (sotto-soglia falsa positiva: con `>=`, **meno** di 3 commit fallirebbe correttamente; **più** di 3 passerebbe silenziosamente).
- [ ] Verificare che il test migrazioni resti valido con una storia Alembic **ramificata** (la rilevazione della head usa "revision non presente tra i down_revision": con più head potrebbe essere ambigua ma non fallace).
- [ ] Confermare che i fake restino allineati alla firma reale di `Initializer` (model usati: `GroupLicense`, `License`, `Attribution`, `Datasets`).

## 8. Possibili criticità

- **Tautologia controllata**: il test 3 verifica il **flusso di controllo/wiring** dell'initializer (idempotenza + cron), **non** la correttezza dei dati di seed. Coglierebbe regressioni come "crea duplicati pur con righe esistenti", "smette di ricreare il cron" o "meno di 3 commit"; **non** coglierebbe seed con descrizioni/URL errati o categorie sbagliate.
- **Fragilità dei fake**: l'invariante `added == []` dipende da `_AlwaysMatchingValue_EXT` e dal nome dataset coordinato; modifiche all'ordine/forma dei confronti nell'initializer possono rompere il test senza un difetto reale.
- **Copertura parziale del cron**: solo il ramo "esistente"; il ramo "assente" (prima installazione) non è esercitato.
- **Test 1 a basso valore**: utile come canarino di import, ma l'asserzione minima lo rende poco informativo.
- **Dipendenza dal filesystem (test 2)**: deriva `versions_dir` dal path del modulo importato; corretto sia da host sia nel mount `tests/custom`, ma legato alla struttura `migrations/versions` (un refactor della cartella romperebbe il test).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Fake/mock | Fixture | Può passare banalmente? |
|---|---|---|---|---|---|
| `test_initializer_module_imports_without_running_seed_EXT` | import `mistral.initialization` | `hasattr(Initializer)` | — | — | **Sì** (solo `hasattr`; nessun assert sui side effect) |
| `test_migration_versions_import_without_running_upgrade_EXT` | import `migrations/versions/*.py` | revisioni univoche, callable `upgrade`/`downgrade`, ≥1 base + ≥1 head | import isolato (no upgrade) | — | No (asserzioni reali, ma solo **strutturali**) |
| `test_initializer_recreates_cleanup_cron_without_duplicate_seed_EXT` | `Initializer.__init__` | nessun seed duplicato (`added==[]`), `commit_count>=3`, cron `requests_cleanup` delete+recreate | fake SQLAlchemy/Celery/Arkimet + `monkeypatch` | `monkeypatch` | No, ma **tautologico** sul flusso (fake permissivi): non valida i dati di seed |
