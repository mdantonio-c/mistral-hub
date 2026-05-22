# Guida Finale Della Suite Test Backend Meteo-Hub

## Scopo

Questo documento e il punto di ingresso principale per capire la suite test backend di Meteo-Hub dopo il refactor strutturale.

Se devi lavorare oggi sulla suite, parti da qui. La documentazione mantenuta della suite e concentrata in questa cartella `docs/` e in `projects/mistral/backend/tests/README.md`.

## Documenti da usare davvero

Usa questi riferimenti in questo ordine:

1. `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
   - panoramica corrente della suite, struttura finale e metodo di validazione;
2. `projects/mistral/backend/tests/README.md`
   - mappa locale della cartella `tests`, con spiegazione concreta di `conftest.py`, `helpers/`, `integration/` e dei path `tests/custom/...` visti dal container;
3. `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`
   - matrice esplicita `legacy -> nuova suite` per i contratti migrati dai monoliti storici;
4. `projects/mistral/backend/tests/docs/piano_refactoring_suite_test.md`
   - rationale storico del refactor, utile solo quando serve ricostruire il percorso che ha portato alla struttura attuale.

## Stato corrente in una pagina

Il refactor strutturale della suite backend e chiuso e validato nel runtime corrente.

In pratica questo significa:

- i vecchi monoliti principali sono stati sostituiti da test organizzati per dominio sotto `projects/mistral/backend/tests/integration/`;
- gli helper globali contengono solo riuso cross-area o infrastruttura di suite;
- la logica di dominio singolo vive in moduli locali come `integration/<area>/support.py`;
- il `conftest.py` globale contiene solo fixture davvero trasversali, mentre i `conftest.py` locali limitano la visibilita delle fixture al sottoalbero giusto;
- il root di `projects/mistral/backend/tests/` non contiene piu moduli `test_*.py`: oggi espone solo file globali di suite, `docs/`, `helpers/`, `integration/` e lo smoke script `test_arpaesimc.sh`.

La fase successiva non e piu il refactor della suite esistente, ma l'eventuale estensione della copertura verso endpoint, services e task che non erano coperti nemmeno nei test storici.

## Cosa e stato fatto

Il refactor non e stato un semplice spostamento di file. Ha introdotto una struttura piu leggibile e meno fragile.

I risultati pratici sono questi:

- i test `data_ready`, `opendata`, `postprocessing`, `observed`, `requests`, `access_key`, `arco`, `data`, `dataset` e `schedules` sono ora separati per area funzionale;
- il setup ripetitivo di utenti, dataset, request, schedule, file e polling e stato spostato in helper mirati;
- le dipendenze d'ordine e l'uso di stato condiviso implicito sono stati rimossi dai punti piu fragili della suite;
- i vecchi `sleep()` sono stati sostituiti da polling osservabile nei punti rilevanti del refactor;
- la copertura storica dei monoliti e stata riallineata e tracciata in una matrice esplicita.

## Struttura finale della suite

### 1. Root della suite

Percorso host:

- `projects/mistral/backend/tests/...`

Percorso visto dal container backend:

- `tests/custom/...`

Nel root stanno solo:

- `README.md`, con il manuale pratico della suite;
- `docs/`, con la documentazione mantenuta della suite;
- `conftest.py`, con fixture globali di suite come `test_runtime`, `test_ctx` e `cleanup_registry`;
- `__init__.py`, che marca la suite come package Python;
- `helpers/`, con il riuso cross-area;
- `integration/`, con i test veri organizzati per dominio;
- `test_arpaesimc.sh`, smoke script shell per la toolchain meteo di base.

### 2. Helpers globali

La cartella `helpers/` contiene solo infrastruttura riusabile tra piu aree.

Esempi:

- `helpers/runtime.py`: runtime di sessione e contesto per-test;
- `helpers/cleanup.py`: registry LIFO per teardown affidabile;
- `helpers/auth.py`: utenti temporanei e header di autenticazione;
- `helpers/polling.py`: attesa osservabile senza `sleep` fissi;
- `helpers/datasets.py`: supporto per scegliere un dataset pubblico realmente presente nel runtime;
- `helpers/celery_fakes.py`: stand-in Celery usati nei test che devono restare locali o inline;
- `helpers/data_ready.py`, `helpers/schedules.py`, `helpers/dataset_window.py`: cluster condiviso tra `data_ready` e `schedules`.

Regola pratica: se una funzione serve a un solo dominio, non resta in `helpers/`; vive nel dominio che la usa.

### 3. Aree di integrazione

I test reali vivono sotto `integration/` e sono organizzati per dominio:

- `access_key`
- `arco`
- `data`
- `data_ready`
- `dataset`
- `observed`
- `opendata`
- `postprocessing`
- `requests`
- `schedules`

Dentro ogni area puoi trovare fino a tre tipi di file:

- `conftest.py`: fixture locali valide solo in quel sottoalbero;
- `support.py` o moduli equivalenti: builder, seed helper, parser e assert di dominio;
- `test_*.py`: scenari veri e propri, ciascuno focalizzato su un contratto leggibile.

## Come pytest vede la suite

Il flusso di caricamento e semplice se lo leggi per livelli:

1. Pytest parte da `tests/custom/` dentro il container backend.
2. Carica `tests/custom/conftest.py` e rende visibili le fixture globali.
3. Se il file raccolto e sotto `tests/custom/integration/`, carica anche `tests/custom/integration/conftest.py`.
4. Se il test appartiene a un dominio con un proprio `conftest.py`, carica anche quello.
5. I test usano fixture e helper per preparare lo scenario, eseguire una sola azione e verificare il contratto.
6. Il cleanup avviene in teardown tramite `cleanup_registry` o `test_ctx`.

La conseguenza importante e questa: la posizione del `conftest.py` decide la visibilita delle fixture. Per questo la suite separa nettamente fixture globali, fixture condivise del sottoalbero `integration/` e fixture locali di area.

## Come validare le modifiche

La regola operativa e: partire sempre dal check piu stretto che puo provare il comportamento toccato.

Ordine consigliato:

1. file o test specifico toccato;
2. cartella dell'area toccata;
3. collect-only piu ampio se hai toccato helper o wiring condivisi;
4. controlli editoriali o mirati quando hai modificato solo documentazione.

Comandi tipici:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/access_key/test_access_key_api.py'
```

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/postprocessing'
```

```bash
.mhub-venv/bin/rapydo shell backend 'pytest --collect-only tests/custom'
```

```bash
.mhub-venv/bin/rapydo shell backend 'pytest tests/custom -m "integration and not async_real" -q -rs'
```

```bash
.mhub-venv/bin/rapydo shell backend 'pytest tests/custom -m "async_real" -q -rs'
```

La suite registra i marker `integration`, `deterministic`, `async_real` e `runtime_sensitive`. Servono a dare visibilita operativa e a preparare un'eventuale futura separazione della CI, ma non cambiano il job corrente finche il workflow backend non introduce filtri `-m`.

## Cosa copre oggi la suite

La suite rifattorizzata copre i contratti principali che prima erano dispersi nei monoliti storici:

- autenticazione e ciclo di vita delle access key;
- proxy e catalogo ARCO;
- protezione dell'endpoint `/api/data`;
- visibilita e autorizzazione dei dataset;
- trigger `data_ready`, mismatch, crontab e periodic scheduling;
- query observed con filtri, station details e scenari `dballe` / `arkimet` / `mixed`;
- listing e download opendata;
- postprocessing forecast e observed, inclusi error handling, chaining e scenari spaziali;
- cleanup di pending requests;
- bridge `schedule -> request opendata -> listing/download` nell'area `schedules`.

Per la corrispondenza scenario per scenario con i moduli legacy, usa la matrice in `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`.

## Cosa resta aperto

Sul piano del refactor strutturale non restano failure funzionali aperti nel runtime corrente.

Resta una decisione operativa di manutenzione:

1. decidere se mantenere in CI i dataset forecast storici `lm5` e `lm2.2`, che richiedono ancora un utente esplicitamente autorizzato per alcuni probe e schedule.

Questo punto non rende il refactor incompleto; e una decisione di semplificazione futura del runtime di test.

## Documentazione mantenuta

I file mantenuti per capire e usare la suite oggi sono questi:

- `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
- `projects/mistral/backend/tests/README.md`
- `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`
- `projects/mistral/backend/tests/docs/piano_refactoring_suite_test.md`

Per lo stato corrente della suite backend non ci sono piu riferimenti operativi mantenuti verso altre cartelle `docs/` del repository.