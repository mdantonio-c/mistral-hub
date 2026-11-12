# Review — `test_observations_download.py`

> File di review per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo: copertura di `MapsObservations.post` (download).

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/integration/observed/test_observations_download.py`
- **Scopo**: coprire il **download** osservato `POST /api/observations`: stream JSON/BUFR, smoke `reliabilityCheck`, validazioni di schema/controller (`output_format`, bbox, license, `singleStation`), mismatch licenza, network inesistente/non autorizzato e autorizzazione ai dati archiviati.
- **Tipologia**: test di **integrazione HTTP** su **dati reali** (DBALLE/Arkimet) con finestre `agrmet` **fisse**. Marker di modulo: `integration`, `deterministic`, `runtime_sensitive`.
- **Finestre dati fisse** (dall'intestazione del file): DBALLE `agrmet 2020-04-06 00:00–01:00`; Arkimet `agrmet 2020-03-31/2020-04-01`. Le date fuori da queste finestre servono solo come trigger di validazione, non come oracolo dati.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `MapsObservations.post` | `projects/mistral/backend/endpoints/maps_observed.py` | Endpoint download (legge **tutto dalla query string**, non dal body): bbox, parsing `q`, network auth, `singleStation`, license, reftime, `db_type`, streaming. |
| `ObservationsDownloader` (schema) | `projects/mistral/backend/endpoints/maps_observed.py` | `output_format` **required** con `OneOf(["BUFR","JSON"])` (CSV → 400 di schema); `q` **required**. |
| `BeArkimet.from_network_to_dataset` | `projects/mistral/backend/services/arkimet.py` | Network ignoto → `None` → **404** "The requested network does not exist". |
| `SqlApiDbManager.check_dataset_authorization` | `projects/mistral/backend/services/sqlapi_db_manager.py` | Network privato senza grant → `Unauthorized` → **401**. |
| `BeDballe.check_access_authorization` | `projects/mistral/backend/services/dballe.py` | `UnexistingLicenseGroup`→400, `NetworkNotInLicenseGroup`→400, `UnAuthorizedUser`→401. |
| `BeDballe.get_db_type` / `LASTDAYS` | `projects/mistral/backend/services/dballe.py` | Classifica la finestra; senza override una data del 2020 è **arkimet**. |
| `SqlApiDbManager.get_user_permissions` | `projects/mistral/backend/services/sqlapi_db_manager.py` | `allowed_obs_archive` per il ramo archiviato (401 se assente). |
| `MapsObservations.get` (via `/fields`) | `projects/mistral/backend/endpoints/maps_observed.py` | **Probe** indiretto: `_require_dballe_product` interroga `/fields` per scegliere un prodotto reale. |
| Modelli `Datasets`/`License`/`GroupLicense` | `projects/mistral/backend/models/sqlalchemy.py` | Letti; il test 10 crea solo righe sintetiche tramite `create_test_dataset` (vedi §6). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `auth_headers` | fixture | `projects/mistral/backend/tests/integration/conftest.py` | Utente DEFAULT (`allowed_obs_archive=True` via `projects/mistral/backend/customization.py`). |
| `test_runtime` | fixture | `projects/mistral/backend/tests/conftest.py` | Singleton di sessione; usato per `override_attr(BeDballe, "LASTDAYS", ...)`. |
| `cleanup_registry` | fixture | `projects/mistral/backend/tests/conftest.py` | Teardown **LIFO**; raccoglie utenti temporanei e il dataset privato sintetico. |
| `create_dataset_test_user` | helper condiviso | `projects/mistral/backend/tests/helpers/auth.py` | Crea utente via API admin + login + cleanup (FS + delete utente). |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Accesso DB diretto (dataset privato sintetico). |
| `dballe_window_override`, `api_url`, costanti `OBS_*`/`OBSERVED_*` | helper condivisi | `projects/mistral/backend/tests/helpers/observed_windows.py` | Patch di `BeDballe.LASTDAYS` perché `2020-04-06` sia classificata **dballe** anche eseguendo nel 2026; URL e finestre dati comuni con `/fields`. |
| `require_observed_dataset_user` | helper condiviso | `projects/mistral/backend/tests/helpers/observed_windows.py` | Utente con grant `agrmet` e archive flag controllato; **`pytest.skip`** se `agrmet` non esiste. |
| `_require_dballe_product` | helper locale | (file) | Wrapper su `require_dballe_product` (helpers/observed_windows.py): probe `/fields`; **`pytest.skip`** se 200 non ottenuto o nessun prodotto. |
| `create_dataset_test_user` (senza dataset) | helper condiviso | `projects/mistral/backend/tests/helpers/auth.py` | Utente senza grant del test 10. |
| `create_private_test_network` | helper condiviso | `projects/mistral/backend/tests/helpers/datasets.py` | Crea un dataset privato sintetico e mappa una rete sintetica su di esso; le altre reti usano la mappatura reale. Condiviso con `fields/test_fields_api.py`. |
| `uuid4` | stdlib | `uuid` | Nomi/licenze/network sicuramente inesistenti. |

## 4. Analisi dettagliata di ogni test

### `test_observed_post_download_json_returns_stream_for_dballe_window`
- **Obiettivo**: download **JSON** sulla finestra DBALLE agrmet.
- **Backend coinvolto**: `post` → ramo `db_type=="dballe"` → `download_data_from_map` (stream).
- **Flusso**: `_require_dballe_product` (probe, **skip** se assente) → POST con prodotto reale, `output_format=JSON`, dentro `dballe_window_override`.
- **Assert**: `200`, `mimetype=="application/json"`, `data` non vuoto; il payload è **newline-delimited JSON** (ogni riga è un documento; lo stream **non** è un array unico).
- **Casi coperti**: happy path JSON + forma NDJSON dello stream.

### `test_observed_post_download_bufr_returns_octet_stream_for_dballe_window`
- **Obiettivo**: download **BUFR** sulla stessa finestra.
- **Assert**: `200`, `mimetype=="application/octet-stream"`, `data` non vuoto.
- **Casi coperti**: secondo formato ammesso dallo schema. **Skippabile** via probe.

### `test_observed_post_reliability_check_smoke_uses_dballe_window`
- **Obiettivo**: smoke positivo `reliabilityCheck=true` (il flag attraversa controller + download senza errore).
- **Assert**: `200`, `mimetype=="application/json"`. Il contenuto QC dipende dagli attributi dei dati e **non** viene verificato.
- **Casi coperti**: ramo `query["query"]="attrs"`. **Skippabile** via probe.

### `test_observed_post_invalid_output_format_returns_bad_request`
- **Obiettivo**: `output_format=CSV` → **400** (validazione `OneOf` di schema).
- **Backend coinvolto**: `ObservationsDownloader` rifiuta CSV **prima** del controller.
- **Flusso**: POST con `_download_query()` senza prodotto, senza probe `/fields` né fixture `test_runtime`.
- **Assert**: `400` e payload `{"output_format": ["Must be one of: BUFR, JSON."]}`, specifico della validazione `OneOf`. Non dipende dalla presenza di dati reali e non è skippabile tramite il probe.

### `test_observed_post_incomplete_bbox_returns_bad_request`
- **Obiettivo**: solo `lonmin` (bbox incompleta) → **400** del controller ("Coordinates for bounding box are missing").
- **Flusso**: POST con `_download_query()` senza prodotto, senza probe `/fields` né fixture `test_runtime`.
- **Assert**: `400` e messaggio esatto `"Coordinates for bounding box are missing"`, dal controllo bbox precedente al parsing di `q` e all'accesso ai dati. Non è skippabile tramite il probe.

### `test_observed_post_missing_license_returns_bad_request`
- **Obiettivo**: `q` senza `license` → **400** ("License group parameter is mandatory"). **Nessun** probe → non skippabile.

### `test_observed_post_unknown_license_group_returns_bad_request`
- **Obiettivo**: `license:missing_<uuid>` → **400** (`UnexistingLicenseGroup`). **Nessun** probe.

### `test_observed_post_mismatch_network_license_returns_bad_request`
- **Obiettivo**: `agrmet` con `CCBY-SA_COMPLIANT` (gruppo non coerente) → **400** (`NetworkNotInLicenseGroup`). **Nessun** probe.

### `test_observed_post_unknown_network_returns_not_found`
- **Obiettivo**: network inesistente → **404**. **Nessun** probe.

### `test_observed_post_private_network_returns_unauthorized_without_local_oracle`
- **Obiettivo**: **401** portabile su network privato.
- **Backend coinvolto**: `check_dataset_authorization` (dataset privato, utente senza grant) → `Unauthorized`.
- **Flusso**: `create_private_test_network(db, cleanup_registry, monkeypatch, prefix=...)` (dataset privato sintetico + rete sintetica mappata su di esso) → utente senza grant → POST con `networks=<rete sintetica>` → 401.
- **Setup/cleanup**: solo righe sintetiche, rimosse dal cleanup di `create_test_dataset`; agrmet non viene modificato.
- **Casi coperti**: error path 401 senza dipendere da una restrizione locale preesistente e senza alterare il catalogo reale.

### `test_observed_post_single_station_without_networks_returns_bad_request`
- **Obiettivo**: `singleStation=true` senza `networks` → **400** ("Parameter networks is missing"). **Nessun** probe.

### `test_observed_post_single_station_with_multiple_networks_returns_bad_request`
- **Obiettivo**: `singleStation` con `"agrmet or agrmet"` (2 network, entrambi validi) → **400** (`len != 1`). Anche con `lat`/`lon` presenti, il controllo sul numero di network scatta prima. **Nessun** probe.

### `test_observed_post_single_station_without_station_identity_returns_bad_request`
- **Obiettivo**: `singleStation` con `networks` ma **senza** `lat`/`lon`/`ident` → **400**. **Nessun** probe.

### `test_observed_post_archived_window_rejects_anonymous_user`
- **Obiettivo**: finestra **Arkimet** + utente **anonimo** → **401** ("to access archived data the user has to be logged").
- **Backend coinvolto**: `get_db_type` → `arkimet` (date 2020, nessun override) → `if db_type != "dballe" and not user` → 401.
- **Casi coperti**: error path archive anonimo. **Nessun** override e **nessun** probe.

### `test_observed_post_archived_window_rejects_user_without_archive_permission`
- **Obiettivo**: finestra Arkimet + utente con `allowed_obs_archive=False` → **401**.
- **Flusso**: `require_observed_dataset_user(..., allowed_obs_archive=False)` (associato ad agrmet, cleanup registrato) → POST archive → 401.
- **Casi coperti**: error path archive senza permesso. **Skippabile** se `agrmet` manca.

## 5. Call chain

```
POST /api/observations?q=...&networks=...&output_format=...   (query string)
  → use_kwargs(ObservationsDownloader)        (output_format OneOf BUFR/JSON; q required → CSV/q mancante = 400)
  → MapsObservations.post
     → bbox check (parziale → 400)
     → from_query_to_dic(q)                    (license mancante → 400 più avanti)
     → [networks loop: from_network_to_dataset (None→404) → check_dataset_authorization (privato→401)]
     → [singleStation: networks richiesto / ==1 / ident|lat&lon  → 400]
     → "license" in query? no → 400
     → check_access_authorization              (Unexisting→400, NetworkNotInGroup→400, UnAuthorized→401)
     → reftime? no → 400
     → get_db_type (LASTDAYS)
        → != dballe: not user → 401 ; else not allowed_obs_archive → 401
     → ramo dballe/arkimet/mixed → get_maps_response(download=True)
     → FlaskResponse(stream download_data_from_map(...), mimetype=json|octet-stream)

probe interno (success path): GET /api/fields?q=<DBALLE_QUERY;network:agrmet>  (dentro LASTDAYS override)
     → status != 200 o nessun product → pytest.skip
```

## 6. Comportamenti nascosti

- **`POST` legge dalla query string, non dal body**: `_post_observations` mette tutto in URL (`urlencode`). Coerente col controller, ma non ovvio per chi si aspetta un body JSON in un POST.
- **Override `LASTDAYS` (non un mock dei dati)**: `dballe_window_override` patcha solo la **soglia mobile** di `get_db_type` (via `test_runtime.override_attr`), così che `2020-04-06` sia classificata "dballe" anche eseguendo nel 2026. I dati restano quelli reali del runtime. I rami **archived** (test 14–15) **non** usano l'override, perché vogliono `db_type=arkimet`.
- **Rete privata sintetica (test 10)**: `create_private_test_network` crea un dataset privato sintetico e sostituisce `BeArkimet.from_network_to_dataset` solo per la rete sintetica, delegando ogni altra rete alla funzione reale. `check_dataset_authorization` resta reale. In precedenza il test spostava agrmet su una licenza privata con commit: il catalogo reale era alterato per tutti durante il test e restava privato se il teardown saltava.
- **Validazioni indipendenti dai dati** (test 4 e 5): usano `_download_query()` senza prodotto e senza probe `/fields`; verificano il payload specifico del 400 di schema/controller, senza dipendere dalla disponibilità della finestra DBALLE.
- **Triplice canale di skip silenzioso** (runtime-sensitive): (1) `require_observed_dataset_user` (via `require_dataset`) se agrmet manca; (2) `_require_dballe_product` se `/fields` non risponde 200 o non espone prodotti; (3) `_require_dballe_product` se `summarystats["c"] <= 0`.
- **NDJSON nel test JSON**: l'asserzione decodifica **riga per riga** (`splitlines`), perché il downloader DBALLE emette JSON newline-delimited e non un array unico. Un reviewer potrebbe aspettarsi `json.loads(response.data)` su tutto il body.
- **`allowed_obs_archive` di default True** per gli utenti creati (`projects/mistral/backend/customization.py`): il test 15 passa **esplicitamente** `False` per ottenere il 401; senza quell'override l'utente avrebbe accesso archivio.

## 7. Checklist di revisione

- [ ] Verificare che `create_private_test_network` mappi solo la rete sintetica e deleghi tutte le altre alla mappatura Arkimet reale.
- [x] I test 4 e 5 (validazioni 400) evitano il probe `_require_dballe_product` e la fixture `test_runtime`, usano `_download_query()` senza prodotto e asseriscono il motivo specifico del 400 del ramo dichiarato nel docstring.
- [ ] Confermare in CI quanti test risultano `skipped` per assenza di agrmet/finestra DBALLE.
- [ ] Confermare che `2020-04-06` resti la finestra DBALLE attesa e `2020-03-31/04-01` quella Arkimet nei dati seed.
- [ ] Confermare che `CCBY-SA_COMPLIANT` sia un gruppo **esistente ma non coerente** con agrmet (per ottenere `NetworkNotInLicenseGroup`, non `UnexistingLicenseGroup`).
- [ ] Verificare l'assert NDJSON (decodifica riga per riga) resti valido se cambia il formato di output del downloader.

## 8. Possibili criticità

- **Mappatura rete→dataset finta nel test 10**: il 401 non verifica la mappatura Arkimet reale di agrmet, già esercitata dai test positivi e dal 404 di rete inesistente.
- **Copertura "verde per skip"**: tre canali di `pytest.skip` possono annullare silenziosamente i success path (JSON/BUFR/reliability/private/archive-no-perm).
- **Dipendenza forte dalle date fisse**: l'intero modulo è ancorato a `agrmet 2020-04-06` e `2020-03-31/04-01`; un reseeding con date diverse lo rende inservibile (skip o fallimenti).
- **`reliabilityCheck` solo smoke**: verifica solo `200`+mime, non il contenuto QC; il ramo `query="attrs"` è esercitato ma non validato nei risultati.
- **Accoppiamento all'utente DEFAULT** e al permesso `allowed_obs_archive` per distinguere i rami archive.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/patch | Fixture | Skip silenzioso |
|---|---|---|---|---|---|
| `..._download_json_..._dballe_window` | `post` dballe + stream | 200 + JSON (NDJSON) | `LASTDAYS` override | `client`,`auth_headers`,`test_runtime` | sì (probe) |
| `..._download_bufr_..._dballe_window` | `post` dballe + stream | 200 + octet-stream | `LASTDAYS` override | id. | sì (probe) |
| `..._reliability_check_smoke_...` | `post` + `query=attrs` | 200 + JSON (smoke) | `LASTDAYS` override | id. | sì (probe) |
| `..._invalid_output_format_...` | schema `OneOf` | 400 + errore `output_format` (CSV) | — | `client`,`auth_headers` | No |
| `..._incomplete_bbox_...` | controller bbox | 400 + "Coordinates for bounding box are missing" | — | `client`,`auth_headers` | No |
| `..._missing_license_...` | "License mandatory" | 400 | — | `client`,`auth_headers` | No |
| `..._unknown_license_group_...` | `UnexistingLicenseGroup` | 400 | — | id. | No |
| `..._mismatch_network_license_...` | `NetworkNotInLicenseGroup` | 400 | — | id. | No |
| `..._unknown_network_...` | `from_network_to_dataset` None | 404 | — | id. | No |
| `..._private_network_..._unauthorized_...` | `check_dataset_authorization` | 401 | rete sintetica (`from_network_to_dataset`) | `client`,`cleanup_registry`,`monkeypatch` | No |
| `..._single_station_without_networks_...` | "Parameter networks is missing" | 400 | — | `client`,`auth_headers` | No |
| `..._single_station_with_multiple_networks_...` | `len(networks)!=1` | 400 | — | id. | No |
| `..._single_station_without_station_identity_...` | "Parameters ... missing" | 400 | — | id. | No |
| `..._archived_window_rejects_anonymous_user` | archive + `not user` | 401 | — (no override) | `client` | No |
| `..._archived_window_rejects_user_without_archive_permission` | archive + `allowed_obs_archive=False` | 401 | utente temp | `client`,`cleanup_registry` | sì (agrmet) |
