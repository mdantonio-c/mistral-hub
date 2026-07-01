# Review — `observed/conftest.py` (infrastruttura di dominio observed)

> File di review per modulo di supporto (fixture locali). Non contiene test. Struttura **ADATTATA** (niente "Call chain" o "Analisi per test").

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/observed/conftest.py](projects/mistral/backend/tests/integration/observed/conftest.py)
- **Scopo**: esporre **una** scenario valido di dati osservati per ciascuna modalità backend supportata (`dballe`, `arkimet`, `mixed`), così che i test parametrizzati possano concentrarsi sulle asserzioni e non sulla scoperta dei dati.
- **Tipologia**: `conftest.py` di dominio (solo fixture locali, visibili a `integration/observed/**`). Tutta la logica pesante è delegata a [observed/support.py](projects/mistral/backend/tests/integration/observed/support.py).

## 2. Backend realmente esercitato

Le fixture non testano direttamente: **scoprono** uno scenario interrogando il runtime reale (DBALLE live, Arkimet archive, DB SQLAlchemy) tramite `yield_observed_case` → `discover_observed_params` (vedi review di `support.py`). L'unico endpoint toccato in fase di scoperta è `GET /api/fields` ([endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py)); il `db_type` è classificato da `BeDballe.get_db_type` ([services/dballe.py](projects/mistral/backend/services/dballe.py#L117)).

## 3. Elementi definiti

| Fixture | Scope | Dipende da | Cosa produce / effetti |
|---|---|---|---|
| `dballe_observed_case` | function | `client`, `auth_headers`, `test_runtime` | `yield from yield_observed_case(..., "dballe")` → `ObservedCase` su dati **recenti** DBALLE. |
| `arkimet_observed_case` | function | `client`, `auth_headers`, `test_runtime` | `yield from yield_observed_case(..., "arkimet")` → `ObservedCase` su dati **archiviati** Arkimet. |
| `mixed_observed_case` | function | `client`, `auth_headers`, `test_runtime` | `yield from yield_observed_case(..., "mixed")` → `ObservedCase` che **attraversa** entrambi i mondi. |

- Tutte e tre usano `auth_headers` (utente **DEFAULT** condiviso, [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py)) e `test_runtime` (singleton di sessione, [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L31)).
- Le fixture **non** sono `autouse`: vengono attivate dai test tramite l'indirezione `pytest.mark.parametrize("case_fixture", ...)` + `request.getfixturevalue(case_fixture)` (vedi §4).

## 4. Comportamenti nascosti

- **Indirezione `parametrize` + `getfixturevalue`**: i test parametrizzano sul **nome** della fixture (stringhe in `ALL_CASES`/`ARCHIVE_CASES`/`RECENT_CASES`) e la risolvono a runtime. Questo `conftest.py` definisce proprio le tre fixture richiamate per nome. La conseguenza pratica è che **lo `skip` o l'errore della fixture diventa lo `skip`/errore dell'istanza del test**.
- **`yield from` + teardown via `override_attr`**: ogni fixture cede il `yield` di `yield_observed_case`, che può **patchare temporaneamente `BeDballe.LASTDAYS`** (per `dballe`/`mixed`) tramite `test_runtime.override_attr`. L'override è attivo **solo durante la vita della fixture** e ripristinato nel teardown; **non** avvolge l'esecuzione del corpo del test (importante: nei test, le richieste HTTP che richiedono quella finestra usano i propri override locali quando serve).
- **Skip silenzioso ereditato**: `discover_observed_params` fa `pytest.skip` se non trova un dataset osservato utilizzabile per quel `db_type`. Quindi **ogni** istanza parametrizzata che dipende da una di queste fixture è **silenziosamente saltabile** quando il runtime non ha dati osservati adeguati. È il principale rischio "verde per skip" del dominio.
- **Dipendenza dall'utente DEFAULT**: gli scenari `arkimet`/`mixed` producono richieste su `db_type` archiviato; il fatto che non vengano respinte con 401 dipende dal permesso `allowed_obs_archive=True` impostato di default dal customizer ([customization.py](projects/mistral/backend/customization.py#L33)).
- **Commenti decorativi**: i commenti italiani ("Prepariamo la fixture osservazioni…") sono uniformi e auto-generati; non descrivono logica specifica.

## 5. Checklist di revisione

- [ ] Confermare la comprensione dell'accoppiamento `parametrize`+`getfixturevalue`: queste fixture sono attivate **per nome**, non per dipendenza diretta.
- [ ] Verificare in CI quante istanze risultano `skipped` per assenza di scenari `dballe`/`arkimet`/`mixed`.
- [ ] Confermare che l'override `LASTDAYS` della fixture non "perda" stato tra test (è gestito da `override_attr` con ripristino in `finally`).
- [ ] Verificare che `auth_headers` (utente DEFAULT) mantenga `allowed_obs_archive=True` per gli scenari archiviati.

## 6. Possibili criticità

- **Copertura potenzialmente illusoria**: lo `skip` di discovery può azzerare interi scenari parametrizzati senza segnalazione evidente (la suite resta "verde con skip").
- **Stato condiviso**: utente DEFAULT e singleton `test_runtime` sono condivisi; l'override `LASTDAYS` è globale sulla classe `BeDballe` per la durata della fixture (mitigato dal ripristino, ma è uno stato di processo, non isolato per test).
- **Logica delegata**: tutta la complessità reale (e i rischi) vive in `support.py`; questo file è solo il "punto di aggancio" pytest. La review sostanziale va fatta su `support.py`.
