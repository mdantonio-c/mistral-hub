# Review — `test_observations_station_details.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo **runtime-sensitive** e **parametrizzato** sui tre backend osservati (`dballe`, `arkimet`, `mixed`).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/observed/test_observations_station_details.py](projects/mistral/backend/tests/integration/observed/test_observations_station_details.py)
- **Scopo**: verificare le viste **station-only** (`onlyStations`) e **station-details** (`stationDetails`) di `GET /api/observations`: soppressione prodotti in modalità solo-stazioni, dettaglio per stazione nota, controllo network valido anche in modalità dettaglio, e 400 quando mancano le coordinate.
- **Tipologia**: test di **integrazione HTTP** su **dati reali**. Marker di modulo: `integration`, `deterministic`, `runtime_sensitive`.
- **Pattern chiave**: 4 funzioni, tutte `@pytest.mark.parametrize("case_fixture", ALL_CASES)` risolte con `request.getfixturevalue(...)` → **12 istanze** (`dballe`/`arkimet`/`mixed`).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `MapsObservations.get` | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | Blocco `stationDetails`: richiede `networks` (1 solo), `ident` **o** (`lat` e `lon`); imposta `query_station_data` e ricalcola il gruppo licenza via `get_license_group`. |
| `onlyStations` (param) | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | Passato a `get_maps_response`; la risposta espone stazioni con `prod == []`. |
| `BeArkimet.from_network_to_dataset` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L278) | Network sconosciuto → `None` → **404**. |
| `SqlApiDbManager.get_license_group` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L546) | Ricava il gruppo licenza del dataset di stazione per coerenza con la query. |
| `BeDballe.parse_obs_maps_response` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2039) | Costruisce `data[].stat` (con `lat`/`lon`) e `data[].prod[]`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `request` | fixture | `pytest` | `getfixturevalue(case_fixture)`: risolve lo scenario. |
| `dballe_/arkimet_/mixed_observed_case` | fixture locale | [observed/conftest.py](projects/mistral/backend/tests/integration/observed/conftest.py) | `ObservedCase`; **possono `pytest.skip`**. |
| `ALL_CASES` | costante | [observed/support.py](projects/mistral/backend/tests/integration/observed/support.py) | Nomi delle 3 fixture di scenario. |
| `build_reftime_query`, `build_observations_endpoint`, `fetch_observations` | helper | [observed/support.py](projects/mistral/backend/tests/integration/observed/support.py) | Costruzione query/URL e chiamata HTTP. |
| `fetch_station_sample` | helper | [observed/support.py](projects/mistral/backend/tests/integration/observed/support.py) | **Esegue una prima query observed reale** (asserisce 200 + dict nel setup) e ne estrae `lat`/`lon` della prima stazione. |
| `auth_headers` (indiretta) | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | Utente DEFAULT con `allowed_obs_archive=True` ([customization.py](projects/mistral/backend/customization.py#L33)) → scenari archiviati non respinti. |

## 4. Analisi dettagliata di ogni test

### `test_only_stations_returns_entries_without_products` — `ALL_CASES` (×3)
- **Obiettivo**: con `onlyStations` la lista stazioni non contiene dettagli prodotto.
- **Backend coinvolto**: `get` con `onlyStations=True` → `get_maps_response` → `parse_obs_maps_response`.
- **Flusso**: URL con sola query reftime + `onlyStations=true` → 200.
- **Assert**: `isinstance(content, dict)`, `200`, `content["data"][0]["prod"] == []`.
- **Casi coperti**: contratto della modalità solo-stazioni. **Attenzione**: l'assert indicizza `data[0]` **senza guard**: se lo scenario, pur scoperto, non restituisse stazioni in questa specifica chiamata, sarebbe `IndexError` (errore, non skip) — vedi §8.

### `test_station_details_returns_success_for_known_station` — `ALL_CASES` (×3)
- **Obiettivo**: `stationDetails` ha successo per una stazione **scoperta** da una query valida.
- **Backend coinvolto**: blocco `stationDetails` (networks=1, lat/lon presenti) + query meteogramma.
- **Flusso**: `fetch_station_sample` (prima query reale → `lat`/`lon` della prima stazione) → seconda chiamata con `stationDetails=true`, `networks=<scoperto>`, `lat`/`lon`.
- **Setup**: `fetch_station_sample` **asserisce 200 e dict nel suo interno** (un fallimento qui appare come errore di setup).
- **Assert**: `200`, `content is not None`.
- **Casi coperti**: happy path dettaglio stazione. Assert volutamente **debole** (`is not None`).

### `test_station_details_with_unknown_network_returns_not_found` — `ALL_CASES` (×3)
- **Obiettivo**: anche in modalità dettaglio, un network inesistente dà **404**.
- **Backend coinvolto**: ramo `networks` (loop autorizzazione) → `from_network_to_dataset(None)` → `NotFound` **prima** della logica stazione.
- **Flusso**: `fetch_station_sample` (per ottenere lat/lon realistici) → chiamata con `networks="network_does_not_exist"`, `stationDetails=true`, lat/lon → 404.
- **Assert**: `404`.
- **Nota**: il 404 nasce dal **network** sconosciuto, non dalla stazione mancante (quel ramo è coperto — e problematico — nel modulo edge cases EXT).

### `test_station_details_without_coordinates_returns_bad_request` — `ALL_CASES` (×3)
- **Obiettivo**: `stationDetails` senza `lat`/`lon` (né `ident`) dà **400**.
- **Backend coinvolto**: `stationDetails` → `if not ident: if not lat or not lon: raise BadRequest("Parameters to get station details are missing")`.
- **Flusso**: URL con `networks=<scoperto>`, `stationDetails=true`, **senza** coordinate → 400.
- **Assert**: `400`. **Non** usa `fetch_station_sample` (nessuna prima query).

## 5. Call chain

```
test → request.getfixturevalue(<case_fixture>)  → ObservedCase  [può pytest.skip]
     → [fetch_station_sample(client, case)]      → prima GET observed reale (assert 200+dict) → lat/lon
     → build_observations_endpoint(query, networks?, lat?, lon?, only_stations?/station_details?)
     → fetch_observations → client.get(...)
        → MapsObservations.get
           → [networks loop: from_network_to_dataset → check_dataset_authorization]   (unknown → 404)
           → stationDetails block: networks==1? lat/lon o ident? (mancanti → 400) → get_license_group
           → license gate → check_access_authorization → reftime → get_db_type
           → get_maps_response(onlyStations=...) → parse_obs_maps_response → self.response(res)
     → assert
```

## 6. Comportamenti nascosti

- **Indirezione `parametrize` + `getfixturevalue`**: identica al modulo filters. I 4 corpi girano su 3 scenari (12 istanze); lo `skip` della fixture diventa skip dell'istanza.
- **Doppia chiamata HTTP per i test che usano `fetch_station_sample`**: due dei quattro test eseguono **prima** una query observed reale per ricavare coordinate plausibili, poi la query sotto test. La prima query **asserisce nel setup** (200 + dict): un problema dell'endpoint può presentarsi come errore di arrange invece che come fallimento del test.
- **`stationDetails` ricalcola il gruppo licenza**: il controller, in modalità dettaglio, **sovrascrive** `query["license"]` con `get_license_group(station_dataset).name`. Comportamento non visibile dal test ma rilevante per capire perché la coerenza network/licenza non esplode in questi casi.
- **Skip silenziosi**: l'unico canale di skip è la fixture di scenario (`discover_observed_params`). Questo modulo **non** usa `require_secondary_product`, quindi non salta per "prodotto singolo".
- **Assert deboli/fragili**: `content is not None` (test 2) verifica pochissimo; `data[0]` senza guard (test 1) assume almeno una stazione nella risposta.
- **Accesso archiviato**: per `arkimet`/`mixed` serve `allowed_obs_archive` dell'utente DEFAULT (`True` di default via customizer).

## 7. Checklist di revisione

- [ ] Confermare la comprensione dell'indirezione `parametrize`+`getfixturevalue` (4 corpi × 3 scenari = 12 istanze).
- [ ] Verificare in CI il numero di istanze `skipped`: la copertura reale dipende dalla presenza di scenari osservati.
- [ ] Valutare se l'assert `content is not None` di `test_station_details_returns_success_for_known_station` sia troppo debole per certificare il contratto dettaglio.
- [ ] Aggiungere/valutare un guard per `content["data"][0]` in `onlyStations` (rischio `IndexError` se la risposta è vuota).
- [ ] Confermare che il 404 del test "unknown network" derivi dal network e non da altra causa (l'ordine dei controlli lo garantisce).
- [ ] Confermare `allowed_obs_archive=True` per l'utente DEFAULT (scenari archiviati).

## 8. Possibili criticità

- **`IndexError` invece di skip/assert leggibile**: `content["data"][0]["prod"]` presuppone almeno una stazione; se uno scenario scoperto restituisse `data == []` per la modalità `onlyStations`, il test crasherebbe in modo poco diagnostico anziché fallire/saltare in modo pulito.
- **Assert poco stringente** nel test happy-path dettaglio (`is not None`): un payload degenere ma non nullo passerebbe.
- **Copertura condizionata dal runtime**: come per filters, molte istanze possono `skip` se mancano dati `dballe`/`arkimet`/`mixed`.
- **Assert nel setup di `fetch_station_sample`**: i fallimenti dell'endpoint nella prima query appaiono come errori di fixture, più difficili da triagare.
- **Il 404 "stazione inesistente" NON è qui**: la modalità dettaglio con stazione assente (ma network valido) è demandata al modulo edge cases EXT, dove emerge un problema di backend (ramo `NotFound` di fatto irraggiungibile).

## 9. Riassunto finale

| Test | Scenari | Backend | Cosa verifica | Skip silenzioso | Complessità |
|---|---|---|---|---|---|
| `test_only_stations_returns_entries_without_products` | ALL ×3 | `onlyStations` | 200 + `data[0].prod == []` | fixture | Bassa |
| `test_station_details_returns_success_for_known_station` | ALL ×3 | blocco `stationDetails` | 200 + `content is not None` | fixture | Media |
| `test_station_details_with_unknown_network_returns_not_found` | ALL ×3 | `from_network_to_dataset` None | 404 | fixture | Bassa |
| `test_station_details_without_coordinates_returns_bad_request` | ALL ×3 | "Parameters to get station details are missing" | 400 | fixture | Bassa |
