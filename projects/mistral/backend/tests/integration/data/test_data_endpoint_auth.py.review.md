# Review — `test_data_endpoint_auth.py`

> File di review per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo: test di autenticazione del dominio `data`. Gli altri test del dominio sono in moduli separati e non ne spostano le fixture.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/integration/data/test_data_endpoint_auth.py`
- **Scopo**: verificare che `POST /api/data` senza credenziali risponda `401`, cioè che il gate di autenticazione protegga l'endpoint di estrazione **prima** di qualsiasi validazione schema o logica applicativa.
- **Tipologia**: test di **integrazione HTTP** minimale (1 solo test). Marker: `integration`, `deterministic`.
- **Dimensione**: un singolo `client.post` anonimo + un solo assert sullo status code.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Data.post` (decoratore auth) | `projects/mistral/backend/endpoints/data.py` | `@decorators.auth.require()` sull'endpoint `POST /data`: in assenza di token la richiesta è respinta con **401** prima di entrare nel corpo della `post`. |

> Nota: nessuna parte del **corpo** di `Data.post` (validazione, quota, submit Celery) viene eseguita: il test si ferma al solo controllo di autenticazione. Lo schema `DataExtraction` non viene neppure valutato.

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test; nessuna autenticazione applicata. |
| `API_URI` | costante | `restapi.tests` | Prefisso `/api`. |
| `pytest.mark.integration` / `deterministic` | marker | `pytest` (registrati in `projects/mistral/backend/tests/conftest.py`) | Classificazione della suite. |

- **Nessun** uso di `support.py`, `cleanup_registry`, `monkeypatch`, utenti temporanei o fake: il test è volutamente autosufficiente e senza side effect.

## 4. Analisi dettagliata di ogni test

### `test_data_endpoint_requires_authentication`
- **Obiettivo**: proteggere il contratto “l'estrazione dati richiede autenticazione”.
- **Backend coinvolto**: solo il decoratore `@decorators.auth.require()` di `Data.post`.
- **Flusso**: una sola `POST` anonima a `/api/data`, senza header né body.
- **Setup**: nessuno (nessuna fixture oltre a `client`).
- **Assert**: `response.status_code == 401`.
- **Casi coperti**: error path / gate di sicurezza. Non verifica il body della risposta né attiva alcuna logica di validazione o submit.
- **Cosa non dimostra**: input, quote, routing o creazione della request.
- **Se fallisce, guarda**: il decoratore auth e il wiring dell'endpoint; un `400` al posto di `401` può indicare un diverso ordine dei controlli (schema valutato prima dell'autenticazione).

## 5. Call chain

```
POST /api/data  (nessuna credenziale)
  → @decorators.auth.require()  → 401 Unauthorized
  ✗ (corpo di Data.post mai raggiunto: niente schema, niente DB, niente Celery)
```

## 6. Comportamenti nascosti

- **Stop pre-schema**: il `401` precede la deserializzazione di `DataExtraction`; inviare body assente o malformato è irrilevante per questo test.
- **Copertura auth centralizzata**: è il punto di ancoraggio della copertura auth del dominio; `test_data_endpoint_submission.py` e `test_data_endpoint_validation.py` coprono gli altri rami di `Data.post`.
- **Nessun cleanup**: non crea utenti, request o file → nessuna registrazione in `cleanup_registry`.

## 7. Checklist di revisione

- [ ] Confermare che `401` (e non `403`) sia il contratto atteso per richiesta **anonima** all'endpoint di estrazione.
- [ ] Verificare che il test resti volutamente minimale (solo gate auth) e che la copertura del corpo `Data.post` sia demandata a `test_data_endpoint_submission.py` e `test_data_endpoint_validation.py`.

## 8. Possibili criticità

- **Copertura volutamente parziale**: il test garantisce solo il gate auth; non protegge alcun ramo applicativo. È corretto, ma un reviewer non deve interpretarlo come copertura del comportamento di `POST /data`.
- **Assenza di asserzioni sul body**: accettabile per un gate 401, ma non distingue tra 401 “mancanza token” e altri 401 applicativi (non rilevante qui perché il corpo non è raggiunto).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_endpoint_requires_authentication` | `Data.post` (`auth.require()`) | `POST /data` anonimo → 401 | — | `client` | Bassa |
