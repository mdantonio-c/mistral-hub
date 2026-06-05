# Prompt 04 - Requests, Schedules e Task Data-Ready Edge

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Estendi i domini `requests` e `schedules` oltre i contratti legacy gia migrati.

Per avere una panoramica e basarti poi sulle azioni da intraprendere e su alcuni vincoli, leggi prima:
- `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/coverage_extension_blueprint.md`
- `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/coverage_extension_prompts/README.md`

Vincoli tassativi:

- Tratta `/home/federico/mistral/meteo-hub/untracked_stuff` come inesistente.
- Non modificare alcun file fuori da `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests`.
- Tutti i nuovi moduli devono essere `*_EXT.py`, con eccezione del filename speciale `conftest.py`.
- Se crei o modifichi `conftest.py`, la stessa cartella deve contenere o aggiornare anche `README_conftest_EXT.md` con documentazione completa delle fixture.
- Non usare `xfail`: se emerge un bug backend o un comportamento anomalo non risolvibile nel perimetro della suite, usa solo `skip` esplicito e fortemente documentato.
- Ogni bug scoperto o skip forzato introdotto dal lavoro deve aggiornare `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.
- `conftest.py` e consentito se il riuso locale nel dominio `requests`, `schedules` o `tasks` lo giustifica davvero; altrimenti usa `support_EXT.py`.
- Ogni file `_EXT.py` deve avere commenti molto verbosi che esplicitino perche si usa fake Celery/RedBeat e quali date runtime sono ammesse.
- Per dataset reali forecast valgono solo: `lm5` `2021-10-19` e `lm2.2` `2019-09-10`.
- Usa prima i dati reali forecast gia presenti a costo zero quando aggiungono copertura utile.
- Se le finestre forecast disponibili non bastano per coprire bene un ramo runtime, segnala esplicitamente quali dati aggiuntivi sarebbero utili in futuro.
- Le fixture devono essere portabili tra locale e CI: non usare la restrizione locale su `lm5` o `lm2.2` come base fissa dell'assert.

Obiettivo ristretto:

- Coprire listing/archive/clone di `projects/mistral/backend/endpoints/requests.py`.
- Coprire CRUD, validazioni e scheduled requests di `projects/mistral/backend/endpoints/schedules.py`.
- Coprire edge deterministici di `projects/mistral/backend/tasks/on_data_ready_extractions.py`.

File target:

- Crea `projects/mistral/backend/tests/integration/requests/test_requests_listing_archive_clone_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/schedules/test_schedule_api_contracts_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/schedules/test_schedule_validation_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/schedules/test_scheduled_requests_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/tasks/test_on_data_ready_task_edges_EXT.py`.
- Crea `support_EXT.py` locale solo se serve riuso nel dominio.
- Eventuale: crea o modifica `conftest.py` in `requests`, `schedules` o `tasks` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche `README_conftest_EXT.md` nella stessa cartella.

Vincoli della suite:

- Marker default: `integration`, `deterministic`; aggiungi `runtime_sensitive` solo per dataset reali nelle date ammesse.
- Non aggiungere nuovi `async_real` salvo motivazione tecnica esplicita.
- Usa fake Celery/RedBeat per create/patch schedule deterministici.
- Usa `helpers/polling.py` solo per side effect osservabili; niente `sleep`.
- Se il runtime non espone `lm5` `2021-10-19` o `lm2.2` `2019-09-10`, usa skip esplicito e leggibile.

Struttura attesa dei test:

- Requests: `GET /requests` shape, `get_total` 206, `archived=true/false`, archive PUT success, archive pending forbidden, owner mismatch, clone success con dataset specs, clone missing/foreign request.
- Schedules list/get: `GET /schedules`, `get_total`, `GET /schedules/<id>`, owner mismatch.
- Schedules create validation: no schedule setting `400`, min period `<15 minutes` `403`, opendata admin-only `403`, opendata multidataset `400`, opendata observed dataset `400`, postprocessor unauthorized `401`, push queue missing/nonexistent `403`.
- Schedules patch/delete: disable enabled periodic, disable already disabled conflict, enable disabled recreates fake RedBeat task, enable already enabled conflict, delete removes DB schedule and fake periodic task.
- Scheduled requests: `last=true` no successful request `404`, `last=false` list, `get_total` total.
- On-data-ready task edge: schedule with zero datasets skipped, multiple datasets skipped, invalid run filter decode skipped, fake Celery send failure raises `SystemError`.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/requests'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/schedules'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/tasks/test_on_data_ready_task_edges_EXT.py'
```

Criterio di completamento:

- Requests e schedules hanno contratti CRUD/API espliciti oltre al bridge opendata esistente.
- I test non dipendono da beat/broker reale per i nuovi scenari.
- I dataset storici sono gestiti con skip leggibili e con date esatte documentate nei commenti.
