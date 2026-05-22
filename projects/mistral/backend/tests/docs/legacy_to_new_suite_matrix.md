# Matrice Legacy -> Nuova Suite

## Scopo

Questa matrice traccia in modo esplicito i contratti storici coperti dai monoliti legacy del refactor e il punto della suite rifattorizzata che oggi li verifica davvero.

Regole di lettura:

- la colonna `Legacy` riporta i nomi storici dei moduli di origine; non corrisponde a file ancora presenti sotto `projects/mistral/backend/tests/`;
- la prova di copertura vive nei file `integration/` o, quando necessario, negli helper locali usati da quei test;
- la colonna `stato` distingue tra migrazione equivalente, copertura rafforzata e casi chiusi durante la validazione finale del refactor.

## Matrice

| Legacy (nome storico) | Contratto/scenario storico | Nuova suite | Stato | Note |
| --- | --- | --- | --- | --- |
| `conftest.py` | fixture auth/globali riusate dai monoliti | `conftest.py`, `integration/conftest.py`, `integration/access_key/conftest.py`, `helpers/auth.py` | coperto | le fixture comuni sono ora separate per visibilita pytest |
| `test_api_access_key.py` | GET senza login rifiutato | `integration/access_key/test_access_key_api.py` | coperto | contratto invariato |
| `test_api_access_key.py` | GET restituisce access key esistente | `integration/access_key/test_access_key_api.py` | coperto | contratto invariato |
| `test_api_access_key.py` | PATCH rigenera la key | `integration/access_key/test_access_key_api.py` | coperto | contratto invariato |
| `test_api_access_key.py` | key senza scadenza resta valida | `integration/access_key/test_access_key_api.py`, `integration/access_key/test_access_key_validation.py` | coperto | coperta sia lato API key sia lato validate |
| `test_api_access_key.py` | key scaduta e credenziali mancanti/errate sono rifiutate | `integration/access_key/test_access_key_api.py`, `integration/access_key/test_access_key_validation.py` | coperto | missing email, wrong email, wrong key, expired key |
| `test_api_access_key.py` | validate con credenziali corrette | `integration/access_key/test_access_key_validation.py` | coperto | contratto invariato |
| `test_api_arco.py` | proxy ARCO richiede autenticazione | `integration/arco/test_arco_proxy.py` | coperto | contratto invariato |
| `test_api_arco.py` | proxy ARCO restituisce zgroup per utente autorizzato | `integration/arco/test_arco_proxy.py` | coperto | contratto invariato |
| `test_api_arco.py` | catalogo ARCO espone metadati dataset | `integration/arco/test_arco_catalog.py` | coperto | contratto invariato |
| `test_api_data.py` | endpoint `/api/data` richiede autenticazione | `integration/data/test_data_endpoint_auth.py` | coperto | contratto invariato |
| `test_api_dataset.py` | catalogo e dettaglio dataset pubblici visibili senza login | `integration/dataset/test_dataset_visibility.py` | coperto/rafforzato | il dataset pubblico e scoperto dinamicamente invece di essere hardcoded |
| `test_api_dataset.py` | dataset inesistente restituisce `404` | `integration/dataset/test_dataset_visibility.py` | coperto | contratto invariato |
| `test_api_dataset.py` | dataset privato visibile solo a utente autorizzato | `integration/dataset/test_dataset_authorization.py` | coperto | contratto invariato |
| `test_api_dataset.py` | dataset privato negato a utente non autorizzato | `integration/dataset/test_dataset_authorization.py` | coperto | contratto invariato |
| `test_api_dataset.py` | `open_dataset=False` nasconde il catalogo pubblico all'utente | `integration/dataset/test_dataset_visibility.py` | coperto | contratto invariato |
| `test_delete_pending_request.py` | delete manuale di pending request ammessa dopo il grace period | `integration/requests/test_delete_pending_request.py` | coperto | non usa piu stato cross-test |
| `test_delete_pending_request.py` | delete manuale rifiutata dentro il grace period | `integration/requests/test_delete_pending_request.py` | coperto | non usa piu `self.save/get` |
| `test_delete_pending_request.py` | `automatic_cleanup` elimina le request stale ma non quelle recenti | `integration/requests/test_delete_pending_request.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | query senza license o con reftime incompleto restituiscono `400` | `integration/observed/test_observations_auth.py`, `integration/observed/test_observations_filters.py` | coperto/rafforzato | i vecchi assert impliciti sono ora espliciti |
| `test_api_maps_observed.py` | query observed valide restituiscono prodotti attesi su `dballe`, `arkimet`, `mixed` | `integration/observed/test_observations_filters.py` | coperto | discovery runtime dinamico mantenuto |
| `test_api_maps_observed.py` | filtro `network` mantiene solo il network richiesto | `integration/observed/test_observations_filters.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | bounding box restringe i risultati e bbox esterno restituisce dataset vuoto | `integration/observed/test_observations_filters.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | filtro `product` e filtri combinati restringono i prodotti | `integration/observed/test_observations_filters.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | `onlyStations` restituisce sole stazioni | `integration/observed/test_observations_station_details.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | `stationDetails` gestisce caso valido, network ignoto e coordinate mancanti | `integration/observed/test_observations_station_details.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | `/data/ready` su export non filesystem restituisce `1` | `integration/data_ready/test_base_cases.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule per dataset non abilitato viene rifiutata | `integration/data_ready/test_base_cases.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule inattiva o senza flag `on-data-ready` non genera request | `integration/data_ready/test_base_cases.py` | coperto/rafforzato | la nuova suite asserisce esplicitamente assenza di request |
| `test_api_data_ready.py` | mismatch su dataset/modello non attiva la schedule | `integration/data_ready/test_run_mismatch.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | mismatch su `runhour` non attiva la schedule | `integration/data_ready/test_run_mismatch.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | crontab completo non corrispondente non genera request | `integration/data_ready/test_crontab.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | crontab parziale non corrispondente non genera request | `integration/data_ready/test_crontab.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule giornaliera genera una nuova request dopo un giorno | `integration/data_ready/test_periodic.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule ogni due giorni genera una nuova request solo a scadenza completa | `integration/data_ready/test_periodic.py` | coperto | copre sia caso positivo sia caso anticipato negativo |
| `test_api_opendata.py` | listing/download su dataset inesistente restituisce `404` | `integration/opendata/test_listing_filters.py`, `integration/opendata/test_download.py` | coperto | contratto invariato |
| `test_api_opendata.py` | dataset privato negato o consentito in base all'autorizzazione | `integration/opendata/test_authorization.py` | coperto | contratto invariato |
| `test_api_opendata.py` | filtri di listing per `run`, `reftime` e combinazione esclusiva | `integration/opendata/test_listing_filters.py` | coperto | il setup e ora seedato e focalizzato |
| `test_api_opendata.py` | download valida query `reftime`/`run`, zip multiple e file singolo | `integration/opendata/test_download.py` | coperto | contratto invariato |
| `test_api_opendata.py` | file opendata inesistente non esiste sul filesystem | `integration/opendata/test_download.py` | coperto/rafforzato | il nuovo test verifica sia `404` API sia assenza del file richiesto |
| `test_api_opendata.py` | schedule `crontab` reale produce request opendata visibile in listing e scaricabile | `integration/schedules/test_schedule_opendata_bridge.py` | chiuso in questa verifica | nuovo test `test_crontab_schedule_publishes_opendata_package`, marcato `async_real` e `runtime_sensitive` |
| `test_postprocessing_extraction.py` | failure per postprocessor sconosciuto | `integration/postprocessing/test_error_handling.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | forecast semplice produce output | `integration/postprocessing/test_forecast_basic.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | forecast `derived_variables` fallisce con input incompleti e riesce con input completi | `integration/postprocessing/test_error_handling.py`, `integration/postprocessing/test_forecast_basic.py` | coperto | il successo preserva anche campi indipendenti |
| `test_postprocessing_extraction.py` | forecast `statistic_elaboration` fallisce con input invalidi e riesce con input completi | `integration/postprocessing/test_error_handling.py`, `integration/postprocessing/test_forecast_basic.py` | coperto | il successo verifica anche `stepRange` e campo `sp` |
| `test_postprocessing_extraction.py` | interpolazione spaziale, template, crop e spare-point | `integration/postprocessing/test_forecast_spatial.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | chaining forecast multiplo con output JSON | `integration/postprocessing/test_forecast_chaining.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed semplice produce output | `integration/postprocessing/test_observed_postprocessing.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed `derived_variables` fallisce con input incompleti | `integration/postprocessing/test_error_handling.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed `derived_variables` riesce con input completi | `integration/postprocessing/test_observed_postprocessing.py` | chiuso in questa verifica | nuovo test `test_observed_derived_variables_create_output` |
| `test_postprocessing_extraction.py` | observed `statistic_elaboration` fallisce con input incompleti | `integration/postprocessing/test_error_handling.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed `statistic_elaboration` riesce con input completi | `integration/postprocessing/test_observed_postprocessing.py` | chiuso in questa verifica | nuovo test `test_observed_statistic_elaboration_creates_output` |
| `test_postprocessing_extraction.py` | chaining observed multiplo esporta JSON | `integration/postprocessing/test_observed_postprocessing.py` | coperto | contratto invariato |
| `test_arpaesimc.sh` | smoke toolchain meteo (`arki-query`, `dballe`, `vg6d_transform`, `v7d_transform`, `dbadb`) | `test_arpaesimc.sh` | coperto | file invariato, ancora unico punto corretto |

## Visibilita marker della nuova suite

La matrice resta centrata sui contratti legacy, ma la visibilita operativa della nuova suite ora e questa:

| Nuova suite | Marker | Note |
| --- | --- | --- |
| `integration/access_key/`, `integration/arco/`, `integration/data/`, `integration/requests/` | `integration`, `deterministic` | contratti stabili senza dipendenze runtime forti o dispatch asincrono reale |
| `integration/dataset/`, `integration/data_ready/`, `integration/observed/`, `integration/opendata/`, `integration/postprocessing/` | `integration`, `deterministic`, `runtime_sensitive` | i test restano deterministici nel flusso, ma dipendono da dataset, servizi o stato runtime presenti |
| `integration/schedules/test_schedule_opendata_bridge.py::test_on_data_ready_schedule_publishes_opendata_package` | `integration`, `deterministic`, `runtime_sensitive` | usa path inline/in-process, ma poggia comunque su fixture e dati runtime |
| `integration/schedules/test_schedule_opendata_bridge.py::test_crontab_schedule_publishes_opendata_package` | `integration`, `async_real`, `runtime_sensitive` | aspetta la catena reale `celerybeat -> broker -> worker` |

Finche la CI backend non introduce selezioni `-m`, questi marker non escludono nulla: servono a rendere leggibile la suite e a preparare un futuro split del workflow.

## Esito della verifica finale

- non restano gap funzionali aperti rispetto ai contratti esplicitamente verificati dai moduli legacy di origine;
- il bridge storico `schedule crontab -> request opendata -> listing/download` ora e coperto in modo diretto sotto `integration/schedules/`;
- i success path observed per `derived_variables` e `statistic_elaboration` sono ora coperti in modo esplicito sotto `integration/postprocessing/`;
- eventuali limiti residui vanno letti come note operative del runtime o, quando serve contesto storico, nel piano di refactor mantenuto in `projects/mistral/backend/tests/docs/piano_refactoring_suite_test.md`; non rappresentano buchi di migrazione `legacy -> nuova suite` ne skip funzionali ancora aperti nel runtime corrente.# Matrice Legacy -> Nuova Suite

## Scopo

Questa matrice traccia in modo esplicito i contratti storici coperti dai file legacy in `data/user_repo/old_tests/as_is_tests/` e il punto della suite rifattorizzata che oggi li verifica davvero.

Regole di lettura:

- i file root `test_*.py` sotto `projects/mistral/backend/tests/` non valgono come prova di copertura: sono shim legacy intenzionali;
- la prova di copertura vive nei file `integration/` o, quando necessario, nei helper locali usati da quei test;
- la colonna `stato` distingue tra migrazione equivalente, copertura rafforzata e casi chiusi durante questa verifica finale.

## Matrice

| Legacy | Contratto/scenario storico | Nuova suite | Stato | Note |
| --- | --- | --- | --- | --- |
| `conftest.py` | fixture auth/globali riusate dai monoliti | `conftest.py`, `integration/conftest.py`, `integration/access_key/conftest.py`, `helpers/auth.py` | coperto | le fixture comuni sono ora separate per visibilita pytest |
| `test_api_access_key.py` | GET senza login rifiutato | `integration/access_key/test_access_key_api.py` | coperto | contratto invariato |
| `test_api_access_key.py` | GET restituisce access key esistente | `integration/access_key/test_access_key_api.py` | coperto | contratto invariato |
| `test_api_access_key.py` | PATCH rigenera la key | `integration/access_key/test_access_key_api.py` | coperto | contratto invariato |
| `test_api_access_key.py` | key senza scadenza resta valida | `integration/access_key/test_access_key_api.py`, `integration/access_key/test_access_key_validation.py` | coperto | coperta sia lato API key sia lato validate |
| `test_api_access_key.py` | key scaduta e credenziali mancanti/errate sono rifiutate | `integration/access_key/test_access_key_api.py`, `integration/access_key/test_access_key_validation.py` | coperto | missing email, wrong email, wrong key, expired key |
| `test_api_access_key.py` | validate con credenziali corrette | `integration/access_key/test_access_key_validation.py` | coperto | contratto invariato |
| `test_api_arco.py` | proxy ARCO richiede autenticazione | `integration/arco/test_arco_proxy.py` | coperto | contratto invariato |
| `test_api_arco.py` | proxy ARCO restituisce zgroup per utente autorizzato | `integration/arco/test_arco_proxy.py` | coperto | contratto invariato |
| `test_api_arco.py` | catalogo ARCO espone metadati dataset | `integration/arco/test_arco_catalog.py` | coperto | contratto invariato |
| `test_api_data.py` | endpoint `/api/data` richiede autenticazione | `integration/data/test_data_endpoint_auth.py` | coperto | contratto invariato |
| `test_api_dataset.py` | catalogo e dettaglio dataset pubblici visibili senza login | `integration/dataset/test_dataset_visibility.py` | coperto/rafforzato | il dataset pubblico e scoperto dinamicamente invece di essere hardcoded |
| `test_api_dataset.py` | dataset inesistente restituisce `404` | `integration/dataset/test_dataset_visibility.py` | coperto | contratto invariato |
| `test_api_dataset.py` | dataset privato visibile solo a utente autorizzato | `integration/dataset/test_dataset_authorization.py` | coperto | contratto invariato |
| `test_api_dataset.py` | dataset privato negato a utente non autorizzato | `integration/dataset/test_dataset_authorization.py` | coperto | contratto invariato |
| `test_api_dataset.py` | `open_dataset=False` nasconde il catalogo pubblico all'utente | `integration/dataset/test_dataset_visibility.py` | coperto | contratto invariato |
| `test_delete_pending_request.py` | delete manuale di pending request ammessa dopo il grace period | `integration/requests/test_delete_pending_request.py` | coperto | non usa piu stato cross-test |
| `test_delete_pending_request.py` | delete manuale rifiutata dentro il grace period | `integration/requests/test_delete_pending_request.py` | coperto | non usa piu `self.save/get` |
| `test_delete_pending_request.py` | `automatic_cleanup` elimina le request stale ma non quelle recenti | `integration/requests/test_delete_pending_request.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | query senza license o con reftime incompleto restituiscono `400` | `integration/observed/test_observations_auth.py`, `integration/observed/test_observations_filters.py` | coperto/rafforzato | i vecchi assert impliciti sono ora espliciti |
| `test_api_maps_observed.py` | query observed valide restituiscono prodotti attesi su `dballe`, `arkimet`, `mixed` | `integration/observed/test_observations_filters.py` | coperto | discovery runtime dinamico mantenuto |
| `test_api_maps_observed.py` | filtro `network` mantiene solo il network richiesto | `integration/observed/test_observations_filters.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | bounding box restringe i risultati e bbox esterno restituisce dataset vuoto | `integration/observed/test_observations_filters.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | filtro `product` e filtri combinati restringono i prodotti | `integration/observed/test_observations_filters.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | `onlyStations` restituisce sole stazioni | `integration/observed/test_observations_station_details.py` | coperto | contratto invariato |
| `test_api_maps_observed.py` | `stationDetails` gestisce caso valido, network ignoto e coordinate mancanti | `integration/observed/test_observations_station_details.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | `/data/ready` su export non filesystem restituisce `1` | `integration/data_ready/test_base_cases.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule per dataset non abilitato viene rifiutata | `integration/data_ready/test_base_cases.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule inattiva o senza flag `on-data-ready` non genera request | `integration/data_ready/test_base_cases.py` | coperto/rafforzato | la nuova suite asserisce esplicitamente assenza di request |
| `test_api_data_ready.py` | mismatch su dataset/modello non attiva la schedule | `integration/data_ready/test_run_mismatch.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | mismatch su `runhour` non attiva la schedule | `integration/data_ready/test_run_mismatch.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | crontab completo non corrispondente non genera request | `integration/data_ready/test_crontab.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | crontab parziale non corrispondente non genera request | `integration/data_ready/test_crontab.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule giornaliera genera una nuova request dopo un giorno | `integration/data_ready/test_periodic.py` | coperto | contratto invariato |
| `test_api_data_ready.py` | schedule ogni due giorni genera una nuova request solo a scadenza completa | `integration/data_ready/test_periodic.py` | coperto | copre sia caso positivo sia caso anticipato negativo |
| `test_api_opendata.py` | listing/download su dataset inesistente restituisce `404` | `integration/opendata/test_listing_filters.py`, `integration/opendata/test_download.py` | coperto | contratto invariato |
| `test_api_opendata.py` | dataset privato negato o consentito in base all'autorizzazione | `integration/opendata/test_authorization.py` | coperto | contratto invariato |
| `test_api_opendata.py` | filtri di listing per `run`, `reftime` e combinazione esclusiva | `integration/opendata/test_listing_filters.py` | coperto | il setup è ora seedato e focalizzato |
| `test_api_opendata.py` | download valida query `reftime`/`run`, zip multiple e file singolo | `integration/opendata/test_download.py` | coperto | contratto invariato |
| `test_api_opendata.py` | file opendata inesistente non esiste sul filesystem | `integration/opendata/test_download.py` | coperto/rafforzato | il nuovo test verifica sia `404` API sia assenza del file richiesto |
| `test_api_opendata.py` | schedule `crontab` reale produce request opendata visibile in listing e scaricabile | `integration/schedules/test_schedule_opendata_bridge.py` | chiuso in questa verifica | nuovo test `test_crontab_schedule_publishes_opendata_package`, marcato `async_real` e `runtime_sensitive` |
| `test_postprocessing_extraction.py` | failure per postprocessor sconosciuto | `integration/postprocessing/test_error_handling.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | forecast semplice produce output | `integration/postprocessing/test_forecast_basic.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | forecast `derived_variables` fallisce con input incompleti e riesce con input completi | `integration/postprocessing/test_error_handling.py`, `integration/postprocessing/test_forecast_basic.py` | coperto | il successo preserva anche campi indipendenti |
| `test_postprocessing_extraction.py` | forecast `statistic_elaboration` fallisce con input invalidi e riesce con input completi | `integration/postprocessing/test_error_handling.py`, `integration/postprocessing/test_forecast_basic.py` | coperto | il successo verifica anche `stepRange` e campo `sp` |
| `test_postprocessing_extraction.py` | interpolazione spaziale, template, crop e spare-point | `integration/postprocessing/test_forecast_spatial.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | chaining forecast multiplo con output JSON | `integration/postprocessing/test_forecast_chaining.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed semplice produce output | `integration/postprocessing/test_observed_postprocessing.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed `derived_variables` fallisce con input incompleti | `integration/postprocessing/test_error_handling.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed `derived_variables` riesce con input completi | `integration/postprocessing/test_observed_postprocessing.py` | chiuso in questa verifica | nuovo test `test_observed_derived_variables_create_output` |
| `test_postprocessing_extraction.py` | observed `statistic_elaboration` fallisce con input incompleti | `integration/postprocessing/test_error_handling.py` | coperto | contratto invariato |
| `test_postprocessing_extraction.py` | observed `statistic_elaboration` riesce con input completi | `integration/postprocessing/test_observed_postprocessing.py` | chiuso in questa verifica | nuovo test `test_observed_statistic_elaboration_creates_output` |
| `test_postprocessing_extraction.py` | chaining observed multiplo esporta JSON | `integration/postprocessing/test_observed_postprocessing.py` | coperto | contratto invariato |
| `test_arpaesimc.sh` | smoke toolchain meteo (`arki-query`, `dballe`, `vg6d_transform`, `v7d_transform`, `dbadb`) | `test_arpaesimc.sh` | coperto | file invariato, ancora unico punto corretto |

## Visibilita marker della nuova suite

La matrice resta centrata sui contratti legacy, ma la visibilita operativa della nuova suite ora e questa:

| Nuova suite | Marker | Note |
| --- | --- | --- |
| `integration/access_key/`, `integration/arco/`, `integration/data/`, `integration/requests/` | `integration`, `deterministic` | contratti stabili senza dipendenze runtime forti o dispatch asincrono reale |
| `integration/dataset/`, `integration/data_ready/`, `integration/observed/`, `integration/opendata/`, `integration/postprocessing/` | `integration`, `deterministic`, `runtime_sensitive` | i test restano deterministici nel flusso, ma dipendono da dataset, servizi o stato runtime presenti |
| `integration/schedules/test_schedule_opendata_bridge.py::test_on_data_ready_schedule_publishes_opendata_package` | `integration`, `deterministic`, `runtime_sensitive` | usa path inline/in-process, ma poggia comunque su fixture e dati runtime |
| `integration/schedules/test_schedule_opendata_bridge.py::test_crontab_schedule_publishes_opendata_package` | `integration`, `async_real`, `runtime_sensitive` | aspetta la catena reale `celerybeat -> broker -> worker` |

Finche la CI backend non introduce selezioni `-m`, questi marker non escludono nulla: servono a rendere leggibile la suite e a preparare un futuro split del workflow.

## Esito della verifica finale

- non restano gap funzionali aperti rispetto ai contratti esplicitamente verificati dai moduli legacy di origine;
- il bridge storico `schedule crontab -> request opendata -> listing/download` ora e coperto in modo diretto sotto `integration/schedules/`;
- i success path observed per `derived_variables` e `statistic_elaboration` sono ora coperti in modo esplicito sotto `integration/postprocessing/`;
- eventuali limiti residui vanno letti come note operative del runtime o, quando serve contesto storico, nel piano di refactor mantenuto in `projects/mistral/backend/tests/docs/piano_refactoring_suite_test.md`; non rappresentano buchi di migrazione `legacy -> nuova suite` ne skip funzionali ancora aperti nel runtime corrente.