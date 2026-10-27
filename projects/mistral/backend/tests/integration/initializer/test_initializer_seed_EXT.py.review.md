# Review — `test_initializer_seed_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: test di **stato reale** su `mistral.initialization.Initializer`, complementare allo smoke [test_initializer_smoke_EXT.py](./test_initializer_smoke_EXT.py).

## 1. Informazioni generali

- **Percorso**: [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py)
- **Scopo**: verificare ciò che l'initializer **persiste davvero**, non solo il suo flusso di controllo. Copre i tre scenari prioritari: (a) prima creazione del seed, (b) doppia esecuzione idempotente, (c) ripristino di **un singolo campo** divergente.
- **Tipologia**: integrazione su **PostgreSQL e modelli SQLAlchemy reali**. Fake solo per Arkimet (input sintetico) e Celery (recorder con stato). Marker: `integration`, `deterministic`.
- **Numero di test**: 18 raccolti → 17 attesi verdi + 1 `xfail(strict=True)` che documenta un bug reale.
  - `TestInitializerSeed_EXT`: 3 test.
  - `TestInitializerSingleFieldDrift_EXT`: 1 test parametrizzato × 15 casi.
- **Comando**: `rapydo shell backend "restapi tests --file tests/custom/integration/initializer/test_initializer_seed_EXT.py"`
- **Esito verificato**: `17 passed, 1 xfailed`; cartella `custom/integration/initializer` (smoke + seed): `20 passed, 1 xfailed`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo nel test |
|---|---|---|
| Seed `GroupLicense` | [initialization.py](../../../initialization.py#L26) | Creazione da zero, ripristino di `descr` / `is_public` / `dballe_dsn`. |
| Seed `License` | [initialization.py](../../../initialization.py#L85) | Creazione con FK al gruppo corretto; ripristino di `descr` / `url` / `group_license_id`. |
| Seed `Attribution` | [initialization.py](../../../initialization.py#L213) | Creazione di tutti i 19 nomi; ripristino di `descr` / `url`. |
| Seed `Datasets` | [initialization.py](../../../initialization.py#L258) | Creazione da config Arkimet; ripristino di 7 campi (incluso il ramo separato `fileformat` / `bounding`). |
| Cron `requests_cleanup` | [initialization.py](../../../initialization.py#L351) | Prima installazione (solo create) e reinstallazione (get → delete → create). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `app` | fixture | `tests/conftest.py` di restapi | Garantisce l'app context Flask richiesto dal connettore SQLAlchemy. |
| `monkeypatch` | fixture | pytest | Sostituisce `session.commit`, `celery.get_instance` e `arki.load_datasets`; ripristinati a fine test. |
| `initializer_harness_EXT` | fixture locale | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py#L258) | Rollback iniziale, snapshot `(id, name)` delle 4 tabelle, `commit → flush`, dataset sintetico uuid, recorder Celery. In teardown esegue `rollback` e **asserisce** che le tabelle siano identiche allo snapshot iniziale. |
| `_InitializerHarness_EXT` | dataclass locale | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py#L176) | `run()` istanzia l'`Initializer` reale e chiama `expire_all()`, così le letture successive vanno al DB; `commits` conta i commit. |
| `_RecordingCelery_EXT` | fake locale | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py#L149) | Stato `installed` + log `calls`. `get` restituisce il task solo se creato; `create` **fallisce** se il task esiste già (duplicato). |
| `_hide_existing_seed_rows_EXT` | helper | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py#L220) | Rinomina tutte le righe `GroupLicense` / `License` / `Attribution` nella transazione per simulare un DB non inizializzato. Le FK dei dataset reali impediscono di cancellarle. |
| `_capture_writes_EXT` | context manager | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py#L133) | Listener `before_cursor_execute` sull'engine: registra gli statement `INSERT` / `UPDATE` / `DELETE` realmente inviati. |
| `_seed_snapshot_EXT` / `_row_values_EXT` | helper | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py#L236) | Snapshot di **tutte le colonne** delle righe seed e del dataset sintetico, più `(id, name)` di ogni tabella. |
| `EXPECTED_*_EXT` | costanti | [test_initializer_seed_EXT.py](./test_initializer_seed_EXT.py) | Aspettative scritte a mano, senza importarle dal codice di produzione. Coprono gruppi e licenze completi, tutti i nomi delle attribution, `descr` / `url` di 3 attribution campione e il cron atteso. |

## 4. Analisi dettagliata di ogni test

### `test_first_run_creates_full_seed_and_installs_cron_EXT`
- **Obiettivo**: su un DB "senza seed", il primo run crea tutte le righe con i valori e le relazioni attesi.
- **Setup**: `_hide_existing_seed_rows_EXT`, con precondizione verificata: i nomi seed non sono trovabili.
- **Assert**:
  - ogni gruppo, licenza e attribution esiste **esattamente una volta** ed è una riga **nuova** (id non tra quelli nascosti);
  - gruppi: `descr`, `is_public`, `dballe_dsn`;
  - licenze: `descr`, `url` e `group_license.name`. La FK punta al gruppo **appena creato**;
  - attribution: insieme completo dei nomi + `descr` / `url` per 3 campioni, incluso `url=""`;
  - dataset: `name`, `description`, `source="arkimet"`, `category is DatasetCategories.OBS`, `fileformat`, `bounding`, licenza e attribution **nuove** tramite relazione;
  - esattamente 3 commit;
  - cron: `[get, create]` (**nessun delete**) e spec esatta (`automatic_cleanup`, `3:45`, `args=[]`).

### `test_second_run_keeps_rows_ids_and_values_EXT`
- **Obiettivo**: idempotenza reale. Due run consecutivi partendo da un DB senza seed.
- **Assert**:
  - snapshot completo (tutte le colonne + `(id, name)` per tabella) **identico** dopo il secondo run: niente duplicati, id stabili e valori invariati;
  - durante il secondo run nessun `INSERT` e nessun `UPDATE` sulle tabelle seed; l'unica scrittura tollerata è `KNOWN_CATEGORY_REWRITE_EXT`, documentata dal test xfail;
  - 6 commit totali;
  - cron: `[get, create, get, delete, create]` con un solo task installato.

### `test_second_run_on_aligned_state_writes_nothing_EXT` — `xfail(strict=True)`
- **Obiettivo**: con DB già allineato, un rerun non dovrebbe scrivere nulla.
- **Esito osservato**: fallisce con un solo statement:
  `UPDATE datasets SET category=%(category)s WHERE datasets.id = %(datasets_id)s`.
- **Causa**: [initialization.py](../../../initialization.py#L316) confronta `ds_entry.category`, un enum `DatasetCategories.OBS`, con la stringa Arkimet `"OBS"`. Il confronto è sempre `True`, quindi il dataset viene riscritto **a ogni avvio**.
- **Perché strict**: quando il bug sarà corretto, il test passerà come XPASS e la suite fallirà, segnalando di rimuovere il marker. Verificato con un mutante che corregge il confronto: `[XPASS(strict)]`.

### `test_rerun_restores_single_drifted_field_EXT` × 15
- **Obiettivo**: per ogni campo gestito, una divergenza **isolata** viene corretta sulla **stessa riga**.
- **Flusso**:
  1. run iniziale;
  2. snapshot di tutte le colonne;
  3. modifica di **un solo** campo con `flush`;
  4. rilettura dal DB per confermare il valore stale;
  5. rerun e rilettura;
  6. confronto con lo snapshot: id e **tutte** le colonne uguali.
- **Casi**:
  - `group-{descr,is_public,dballe_dsn}`;
  - `license-{descr,url,group_license_id}`;
  - `attribution-{descr,url}`;
  - `dataset-{name,description,license_id,attribution_id,category,fileformat,bounding}`.
- **Valori stale FK**: puntano ad altre righe seed esistenti (`CCBY-SA_COMPLIANT`, `CCBY-SA4.0`, `MISTRAL`), quindi i vincoli FK sono rispettati.

## 5. Call chain

```
initializer_harness_EXT
  session.rollback(); snapshot (id,name) di GroupLicense/License/Attribution/Datasets
  session.commit := flush (+ conteggio)        ← SQL reale, nessuna persistenza
  celery.get_instance := _RecordingCelery_EXT
  arki.load_datasets := [dataset sintetico uuid, category "OBS", license CCBY4.0, attribution ARPAE-SIMC]
harness.run()
  Initializer()  → query/INSERT/UPDATE reali su Postgres nella transazione del test
  session.expire_all()  → le assert rileggono dal DB
teardown
  session.rollback(); assert snapshot == snapshot iniziale
```

## 6. Comportamenti nascosti

- **`commit` sostituito da `flush`**: SQL, vincoli e FK sono reali, ma il comportamento di `COMMIT` (visibilità ad altre connessioni, eventi post-commit) non è testato. L'Initializer non ne dipende.
- **Righe "nascoste" tramite rename**: alternativa necessaria alla cancellazione, bloccata dalle FK dei dataset reali. Le righe rinominate restano nel DB transazionale e generano i warning diagnostici "in db but not in the inizializing schema": è atteso.
- **Warning sui dataset reali**: poiché Arkimet restituisce solo il dataset sintetico, l'Initializer logga un warning per ogni dataset reale "not in the arkimet config". È solo log, senza scritture.
- **Lock di riga temporanei**: durante il test le righe seed rinominate o aggiornate sono bloccate dalla transazione aperta. La durata è breve (~0,5 s per test), ma eventuali scritture concorrenti su quelle righe attenderebbero.
- **Dipendenza dal DB già seedato**: i casi drift e il test di aggiornamento usano lo stato reale di partenza (seed già presente dallo startup). La fixture parte comunque da `rollback()` e verifica l'invarianza a fine test.

## 7. Verifica di efficacia (mutation testing)

Mutanti dell'Initializer caricati **solo nel processo pytest** tramite plugin `-p`, senza modificare il sorgente:

| Mutante | Esito | Test che lo intercetta |
|---|---|---|
| Rimosso update di `fileformat` | ✅ ucciso | `drift[dataset-fileformat]` |
| `dballe_dsn` escluso dal confronto dei gruppi | ✅ ucciso | `drift[group-dballe_dsn]` |
| Lookup licenza ignorato (crea sempre) | ✅ ucciso | `second_run_keeps_rows...` (2 righe `CCBY4.0`) |
| Cron sempre creato senza delete | ✅ ucciso | `second_run_keeps_rows...` (duplicate periodic task) |
| Typo nel seed (`DBALL`) | ✅ ucciso | `first_run_creates_full_seed...` |
| `attribution_id` escluso dal confronto dei dataset | ❌ **sopravvive** | mascherato dal bug `category` |
| Bug `category` corretto | ✅ segnalato | `writes_nothing` → `XPASS(strict)` |
| Bug `category` corretto **e** `attribution_id` escluso | ✅ ucciso | `drift[dataset-attribution_id]` |

**Conclusione**: oggi i casi drift `dataset-{name,description,license_id,attribution_id,category}` passano anche se il relativo confronto viene rimosso. Il confronto `category` è sempre vero e forza il ramo di update. Dopo la correzione del bug diventano discriminanti senza modifiche ai test.

## 8. Checklist di revisione

- [ ] Decidere se correggere il confronto `category` in [initialization.py](../../../initialization.py#L316), ad esempio confrontando `ds_entry.category.name` oppure convertendo la stringa in `DatasetCategories`. Poi rimuovere lo `xfail` e `KNOWN_CATEGORY_REWRITE_EXT`.
- [ ] Confermare che la strategia `commit → flush + rollback` sia accettabile per l'isolamento sul DB condiviso di test.
- [ ] Confermare che le aspettative esplicite (`EXPECTED_*_EXT`) siano il contratto desiderato. Un cambio intenzionale al seed richiede l'aggiornamento del test.
- [ ] Valutare se aggiungere i rami di errore: config dataset incompleta, licenza/attribution inesistente, gruppo mancante per una licenza.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Fake/mock | Fixture | Può passare banalmente? |
|---|---|---|---|---|---|
| `test_first_run_creates_full_seed_and_installs_cron_EXT` | `Initializer.__init__` su DB reale | Creazione completa del seed, relazioni FK verso righe nuove, 3 commit, cron solo create | Arkimet sintetico, Celery recorder | `initializer_harness_EXT` | No (ucciso dal mutante typo) |
| `test_second_run_keeps_rows_ids_and_values_EXT` | idem | Snapshot invariato, nessun INSERT/UPDATE seed, cron delete+create | idem | idem | No (uccisi i mutanti duplicati) |
| `test_second_run_on_aligned_state_writes_nothing_EXT` | idem | Zero scritture su rerun | idem | idem | `xfail(strict)` per bug reale |
| `test_rerun_restores_single_drifted_field_EXT` ×15 | idem | Ripristino di ogni campo singolo sulla stessa riga | idem | idem | Parzialmente, per 5 casi dataset fino alla correzione del bug `category` |
