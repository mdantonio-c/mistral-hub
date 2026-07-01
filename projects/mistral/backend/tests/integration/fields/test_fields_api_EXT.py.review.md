# Review — `test_fields_api_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: prima copertura **di estensione** dedicata a `Fields.get`, sopra la baseline observed.
> Runtime-sensitive: i rami happy path interrogano dati reali nelle finestre consentite dal Prompt 03.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/fields/test_fields_api_EXT.py](projects/mistral/backend/tests/integration/fields/test_fields_api_EXT.py)
- **Scopo**: coprire l'endpoint `GET /api/fields` (summary stats / filtri) nei tre modi operativi — **OBS map mode** (senza `datasets`, via `network`/`license`), **OBS dataset mode** (autenticato), **FOR/Arkimet dataset mode** — più i numerosi rami di errore (401/404/400) e le opzioni `onlySummaryStats`/`SummaryStats`/`allAvailableProducts`.
- **Tipologia**: test di **integrazione HTTP** (controller reale + `SqlApiDbManager` + `BeDballe`/`BeArkimet` + DB). Mix di **happy path su dati reali** e **rami di validazione su dataset sintetici + monkeypatch**. Marker: `integration`, `deterministic`, `runtime_sensitive`.
- **Numero di test**: **21**, tutti in funzioni `test_*` a livello di modulo.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Fields.get` | [endpoints/fields.py](projects/mistral/backend/endpoints/fields.py) | `GET /api/fields` — `auth.optional()`; instrada OBS vs FOR, valida bbox, autorizzazioni, license group; restituisce `summary`. |
| `SqlApiDbManager.get_datasets` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L482) | Verifica esistenza/visibilità dataset in dataset mode (404 se non trovato/non autorizzato). |
| `SqlApiDbManager.get_license_group` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L546) | Ritorna `None` se i dataset appartengono a gruppi licenza diversi (→ 400). |
| `SqlApiDbManager.check_dataset_authorization` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L562) | Autorizzazione di rete in map mode (privato non assegnato → 401). |
| `SqlApiDbManager.get_user_permissions` | [services/sqlapi_db_manager.py](projects/mistral/backend/services/sqlapi_db_manager.py#L665) | `allowed_obs_archive` per il ramo dati archiviati (401 se assente). |
| `BeDballe.get_db_type` / `LASTDAYS` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L117) | Classifica reftime come `dballe`/`mixed`/`arkimet` con soglia mobile su `LASTDAYS`; decide se serve `allowed_obs_archive`. |
| `BeDballe.check_access_authorization` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L196) | Solleva `UnexistingLicenseGroup`/`UnAuthorizedUser`/`NetworkNotInLicenseGroup` (→ 400/401). |
| `BeArkimet.get_datasets_category` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L218) | Categoria comune dei dataset; `None` se incompatibili (→ 400). **Monkeypatchata** in 2 test. |
| `BeArkimet.from_network_to_dataset` / `load_summary` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L278) | Mapping network→dataset (404 se assente) e summary Arkimet per FOR. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient`. |
| `auth_headers` | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py#L15) | Utente **DEFAULT** loggato, header condivisi (admin di default → `allowed_obs_archive` non garantito). |
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L39) | Teardown LIFO per utenti/dataset/licenze sintetici. |
| `test_runtime` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L31) | Singleton di sessione; fornisce `override_attr` per il patch di `LASTDAYS`. |
| `monkeypatch` | fixture | pytest | Patch di `fields_endpoint_module.arki.get_datasets_category` (test 17, 18). |
| `observed_dballe_override` | helper | [fields/support_EXT.py](projects/mistral/backend/tests/integration/fields/support_EXT.py) | Context manager che forza `BeDballe.LASTDAYS` per trattare il 2020-04-06 come recente. |
| `require_observed_dataset_user` / `require_forecast_fields_case` / `require_dataset` | helper | [fields/support_EXT.py](projects/mistral/backend/tests/integration/fields/support_EXT.py) | Creano utenti/scenari reali; **`pytest.skip`** se i dataset richiesti mancano. |
| `create_fields_user` / `create_fields_synthetic_dataset` / `get_or_create_multim_forecast_dataset` / `create_private_observed_dataset_for_all_available_products` / `temporarily_make_observed_dataset_private` | helper | [fields/support_EXT.py](projects/mistral/backend/tests/integration/fields/support_EXT.py) | Setup utenti/dataset/licenze + cleanup; uno **muta agrmet reale** e ripristina. |
| `fields_url`, `parse_response`, costanti `OBS_*`/`OBSERVED_*` | helper/cost. | [fields/support_EXT.py](projects/mistral/backend/tests/integration/fields/support_EXT.py) | Costruzione URL, decodifica risposta, finestre dati ammesse. |

## 4. Analisi dettagliata di ogni test

> Legenda: **R** = dipende da dati reali nelle finestre Prompt 03 (può **fallire** se assenti); **S** = può eseguire `pytest.skip` silenzioso; **D** = deterministico (sintetico/validazione, niente dati reali).

### Gruppo A — OBS map mode (happy path su agrmet DBALLE 2020-04-06)

#### `test_fields_observed_map_mode_returns_recent_agrmet_filters` — R
- **Obiettivo**: filtri OBS map mode su agrmet DBALLE.
- **Backend**: `Fields.get` ramo OBS senza `datasets`; `from_query_to_dic`, `get_db_type` (forzato dballe), autorizzazione network, `load_filters`.
- **Flusso**: `GET /fields?q=...network:agrmet;license:CCBY_COMPLIANT` con `auth_headers` dentro `observed_dballe_override`.
- **Setup**: `auth_headers`, `test_runtime`; override `LASTDAYS`.
- **Assert**: 200; `summarystats.c > 0`; presenza network `agrmet`; `product` non vuoto.
- **Casi coperti**: happy path map mode. **Fallisce** (non skippa) se la finestra DBALLE agrmet è vuota.

#### `test_fields_observed_dataset_mode_returns_agrmet_filters` — R, S
- **Obiettivo**: OBS dataset mode autenticato su agrmet.
- **Backend**: ramo OBS con `datasets=agrmet`; verifica dataset + `load_filters`.
- **Flusso**: utente via `require_observed_dataset_user` (assegna agrmet) → `GET /fields?datasets=agrmet&q=...` in override.
- **Setup**: `cleanup_registry`, `test_runtime`.
- **Assert**: 200; `summarystats.c > 0`; `network` presente.
- **Casi coperti**: dataset mode. **Skip** se la riga agrmet manca; **fail** se manca il dato nella finestra.

### Gruppo B — OBS autorizzazioni / archivio

#### `test_fields_observed_archived_map_mode_rejects_anonymous_user` — D
- **Obiettivo**: 401 anonimo su finestra **archiviata** (2020-03-31/04-01).
- **Backend**: `get_db_type` → `arkimet`/`mixed` (data lontana, indipendente da `LASTDAYS`) → `if not user: Unauthorized`.
- **Flusso**: `GET /fields?q=...` **senza** header.
- **Assert**: 401. Deterministico (nessun override, nessun dato).

#### `test_fields_observed_archived_map_mode_rejects_user_without_archive_permission` — S
- **Obiettivo**: 401 per utente loggato **senza** `allowed_obs_archive` su finestra archiviata.
- **Backend**: `get_user_permissions("allowed_obs_archive")` falso → `Unauthorized`.
- **Flusso**: `require_observed_dataset_user(..., allowed_obs_archive=False)` → GET archive query.
- **Assert**: 401. **Skip** possibile (via `require_dataset(agrmet)`), pur essendo il 401 indipendente dai dati.

#### `test_fields_observed_private_network_returns_unauthorized_without_local_oracle` — S
- **Obiettivo**: costruire un **401 portabile** rendendo agrmet temporaneamente privato.
- **Backend**: `check_dataset_authorization` → privato non assegnato → `Unauthorized`.
- **Flusso**: `temporarily_make_observed_dataset_private` (muta `license_id` di agrmet, ripristino in cleanup) → utente senza dataset → GET map query in override.
- **Assert**: 401. **Skip** se agrmet assente. **Muta dati reali** (ripristinati in teardown).

### Gruppo C — OBS validazione (400/404)

#### `test_fields_observed_unknown_network_returns_not_found` — D
- 404 quando `from_network_to_dataset("missing_…")` ritorna `None`. `auth_headers` + override (innocuo). Deterministico.

#### `test_fields_observed_missing_license_group_returns_bad_request` — D
- 400 quando, in map mode, manca `license` in `q` (`raise BadRequest("License group parameter is mandatory")`). Deterministico.

#### `test_fields_observed_unknown_license_group_returns_bad_request` — D
- 400: gruppo licenza inesistente → `UnexistingLicenseGroup` → `BadRequest`. Deterministico (gruppo "missing_…").

#### `test_fields_observed_mismatch_network_license_returns_bad_request` — R (parziale)
- 400: agrmet accoppiato a `CCBY-SA_COMPLIANT` → `NetworkNotInLicenseGroup`. Richiede che il **mapping network agrmet** esista (altrimenti 404, non 400): implicitamente runtime-sensitive.

#### `test_fields_observed_missing_dataset_returns_not_found` — D
- 404 in dataset mode quando il dataset observed non esiste. `auth_headers`, nessun override. Deterministico.

#### `test_fields_observed_incomplete_bbox_returns_bad_request` — D
- 400: `lonmin` senza gli altri estremi → `BadRequest` in cima al metodo, prima dei controlli dati. Deterministico.

### Gruppo D — OBS opzioni di output

#### `test_fields_observed_only_summary_stats_returns_stats_only` — R (infra)
- `onlySummaryStats=true`: risposta è `summary["items"]["summarystats"]` → `"c" in content`, `"items" not in content`. Non richiede `c>0` ma sì l'accesso reale a DBALLE.

#### `test_fields_observed_summary_stats_false_omits_summary_stats` — R (infra)
- `SummaryStats=false`: `resulting_fields.pop("summarystats")` → `"summarystats" not in content["items"]`. Ramo OBS, dove `resulting_fields` è inizializzato (nessun bug, a differenza del forecast).

#### `test_fields_observed_all_available_products_excludes_unauthorized_private_group` — R, S
- **Obiettivo**: `allAvailableProducts=true` non deve includere un gruppo OBS **privato non autorizzato**.
- **Backend**: `get_all_user_authorized_license_groups` → `all_licenses`.
- **Flusso**: crea gruppo OBS privato sintetico (controllo negativo) + utente agrmet → GET con `allAvailableProducts`.
- **Assert**: 200; `CCBY_COMPLIANT` presente in `all_licenses`; gruppo privato sintetico **assente**. **Skip** se agrmet assente.

### Gruppo E — FOR / Arkimet dataset mode (reale)

#### `test_fields_forecast_dataset_mode_returns_descriptions_for_allowed_window` — R, S
- **Obiettivo**: FOR dataset mode su lm5 2021-10-19 o lm2.2 2019-09-10 con `descriptions`.
- **Backend**: ramo Arkimet → `load_summary` → `get_leveltype_descriptions`/`get_trangetype_descriptions`.
- **Flusso**: `require_forecast_fields_case` prova lm5 poi lm2.2 con utente autorizzato.
- **Assert**: `summarystats.c > 0`; `descriptions.leveltypes` e `descriptions.timerangetypes` valorizzati. **Skip** se nessuna finestra forecast espone dati.

#### `test_fields_forecast_only_summary_stats_returns_stats_only` — R, S
- `onlySummaryStats=true` sul forecast nella sola finestra ammessa: `"c" in content`, `"items" not in content`. **Skip** via `require_forecast_fields_case`.

#### `test_fields_forecast_summary_stats_false_is_skipped_for_known_backend_bug` — S (bug noto)
- **Obiettivo**: sondare `SummaryStats=false` sul forecast e **saltare esplicitamente** un bug backend.
- **Bug documentato**: in [endpoints/fields.py](projects/mistral/backend/endpoints/fields.py) `resulting_fields` è inizializzato **solo** nel ramo OBS, ma il blocco finale `if not SummaryStats: resulting_fields.pop(...)` lo usa anche dopo il ramo forecast → `UnboundLocalError` (esposto come 400/500).
- **Assert/skip**: se status ∈ {400,500} e il body cita `resulting_fields`/`UnboundLocalError` → `pytest.skip` verboso; altrimenti `200` e `"summarystats" not in items`. **Skip** anche via `require_forecast_fields_case`. Politica: niente `xfail` stabile, il test tornerà verde dopo il fix.

### Gruppo F — FOR validazione (dataset sintetici + monkeypatch)

#### `test_fields_forecast_missing_dataset_returns_not_found` — D
- 404 per dataset forecast inesistente. `auth_headers`. Deterministico.

#### `test_fields_forecast_multiple_categories_return_bad_request` — D
- **Obiettivo**: 400 quando i dataset hanno categorie diverse.
- **Setup**: 2 dataset sintetici (FOR + OBS) + utente autorizzato; **`monkeypatch`** `arki.get_datasets_category → None` (simula categorie incompatibili).
- **Assert**: 400. Deterministico (nessun dato Arkimet reale).

#### `test_fields_forecast_multiple_license_groups_return_bad_request` — D
- **Obiettivo**: 400 per dataset di gruppi licenza diversi.
- **Setup**: 2 dataset sintetici (gruppi distinti) + `monkeypatch` `get_datasets_category → "FOR"` (supera il check categoria) → `get_license_group` ritorna `None` → 400.
- **Assert**: 400. Deterministico.

#### `test_fields_forecast_multimodel_multi_dataset_returns_bad_request` — D
- **Obiettivo**: 400 per selezione multi-dataset con `multim-forecast`.
- **Setup**: record `multim-forecast` (reale o sintetico) + dataset compagno sintetico; il check `len(datasets)>1 and "multim-forecast" in datasets` scatta prima di Arkimet.
- **Assert**: 400. Deterministico.

## 5. Call chain

```
GET /api/fields (OBS map)   → auth.optional() → Fields.get(datasets=[])
                              → bbox check → data_type="OBS"
                              → from_query_to_dic(q); get_db_type(LASTDAYS← override) → "dballe"
                              → from_network_to_dataset(network) → None? NotFound 404
                              → check_dataset_authorization → False? Unauthorized 401
                              → "license" in q? else BadRequest 400
                              → check_access_authorization → UnexistingLicenseGroup/NetworkNotInLicenseGroup → BadRequest 400
                              → load_filters → resulting_fields → summary={"items":...} → 200

GET /api/fields (OBS arch)  → get_db_type → "arkimet"/"mixed" → if not user: 401 ; elif not allowed_obs_archive: 401

GET /api/fields (dataset)   → not user? 401 → for ds: get_datasets()→ not found → NotFound 404
                              → len>1 & "multim-forecast"? BadRequest 400
                              → get_datasets_category(datasets) → None? BadRequest 400
                              → get_license_group(datasets) → None? BadRequest 400
                              → (FOR) load_summary → descriptions → 200
                              → (FOR) if not SummaryStats: resulting_fields.pop()  ← UnboundLocalError (bug)
```

## 6. Comportamenti nascosti

- **Override di `LASTDAYS` indispensabile per OBS happy path**: `observed_dballe_override` patcha `BeDballe.LASTDAYS` (via `test_runtime.override_attr`) così che il 2020-04-06 cada nella finestra "dballe" (recente). Senza, `get_db_type` lo classificherebbe come archiviato e i test riceverebbero 401 invece dei dati. L'override è confinato al context manager.
- **`auth_headers` è l'utente DEFAULT condiviso**: i test map mode lo usano come utente "qualsiasi". I rami che richiedono `allowed_obs_archive` o assegnazioni dataset specifiche usano invece utenti dedicati creati ad hoc — non si affidano ai permessi del default.
- **Monkeypatch mirato solo sulla categoria**: i test multi-dataset forecast (17, 18) patchano **esclusivamente** `arki.get_datasets_category` per raggiungere il controllo categoria/gruppo senza dati Arkimet reali; il resto del controller gira davvero.
- **Mutazione di agrmet reale**: `test_..._private_network...` rende temporaneamente agrmet privato (licenza sintetica) per fabbricare un 401 portabile, poi ripristina la licenza originale in cleanup. Stato reale alterato e ripristinato.
- **Bug forecast `SummaryStats=False`**: documentato e gestito con `pytest.skip` verboso (non `xfail`), così la suite non si rompe ma segnala il difetto. Da riportare a verde dopo il fix backend.
- **Skip silenziosi diffusi**: `require_dataset`/`require_forecast_fields_case` saltano quando agrmet/lm5/lm2.2 mancano → in runtime minimali una quota dei test (2, 4, 6, 14, 15, 20, 21) può non eseguire alcuna asserzione.
- **Differenza skip vs fail**: i rami di errore (3, 5, 7, 8, 10, 11, 16, 17, 18, 19) sono deterministici; i happy path map mode (1, 12, 13, 14) **falliscono** (non skippano) se la finestra DBALLE è vuota o l'infrastruttura dballe non risponde.
- **`get_datasets_category` legge la config Arkimet su disco**: nei test reali la categoria dipende dal file `arkimet_conf`; nei sintetici è bypassata via monkeypatch.

## 7. Checklist di revisione

- [ ] Confermare che le finestre dati (agrmet 2020-04-06, lm5 2021-10-19, lm2.2 2019-09-10) siano presenti nell'ambiente di CI, altrimenti gli happy path falliranno o skipperanno.
- [ ] Verificare che l'override di `LASTDAYS` rispecchi fedelmente la logica di `get_db_type` e non mascheri regressioni nella classificazione dballe/arkimet.
- [ ] Tracciare il **bug forecast `SummaryStats=False`** (UnboundLocalError) come difetto reale di [endpoints/fields.py](projects/mistral/backend/endpoints/fields.py) e pianificare il ritorno a verde del test 21.
- [ ] Verificare che la mutazione temporanea di agrmet (test 6) sia sempre ripristinata, anche in caso di errore.
- [ ] Distinguere chiaramente, nei report CI, i test che **skippano** da quelli che **falliscono** per assenza dati (rischio di rumore).
- [ ] Confermare che i monkeypatch di `get_datasets_category` non nascondano differenze rispetto al comportamento reale di Arkimet.
- [ ] Verificare che `auth_headers` (default) abbia/non abbia `allowed_obs_archive` in modo coerente con le aspettative dei test che lo usano.

## 8. Possibili criticità

- **Ampia superficie runtime-sensitive**: ~7 test possono skippare e ~4-5 possono fallire silenziosamente per assenza di dati; il "verde" della suite non garantisce copertura effettiva degli happy path.
- **Bug di backend mascherato da skip**: il difetto forecast `SummaryStats=False` resta latente; finché il test 21 skippa, nessuno se ne accorge dai report.
- **Dipendenza dalla config Arkimet su disco**: i test reali dipendono da `arkimet_conf` e dalla finestra dati; cambiamenti di configurazione possono spostare gli esiti.
- **Mutazione di dati condivisi**: la riassegnazione della licenza di agrmet introduce un rischio di residui se il teardown fallisce (FK pendente verso licenza sintetica eliminata).
- **Accoppiamento ai monkeypatch interni**: i test 17/18 dipendono dal **nome del modulo** `fields_endpoint_module.arki`; un refactor degli import dell'endpoint romperebbe il patch silenziosamente (il controller userebbe l'Arkimet reale).
- **Complessità del controller**: `Fields.get` (302 righe) concentra molti rami; la suite è ricca ma la lettura incrociata test↔endpoint resta onerosa.

## 9. Riassunto finale

| # | Test | Backend chiave | Esito atteso | Mock/patch | Fixture (incl. locali) | R/S/D |
|---|---|---|---|---|---|---|
| 1 | `..._map_mode_returns_recent_agrmet_filters` | OBS map, `load_filters` | 200, c>0 | override LASTDAYS | `auth_headers`, `test_runtime` | R |
| 2 | `..._dataset_mode_returns_agrmet_filters` | OBS dataset | 200, c>0 | override LASTDAYS | `cleanup_registry`, `test_runtime` | R, S |
| 3 | `..._archived_map_mode_rejects_anonymous_user` | archive auth | 401 | — | `client` | D |
| 4 | `..._archived_map_mode_rejects_user_without_archive_permission` | `allowed_obs_archive` | 401 | — | `cleanup_registry` | S |
| 5 | `..._unknown_network_returns_not_found` | `from_network_to_dataset` | 404 | override (innocuo) | `auth_headers`, `test_runtime` | D |
| 6 | `..._private_network_returns_unauthorized_without_local_oracle` | `check_dataset_authorization` | 401 | override LASTDAYS | `cleanup_registry`, `test_runtime` | S, muta agrmet |
| 7 | `..._missing_license_group_returns_bad_request` | license mandatory | 400 | override | `auth_headers`, `test_runtime` | D |
| 8 | `..._unknown_license_group_returns_bad_request` | `UnexistingLicenseGroup` | 400 | override | `auth_headers`, `test_runtime` | D |
| 9 | `..._mismatch_network_license_returns_bad_request` | `NetworkNotInLicenseGroup` | 400 | override | `auth_headers`, `test_runtime` | R (mapping) |
| 10 | `..._missing_dataset_returns_not_found` | `get_datasets` | 404 | — | `auth_headers` | D |
| 11 | `..._incomplete_bbox_returns_bad_request` | bbox check | 400 | override | `auth_headers`, `test_runtime` | D |
| 12 | `..._only_summary_stats_returns_stats_only` | `onlySummaryStats` | 200, solo stats | override LASTDAYS | `auth_headers`, `test_runtime` | R (infra) |
| 13 | `..._summary_stats_false_omits_summary_stats` | `SummaryStats` pop (OBS) | 200, no summarystats | override LASTDAYS | `auth_headers`, `test_runtime` | R (infra) |
| 14 | `..._all_available_products_excludes_unauthorized_private_group` | `get_all_user_authorized_license_groups` | 200, gruppo privato escluso | override LASTDAYS | `cleanup_registry`, `test_runtime` | R, S |
| 15 | `..._forecast_dataset_mode_returns_descriptions_for_allowed_window` | Arkimet `load_summary` + descriptions | 200, descriptions | — | `cleanup_registry` | R, S |
| 16 | `..._forecast_missing_dataset_returns_not_found` | `get_datasets` | 404 | — | `auth_headers` | D |
| 17 | `..._forecast_multiple_categories_return_bad_request` | `get_datasets_category=None` | 400 | **monkeypatch** | `cleanup_registry`, `monkeypatch` | D |
| 18 | `..._forecast_multiple_license_groups_return_bad_request` | `get_license_group=None` | 400 | **monkeypatch** | `cleanup_registry`, `monkeypatch` | D |
| 19 | `..._forecast_multimodel_multi_dataset_returns_bad_request` | check `multim-forecast` | 400 | — | `cleanup_registry` | D |
| 20 | `..._forecast_only_summary_stats_returns_stats_only` | `onlySummaryStats` (FOR) | 200, solo stats | — | `cleanup_registry` | R, S |
| 21 | `..._forecast_summary_stats_false_is_skipped_for_known_backend_bug` | bug `resulting_fields` (FOR) | 200 **o** skip su bug | — | `cleanup_registry` | S (bug noto) |
