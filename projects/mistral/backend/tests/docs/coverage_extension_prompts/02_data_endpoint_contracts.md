# Prompt 02 - Contratti POST Data e File Download

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Estendi il dominio `integration/data` per coprire il contratto HTTP di `POST /data` e il download `/data/<filename>` senza toccare i moduli legacy esistenti.

Per avere una panoramica e basarti poi sulle azioni da intraprendere e su alcuni vincoli, leggi prima:
- `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/coverage_extension_blueprint.md`
- `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/coverage_extension_prompts/README.md`

Vincoli tassativi:

- Tratta `/home/federico/mistral/meteo-hub/untracked_stuff` come inesistente.
- Non modificare alcun file fuori da `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests`.
- Tutti i nuovi moduli devono essere `*_EXT.py`, con eccezione del filename speciale `conftest.py`.
- Non modificare `test_data_endpoint_auth.py`; se serve integrare il dominio, affianca moduli `_EXT.py` separati.
- Se crei o modifichi `conftest.py`, la stessa cartella deve contenere o aggiornare anche `README_conftest_EXT.md` con documentazione completa delle fixture.
- Non usare `xfail`: se emerge un bug backend o un comportamento anomalo non risolvibile nel perimetro della suite, usa solo `skip` esplicito e fortemente documentato.
- Ogni bug scoperto o skip forzato introdotto dal lavoro deve aggiornare `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.
- `conftest.py` e consentito se il dominio `integration/data` ne trae un vantaggio reale; altrimenti usa `support_EXT.py` o fixture inline.
- Ogni file `_EXT.py` deve avere commenti molto verbosi su scenario, fake usati, cleanup e motivi dell'assenza di modifiche alla baseline.
- Preferisci i dati reali forecast gia presenti a costo zero quando aggiungono copertura reale utile; usa fake per quota e size count quando bastano o quando il dato reale non aggiunge valore.
- Se un caso runtime reale forecast e inevitabile, usa solo `lm2.2` il `2019-09-10` o `lm5` il `2021-10-19`, documentalo nei commenti del test e mantieni fixture/helper portabili tra locale e CI.
- Non usare l'eventuale restrizione locale su `lm5` o `lm2.2` come oracolo fisso di autorizzazione: il test deve passare sia localmente sia in CI.

Obiettivo ristretto:

- Coprire validazioni e side effect osservabili di `projects/mistral/backend/endpoints/data.py` senza lanciare worker reali.
- Coprire `projects/mistral/backend/endpoints/file.py` per ownership e file mancanti.

File target:

- Lascia intatto `projects/mistral/backend/tests/integration/data/test_data_endpoint_auth.py`.
- Crea `projects/mistral/backend/tests/integration/data/test_data_endpoint_submission_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/data/test_data_endpoint_validation_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/data/test_file_download_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/data/support_EXT.py` solo se necessario al dominio.
- Eventuale: crea o modifica `projects/mistral/backend/tests/integration/data/conftest.py` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche `projects/mistral/backend/tests/integration/data/README_conftest_EXT.md`.

Vincoli della suite:

- Marker: `integration`, `deterministic`; aggiungi `runtime_sensitive` solo se il test dipende davvero da dataset reali nelle finestre ammesse.
- Usa fake Celery/Rabbit locali o `helpers/celery_fakes.py`; non usare worker reali.
- Non promuovere fixture in `tests/integration/conftest.py`.
- Cleanup via `cleanup_registry` o `test_ctx`.
- Se le finestre `lm2.2` o `lm5` non bastano per un contratto runtime importante, segnala nel lavoro quali dati aggiuntivi servirebbero in futuro.

Struttura attesa dei test:

- Happy path `POST /data` con fake Celery: dataset valido, request record creato, task name `data_extract`, queue/routing coerenti con `queue_sorting`, response `202` con `request_id` e `task_id` se fake lo espone.
- Errori HTTP: dataset inesistente `404`, dataset con formati diversi `400`, license group diverso `400`, output_format invalid schema `400`, output_format incompatibile con grib `400`, postprocessor non autorizzato `401`, only_reliable non supportato `400`.
- Push: queue utente mancante/non esistente -> `403`, con Rabbit fake positivo salva `pushing_queue`.
- Observed quota: se si usa fake di `get_observed_data_size_count` e quota utente bassa, verificare `403` senza DBALLE reale.
- File download: file output proprietario scaricato, file non proprietario negato, fileoutput DB presente ma file assente -> `404`.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/data'
```

Criterio di completamento:

- Il dominio `integration/data` copre autenticazione, submission, validazioni principali, push e file download tramite moduli `_EXT` separati.
- Nessun worker reale e nessuna estrazione meteo pesante sono necessari.
- I test seguono lo schema arrange/act/assert della suite e commentano in modo esplicito ogni fake o limite runtime.
