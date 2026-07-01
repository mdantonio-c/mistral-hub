# Review — `test_observations_filters.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo **runtime-sensitive** e **parametrizzato** sui tre backend osservati (`dballe`, `arkimet`, `mixed`).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/observed/test_observations_filters.py](projects/mistral/backend/tests/integration/observed/test_observations_filters.py)
- **Scopo**: verificare i filtri di `GET /api/observations` su dati osservati realmente presenti: range `reftime`, validazioni reftime parziale, filtro `networks`, bounding box (dentro/fuori), filtro `product`, prodotto sconosciuto, e combinazione di tutti i filtri.
- **Tipologia**: test di **integrazione HTTP** che leggono **dati reali** (DBALLE live, Arkimet archive, DB SQLAlchemy). Marker di modulo: `integration`, `deterministic`, `runtime_sensitive`.
- **Pattern chiave**: 10 funzioni, tutte `@pytest.mark.parametrize("case_fixture", ...)` con il **nome** di una fixture, risolta a runtime con `request.getfixturevalue(case_fixture)` (vedi §6). Genera **28 istanze** parametrizzate.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `MapsObservations.get` | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | Endpoint sotto test: bbox, parsing query, network auth, reftime, `db_type`, esecuzione query e parsing risposta. |
| `BeDballe.from_query_to_dic` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2283) | Parsa `q` in `datetimemin/max`, `network`, `product`, `license`, `timerange`. |
| `BeArkimet.from_network_to_dataset` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L278) | Mappa network→dataset; `None` → **404** "The requested network does not exists". |
| `SqlApiDbManager.check_dataset_authorization` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L562) | Autorizzazione del network richiesto; può dare **401**. |
| `BeDballe.check_access_authorization` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L196) | Coerenza network/gruppo licenza; `NetworkNotInLicenseGroup`→400, `UnexistingLicenseGroup`→400, `UnAuthorizedUser`→401. |
| `BeDballe.get_db_type` / `BeDballe.LASTDAYS` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L117) | Classifica reftime in `dballe`/`arkimet`/`mixed` con soglia mobile `LASTDAYS`; decide se serve `allowed_obs_archive`. |
| `SqlApiDbManager.get_user_permissions` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L665) | `allowed_obs_archive` per i rami archiviati (arkimet/mixed). |
| `BeDballe.parse_obs_maps_response` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2039) | Costruisce `{"descr":..., "data":[...]}`; ogni stazione ha `prod[]`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `request` | fixture | `pytest` | Usata per `getfixturevalue(case_fixture)`: risolve dinamicamente la fixture di scenario. |
| `dballe_observed_case` / `arkimet_observed_case` / `mixed_observed_case` | fixture locale | [observed/conftest.py](projects/mistral/backend/tests/integration/observed/conftest.py) | Producono un `ObservedCase` (auth + tipo db + finestra/parametri scoperti). **Possono fare `pytest.skip`** se non c'è dato utilizzabile. |
| `ALL_CASES` / `ARCHIVE_CASES` / `RECENT_CASES` | costante | [observed/support.py](projects/mistral/backend/tests/integration/observed/support.py) | Liste di `pytest.param` con i **nomi** delle fixture (`id="dballe|arkimet|mixed"`). |
| `build_reftime_query`, `build_observations_endpoint`, `fetch_observations`, `extract_products`, `require_secondary_product` | helper | [observed/support.py](projects/mistral/backend/tests/integration/observed/support.py) | Costruzione query/URL, chiamata HTTP, estrazione prodotti, **skip** se manca il secondo prodotto. |
| `auth_headers` (indiretta) | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | Utente **DEFAULT** loggato; il customizer gli assegna `allowed_obs_archive=True` ([customization.py](projects/mistral/backend/customization.py#L33)) → gli scenari `arkimet`/`mixed` non vengono respinti con 401. Iniettata dentro le fixture di scenario, non direttamente nel test. |
| `uuid4` | stdlib | `uuid` | Genera un nome network sicuramente inesistente. |

## 4. Analisi dettagliata di ogni test

### `test_reftime_range_returns_matching_products` — `ALL_CASES` (×3)
- **Obiettivo**: un range `reftime` valido restituisce dati contenenti **entrambi** i prodotti scoperti.
- **Backend coinvolto**: intero flusso `get` fino a `parse_obs_maps_response`.
- **Flusso**: `getfixturevalue` → `require_secondary_product` (skip se 1 solo prodotto) → URL con sola query reftime → 200 → `extract_products`.
- **Setup**: scenario scoperto dalla fixture; nessun cleanup.
- **Assert**: `isinstance(content, dict)`, `200`, `product_1 in products`, `product_2 in products`.
- **Casi coperti**: happy path multi-prodotto.

### `test_reftime_with_only_date_to_returns_bad_request` — `ARCHIVE_CASES` (×2: arkimet, mixed)
- **Obiettivo**: una query archiviata con **solo** estremo superiore (`<=`) deve dare **400**.
- **Backend coinvolto**: `from_query_to_dic` produce solo `datetimemax` → ramo "Reftime is missing".
- **Flusso**: `build_reftime_query(..., include_from=False)` → 400.
- **Assert**: `response.status_code == 400`.
- **Casi coperti**: error path reftime incompleto (mancante l'estremo inferiore).

### `test_reftime_with_only_date_from_returns_bad_request` — `RECENT_CASES` (×2: dballe, mixed)
- **Obiettivo**: simmetrico al precedente, con **solo** `>=` (manca l'estremo superiore) → **400**.
- **Flusso**: `include_to=False` → solo `datetimemin` → "Reftime is missing".
- **Assert**: `400`.

### `test_network_filter_returns_matching_products` — `ALL_CASES` (×3)
- **Obiettivo**: filtrando per il network scoperto i prodotti attesi restano visibili.
- **Backend coinvolto**: ramo `networks` (`from_network_to_dataset` + `check_dataset_authorization`) + query.
- **Flusso**: `require_secondary_product` → URL con `networks=<scoperto>` → 200 → prodotti presenti.
- **Assert**: `200`, `product_1 in`, `product_2 in`.

### `test_unknown_network_returns_not_found` — `ALL_CASES` (×3)
- **Obiettivo**: un network inesistente dà **404**.
- **Backend coinvolto**: `from_network_to_dataset(...) is None` → `NotFound`.
- **Flusso**: `networks=f"missing_{uuid4().hex}"` → 404.
- **Assert**: `404`. **Non** richiede secondo prodotto (nessuno skip per quel motivo).

### `test_bounding_box_filter_returns_matching_products` — `ALL_CASES` (×3)
- **Obiettivo**: una bbox valida sull'Italia (`lon 6.75–18.48`, `lat 36.62–47.12`) mantiene i prodotti.
- **Backend coinvolto**: ramo bbox (tutti e 4 i lati presenti) + query.
- **Flusso**: `require_secondary_product` → URL con bbox → 200 → prodotti presenti.
- **Assert**: `200`, entrambi i prodotti.

### `test_outside_bounding_box_returns_empty_data` — `ALL_CASES` (×3)
- **Obiettivo**: una bbox **fuori** dall'area stazioni restituisce `data == []` con **200**.
- **Backend coinvolto**: query con bbox che non interseca stazioni.
- **Flusso**: i valori sono volutamente **scambiati** (`lonmin=36.62…`, `latmin=6.75…`): la "scatola" cade su lon 36–47 / lat 6–18, lontano dall'Italia → nessuna stazione.
- **Assert**: `200`, `content["data"] == []`. **Non** richiede secondo prodotto.

### `test_product_filter_returns_only_requested_product` — `ALL_CASES` (×3)
- **Obiettivo**: filtrando per `product_1` il `product_2` **non** deve comparire.
- **Backend coinvolto**: `build_reftime_query(..., product=product_1)` aggiunge `product:` alla query.
- **Flusso**: `require_secondary_product` → 200 → `product_1 in`, `product_2 not in`.
- **Assert**: `200`, inclusione/esclusione.

### `test_unknown_product_returns_empty_data` — `ALL_CASES` (×3)
- **Obiettivo**: un codice prodotto inesistente (`B11111`) dà risposta **200 vuota** (`data == []`), non 404.
- **Backend coinvolto**: query con prodotto valido sintatticamente ma assente.
- **Assert**: `200`, `content["data"] == []`. **Non** richiede secondo prodotto.

### `test_combined_filters_return_only_requested_product` — `ALL_CASES` (×3)
- **Obiettivo**: reftime + network + bbox + product restano **mutuamente coerenti** (solo `product_1`).
- **Flusso**: `require_secondary_product` → URL con tutti i filtri (bbox Italia, network scoperto, product_1) → 200.
- **Assert**: `200`, `product_1 in`, `product_2 not in`.

## 5. Call chain

```
test → request.getfixturevalue("dballe_observed_case"|"arkimet_observed_case"|"mixed_observed_case")
     → conftest fixture → yield_observed_case(...) → discover_observed_params(...)  [può pytest.skip]
     → ObservedCase(db_type, headers, params)
test → [require_secondary_product(case)]  [può pytest.skip se product_2 is None]
     → build_observations_endpoint(query=build_reftime_query(params), ...)
     → fetch_observations(client, headers, endpoint) → client.get(...) + BaseTests().get_content()
         → MapsObservations.get
            → bbox check → from_query_to_dic(q)
            → [networks: from_network_to_dataset → check_dataset_authorization]
            → license gate → check_access_authorization
            → reftime check → get_db_type (LASTDAYS)
               → se arkimet/mixed: get_user_permissions(allowed_obs_archive)
            → get_maps_response / get_maps_response_for_mixed
            → parse_obs_maps_response → self.response(res)
     → assert status/products
```

## 6. Comportamenti nascosti

- **Indirezione `parametrize` + `getfixturevalue` (NON ovvia)**: i test sono parametrizzati sul **nome** della fixture (stringa), non sul valore. `request.getfixturevalue(case_fixture)` istanzia la fixture corrispondente solo all'esecuzione. Conseguenze: (1) la stessa batteria di assert gira su `dballe`/`arkimet`/`mixed` senza duplicare il corpo; (2) **lo `skip` della fixture diventa skip dell'istanza** del test; (3) i fallimenti di discovery appaiono come errori in fase di setup della fixture.
- **Skip silenziosi multipli (runtime-sensitive)**:
  - `dballe_observed_case` / `arkimet_observed_case` / `mixed_observed_case` chiamano `discover_observed_params`, che fa `pytest.skip` se nel runtime non c'è un dataset osservato utilizzabile per quel `db_type`. **Ogni** istanza parametrizzata può quindi sparire silenziosamente.
  - `require_secondary_product` fa `pytest.skip` quando lo scenario espone **un solo** prodotto: tutti i test "matching products" e "product filter" sono saltabili.
- **Accesso ai dati archiviati senza 401**: per gli scenari `arkimet`/`mixed` il `db_type` è archiviato e l'endpoint richiede `allowed_obs_archive`. Funziona perché l'utente DEFAULT lo ha `True` di default ([customization.py](projects/mistral/backend/customization.py#L33)); se quel default cambiasse, questi scenari darebbero 401 invece di 200.
- **Override `LASTDAYS` dentro la fixture**: per gli scenari `dballe`/`mixed` la fixture può patchare `BeDballe.LASTDAYS` (via `test_runtime.override_attr`) così che una finestra storica venga classificata come "recente". L'override avvolge solo la fase di scoperta nella fixture, **non** il corpo del test (vedi review di `conftest.py`/`support.py`).
- **bbox "fuori area" costruita per scambio coordinate**: il test outside-bbox riusa gli stessi numeri della bbox valida ma scambiando lon/lat, ottenendo una scatola geograficamente lontana — trucco non evidente leggendo solo i numeri.
- **`extract_products` naviga la struttura annidata** `data[].prod[].var`: l'assert sui prodotti dipende dalla forma prodotta da `parse_obs_maps_response`.

## 7. Checklist di revisione

- [ ] Confermare la comprensione dell'indirezione `parametrize`+`getfixturevalue`: i "3 test" sono in realtà 1 corpo × 3 scenari.
- [ ] Verificare in CI quante istanze risultano `skipped`: una suite "verde" potrebbe nascondere scenari mai eseguiti (no dato dballe/arkimet/mixed, o prodotto singolo).
- [ ] Confermare che l'utente DEFAULT mantenga `allowed_obs_archive=True`, altrimenti `arkimet`/`mixed` regrediscono a 401.
- [ ] Verificare che `B11111` resti un codice prodotto **inesistente** (oracolo "empty data").
- [ ] Verificare che la bbox "fuori area" non intersechi mai stazioni reali del runtime.
- [ ] Confermare che il prodotto sconosciuto dia **200 vuoto** (non 404), coerente con il contratto dell'endpoint.

## 8. Possibili criticità

- **Copertura potenzialmente illusoria**: con discovery o secondo prodotto assenti, gran parte delle 28 istanze può fare `skip`; il modulo può apparire "verde" pur eseguendo poco. È il rischio principale.
- **Dipendenza da seed runtime non controllato**: i test non *creano* dati osservati, li *scoprono*. La stabilità dipende dalla presenza di `agrmet` (preferito) o di un altro dataset osservato ricco di prodotti.
- **Oracoli geografici hardcoded**: le bbox sono numeri fissi tarati sull'Italia; un cambio di area dati renderebbe ambigui i test inside/outside.
- **Accoppiamento all'utente DEFAULT condiviso** e al suo permesso `allowed_obs_archive` per gli scenari archiviati.
- **`content["data"][0]` non usato qui** ma usato nei test stazione: la robustezza all'assenza di dati è demandata agli helper/`require_secondary_product`, non sempre a un guard esplicito.

## 9. Riassunto finale

| Test | Scenari | Backend | Cosa verifica | Skip silenzioso | Complessità |
|---|---|---|---|---|---|
| `test_reftime_range_returns_matching_products` | ALL ×3 | `get` happy path | 200 + entrambi i prodotti | fixture, `require_secondary_product` | Media |
| `test_reftime_with_only_date_to_returns_bad_request` | ARCHIVE ×2 | "Reftime is missing" | 400 (manca `>=`) | fixture | Bassa |
| `test_reftime_with_only_date_from_returns_bad_request` | RECENT ×2 | "Reftime is missing" | 400 (manca `<=`) | fixture | Bassa |
| `test_network_filter_returns_matching_products` | ALL ×3 | ramo `networks` | 200 + prodotti | fixture, `require_secondary_product` | Media |
| `test_unknown_network_returns_not_found` | ALL ×3 | `from_network_to_dataset` None | 404 | fixture | Bassa |
| `test_bounding_box_filter_returns_matching_products` | ALL ×3 | ramo bbox | 200 + prodotti | fixture, `require_secondary_product` | Media |
| `test_outside_bounding_box_returns_empty_data` | ALL ×3 | bbox fuori area | 200 + `data==[]` | fixture | Bassa |
| `test_product_filter_returns_only_requested_product` | ALL ×3 | filtro `product` | 200 + esclusione `product_2` | fixture, `require_secondary_product` | Media |
| `test_unknown_product_returns_empty_data` | ALL ×3 | prodotto assente | 200 + `data==[]` | fixture | Bassa |
| `test_combined_filters_return_only_requested_product` | ALL ×3 | filtri combinati | 200 + solo `product_1` | fixture, `require_secondary_product` | Media |
