# Prompt 08 - ARCO Edge, S3 Connector, Initializer Smoke

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Chiudi la lunga coda di superfici backend emerse dall'analisi con test mirati e non invasivi.

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
- `conftest.py` e consentito se il riuso locale lo giustifica davvero; altrimenti usa moduli `_EXT.py` espliciti.
- Ogni file `_EXT.py` e ogni test/helper devono avere commenti molto verbosi su mock S3, perimetro del smoke e motivo di eventuali esclusioni.
- Non contattare S3 reale. Non modificare initializer o migration scripts.

Obiettivo ristretto:

- Estendere ARCO edge cases senza dipendere da S3 reale.
- Coprire il connector S3 con mock.
- Aggiungere smoke ragionevole per initializer/migrations senza testare ogni dettaglio di seed.

File target:

- Crea `projects/mistral/backend/tests/integration/arco/test_arco_edge_cases_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/connectors/test_s3_connector_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/initializer/test_initializer_smoke_EXT.py` solo se sostenibile senza fragilita; altrimenti documenta nel test o nella PR perche basta collect/import.
- Eventuale: crea o modifica `conftest.py` in `arco`, `connectors` o `initializer` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche `README_conftest_EXT.md` nella stessa cartella.

Vincoli della suite:

- Marker: `integration`, `deterministic`; `runtime_sensitive` solo se non puoi evitare runtime reale.
- Mockare `mistral.connectors.s3.get_instance` e `boto3.Session`.

Struttura attesa dei test:

- ARCO helpers: `guess_mime_type`, `_round_coord` numerico, stringa non convertibile e `None`.
- ARCO proxy: S3 `NoSuchKey` -> `404`, errore S3 non NoSuchKey propagato come errore server, mime type coerente, BasicAuth mancante/errata resta rifiutata.
- ARCO catalog: pagina con prefissi `.zarr/`, `.zmetadata` valido produce bounding arrotondato e license/attribution enriched; `.zmetadata` mancante mantiene fallback; unknown license/attribution non rompe risposta; pagination `IsTruncated` usa `NextContinuationToken`.
- S3 connector: missing required variables -> `ServiceUnavailable`; endpoint costruito da host/port/scheme; endpoint esplicito rispettato; verify SSL da env/variabili; `connect` fallisce se `list_buckets` fallisce; `is_connected` true/false; `disconnect` resetta client.
- Initializer smoke: import module e, se possibile, fake SQLAlchemy/celery per verificare che non installi duplicati e chiami cleanup cron con task `automatic_cleanup`. Se troppo fragile, limitarsi a collect-only e dichiarare esclusione motivata.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/arco/test_arco_edge_cases_EXT.py'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/connectors'
.mhub-venv/bin/rapydo shell backend 'pytest --collect-only tests/custom -q'
```

Criterio di completamento:

- ARCO e S3 hanno edge/error handling coperti senza rete reale.
- Initializer/migrations sono coperti almeno da collect/import o da esclusione motivata scritta nel lavoro.
- La suite resta aderente al layout rifattorizzato e alla tracciabilita `_EXT`.