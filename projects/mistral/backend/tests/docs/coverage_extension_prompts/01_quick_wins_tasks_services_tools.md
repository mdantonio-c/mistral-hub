# Prompt 01 - Quick Wins Tasks, Services, Tools

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Aggiungi solo test deterministici a basso rischio per funzioni pure e helper, senza toccare la baseline legacy della suite.

Vincoli tassativi:

- Tratta `/home/federico/mistral/meteo-hub/untracked_stuff` come inesistente.
- Non modificare alcun file fuori da `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests`.
- Ogni nuovo file deve usare il suffisso `_EXT.py`, con eccezione del filename speciale `conftest.py`.
- Se crei o modifichi `conftest.py`, la stessa cartella deve contenere o aggiornare anche `README_conftest_EXT.md` con documentazione completa delle fixture.
- Non usare `xfail`: se emerge un bug backend o un comportamento anomalo non risolvibile nel perimetro della suite, usa solo `skip` esplicito e fortemente documentato.
- Ogni bug scoperto o skip forzato introdotto dal lavoro deve aggiornare `/home/federico/mistral/meteo-hub/projects/mistral/backend/tests/docs/problems_and_bugs_discovered_in_extension.md`.
- `conftest.py` e consentito solo se il riuso locale delle fixture lo giustifica davvero; altrimenti usa `support_EXT.py` oppure fixture inline nei moduli di test.
- Ogni file `_EXT.py` e ogni test/helper nuovo devono avere commenti molto verbosi che spieghino cosa coprono e perché il fake basta.
- In questo prompt non usare dataset reali: se un caso li richiede, fermati e mantieni il test deterministico tramite fake o monkeypatch.

Obiettivo ristretto:

- Coprire i quick wins puri in `projects/mistral/backend/tasks`, `projects/mistral/backend/services` e `projects/mistral/backend/tools`.
- Non eseguire tool meteo reali, Celery reale, Rabbit reale o SMTP reale.

File target:

- Crea `projects/mistral/backend/tests/integration/tasks/test_queue_sorting_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/tasks/test_data_extraction_helpers_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/services/test_arkimet_query_parsing_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/services/test_dballe_query_parsing_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/tools/test_tool_helpers_EXT.py`.
- Se serve supporto condiviso solo tra file dello stesso dominio, crea `integration/tasks/support_EXT.py`, `integration/services/support_EXT.py` o `integration/tools/support_EXT.py`; se invece scegli `conftest.py`, aggiungi anche `README_conftest_EXT.md` nella stessa cartella. Non promuovere in `helpers/`.

Vincoli della suite:

- Marker: `pytest.mark.integration`, `pytest.mark.deterministic`.
- Nessun `sleep`.
- Nessuna fixture globale nuova.
- Segui arrange/act/assert e naming `test_<behavior>_<expected_outcome>` nei file `_EXT.py`.

Struttura attesa dei test:

- `test_queue_sorting_EXT.py`: matrice FOR/SEA/RAD/OBS, reftime recente vs vecchia, reftime naive trattata come UTC, `reftime=None` archiviata.
- `test_data_extraction_helpers_EXT.py`: `human_size`, `package_data_license` con filesystem temp, e `adapt_reftime` con fake schedule periodico giornaliero/orario e crontab base se sostenibile senza fragilità.
- `test_arkimet_query_parsing_EXT.py`: `is_filter_allowed`, `parse_reftime`, `parse_matchers`, `decode_run` valido/invalid type/invalid style.
- `test_dballe_query_parsing_EXT.py`: `from_query_to_dic`, `from_filters_to_lists`, `from_query_to_lists`, `parse_query_for_maps`, `parse_query_for_data_extraction` con `get_observed_dataset_params` monkeypatchato, `get_queries_and_dsn_list_with_itertools` e `is_query_for_pluvio_aggregations`.
- `test_tool_helpers_EXT.py`: `grid_interpolation.get_trans_type`, `spare_point_interpol.get_trans_type`, `grid_cropping.format_sub_type`, `check_template_filepath`, `check_coord_filepath` missing file, wrong format, corrupt shapefile bundle.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/tasks'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/services'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/tools'
```

Criterio di completamento:

- I nuovi test `_EXT` passano nei tre folder.
- Non è stato aggiunto alcun test root.
- Non ci sono dipendenze da runtime dataset, broker, SMTP o tool meteo reali.
