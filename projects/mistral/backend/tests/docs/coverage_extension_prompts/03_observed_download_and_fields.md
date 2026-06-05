# Prompt 03 - Observed Download e Fields

Agisci come implementatore senior della suite backend Meteo-Hub Rapydo 2.4. Estendi la copertura observed senza duplicare i test GET già presenti e aggiungi il nuovo dominio `/fields`.

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
- Nuove fixture possono vivere inline, in `support_EXT.py` o in `conftest.py` se il riuso locale lo giustifica davvero.
- Riusa gli helper observed esistenti solo in lettura; ogni nuova logica locale va in file `_EXT.py`.
- Ogni file `_EXT.py` e ogni test devono avere commenti molto verbosi che dichiarino la finestra dati usata.
- Per dati reali di fase 3 valgono solo queste finestre: observed `agrmet` Arkimet `2020-03-31` e `2020-04-01`; observed `agrmet` DBALLE `2020-04-06`, principalmente `00:00`, con esattamente 4 dati alle `01:00` e `02:00`; forecast `/fields` `lm5` solo `2021-10-19`; forecast `/fields` `lm2.2` solo `2019-09-10`.
- Per `/fields` forecast non usare il setup locale come oracolo fisso di autorizzazione: la restrizione su `lm5` e `lm2.2` puo differire tra locale e CI, quindi il setup o le assertion devono restare portabili.
- Usa prima i dati reali `agrmet` già presenti a costo zero. Se non bastano per coprire correttamente un ramo importante, segnala esplicitamente quali dati ulteriori sarebbero utili in futuro.
- Per il ramo forecast di `/fields` puoi riusare in sola lettura `projects/mistral/backend/tests/helpers/dataset_window.py` per derivare una finestra valida e i metadati di run senza duplicare parsing locale.

Obiettivo ristretto:

- Coprire `MapsObservations.post` in `projects/mistral/backend/endpoints/maps_observed.py`.
- Coprire `Fields.get` in `projects/mistral/backend/endpoints/fields.py`, sia nel ramo OBS sia nel ramo FOR/Arkimet.

File target:

- Crea `projects/mistral/backend/tests/integration/observed/test_observations_download_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/observed/test_observations_edge_cases_EXT.py` solo per rami GET non già coperti.
- Crea `projects/mistral/backend/tests/integration/fields/test_fields_api_EXT.py`.
- Crea `projects/mistral/backend/tests/integration/fields/support_EXT.py` solo se servono fixture locali riusate.
- Eventuale: crea o modifica `projects/mistral/backend/tests/integration/observed/conftest.py` o `projects/mistral/backend/tests/integration/fields/conftest.py` solo se il riuso locale lo richiede, e in tal caso crea o aggiorna anche il corrispondente `README_conftest_EXT.md` nella stessa cartella.

Vincoli della suite:

- Marker: `integration`, `deterministic`, `runtime_sensitive`.
- Usa skip esplicito se DBALLE/Arkimet runtime non espone i dati nelle date ammesse.
- Nessun `sleep`; se serve attesa, usa `helpers/polling.py`.

Struttura attesa dei test:

- Observed POST: download JSON e BUFR con query valida; `output_format` invalido `400`; bbox incompleta `400`; license mancante `400`; gruppo license inesistente `400` o mismatch network/license `400` se costruibile; network inesistente `404`; network non autorizzato `401` se costruibile; `singleStation` senza `networks` `400`; `singleStation` con più network `400`; `singleStation` senza coordinate/ident `400`; archived data anonimo `401` o utente senza `allowed_obs_archive` `401`; `reliabilityCheck=true` almeno come smoke positivo se il runtime espone dati coerenti nella finestra ammessa.
- Observed GET edge: aggiungi solo rami controller non già coperti; intervallo oltre limite per anonimo/autenticato, `interval` maggiore del timerange -> `409`, `daily` imposta output valido se dati disponibili, `last` restringe ai dati recenti se scenario supportato, `stationDetails` senza `networks` `400`, `stationDetails` con piu network `400`, stazione inesistente `404` se scenario costruibile anche tentando sia `ident` sia `lat/lon`, `allStationProducts=false` limita i prodotti ai filtri richiesti se il runtime espone una stazione adatta.
- Fields OBS: map mode recente con license valida; map mode archived anonimo `401`; map mode archived con utente senza `allowed_obs_archive` `401` se costruibile in modo portabile; network inesistente `404`; network non autorizzato `401` se costruibile; license group mancante `400`; license group inesistente `400`; mismatch network/license `400`; dataset osservato inesistente `404`; bbox incompleta `400`; `onlySummaryStats`; `SummaryStats=False`; `allAvailableProducts` include solo license groups autorizzati.
- Fields FOR: dataset mode autenticato con `lm5` o `lm2.2`; dataset forecast inesistente `404`; dataset multipli con categorie diverse `400`; dataset multipli con license group diversi `400`; multi-dataset con `multim-forecast` `400`; happy path con verifica di `descriptions.leveltypes` e `descriptions.timerangetypes` quando `summarystats.c > 0`; `onlySummaryStats` anche sul ramo forecast; `SummaryStats=False` va almeno sondato esplicitamente sul forecast e, se riproduce il difetto del controller, il blocco va riportato come bug backend con skip esplicito e ben documentato, mai con `xfail`, e registrato nel file problemi.
- Nei casi runtime-sensitive scegliere `2020-04-06 00:00` come default DBALLE e usare `01:00` o `02:00` solo in test mirati che documentano esplicitamente l'aspettativa sui 4 dati disponibili.

Check minimo di validazione:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/observed/test_observations_download_EXT.py'
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/fields'
```

Criterio di completamento:

- Observed POST ha almeno un caso nominale e i principali errori di validazione/autorizzazione.
- `/fields` ha copertura per OBS/map mode, OBS dataset mode e FOR dataset mode, inclusa la verifica delle `descriptions` forecast, oppure documenta esplicitamente l'eventuale blocco backend riproducibile sul ramo forecast e lo registra nel file problemi.
- Non vengono duplicati i test GET observed già presenti se non per rami nuovi.
