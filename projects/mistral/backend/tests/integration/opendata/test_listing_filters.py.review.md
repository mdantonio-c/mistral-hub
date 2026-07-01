# Review — `test_listing_filters.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Dominio **opendata** marcato `runtime_sensitive`: 3 dei 4 test sono **silenziosamente skippabili** (vedi §6).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/opendata/test_listing_filters.py](projects/mistral/backend/tests/integration/opendata/test_listing_filters.py)
- **Scopo**: verificare l'endpoint di **listing** opendata per dataset pubblici e il parsing del parametro `q` (`run:MINUTE,HH:MM` e finestra `reftime:>=...,<=...`), incluso il caso di **lista vuota legittima** con filtri combinati.
- **Tipologia**: integrazione HTTP reale (controller + DB SQLAlchemy + parsing `q` hand-rolled + `arkimet.decode_run`). Marker: `integration`, `deterministic`, `runtime_sensitive`. Nessun mock.
- **Endpoint coperto**: `OpendataFileList.get` (`GET /datasets/<id>/opendata`).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `OpendataFileList.get` | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L36) | Dataset inesistente → `self.response(..., code=404)`; pubblico → salta l'auth; parsing `q`; query `Request.args.contains(query)` + `opendata.is_(True)`; filtro reftime **in Python**; ordinamento; check coerenza `vars`. |
| Parsing `q` (run) | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L36) | `run:MINUTE,00:00` → `query["filters"] = {"run":[{"desc":"MINUTE(00:00)"}]}` (containment JSONB). |
| Parsing `q` (reftime) | [endpoints/opendata.py](projects/mistral/backend/endpoints/opendata.py#L36) | `>=`/`<=` → `reftime["from"]`/`["to"]` (`%Y-%m-%d %H:%M`); filtro **inclusivo della finestra** (`reftime_from < from or reftime_to > to → continue`). |
| `arki.decode_run` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L621) | Decodifica reale del `run` seminato (`MINUTE`, `value` intero) per `el["run"]`. |
| `db.Request` (JSONB `args`) | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36) | Righe opendata sintetiche; `args.contains(...)` fa il match. |
| `GroupLicense.is_public` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L101) | Dataset pubblico → nessun controllo di autorizzazione. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test; chiamate **anonime** (dataset pubblico). |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py) | Teardown **LIFO**. |
| `create_listing_env` | helper locale | [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) | Crea dataset **pubblico** + 2 risultati (01/01@00:00, 02/01@12:00); **può `pytest.skip`** se manca `Attribution`. |
| `BaseTests().get_content` | helper | `restapi.tests` | Decodifica il body JSON della lista. |
| `timedelta`, `uuid4` | stdlib | — | Costruzione finestre reftime e id dataset inesistente. |

> Infrastruttura condivisa (non ridocumentata): `cleanup_registry` da [tests/conftest.py](projects/mistral/backend/tests/conftest.py); seeding utente/file da [opendata/support.py](projects/mistral/backend/tests/integration/opendata/support.py) e [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py). Cartella `runtime_sensitive`.

## 4. Analisi dettagliata di ogni test

### `test_listing_unknown_dataset_returns_404`
- **Obiettivo**: listing su `arkimet_id` inesistente → `404`.
- **Backend coinvolto**: `OpendataFileList.get`, ramo `if not ds_entry: response(code=404)`.
- **Flusso**: costruisce `missing_<uuid>` → GET.
- **Setup**: nessuno (nessun seeding). **Non usa `cleanup_registry`**.
- **Assert**: `status_code == 404`.
- **Casi coperti**: error path su dataset inesistente. **Mai skippato** (non crea dataset).

### `test_listing_filters_by_run_returns_matching_package`
- **Obiettivo**: il filtro `run` ritorna **solo** il pacchetto di quel run.
- **Backend coinvolto**: parsing `run:MINUTE,00:00` → containment JSONB; `arki.decode_run` sul pacchetto risultante.
- **Flusso**: `create_listing_env` (2 seed: run 00:00 / 12:00) → GET `?q=run:MINUTE,00:00`.
- **Setup**: `cleanup_registry`; dataset pubblico + 2 risultati reali.
- **Assert**: `200`; `len(content) == 1`; `content[0]["filename"] == seeded_results[0].filename` (il run 00:00).
- **Casi coperti**: happy path filtro run; aggancio JSONB run; **dipendenza reale da `decode_run`**.

### `test_listing_filters_by_reftime_returns_matching_package`
- **Obiettivo**: la **finestra reftime** ritorna solo il pacchetto interno alla finestra.
- **Backend coinvolto**: parsing `reftime:>=...,<=...` (`%Y-%m-%d %H:%M`); filtro Python inclusivo della finestra.
- **Flusso**: `query_from = seed[0].reftime + 1min` (esclude seed[0]), `query_to = seed[1].reftime` → GET `?q=reftime:>=<from>,<=<to>`.
- **Setup**: `cleanup_registry`; dataset pubblico + 2 risultati.
- **Assert**: `200`; `len(content) == 1`; `content[0]["filename"] == seeded_results[1].filename`.
- **Casi coperti**: happy path finestra reftime; il confine inferiore esclude il pacchetto a `00:00` perché `reftime_from < from`.

### `test_listing_filters_by_reftime_and_run_can_exclude_results`
- **Obiettivo**: filtri **combinati** reftime+run possono produrre una lista **vuota legittima** (non un errore).
- **Backend coinvolto**: containment run MINUTE(12:00) (aggancia solo seed[1]) **+** filtro reftime Python che poi lo **esclude**.
- **Flusso**: `query_from = seed[0].reftime`, `query_to = seed[1].reftime - 1min` → GET `?q=reftime:>=<from>,<=<to>;run:MINUTE,12:00`. Il run seleziona seed[1] (02/01), ma la finestra reftime arriva a `01/01 23:59` → seed[1] escluso (`reftime_to > to`).
- **Setup**: `cleanup_registry`; dataset pubblico + 2 risultati.
- **Assert**: `200`; `content == []`.
- **Casi coperti**: edge case "match vuoto ma `200`": la combinazione di un filtro JSONB (run) e di un filtro Python (reftime) può azzerare il risultato senza errore.

## 5. Call chain

```
GET /datasets/<id>/opendata?q=...  → auth.optional → OpendataFileList.get
  → Datasets.filter_by(arkimet_id).first → None? → response("Dataset not found", code=404)
  → License → GroupLicense → is_public? (sì nei test) → salta check_dataset_authorization
  → query["datasets"] = [arkimet_id]
  → parse q:
        "run:..."     → query["filters"] = {"run":[{"desc":"MINUTE(<HH:MM>)"}]}
        "reftime:..." → reftime["from"]/["to"] (datetime, %Y-%m-%d %H:%M)
  → Request.query.filter(args.contains(query), opendata.is_(True))
  → for r in risultati:
        reftime set? reftime_from < from OR reftime_to > to → continue (filtro Python)
        run → arki.decode_run(...)  ;  vars → da filters["product"]
        r.fileoutput? → el["filename"]=... ; res.append(el)
  → sort per data desc ; se vars eterogenei → ServerError(500)
  → response(res)   # lista (eventualmente [])
```

## 6. Comportamenti nascosti

- **3 test su 4 silenziosamente skippabili**: tutti quelli che passano da `create_listing_env` → `create_test_dataset` (`pytest.skip` se nessun `Attribution`). Solo `test_listing_unknown_dataset_returns_404` è immune.
- **Due filtri con motori diversi**: il **run** filtra via **containment JSONB** in DB; il **reftime** filtra **in Python** dopo la query (e con semantica "finestra inclusiva", `reftime_from < from or reftime_to > to → continue`). Questa doppia natura è la chiave del test "lista vuota".
- **`reftime` non entra nella query JSONB**: la query DB contiene solo `datasets` (+ eventuale `filters.run`); il reftime non restringe la query SQL ma solo il post-filtro.
- **Parsing `q` fragile**: usa `e.split("run:")[1]`, `ref.strip(">=")`/`strip("<=")` (rimuove **caratteri**, non prefissi) e `datetime.strptime(..., "%Y-%m-%d %H:%M")`. Funziona per gli input dei test ma è sensibile a spazi/format.
- **`run:MINUTE,00:00` → desc `MINUTE(00:00)`**: la trasformazione `val.replace(",", "(") + ")"` deve combaciare con la `desc` seminata da `_build_run_filter`; il containment JSONB richiede solo che la `desc` della query sia sottoinsieme di quella seminata (extra `style`/`value`/`active` ignorati).
- **Dipendenza reale da `decode_run`**: nel test run, `el["run"]` viene calcolato decodificando la struttura `MINUTE` (`value` intero). Se la forma seminata cambiasse, sarebbe `500`, non un mismatch di asserzione.
- **Ramo `ServerError` (vars eterogenei) non coperto**: tutti i seed hanno `vars=[]`, quindi la guardia "pacchetti con variabili diverse" non scatta mai.
- **Nessun filtro `archived` nel listing**: a differenza del download, il listing non esclude `archived=True`; nessun seed è archiviato, quindi l'asimmetria non è esercitata.

## 7. Checklist di revisione

- [ ] **Segnalare lo skip silenzioso** dei 3 test con seeding (precondizione `Attribution`).
- [ ] Confermare la semantica "finestra inclusiva" del filtro reftime (esclude i pacchetti il cui `[from,to]` esce dalla finestra) come comportamento voluto.
- [ ] Verificare la robustezza del parser `q` rispetto a spazi/format alternativi (oggi coperto solo il formato esatto dei test).
- [ ] Valutare un test che faccia scattare la guardia `ServerError` su `vars` eterogenei (oggi codice non coperto).
- [ ] Confermare che `content == []` con `200` sia il contratto desiderato (vs `404`) per filtri che non matchano.
- [ ] Considerare uno scenario `archived=True` per coprire l'asimmetria listing/download.

## 8. Possibili criticità

- **Copertura azzerabile senza preavviso** se l'ambiente non ha `Attribution`.
- **Doppio motore di filtro** (DB containment per run, Python per reftime): un refactor che unificasse o spostasse i filtri potrebbe rompere silenziosamente questi test (match vuoti "plausibili" rendono difficile distinguere un regresso da un comportamento atteso).
- **Parser `q` fragile** (`strip` su set di caratteri, split per prefisso): rischio di falsi positivi/negativi con input leggermente diversi; i test non lo stressano.
- **Dipendenza non mockata da arkimet** (`decode_run`) introdotta nel listing run-filtrato.
- **Rami non coperti**: `ServerError` su `vars` eterogenei e filtro `archived` mai esercitati.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture (incl. locali) | Skip silenzioso |
|---|---|---|---|---|---|
| `test_listing_unknown_dataset_returns_404` | `OpendataFileList.get` (404) | `404` su dataset inesistente | — | `client` | No |
| `test_listing_filters_by_run_returns_matching_package` | parsing run + containment + `decode_run` | 1 solo pacchetto per il run | — (DB+FS) | `client`, `cleanup_registry`, `create_listing_env` | **Sì** |
| `test_listing_filters_by_reftime_returns_matching_package` | finestra reftime (filtro Python) | 1 solo pacchetto nella finestra | — (DB+FS) | `client`, `cleanup_registry`, `create_listing_env` | **Sì** |
| `test_listing_filters_by_reftime_and_run_can_exclude_results` | run (DB) + reftime (Python) | lista **vuota** con `200` | — (DB+FS) | `client`, `cleanup_registry`, `create_listing_env` | **Sì** |
