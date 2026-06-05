# Prompt 06 - Admin CRUD, Customizer e Models

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Copri le superfici backend emerse fuori dal focus iniziale che hanno contratti DB/API autonomi.

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
- `conftest.py` e consentito se il riuso locale lo giustifica davvero; altrimenti usa fixture inline o `support_EXT.py` locale.
- Ogni file `_EXT.py` e ogni test/helper devono avere commenti molto verbosi su cleanup DB, relazioni create e aspettative applicative.
- In questo prompt non usare dataset reali: lavora su DB/API deterministici e fixture locali.

Obiettivo ristretto:

- Coprire endpoint admin metadata in `projects/mistral/backend/endpoints/admin_*.py`.
- Coprire `projects/mistral/backend/customization.py`.
- Coprire metodi modello `AccessKey.generate` e `AccessKey.is_valid` in `projects/mistral/backend/models/sqlalchemy.py`.

File target:

- Crea `projects/mistral/backend/tests/integration/admin/test_admin_attributions_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/admin/test_admin_license_groups_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/admin/test_admin_licenses_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/admin/test_admin_datasets_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/admin/support_EXT.py` locale solo se serve.
- Eventuale: crea o modifica `projects/mistral/backend/tests/integration/admin/conftest.py` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche `projects/mistral/backend/tests/integration/admin/README_conftest_EXT.md`.
- Crea `projects/mistral/backend/tests/integration/customizer/test_user_customizer_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/services/test_access_key_service_EXT.py` per includere service e model, evitando modifiche al file legacy omonimo se esiste.

Vincoli della suite:

- Marker: `integration`, `deterministic`.
- Usa admin login tramite `BaseTests().do_login(client, None, None)` in fixture locale admin.
- Cleanup DB completo per ogni record creato, incluse relazioni dataset/license/group/attribution.
- Non testare `__repr__`.

Struttura attesa dei test:

- Admin attributions: auth admin required, create, list include datasets, update, duplicate conflict se possibile, delete, missing update/delete `404`, empty URL normalizzato a `None`.
- Admin license groups: create/list/update/delete, conflict, missing `404`, `is_public` e `dballe_dsn` preservati.
- Admin licenses: create con group, list nested group/datasets, update group, delete, conflict, missing group/license `404`; se il codice usa `.first` senza chiamata e il test lo rivela, segnalarlo.
- Admin datasets: create con license/attribution, list schema, update `sort_index` empty -> `None`, update license/attribution, delete, not found, conflict.
- Customizer: `custom_user_properties_pre` imposta default e separa `datasets`; `custom_user_properties_post` associa dataset validi e solleva `NotFound` per id mancante; `manipulate_profile` include campi custom; `get_custom_input_fields` per ADMIN/PROFILE/REGISTRATION; `get_custom_output_fields` espone tutti i campi.
- AccessKey model/service: `generate` con scadenza default/null, `is_valid` per no expiration/future/past, `is_access_key_valid` con wrong key.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/admin'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/customizer'
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/services/test_access_key_service_EXT.py'
```

Criterio di completamento:

- Le superfici admin principali hanno CRUD e errori base coperti.
- Customizer e AccessKey model hanno test deterministici in moduli `_EXT`.
- Nessuna fixture globale nuova e nessuna modifica al comportamento applicativo.
