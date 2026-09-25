# Review — `test_data_endpoint_auth.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo **baseline (NON `_EXT`)**: è il test legacy di autenticazione del dominio `data`. I moduli `*_EXT` del dominio dichiarano esplicitamente di **non** modificarlo e di non spostarne le fixture.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/test_data_endpoint_auth.py](projects/mistral/backend/tests/integration/data/test_data_endpoint_auth.py)
- **Scopo**: verificare che `POST /api/data` senza credenziali risponda `401`, cioè che il gate di autenticazione protegga l'endpoint di estrazione **prima** di qualsiasi validazione schema o logica applicativa.
- **Tipologia**: test di **integrazione HTTP** minimale (1 solo test). Marker: `integration`, `deterministic`.
- **Dimensione**: un singolo `client.post` anonimo + un solo assert sullo status code.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Data.post` (decoratore auth) | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | `@decorators.auth.require()` sull'endpoint `POST /data`: in assenza di token la richiesta è respinta con **401** prima di entrare nel corpo della `post`. |

> Nota: nessuna parte del **corpo** di `Data.post` (validazione, quota, submit Celery) viene eseguita: il test si ferma al solo controllo di autenticazione. Lo schema `DataExtraction` non viene neppure valutato.

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test; nessuna autenticazione applicata. |
| `API_URI` | costante | `restapi.tests` | Prefisso `/api`. |
| `pytest.mark.integration` / `deterministic` | marker | `pytest` (registrati in [tests/conftest.py](projects/mistral/backend/tests/conftest.py)) | Classificazione della suite. |

- **Nessun** uso di `support_EXT.py`, `cleanup_registry`, `monkeypatch`, utenti temporanei o fake: il test è volutamente autosufficiente e senza side effect.

## 4. Analisi dettagliata di ogni test

### `test_data_endpoint_requires_authentication`
- **Obiettivo**: proteggere il contratto “l'estrazione dati richiede autenticazione”.
- **Backend coinvolto**: solo il decoratore `@decorators.auth.require()` di `Data.post`.
- **Flusso**: una sola `POST` anonima a `/api/data`, senza header né body.
- **Setup**: nessuno (nessuna fixture oltre a `client`).
- **Assert**: `response.status_code == 401`.
- **Casi coperti**: error path / gate di sicurezza. Non verifica il body della risposta né attiva alcuna logica di validazione o submit.

## 5. Call chain

```
POST /api/data  (nessuna credenziale)
  → @decorators.auth.require()  → 401 Unauthorized
  ✗ (corpo di Data.post mai raggiunto: niente schema, niente DB, niente Celery)
```

## 6. Comportamenti nascosti

- **Stop pre-schema**: il `401` precede la deserializzazione di `DataExtraction`; inviare body assente o malformato è irrilevante per questo test.
- **Baseline preservata**: i moduli `test_data_endpoint_submission_EXT.py` e `test_data_endpoint_validation_EXT.py` dichiarano in testata di non toccare questo file; è il punto di ancoraggio della copertura auth del dominio.
- **Nessun cleanup**: non crea utenti, request o file → nessuna registrazione in `cleanup_registry`.

## 7. Checklist di revisione

- [ ] Confermare che `401` (e non `403`) sia il contratto atteso per richiesta **anonima** all'endpoint di estrazione.
- [ ] Verificare che il test resti volutamente minimale (solo gate auth) e che la copertura del corpo `Data.post` sia demandata ai moduli `*_EXT`.

## 8. Possibili criticità

- **Copertura volutamente parziale**: il test garantisce solo il gate auth; non protegge alcun ramo applicativo. È corretto, ma un reviewer non deve interpretarlo come copertura del comportamento di `POST /data`.
- **Assenza di asserzioni sul body**: accettabile per un gate 401, ma non distingue tra 401 “mancanza token” e altri 401 applicativi (non rilevante qui perché il corpo non è raggiunto).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_data_endpoint_requires_authentication` | `Data.post` (`auth.require()`) | `POST /data` anonimo → 401 | — | `client` | Bassa |
