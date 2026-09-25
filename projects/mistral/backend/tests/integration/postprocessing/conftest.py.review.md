# Review — `postprocessing/conftest.py` (infrastruttura di dominio)

> File di review per modulo di supporto (fixture locali). Non contiene test.
> Struttura **ADATTATA** (solo fixture, nessun test).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/conftest.py](projects/mistral/backend/tests/integration/postprocessing/conftest.py)
- **Scopo**: assemblare due **ambienti completi** (`PostprocessingEnv`) pronti all'uso per gli scenari di postprocessing: uno forecast legato al dataset `lm5`, uno observed legato al dataset `agrmet`. Ogni fixture prepara DB, utente dedicato autorizzato, cleanup e — nel caso observed — un override temporaneo di `BeDballe.LASTDAYS`.
- **Tipologia**: `conftest.py` di dominio (solo fixture locali, visibili a `integration/postprocessing/**`). Tutta la logica pesante è delegata a [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) (vedi review dedicata).

## 2. Backend realmente esercitato

Le fixture **non** invocano ancora il backend di estrazione: predispongono lo scenario. Toccano però backend reale per:

- Creazione utente + login: `create_postprocessing_user` (in `support.py`) usa i canali reali `BaseTests.create_user` / `do_login` e legge l'utente da `sqlalchemy.get_instance()`.
- Lettura dataset: `require_dataset(db, "lm5"|"agrmet")` interroga la tabella `Datasets` ([services](projects/mistral/backend/services/sqlapi_db_manager.py)) e **fa `pytest.skip`** se assente.
- Solo observed: `require_observed_lastdays()` si connette al **DB DBALLE reale** per derivare `LASTDAYS` e sovrascrive `BeDballe.LASTDAYS` ([services/dballe.py](projects/mistral/backend/services/dballe.py#L33)).

## 3. Elementi definiti

### Fixture `pp_forecast_env` → `PostprocessingEnv`
- **Dipende da**: `app`, `client`, `faker`, `cleanup_registry` (LIFO, da [tests/conftest.py](projects/mistral/backend/tests/conftest.py)).
- **Cosa fa**: `db = sqlalchemy.get_instance()`; `require_dataset(db,"lm5")` (**skip** se manca); crea `PostprocessingSupport`, un utente autorizzato al solo dataset `lm5` (`create_postprocessing_user`), registra il cleanup utente+filesystem; costruisce e **ritorna** l'`env` (`dataset_name="lm5"`).
- **Tipo**: fixture a `return` (nessun teardown proprio oltre al `cleanup_registry`).
- **Usata da**: `test_forecast_basic.py`, `test_forecast_spatial.py`, `test_forecast_chaining.py` e i 3 test forecast di `test_error_handling.py`.

### Fixture `pp_observed_env` → `PostprocessingEnv`
- **Dipende da**: `app`, `client`, `faker`, `cleanup_registry`, **`test_runtime`** (da [tests/conftest.py](projects/mistral/backend/tests/conftest.py)).
- **Cosa fa**: come sopra ma su `agrmet`; in più calcola `observed_lastdays = require_observed_lastdays()` (**skip** se `ALCHEMY_*` non configurate o se non ci sono dati observed) e crea l'`env` **dentro** `with test_runtime.override_attr(BeDballe, "LASTDAYS", observed_lastdays):`.
- **Tipo**: fixture a **`yield`**: lo `yield env` è interno al `with`, quindi l'override `LASTDAYS` resta attivo per **tutta** la durata del test e viene ripristinato al teardown.
- **Usata da**: `test_observed_postprocessing.py` e i 2 test observed di `test_error_handling.py`.

## 4. Comportamenti nascosti

- **Skip silenziosi annidati**: entrambe le fixture possono terminare in `pytest.skip` *durante il setup* (dataset assente; observed: `ALCHEMY_*` mancanti o niente dati DBALLE; più, a valle, l'archivio spare-point). Un intero file di test può quindi risultare “skipped” senza che il corpo dei test venga mai eseguito.
- **Override `LASTDAYS` solo observed e con dato reale**: il valore non è una costante ma è **derivato dai dati DBALLE reali** in `require_observed_lastdays`; la fixture observed è perciò accoppiata sia alla configurazione (`ALCHEMY_*`) sia allo stato del DB.
- **`return` vs `yield`**: solo `pp_observed_env` è generatore, perché deve mantenere vivo il context manager dell'override; `pp_forecast_env` non ha override e quindi non necessita teardown proprio.
- **Commenti `# arrange/act/assert` fuorvianti**: le fixture riportano gli stessi commenti-template dei test (“Eseguiamo l'azione sotto test…”, “Verifichiamo l'effetto osservabile…”), ma qui **non c'è act né assert**: si limita a costruire l'`env`. I commenti sono boilerplate, non descrivono il codice.
- **Utente per-scenario**: ogni test ottiene un utente nuovo, autorizzato al solo dataset richiesto (`allowed_postprocessing=True`, `open_dataset=True`, quota 1 GB); il cleanup (utente + cartella `DOWNLOAD_DIR/<uuid>`) è registrato subito.

## 5. Checklist di revisione

- [ ] Verificare che lo `skip` in setup sia il comportamento voluto e che in CI sia monitorato (un file interamente skippato non protegge nulla).
- [ ] Confermare che l'override `LASTDAYS` derivato dai dati reali sia coerente con l'estrazione observed senza reftime (`db_type="mixed"`).
- [ ] Verificare che il `test_runtime` ripristini correttamente `BeDballe.LASTDAYS` anche se il test fallisce a metà.
- [ ] Valutare se i commenti-template vadano rimossi dalle fixture per non confondere il revisore.

## 6. Possibili criticità

- **Dipendenza d'ambiente in setup**: la fixture observed apre una connessione DBALLE reale e legge dati durante l'arrange; un ambiente parziale produce skip invece di un segnale chiaro di copertura mancante.
- **Accoppiamento a dataset fissi** (`lm5`, `agrmet`): rinominare o riconfigurare i dataset disattiva silenziosamente gli interi file di test che dipendono da queste fixture.
- **Stato condiviso `BeDballe.LASTDAYS`**: l'override è globale di classe; va garantito che non si sovrapponga ad altri test observed eseguiti in parallelo.
