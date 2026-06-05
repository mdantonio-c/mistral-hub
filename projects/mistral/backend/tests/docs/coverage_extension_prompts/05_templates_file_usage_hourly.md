# Prompt 05 - Templates, File, Usage e Hourly

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Aggiungi copertura per superfici backend user-facing emerse dall'analisi e non coperte dai legacy.

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
- `conftest.py` e consentito se il riuso locale lo giustifica davvero; altrimenti usa `support_EXT.py` o fixture inline.
- Ogni file `_EXT.py` e ogni test/helper devono avere commenti molto verbosi su cleanup filesystem, monkeypatch e comportamento atteso.
- In questo prompt non usare dataset reali salvo necessità non prevista; il focus e HTTP/filesystem deterministico.

Obiettivo ristretto:

- Coprire `projects/mistral/backend/endpoints/templates.py`.
- Coprire `projects/mistral/backend/endpoints/usage.py`.
- Coprire `projects/mistral/backend/endpoints/request_hourly_report.py`.
- Se non gia completato nel prompt 02, coprire `projects/mistral/backend/endpoints/file.py`.

File target:

- Crea `projects/mistral/backend/tests/integration/templates/test_templates_listing_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/templates/test_templates_upload_delete_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/templates/support_EXT.py` locale solo se serve.
- Eventuale: crea o modifica `projects/mistral/backend/tests/integration/templates/conftest.py` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche `projects/mistral/backend/tests/integration/templates/README_conftest_EXT.md`.
- Crea `projects/mistral/backend/tests/integration/user_limits/test_usage_and_hourly_EXT.py`.
- Eventuale: `projects/mistral/backend/tests/integration/data/test_file_download_EXT.py`.

Vincoli della suite:

- Marker: `integration`, `deterministic`; `runtime_sensitive` solo se il test dipende da filesystem reale persistente oltre temp dirs.
- Usare `cleanup_registry.add_path` per directory utente e upload.
- Non invocare conversioni GDAL reali se non necessario: monkeypatch `Template.convert_to_shapefile` nei test che verificano il wiring upload geojson/zip.
- Non aggiungere fixture globali.

Struttura attesa dei test:

- Templates listing: auth required, lista grib/shp vuota, filtro format, `get_total`, `max_allowed` quando raggiunge `max_templates`.
- Upload: grib valido, zip shapefile completo, zip shapefile senza `.shx` o `.dbf` -> `400`, estensione errata -> `400`, quota superata -> `403`, max templates -> `401`.
- Get/delete: template esistente dovrebbe restituire filepath e format; template mancante `404`; delete rimuove file sidecar con stesso stem. Se emerge un bug esistente, scrivere test che documenta il comportamento atteso e segnalarlo senza cambiare codice non richiesto.
- Usage: directory utente assente -> used `0`, directory con file -> used > 0, quota uguale a `user.disk_quota`.
- Hourly: user senza `request_par_hour` -> `{}`; user con limite e richieste nell'ora corrente -> `submitted`, `total`, `remaining`.
- File download: output proprietario scaricabile, file di altro utente negato, DB entry senza file fisico `404`.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/templates'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/user_limits'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/data/test_file_download_EXT.py'
```

Criterio di completamento:

- Le superfici templates, usage/hourly e file download hanno contratti HTTP espliciti in moduli `_EXT`.
- Cleanup filesystem affidabile e locale al dominio.
- Ogni bug scoperto o skip forzato e riportato chiaramente e censito nel registro problemi, senza workaround opachi nei test.
