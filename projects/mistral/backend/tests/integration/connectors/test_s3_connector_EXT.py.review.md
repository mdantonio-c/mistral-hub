# Review — `test_s3_connector_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/connectors/test_s3_connector_EXT.py](projects/mistral/backend/tests/integration/connectors/test_s3_connector_EXT.py)
- **Scopo**: verificare i contratti del connector S3 custom (`S3Ext`) di Meteo-Hub — validazione dei parametri obbligatori, costruzione dell'endpoint da `scheme/host/port`, precedenza dell'endpoint esplicito e del `verify_ssl` letto dalle variabili, gestione del fallimento del probe `list_buckets`, semantica di `is_connected` (client sano / client guasto / `disconnected`) e cleanup di `disconnect`.
- **Tipologia**: **unit / connector-level**, nonostante il marker. Nessuna connessione reale a MinIO/AWS, nessuna rete, nessun DB, nessun HTTP. `boto3.Session` è **monkeypatchato** con una sessione fake in-memory in tutti i test che chiamano `connect`; i metodi del connector sono invocati direttamente su istanze locali. Marker dichiarati: `integration`, `deterministic` (vedi §6 per la discrepanza marker↔natura reale).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `S3Ext.__init__` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py#L19) | Inizializza `self.client = None`. |
| `S3Ext.connect` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py#L25) | Merge `variables.copy()`+`kwargs`; valida `host/key_id/access_key` (→ `ServiceUnavailable`); costruisce `endpoint` (esplicito **o** `scheme://host:port`); apre `boto3.Session(key_id, access_key)`; crea `session.client("s3", endpoint_url, verify, config)`; probe `list_buckets()` (→ `ServiceUnavailable` su errore); ritorna `self`. |
| `S3Ext.is_connected` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py#L77) | `False` se `disconnected` o manca `client`; altrimenti probe `list_buckets()` → `True`/`False` (except **largo**). |
| `S3Ext.disconnect` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py#L86) | `client = None`, `disconnected = True`. |
| `S3Ext.get_connection_exception` | [connectors/s3/__init__.py](projects/mistral/backend/connectors/s3/__init__.py#L91) | Ritorna `None` (nessuna lista eccezioni di retry). **Non testato.** |
| `Env.to_bool` | `restapi.env` | Parsing di `verify_ssl` (default `APP_MODE != "development"`). |
| `ServiceUnavailable` | `restapi.exceptions` | Sollevata su parametri mancanti **e** su probe fallito. |
| `Connector.services["s3"]` | `restapi.connectors` | Sorgente di `self.variables`; **monkeypatchata** via `setitem`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `monkeypatch` | fixture | `pytest` (built-in) | Patcha `s3_connector.boto3.Session`, `Connector.services["s3"]`, `S3Ext.app`; ripristino automatico a fine test. |
| `_FakeS3Client_EXT` | fake | (questo file) | Registra `list_buckets_calls`; può fallire a comando (`fail_list_buckets`) sollevando `RuntimeError`. |
| `_FakeSession_EXT` | fake | (questo file) | `client(service_name, **kwargs)` registra i kwargs e restituisce il fake client; nessuna connessione reale. |
| `_new_s3_connector_EXT` | helper | (questo file) | Imposta `S3Ext.app=object()` (placeholder) e `Connector.services["s3"]=variables`, poi istanzia `S3Ext()`. |
| `_install_fake_boto3_session_EXT` | helper | (questo file) | Sostituisce `boto3.Session` con una factory che registra le credenziali e restituisce `_FakeSession_EXT`; ritorna il `recorder`. |
| `s3_connector.boto3` | modulo | `boto3` (importato in `connectors/s3/__init__.py`) | Riferimento patchato direttamente nel modulo del connector. |
| `Connector` | classe base | `restapi.connectors` | Fornisce `services` e `self.variables`. |
| `ServiceUnavailable` | eccezione | `restapi.exceptions` | Target di `pytest.raises`. |
| `pytest.mark.integration` / `deterministic` | marker | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L9) | Solo classificazione. |

> **Nota infra**: nessun `conftest.py`/`support` locale in `integration/connectors/`. Le sole fixture usate sono la built-in `monkeypatch`; le fixture condivise ([`test_runtime`/`cleanup_registry`](projects/mistral/backend/tests/conftest.py#L31)) non sono autouse e non vengono richieste.

## 4. Analisi dettagliata di ogni test

> Tutti i test sono metodi della classe `TestS3Connector_EXT` (raggruppamento; nessun setup di classe).

### `test_connect_requires_host_key_id_and_access_key_EXT`
- **Obiettivo**: `connect` deve fallire esplicitamente se mancano `host`/`key_id`/`access_key`.
- **Backend coinvolto**: `connect` (ramo `missing` → `ServiceUnavailable`), **prima** di qualsiasi sessione boto3.
- **Flusso**: connector con `variables={}` e nessun kwarg → tutti e tre i parametri mancanti.
- **Setup**: solo `_new_s3_connector_EXT` (nessun fake boto3: non serve, il fallimento precede la sessione).
- **Assert**: `ServiceUnavailable` il cui messaggio contiene `"host"`, `"key_id"`, `"access_key"`.
- **Casi coperti**: error path / validazione input. Isola la macchina/container da env locali (variabili forzate a `{}`).

### `test_connect_builds_endpoint_from_host_port_scheme_EXT`
- **Obiettivo**: senza endpoint esplicito, comporre `scheme://host:port` e propagare `verify`.
- **Backend coinvolto**: `connect` (ramo `endpoint is None` → costruzione URL; `boto3.Session`; `session.client`; probe).
- **Flusso**: `connect(host="minio.test", port="9001", scheme="http", key_id, access_key, verify_ssl="false")`.
- **Setup**: fake client sano + `_install_fake_boto3_session_EXT`; `variables={}`.
- **Assert**: `returned is connector`; `session_calls == [{aws_access_key_id:"synthetic-id", aws_secret_access_key:"synthetic-secret"}]`; `client_call["service_name"]=="s3"`; `endpoint_url == "http://minio.test:9001"`; `verify is False`; `connector.client is fake_client`; `list_buckets_calls == 1`.
- **Casi coperti**: happy path completo + costruzione endpoint + parsing `verify_ssl` + probe singolo.

### `test_connect_respects_explicit_endpoint_and_verify_ssl_variable_EXT`
- **Obiettivo**: l'`endpoint` esplicito e `verify_ssl` dalle **variabili** devono prevalere.
- **Backend coinvolto**: `connect` con `variables` che imitano la config Rapydo (endpoint esplicito presente).
- **Flusso**: `variables={host, key_id, access_key, endpoint:"https://s3.explicit.test/custom", verify_ssl:"true"}`; `connect()` senza kwargs.
- **Setup**: fake client sano + fake session; `host` presente solo per superare il check obbligatorio.
- **Assert**: `endpoint_url == "https://s3.explicit.test/custom"` (host **ignorato** per l'URL); `verify is True`.
- **Casi coperti**: precedenza endpoint esplicito + `verify_ssl="true"` da variabili.

### `test_connect_raises_service_unavailable_when_bucket_probe_fails_EXT`
- **Obiettivo**: un fallimento di `list_buckets` deve bloccare la connessione.
- **Backend coinvolto**: `connect` (ramo `try/except` attorno al probe → `ServiceUnavailable(... ) from exc`).
- **Flusso**: fake client con `fail_list_buckets=True`; sessione e client vengono creati, poi il probe fallisce.
- **Setup**: `_FakeS3Client_EXT(fail_list_buckets=True)` + fake session; `variables={}`; `connect(host, key_id, access_key)`.
- **Assert**: messaggio `"Unable to connect to S3"`; `list_buckets_calls == 1` (probe eseguito una volta prima dell'errore).
- **Casi coperti**: error path sul probe, distinto dalla validazione input.

### `test_is_connected_returns_true_or_false_from_bucket_probe_EXT`
- **Obiettivo**: coprire i tre esiti osservabili di `is_connected`.
- **Backend coinvolto**: `is_connected` (guardia `disconnected` + probe `list_buckets`).
- **Flusso**: imposta direttamente `connector.client` e `connector.disconnected` senza passare da `connect`.
- **Setup**: due fake client (sano / guasto); nessun boto3 patchato (probe diretto sui fake).
- **Assert**: client sano + `disconnected=False` → `True`; client guasto + `disconnected=False` → `False`; client sano + `disconnected=True` → `False` (cortocircuito **prima** del probe).
- **Casi coperti**: matrice stato↔probe. Nota: `hasattr(self, "client")` è sempre vero (vedi §6), quindi solo `disconnected` e l'esito del probe determinano il risultato.

### `test_disconnect_resets_client_and_marks_connector_disconnected_EXT`
- **Obiettivo**: `disconnect` rimuove il client e marca il connector come chiuso.
- **Backend coinvolto**: `disconnect`.
- **Flusso**: assegna un fake client, poi `disconnect()`.
- **Setup**: nessun boto3/variabili; solo cleanup locale.
- **Assert**: `connector.client is None`; `connector.disconnected is True`.
- **Casi coperti**: teardown del connector.

## 5. Call chain

```
connect(**kwargs)                                          [test_connect_*]
  → variables = self.variables.copy(); variables.update(kwargs)   (Connector.services["s3"] MONKEYPATCH)
  → missing = [host,key_id,access_key non valorizzati] → ServiceUnavailable("Missing parameters: ...")
  → endpoint = variables.get("endpoint") or None
        → None? endpoint = f"{scheme}://{host}:{port}"  (default scheme=https, port=9000)
  → verify_ssl = Env.to_bool(variables.get("verify_ssl"), default=APP_MODE!="development")
  → session = boto3.Session(aws_access_key_id=key_id, aws_secret_access_key=access_key)   (MONKEYPATCH)
  → config = Config(retries, connect_timeout=5, read_timeout=60)
  → self.client = session.client("s3", endpoint_url=endpoint, verify=verify_ssl, config=config)
  → self.client.list_buckets()  → except → ServiceUnavailable("Unable to connect to S3") from exc
  → return self

is_connected()                                             [test_is_connected_*]
  → self.disconnected or not hasattr(self,"client")? → False
  → self.client.list_buckets() → True : except → False

disconnect()                                               [test_disconnect_*]
  → self.client = None ; self.disconnected = True
```

## 6. Comportamenti nascosti

- **Marker fuorviante**: classificato `integration` ma è **unit/connector-level**; nessun MinIO/AWS, nessuna rete, nessun DB. Il `monkeypatch` di `boto3.Session` chiude ogni accesso esterno.
- **`self.variables` da `Connector.services["s3"]`**: il valore è iniettato via `monkeypatch.setitem`; i test pilotano il connector senza Flask reale (l'`app` è un `object()` placeholder, anch'esso patchato).
- **Guardia `hasattr(self, "client")` di fatto morta**: `__init__` imposta sempre `self.client`, quindi `not hasattr(...)` è sempre `False`; solo `disconnected` e l'esito del probe contano in `is_connected`.
- **`endpoint = variables.get("endpoint") or None`**: un endpoint **stringa vuota** ricade nella costruzione `scheme://host:port` (per via dell'`or None`). Non testato esplicitamente con `""`.
- **`verify_ssl` default ambientale**: senza `verify_ssl` esplicito il default è `APP_MODE != "development"`. I test passano sempre un valore esplicito → il ramo **default da `APP_MODE`** non è coperto.
- **`Config` non assertato**: `retries={max_attempts:3, mode:standard}`, `connect_timeout=5`, `read_timeout=60` vengono passati al client ma non verificati.
- **`boto3.Session` riceve solo le credenziali**: `endpoint_url`/`verify`/`config` vanno a `session.client(...)`, non al costruttore della sessione (riflesso nelle asserzioni su `session_calls` vs `client_calls`).
- **`is_connected` con `except` larga**: qualunque eccezione del probe → `False` (nessuna distinzione fra errore di rete, permessi IAM o servizio giù).
- **`get_connection_exception` → `None`**: nessuna lista di eccezioni per i retry; non esercitato dai test.
- **Nessuno `skip`**: tutti e sei i test eseguono sempre; i monkeypatch sono ripristinati automaticamente.

## 7. Checklist di revisione

- [ ] Confermare che la natura **unit/connector** sia voluta nonostante marker/collocazione `integration`.
- [ ] Verificare che `self.variables` provenga davvero da `Connector.services["s3"]` (seam stabile lato restapi).
- [ ] Valutare un test per il ramo **default `verify_ssl` da `APP_MODE`** (oggi sempre esplicito).
- [ ] Considerare almeno un'asserzione su `Config` (retries/timeouts) o accettarne la non-copertura.
- [ ] Confermare che `list_buckets` sia il probe di salute desiderato (implicazioni IAM: con permessi limitati potrebbe fallire pur essendo "connessi").
- [ ] Documentare/ridurre la guardia morta `hasattr(self,"client")` in `is_connected`.
- [ ] Valutare copertura del caso `endpoint=""` (fallback silenzioso a `scheme://host:port`).

## 8. Possibili criticità

- **Marker mismatch (unit vs integration)**: la collocazione suggerisce I/O reale che qui non avviene; rischio di aspettative errate sulla copertura "live S3".
- **Default `verify_ssl` ambientale non testato**: il comportamento dipende da `APP_MODE`; un cambio di default non sarebbe intercettato.
- **`Config` (retry/timeout) non verificato**: regressioni su robustezza della connessione passerebbero inosservate.
- **`except` larga in `is_connected`**: maschera la causa del fallimento; difficile diagnosticare problemi di permessi vs servizio giù.
- **`get_connection_exception() -> None`**: la policy di retry del framework non ha eccezioni dedicate e non è coperta.
- **Probe basato su `list_buckets`**: dipende da un permesso ampio; non è un difetto del test, ma il contratto "connesso" è legato a quella specifica API.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_connect_requires_host_key_id_and_access_key_EXT` | `connect` (validazione) | parametri mancanti → `ServiceUnavailable` | `monkeypatch` (services/app) | `monkeypatch` | Bassa |
| `test_connect_builds_endpoint_from_host_port_scheme_EXT` | `connect` (endpoint+probe) | `scheme://host:port`, `verify=False`, 1 probe | `monkeypatch` (boto3.Session + fake client) | `monkeypatch` | Alta |
| `test_connect_respects_explicit_endpoint_and_verify_ssl_variable_EXT` | `connect` (variabili) | endpoint esplicito + `verify=True` prevalgono | `monkeypatch` (boto3.Session + fake client) | `monkeypatch` | Media |
| `test_connect_raises_service_unavailable_when_bucket_probe_fails_EXT` | `connect` (probe fail) | `list_buckets` fallito → `ServiceUnavailable` | `monkeypatch` (fake client che fallisce) | `monkeypatch` | Media |
| `test_is_connected_returns_true_or_false_from_bucket_probe_EXT` | `is_connected` | sano→True, guasto→False, disconnected→False | fake client (no boto3) | `monkeypatch` | Media |
| `test_disconnect_resets_client_and_marks_connector_disconnected_EXT` | `disconnect` | `client=None`, `disconnected=True` | fake client | `monkeypatch` | Bassa |
