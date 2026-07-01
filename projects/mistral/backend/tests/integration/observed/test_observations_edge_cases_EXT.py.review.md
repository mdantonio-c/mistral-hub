# Review — `test_observations_edge_cases_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** (Prompt 03) sui rami **controller-only** di `GET /api/observations` non già coperti dalla baseline.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/observed/test_observations_edge_cases_EXT.py](projects/mistral/backend/tests/integration/observed/test_observations_edge_cases_EXT.py)
- **Scopo**: coprire limiti di intervallo (`MAX_REQ_DAYS`/`MAX_REQ_DAYS_AUTHENTICATED`), conflitto `interval`/`timerange` (409), `daily`, `last`, e i rami `stationDetails` (senza/multi network, stazione inesistente, `allStationProducts=false`).
- **Tipologia**: test di **integrazione HTTP** su **dati reali** con finestra DBALLE `agrmet` **fissa** (`2020-04-06 00:00–01:00`). Marker di modulo: `integration`, `deterministic`, `runtime_sensitive`.
- **Finestra dati fissa**: i rami positivi usano `agrmet DBALLE 2020-04-06`; i limiti di durata usano date sintetiche **solo** per fallire prima dell'accesso ai dati.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `MapsObservations.get` | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | Rami `MAX_REQ_DAYS`, `Conflict` interval/timerange, `daily`, `last`, blocco `stationDetails`, `allStationProducts`. |
| `BeDballe.get_db_type` / `LASTDAYS` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L117) | Senza override una data 2020 è **arkimet**; con override è **dballe**. |
| `SqlApiDbManager.get_user_permissions` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L665) | `allowed_obs_archive` (rilevante per il test 409, vedi §6). |
| `BeDballe.parse_obs_maps_response` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2039) | **Ritorna sempre** `{"descr":..., "data":[...]}` (dict non vuoto): centrale per il caso "stazione inesistente" (vedi §6, **EDGE-001**). |
| `MapsObservations.get` via `/fields` | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | Probe `_require_dballe_product` / `_require_station_coordinates`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `auth_headers` | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py) | Utente DEFAULT (`allowed_obs_archive=True` via [customization.py](projects/mistral/backend/customization.py#L33)). |
| `test_runtime` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L31) | `override_attr(BeDballe, "LASTDAYS", ...)`. |
| `_dballe_window_override` | helper locale | (file) | Classifica `2020-04-06` come dballe per i soli test positivi. |
| `_require_dballe_product` | helper locale | (file) | Probe `/fields`; **`pytest.skip`** se non 200 o nessun prodotto. |
| `_require_station_coordinates` | helper locale | (file) | Esegue una query reale e ricava `lat`/`lon`; **`pytest.skip`** se nessuna stazione. |
| `_extract_products` | helper locale | (file) | Estrae i `var` dei prodotti dalla struttura annidata. |
| `_get_observations` / `_url` / `_parse_response` | helper locale | (file) | Costruzione URL + GET + parsing. |

Nessun mock dei dati; l'unica patch è la soglia `LASTDAYS`. Nessuna scrittura DB.

## 4. Analisi dettagliata di ogni test

### `test_observations_anonymous_interval_over_three_days_returns_unauthorized`
- **Obiettivo**: anonimo, intervallo **>3 giorni** → **401**.
- **Backend coinvolto**: ramo `requested_days > MAX_REQ_DAYS` con `user` assente. Avviene **prima** della selezione `db_type`.
- **Flusso**: `q` su 4 giorni (06→10 aprile), senza header → 401.
- **Assert**: `401`. **Nessun** override/probe, **nessuno** skip.

### `test_observations_authenticated_interval_over_ten_days_returns_unauthorized`
- **Obiettivo**: autenticato, intervallo **>10 giorni** → **401**.
- **Backend coinvolto**: ramo `requested_days > MAX_REQ_DAYS_AUTHENTICATED`.
- **Flusso**: `q` su 11 giorni (06→17 aprile), `auth_headers` → 401.
- **Assert**: `401`. **Nessun** override/probe.

### `test_observations_interval_greater_than_timerange_returns_conflict`
- **Obiettivo**: `interval` minore del `timerange` richiesto → **409**.
- **Backend coinvolto**: ramo finale `interval` → `Conflict`. **Dipendenza nascosta**: questo controllo è **dopo** il gate archivio; con la finestra 2020-04-06 senza override `db_type=arkimet`, quindi il 409 è raggiunto **solo perché** l'utente DEFAULT ha `allowed_obs_archive=True` (vedi §6).
- **Flusso**: `q` con `timerange:1,7200,10800` (interval implicito 2h) + `interval=1` → `2 > 1` → 409.
- **Assert**: `409`. **Nessun** override (volutamente arkimet), **nessuno** skip.

### `test_observations_daily_returns_valid_payload_on_dballe_window`
- **Obiettivo**: `daily=true` produce payload valido sulla finestra DBALLE.
- **Backend coinvolto**: ramo `daily` (calcola `timerange` su tempo ITA) → query DBALLE.
- **Flusso**: `_require_dballe_product` (**skip**) → GET `daily=true` dentro `_dballe_window_override`.
- **Assert**: `200`, `isinstance(content, dict)`, `"data" in content`. **Skippabile** via probe.

### `test_observations_last_smoke_returns_valid_payload_on_dballe_window`
- **Obiettivo**: smoke `last=true` sulla finestra DBALLE.
- **Flusso**: probe (**skip**) → GET `last=true` con override → 200.
- **Assert**: `200`, dict, `"data" in content`. Il commento del test riconosce che con **un solo giorno** DBALLE l'oracolo storico non è rinforzabile (smoke). **Skippabile**.

### `test_observations_station_details_without_networks_returns_bad_request`
- **Obiettivo**: `stationDetails=true` senza `networks` (anche con `lat`/`lon`) → **400** ("Parameter networks is missing").
- **Nota**: la `q` contiene `network:agrmet`, ma il controllo usa il **parametro** `networks` (assente), non il network dentro `q`. **Nessun** probe.
- **Assert**: `400`.

### `test_observations_station_details_with_multiple_networks_returns_bad_request`
- **Obiettivo**: `stationDetails=true` con `"agrmet or agrmet"` → **400** (`len != 1`).
- **Flusso**: `_require_station_coordinates` (probe+override, **skip**) per ottenere `lat`/`lon` realistici → GET con 2 network → 400. Il controllo `len != 1` scatta **prima** del `db_type`, quindi il 400 non dipende dall'override.
- **Assert**: `400`. **Skippabile** solo per via del probe in arrange.

### `test_observations_station_details_unknown_station_returns_not_found` — **EDGE-001 (skippabile)**
- **Obiettivo**: `stationDetails` su stazione **inesistente** (network valido) → atteso **404**.
- **Backend coinvolto**: il 404 dovrebbe venire da `if not res and stationDetails: raise NotFound("Station data not found")`. **Ma** `parse_obs_maps_response` ritorna **sempre** un dict non vuoto → `not res` è **sempre False** → quel ramo è di fatto **codice morto** (vedi §6/§8).
- **Flusso difensivo a 3 stadi**: (1) prova con `ident="missing-station-ext"`; (2) se `200` con `data` vuoto, riprova con `lat`/`lon` lontani dalla stazione reale; (3) se ancora `200` vuoto → **`pytest.skip`** ("backend returns an empty 200 payload instead").
- **Assert**: `404` **solo** se il backend lo costruisce; altrimenti **skip**.
- **Casi coperti**: edge/contract negativo che **nel backend attuale non si verifica**; il test documenta onestamente l'assenza del 404 saltando.

### `test_observations_all_station_products_false_limits_station_details_products`
- **Obiettivo**: `allStationProducts=false` mantiene **solo** il prodotto richiesto nel dettaglio stazione.
- **Backend coinvolto**: ramo `if "product" in q and not allStationProducts: query_station_data["product"] = ...`.
- **Flusso**: `_require_dballe_product` + `_require_station_coordinates` (**skip**) → GET `stationDetails=true`, `allStationProducts=false`, `product:<scoperto>` → 200.
- **Assert**: `200`; se `products` vuoto → **skip**; altrimenti `products <= {product}`.

## 5. Call chain

```
GET /api/observations?q=...&...   (auth o anonimo)
  → MapsObservations.get
     → bbox → from_query_to_dic(q)
     → [networks param? loop auth]
     → reliabilityCheck
     → stationDetails: networks richiesto / ==1 / ident|lat&lon → 400
     → license gate → check_access_authorization
     → reftime → requested_days > MAX_REQ_DAYS(_AUTHENTICATED)?  → 401   [test 1,2]
     → get_db_type (LASTDAYS) → archive gate (allowed_obs_archive)
     → daily (timerange ITA)                                      [test 4]
     → interval < timerange? → Conflict 409                       [test 3, dopo archive gate]
     → get_maps_response(...) → parse_obs_maps_response  (ritorna SEMPRE dict non vuoto)
     → if not res and stationDetails → NotFound   ← MAI vero (EDGE-001)
     → self.response(res)

probe (test 4,5,7,8,9): GET /api/fields?q=<DBALLE_QUERY>  dentro LASTDAYS override → skip se vuoto
```

## 6. Comportamenti nascosti

- **EDGE-001 — `NotFound("Station data not found")` irraggiungibile**: `parse_obs_maps_response` costruisce sempre `response = {"descr": ..., "data": ...}` e lo ritorna; essendo un dict con chiavi, `not res` è **sempre False**. Quindi `if not res and stationDetails` non scatta mai e il backend, per una stazione inesistente, risponde **200 con `data` vuoto** invece di 404. Il test `..._unknown_station_...` lo riconosce e fa `pytest.skip`. **Conseguenza**: il contratto "404 stazione inesistente" **non è verificato**; è un probabile bug di backend mascherato da skip.
- **Override `LASTDAYS` selettivo**: applicato solo ai test positivi (`daily`, `last`, probe). I test di limite/conflitto **non** lo usano: il 409 (test 3) si appoggia volutamente alla classificazione `arkimet`.
- **Il 409 dipende dal permesso archivio dell'utente DEFAULT**: il controllo `interval` è **dopo** il gate archivio; con `db_type=arkimet` (nessun override) il 409 è raggiungibile solo perché l'utente DEFAULT ha `allowed_obs_archive=True`. Se quel default cambiasse, il test riceverebbe **401** invece di 409. (Non verificabile dal solo corpo del test; dipende da [customization.py](projects/mistral/backend/customization.py#L33).)
- **`network` dentro `q` ≠ parametro `networks`**: nei test stationDetails la `q` contiene `network:agrmet`, ma i controlli usano il **parametro** `networks`. Il 400 "Parameter networks is missing" scatta anche se `q` cita un network.
- **Skip silenziosi multipli**: `_require_dballe_product` e `_require_station_coordinates` possono saltare 5 dei 9 test (4,5,7,8,9). Il test 8 ha **in più** lo skip EDGE-001.
- **Limiti di durata prima del `db_type`**: i test 1 e 2 falliscono al gate `MAX_REQ_DAYS` **prima** di qualsiasi accesso dati → deterministici, niente skip, niente dipendenza archivio.
- **`daily` calcola il `timerange` su orario italiano** (CET/CEST) e ri-esegue la query per l'ora precedente: comportamento non ovvio del controller, qui solo "smoke".

## 7. Checklist di revisione

- [ ] **EDGE-001**: decidere se il backend debba davvero restituire **404** per stazione inesistente in `stationDetails` (oggi è 200 vuoto per `not res` sempre falso). Finché non si corregge, quel contratto resta **verificato solo come skip**.
- [ ] Confermare che il 409 (test 3) sia il contratto atteso **anche** con l'utente DEFAULT che ha accesso archivio; valutare se forzare `dballe` con override per isolare il 409 dalla logica archivio.
- [ ] Verificare in CI quanti dei 5 test "positivi/coordinate" risultano `skipped`.
- [ ] Confermare `MAX_REQ_DAYS=3` e `MAX_REQ_DAYS_AUTHENTICATED=10` come soglie reali.
- [ ] Verificare che `_require_station_coordinates` produca coordinate stabili nel runtime (i "miss" a `+20°` non devono finire fuori range né su un'altra stazione).

## 8. Possibili criticità

- **Bug di backend mascherato (EDGE-001)**: il ramo `NotFound("Station data not found")` è morto; il test lo aggira con uno skip invece di fallire. Un reviewer potrebbe leggere "test del 404" e non accorgersi che il 404 **non avviene mai**.
- **Fragilità del 409 rispetto ai permessi**: il test conflitto attraversa il gate archivio; il suo esito dipende da una proprietà dell'utente DEFAULT estranea al concetto di "interval vs timerange".
- **Copertura condizionata dal runtime**: cinque test possono `skip` per assenza della finestra DBALLE agrmet; più lo skip EDGE-001.
- **Smoke deboli** (`daily`, `last`, `allStationProducts`): verificano forma/stato `200` ma poco del comportamento specifico (il commento del test su `last` lo ammette).
- **Date fisse 2020**: come per il download EXT, l'intero modulo è ancorato a `agrmet 2020-04-06`.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Patch | Skip silenzioso |
|---|---|---|---|---|
| `..._anonymous_interval_over_three_days_...` | `MAX_REQ_DAYS` (anon) | 401 (>3gg) | — | No |
| `..._authenticated_interval_over_ten_days_...` | `MAX_REQ_DAYS_AUTHENTICATED` | 401 (>10gg) | — | No |
| `..._interval_greater_than_timerange_...` | `Conflict` interval/timerange | 409 (dopo gate archivio) | — | No (ma dipende da archivio DEFAULT) |
| `..._daily_returns_valid_payload_...` | ramo `daily` | 200 + `data` | `LASTDAYS` | sì (probe) |
| `..._last_smoke_returns_valid_payload_...` | ramo `last` | 200 (smoke) | `LASTDAYS` | sì (probe) |
| `..._station_details_without_networks_...` | "Parameter networks is missing" | 400 | — | No |
| `..._station_details_with_multiple_networks_...` | `len(networks)!=1` | 400 | `LASTDAYS` (probe) | sì (probe) |
| `..._station_details_unknown_station_...` | `NotFound` morto (**EDGE-001**) | 404 **o skip** | `LASTDAYS` | **sì (EDGE-001 + probe)** |
| `..._all_station_products_false_...` | `allStationProducts=false` | 200 + `products<= {p}` | `LASTDAYS` | sì (probe / no products) |
