# Review — `test_arco_edge_cases_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** (Prompt 08 del piano) sopra la baseline ARCO (`test_arco_proxy.py`, `test_arco_catalog.py`), che resta invariata. Aggiunge edge case isolati, senza fixture globali né `conftest.py` locali.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/arco/test_arco_edge_cases_EXT.py](projects/mistral/backend/tests/integration/arco/test_arco_edge_cases_EXT.py)
- **Scopo**: coprire i contratti ARCO non esercitati dalla baseline: (a) **helper puri** (`guess_mime_type`, `_round_coord`); (b) **rami di errore del proxy** (no auth, auth errata, `NoSuchKey`→404, `ClientError` generico, mimetype dal filename); (c) **varianti del catalogo** (filtro prefissi `.zarr/`, `.zmetadata` mancante con fallback, license/attribution sconosciute, paginazione con `NextContinuationToken`).
- **Tipologia**: misto **unit puro** (i due helper) + **integrazione HTTP** (proxy e catalogo via `FlaskClient`), con S3 e SQLAlchemy **sempre rimpiazzati** da fake locali in memoria. Marker: `pytestmark = [pytest.mark.integration, pytest.mark.deterministic]`.
- **Numero di test**: 11 funzioni (1 di cui parametrizzata su 4 casi) in 3 classi. Una è **silenziosamente skippabile** (`ARCO-001`, vedi §6/§8).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `arco.guess_mime_type` | [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) | Helper puro: mimetype dal nome file. |
| `arco._round_coord` | [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) | Helper puro: arrotonda coordinate o preserva valori non convertibili. |
| `ArcoResource.get` | [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) | Proxy `GET /api/arco/<path>`: auth → S3 `get_object` → `Response`; `NoSuchKey`→404, altro `ClientError`→`raise Exception`. |
| `ArcoDatasetsResource.get` | [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) | Catalogo `GET /api/arco/datasets` (pubblico): filtro `.zarr/`, lettura `.zmetadata`, fallback `NoSuchKey`, enrichment, paginazione `ContinuationToken`. |
| `validate_access_key_from_request` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py#L51) | Auth BasicAuth del proxy (401 su assente/errata). |
| `arco.s3.get_instance` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py) | Connettore S3 — **sempre fake**. |
| `arco.sqlalchemy.get_instance` | `restapi.connectors` | DB — **sempre fake** nel catalogo. |
| `DatasetSchema` | [endpoints/schemas.py](projects/mistral/backend/endpoints/schemas.py) | Marshalling output catalogo (indiretto). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `fresh_access_key` | fixture | [tests/integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py#L29) | Access key reale del default user; usata solo dai test proxy che necessitano auth valida. |
| `monkeypatch` | fixture | `pytest` | Sostituisce `arco.s3.get_instance` / `arco.sqlalchemy.get_instance`; teardown automatico. |
| `make_basic_auth` | helper | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py#L114) | Header `Authorization: Basic email:key`. |
| `_FakeBody_EXT` | classe locale | nel file di test | Body S3 minimale con solo `read()` (deterministico, non consuma il buffer). |
| `_NoSuchKey_EXT` | classe locale | nel file di test | Eccezione che simula `client.exceptions.NoSuchKey` del **catalogo**. |
| `_FakeS3Client_EXT` | classe locale | nel file di test | Client S3 in memoria: `list_objects_v2` (paginazione + tracciamento `list_calls`), `get_object` (mappa `objects`, solleva `NoSuchKey` se chiave assente), `exceptions.NoSuchKey`. |
| `_FakeS3Connection_EXT` | classe locale | nel file di test | Wrapper con attributo `client` come il connettore reale. |
| `_AttributionRow_EXT` / `_LicenseRow_EXT` / `_GroupLicenseRow_EXT` | classi locali | nel file di test | Righe SQLAlchemy fake con i soli campi letti dal catalogo. |
| `_Query_EXT` / `_ModelFacade_EXT` / `_DatabaseFacade_EXT` | classi locali | nel file di test | Facciata DB fake con `.query.all()` per `Attribution`/`License`. |
| `_client_error_EXT(code)` | helper locale | nel file di test | Costruisce un `botocore.exceptions.ClientError` con `Error.Code` controllato (ramo **proxy**). |
| `_metadata_payload_EXT(zattrs)` | helper locale | nel file di test | Serializza un `.zmetadata` Zarr minimale con `.zattrs` dato. |
| `_install_fake_arco_s3_EXT` / `_install_fake_catalog_db_EXT` | helper locali | nel file di test | Patchano `arco.s3.get_instance` / `arco.sqlalchemy.get_instance` con i fake. |
| `_basic_headers_EXT` | helper locale | nel file di test | Converte `fresh_access_key` in header BasicAuth ARCO. |

## 4. Analisi dettagliata di ogni test

### Classe `TestArcoHelpers_EXT`

#### `test_guess_mime_type_returns_known_json_type_EXT`
- **Obiettivo**: documentare il contratto di `guess_mime_type` per file JSON.
- **Backend coinvolto**: `arco.guess_mime_type` (puro, nessun HTTP).
- **Flusso/Setup**: chiama l'helper su `"metadata.json"`.
- **Assert**: `== "application/json"` → mappatura estensione→mimetype stabile (poi usata dal proxy).
- **Casi coperti**: happy path helper puro.

#### `test_round_coord_handles_numbers_strings_and_none_EXT` (parametrizzato ×4)
- **Obiettivo**: `_round_coord` arrotonda i numeri e **preserva** i valori non convertibili.
- **Backend coinvolto**: `arco._round_coord` (puro).
- **Casi/Assert**: `"44.126"→44.13`, `-7.891→-7.89` (ramo numerico, anche stringa numerica), `"not-a-coordinate"→"not-a-coordinate"` (ValueError → originale), `None→None` (TypeError → originale).
- **Casi coperti**: ramo numerico + due rami di fallback (`.zattrs` incompleti/non numerici).

### Classe `TestArcoProxyEdges_EXT`

#### `test_proxy_missing_basic_auth_is_rejected_before_s3_EXT`
- **Obiettivo**: senza BasicAuth la richiesta si ferma **prima** del connettore S3.
- **Backend coinvolto**: `ArcoResource.get` → `validate_access_key_from_request` (no auth → 401).
- **Setup**: `monkeypatch` su `arco.s3.get_instance` con `lambda: pytest.fail(...)` → se S3 venisse chiamato il test fallirebbe.
- **Flusso/Assert**: `GET /arco/ww3.zarr/.zgroup` senza header → `401`; `pytest.fail` **non** scatta → prova che S3 non è raggiunto.
- **Casi coperti**: error path + invariante "auth prima di S3".

#### `test_proxy_wrong_basic_auth_is_rejected_before_s3_EXT`
- **Obiettivo**: BasicAuth con access key errata resta un `401` deterministico, senza toccare S3.
- **Backend coinvolto**: `ArcoResource.get` → validazione (chiave inesistente → `Unauthorized`).
- **Setup**: stesso trucco `pytest.fail` su `arco.s3.get_instance`; header `make_basic_auth(default_user, "wrong-access-key")`.
- **Assert**: `status_code == 401`.
- **Casi coperti**: error path (credenziale errata).

#### `test_proxy_s3_no_such_key_returns_404_EXT`
- **Obiettivo**: il `NoSuchKey` S3 è tradotto nel `404` pubblico del proxy.
- **Backend coinvolto**: ramo `except botocore...ClientError` con `Error.Code == "NoSuchKey"` → `NotFound`.
- **Setup**: `fake_client = MagicMock()`, `get_object.side_effect = _client_error_EXT("NoSuchKey")`; `_install_fake_arco_s3_EXT`; header da `fresh_access_key`.
- **Flusso/Assert**: `GET /arco/missing.zarr/.zgroup` → `404`.
- **Casi coperti**: error path / mapping eccezione→HTTP (usa `ClientError`, non `client.exceptions.NoSuchKey`).

#### `test_proxy_s3_non_no_such_key_returns_server_error_EXT` — **ARCO-001 (skippabile)**
- **Obiettivo**: un `ClientError` S3 diverso da `NoSuchKey` deve restare errore server (atteso `500`).
- **Backend coinvolto**: ramo `else: raise Exception from e`.
- **Setup**: `get_object.side_effect = _client_error_EXT("InternalError")`; fake S3 installato; header valido.
- **Flusso/Assert**: `GET /arco/ww3.zarr/.zgroup` → **se `status_code != 500` → `pytest.skip("ARCO-001: ...")`**, altrimenti `assert == 500`.
- **Casi coperti**: error path documentato ma **non garantito**: oggi il wrapper restapi espone l'eccezione generica con un codice diverso da 500 → il test si autoesclude. Vedi §8.

#### `test_proxy_sets_mimetype_from_object_filename_EXT`
- **Obiettivo**: il proxy imposta il mimetype da `guess_mime_type(filename)`.
- **Backend coinvolto**: `ArcoResource.get` (successo) → `Response(..., mimetype=...)`.
- **Setup**: `fake_client.get_object` → body `b'{"zarr_format": 2}'`; fake S3 installato; header valido.
- **Flusso/Assert**: `GET /arco/ww3.zarr/metadata.json` → `200`; `response.mimetype == "application/json"`; `response.data == b'{"zarr_format": 2}'` → mimetype derivato dall'estensione **e** body propagato invariato.
- **Casi coperti**: happy path con verifica mimetype (assert assente nella baseline proxy).

### Classe `TestArcoCatalogEdges_EXT`

> Tutti i test catalogo chiamano `GET /arco/datasets` **senza header**, confermando che l'endpoint catalogo è **pubblico**.

#### `test_catalog_keeps_only_zarr_prefixes_and_enriches_metadata_EXT`
- **Obiettivo**: scartare i prefissi non `.zarr/` e arricchire license/attribution/group dal DB, con rounding del bounding.
- **Setup**: `_FakeS3Client_EXT` con pagina `forecast.zarr/` + `plain-folder/` e `.zmetadata` con coordinate a più decimali (`"44.126"`, ...), `is_public/authorized` = `False`; DB fake con `KNOWN_ATTR`, `KNOWN_LICENSE`+`OPEN_GROUP`.
- **Assert**: 1 solo dataset (`forecast.zarr`), `name`/`description`/`category` da `.zattrs`, `is_public False`/`authorized False`, `bounding` con coordinate arrotondate a 2 decimali, e tutti i campi attribution/license/group valorizzati dal DB.
- **Casi coperti**: filtro prefissi + enrichment completo + rounding.

#### `test_catalog_missing_zmetadata_keeps_default_dataset_fallback_EXT`
- **Obiettivo**: un prefisso `.zarr/` **senza** `.zmetadata` resta visibile col dataset di default.
- **Setup**: `_FakeS3Client_EXT` con `fallback.zarr/` ma `objects` vuoto → `get_object` solleva `_NoSuchKey_EXT` (= `client.exceptions.NoSuchKey`); DB fake vuoto.
- **Assert**: `200`, 1 dataset, `id == "fallback.zarr"`, `name == "fallback"`, `category == "unknown"`, `format == "zarr"`, `source == "arco"`, `is_public True`, `authorized True`, `bounding is None` → il ramo `except client.exceptions.NoSuchKey` conserva il dataset base.
- **Casi coperti**: error path interno (metadata mancante) senza far cadere la risposta.

#### `test_catalog_unknown_license_and_attribution_do_not_break_response_EXT`
- **Obiettivo**: nomi license/attribution non presenti nel DB non bloccano il catalogo (vengono conservati ma non arricchiti).
- **Setup**: `.zmetadata` con `UNKNOWN_ATTR_NAME`/`UNKNOWN_LICENSE_NAME`; DB fake vuoto.
- **Assert**: `200`; `attribution == "UNKNOWN_ATTR_NAME"` ma `attribution_description`/`attribution_url` `None`; idem per license → enrichment assente, nessun crash.
- **Casi coperti**: ramo "nome noto in `.zattrs` ma assente nel DB" (log warning lato backend).

#### `test_catalog_pagination_uses_next_continuation_token_EXT`
- **Obiettivo**: quando S3 tronca la lista, il catalogo usa `NextContinuationToken` per la pagina successiva.
- **Setup**: due pagine; pagina 1 `IsTruncated True` + `NextContinuationToken "token-page-two"`, pagina 2 `IsTruncated False`; `.zmetadata` per entrambe.
- **Assert**: gli `id` sono `["page-one.zarr", "page-two.zarr"]`; `len(fake_client.list_calls) == 2`; `"ContinuationToken" not in list_calls[0]`; `list_calls[1]["ContinuationToken"] == "token-page-two"` → la paginazione passa il token **solo** dalla seconda chiamata.
- **Casi coperti**: happy path paginazione + invariante sui parametri delle chiamate S3.

## 5. Call chain

```
# Helper puri (nessun HTTP)
arco.guess_mime_type("metadata.json")  → MimeTypes().guess_type(...) → "application/json"
arco._round_coord(value)               → round(float(value), 2)  oppure  value (TypeError/ValueError)

# Proxy
GET /api/arco/<path:object_path>
  → ArcoResource.get
    → validate_access_key_from_request()   (no/errata auth → Unauthorized → 401)
    → arco.s3.get_instance() [FAKE].client.get_object(Bucket="arco", Key=path)
        → ClientError Code=="NoSuchKey" → NotFound → 404
        → altro ClientError → raise Exception → (500? ARCO-001: oggi diverso → skip)
    → Response(body, mimetype=guess_mime_type(filename)) → 200

# Catalogo (PUBBLICO, senza header)
GET /api/arco/datasets
  → ArcoDatasetsResource.get
    → arco.sqlalchemy.get_instance() [FAKE] → Attribution.query.all() + License.query.all()
    → arco.s3.get_instance() [FAKE].client.list_objects_v2(Bucket="arco", Delimiter="/", [ContinuationToken])
        per CommonPrefix endswith(".zarr/"):
          → client.get_object(Key="<root>/.zmetadata")
              → presente → enrich (bounding _round_coord, attribution/license/group)
              → client.exceptions.NoSuchKey → fallback dataset base
        → IsTruncated? → continuation_token = NextContinuationToken → loop
    → marshal_with(DatasetSchema(many=True)) → 200
```

## 6. Comportamenti nascosti

- **`pytest.fail` come "sentinella" di mock**: nei due test "rejected before S3", `arco.s3.get_instance` è sostituito con `lambda: pytest.fail(...)`. Non è un mock di dati ma una **trappola**: prova che il ramo S3 non viene eseguito quando l'auth fallisce.
- **`pytest.skip` (ARCO-001)**: `test_proxy_s3_non_no_such_key_returns_server_error_EXT` si **autoesclude** se il backend non risponde `500`. In CI può apparire `skipped` senza fallire: la copertura del ramo "errore S3 generico → 500" è **sospesa**, non verificata (il backend fa `raise Exception` e il wrapper restapi oggi non mappa a 500).
- **Due meccanismi distinti di "chiave mancante"**: il **proxy** usa `botocore.exceptions.ClientError` con `Error.Code == "NoSuchKey"`; il **catalogo** usa `except client.exceptions.NoSuchKey`. I fake li modellano separatamente (`_client_error_EXT` vs `_NoSuchKey_EXT` esposto da `_FakeS3Client_EXT.exceptions`). È un dettaglio non ovvio e correttamente replicato.
- **Catalogo pubblico**: i test catalogo non inviano header e ottengono `200`, documentando esplicitamente l'assenza di auth (cosa che la baseline catalogo **non** fa, anzi invia header inutili).
- **Tracciamento delle chiamate S3**: `_FakeS3Client_EXT` registra `list_calls`/`get_calls`; la paginazione è verificabile **osservando i parametri** (presenza/assenza di `ContinuationToken`) senza S3 reale.
- **Helper "puri" sotto marker `integration`**: `guess_mime_type`/`_round_coord` non fanno HTTP; pur essendo unit test, ereditano il marker `integration`/`deterministic` del modulo.
- **`fresh_access_key`** è l'unico stato persistente reale (chiave del default user); i fake sono in memoria e rimossi da pytest.
- **`_FakeBody_EXT.read()` non consuma il buffer**: ritorna sempre gli stessi byte (i test non verificano lo streaming).

## 7. Checklist di revisione

- [ ] **ARCO-001**: decidere se correggere il backend perché un `ClientError` S3 non-`NoSuchKey` diventi davvero `500` (oggi `raise Exception` generico) e riattivare l'assert; finché c'è lo `skip`, quel ramo **non è verificato**.
- [ ] Verificare in [endpoints/arco.py](projects/mistral/backend/endpoints/arco.py) il ramo `else: raise Exception from e` del proxy: è il punto esatto coperto/skippato da ARCO-001.
- [ ] Confermare che il catalogo debba essere pubblico (i test EXT lo assumono chiamando senza header) e allineare la baseline.
- [ ] Verificare che il filtro `.zarr/` e il fallback su `.zmetadata` mancante siano i contratti desiderati.
- [ ] Confermare che la paginazione passi `ContinuationToken` solo dalla 2ª chiamata (invariante asserita).
- [ ] Valutare se i due helper puri vadano marcati come unit (non `integration`).

## 8. Possibili criticità

- **Ramo 500 non garantito (ARCO-001)**: il test del `ClientError` generico fa `pytest.skip` nel backend attuale → **falso senso di copertura** sull'errore server del proxy. È onesto e documentato, ma quel contratto resta non verificato (e il backend solleva un `Exception` nudo, anti-pattern).
- **Fake elaborati = costo di manutenzione**: l'infrastruttura `_Fake*_EXT` riproduce in dettaglio il contratto S3/DB. Se l'endpoint cambiasse il modo di leggere `.zmetadata`/paginare, i fake andrebbero aggiornati a mano; rischio di drift fake-vs-reale (es. forme di `ClientError`/`exceptions`).
- **Over-mocking strutturale**: nessun test EXT tocca S3/DB reali; la copertura è di logica del controller, non di integrazione end-to-end (coerente con lo scopo "edge", ma da non confondere con copertura del connettore).
- **Marker fuorviante sui puri**: `guess_mime_type`/`_round_coord` sono unit test marcati `integration`; impatto minimo ma rende meno chiara la tassonomia della suite.
- **Assert di paginazione legati ai parametri interni**: il test ispeziona `list_calls[1]["ContinuationToken"]`; è white-box sul protocollo S3 — robusto ma sensibile a refactor del modo in cui i kwargs vengono costruiti.
- **Dipendenza dal default user** in `fresh_access_key` (test proxy): possibile accoppiamento d'ordine con i moduli access-key in esecuzioni parallele.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_guess_mime_type_returns_known_json_type_EXT` | `arco.guess_mime_type` | mimetype JSON | — (puro) | — | Bassa |
| `test_round_coord_handles_numbers_strings_and_none_EXT` | `arco._round_coord` | rounding + fallback (×4 param) | — (puro) | — | Bassa |
| `test_proxy_missing_basic_auth_is_rejected_before_s3_EXT` | `ArcoResource.get` + auth | 401 senza header, S3 non toccato | `pytest.fail` su `s3.get_instance` | `client`, `monkeypatch` | Bassa |
| `test_proxy_wrong_basic_auth_is_rejected_before_s3_EXT` | `ArcoResource.get` + auth | 401 con key errata, S3 non toccato | `pytest.fail` su `s3.get_instance` | `client`, `monkeypatch` | Bassa |
| `test_proxy_s3_no_such_key_returns_404_EXT` | `ArcoResource.get` (ClientError NoSuchKey) | 404 su oggetto assente | `MagicMock` S3 + `ClientError` | `client`, `fresh_access_key`, `monkeypatch` | Media |
| `test_proxy_s3_non_no_such_key_returns_server_error_EXT` | `ArcoResource.get` (else `raise Exception`) | **skip** se ≠500 (ARCO-001), altrimenti 500 | `MagicMock` S3 + `ClientError` | `client`, `fresh_access_key`, `monkeypatch` | Media (skippabile) |
| `test_proxy_sets_mimetype_from_object_filename_EXT` | `ArcoResource.get` + `guess_mime_type` | 200 + mimetype JSON + body invariato | fake S3 (`_FakeBody_EXT`) | `client`, `fresh_access_key`, `monkeypatch` | Media |
| `test_catalog_keeps_only_zarr_prefixes_and_enriches_metadata_EXT` | `ArcoDatasetsResource.get` | filtro `.zarr/` + enrichment + rounding | fake S3 + fake DB | `client`, `monkeypatch` | Alta |
| `test_catalog_missing_zmetadata_keeps_default_dataset_fallback_EXT` | `ArcoDatasetsResource.get` (NoSuchKey) | fallback dataset base, `bounding` None | fake S3 + fake DB | `client`, `monkeypatch` | Media |
| `test_catalog_unknown_license_and_attribution_do_not_break_response_EXT` | `ArcoDatasetsResource.get` | nomi sconosciuti conservati, non arricchiti | fake S3 + fake DB | `client`, `monkeypatch` | Media |
| `test_catalog_pagination_uses_next_continuation_token_EXT` | `ArcoDatasetsResource.get` | paginazione via `NextContinuationToken` | fake S3 (tracking `list_calls`) | `client`, `monkeypatch` | Alta |
