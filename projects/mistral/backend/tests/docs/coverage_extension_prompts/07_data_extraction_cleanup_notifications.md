# Prompt 07 - Data Extraction, Cleanup, Quota e Notifications

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Aggiungi copertura mirata dei rami task ad alto rischio senza duplicare gli happy path postprocessing gia esistenti.

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
- `conftest.py` e consentito se il riuso locale lo giustifica davvero; altrimenti usa `support_EXT.py`.
- Ogni file `_EXT.py` e ogni test/helper devono avere commenti molto verbosi su side effect, fake usati, cleanup e motivazione del mancato uso di runtime reale.
- Non usare SMTP/Rabbit reali. Non eseguire estrazioni meteo reali se il contratto testato e quota/notification/cleanup.
- Se una branch richiedesse davvero dati runtime, usa solo le finestre gia documentate nel README del prompt pack, sfruttando prima i dati reali gia presenti a costo zero e commentandoli in modo esplicito.
- Se quelle finestre non bastano per coprire bene il ramo, segnala nel lavoro quali dati aggiuntivi sarebbero utili in futuro.

Obiettivo ristretto:

- Estendere `projects/mistral/backend/tasks/requests_cleanup.py` oltre il caso pending stale.
- Coprire helper e rami side-effect di `projects/mistral/backend/tasks/data_extraction.py`: quota, cleanup, duplicate data-ready, notifications, AMQP.

File target:

- Crea `projects/mistral/backend/tests/integration/tasks/test_requests_cleanup_expiration_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/tasks/test_data_extraction_quota_and_notifications_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/tasks/support_EXT.py` con fake SMTP/Rabbit/Celery/Popen solo se riusato.
- Eventuale: crea o modifica `projects/mistral/backend/tests/integration/tasks/conftest.py` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche `projects/mistral/backend/tests/integration/tasks/README_conftest_EXT.md`.

Vincoli della suite:

- Marker: `integration`, `deterministic`; `runtime_sensitive` solo se usi filesystem reale fuori temp utente.
- Monkeypatch `time.sleep` a no-op nei test retry email.
- Cleanup via `cleanup_registry`.

Struttura attesa dei test:

- `automatic_cleanup`: request completata scaduta viene archiviata se `requests_expiration_delete=False`; viene cancellata se `True`; request completata recente resta; request gia archiviata resta; user con expiration disabilitata ignorato; file `.tmp` orfano oltre grace cancellato; output orfano oltre grace cancellato; file recente non cancellato.
- `check_user_quota`: stima sopra `max_output_size` solleva `MaxOutputSizeExceeded`; quota disco insufficiente solleva `DiskQuotaException`; con `schedule_id` disabilita schedule e cancella periodic task fake; con `opendata=True` non applica limiti user quota.
- Duplicate data-ready in `data_extract`: se ultima request success ha stessa reftime, non crea nuovo output e non fallisce.
- `notify_by_email`: payload subject/body, retry con sleep no-op, nessuna eccezione quando primo invio fallisce e successivo riesce.
- `notify_by_amqp_queue`: payload include status/reftime; su success include filename e download URL.
- `package_data_license`: tar contiene output e `LICENSE`, file output originale rimosso.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/tasks/test_requests_cleanup_expiration_EXT.py'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/tasks/test_data_extraction_quota_and_notifications_EXT.py'
```

Criterio di completamento:

- I rami cleanup/quota/notification hanno assert su DB, filesystem o payload fake.
- Nessun side effect verso servizi esterni reali.
- Non viene duplicato il flusso postprocessing gia coperto da `integration/postprocessing`.
