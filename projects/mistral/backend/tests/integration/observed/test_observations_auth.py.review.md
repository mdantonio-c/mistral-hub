# Review — `test_observations_auth.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo di **validazione precoce**: copre i rami che falliscono *prima* di qualsiasi lookup dei dati osservati.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/observed/test_observations_auth.py](projects/mistral/backend/tests/integration/observed/test_observations_auth.py)
- **Scopo**: verificare che `GET /api/observations` rifiuti con **400** le richieste **anonime** in cui mancano input obbligatori: (a) una `reftime` completa (manca un estremo) e (b) la clausola `license`.
- **Tipologia**: test di **integrazione HTTP** (controller reale + schema marshmallow + parsing query). Marker di modulo: `integration`, `deterministic`, `runtime_sensitive`.
- **Nota sul marker `runtime_sensitive`**: è applicato a livello di modulo per coerenza col dominio observed, ma **questi due test non dipendono dai dati runtime** né possono fare `pytest.skip`: falliscono entrambi alla validazione, prima di toccare DBALLE/Arkimet. Sono di fatto deterministici.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `MapsObservations.get` | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | `GET /api/observations` con `@decorators.auth.optional()`: i due rami di `BadRequest` esercitati sono "Reftime is missing" e "License group parameter is mandatory". |
| `ObservationsQuery` (schema) | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | Tutti i campi sono `required=False`: nessun 422 di schema; la validazione è **applicativa** dentro `get`. |
| `BeDballe.from_query_to_dic` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2283) | Parsa la stringa `q`; con `q="license:CCBY_COMPLIANT"` produce solo `{"license": ...}`, **senza** `datetimemin`/`datetimemax`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test; le chiamate sono **anonime** (nessun header passato). |
| `API_URI` | costante | `restapi.tests` | Prefisso `/api`. |
| `pytest.mark.*` | marker | modulo | `integration`, `deterministic`, `runtime_sensitive`. |

Nessuna fixture locale, nessun mock, nessun `monkeypatch`, nessun accesso DB diretto.

## 4. Analisi dettagliata di ogni test

### `test_observations_without_complete_reftime_returns_bad_request`
- **Obiettivo**: una query con `reftime` incompleta (qui addirittura assente, presente solo `license`) deve dare **400**.
- **Backend coinvolto**: `get` → `from_query_to_dic` → ramo `if not datetime_min or not datetime_max: raise BadRequest("Reftime is missing")`.
- **Flusso**: `q=license:CCBY_COMPLIANT` senza header → niente bbox → parsing query (`{license}`) → niente `networks` → niente `stationDetails` → `license` presente (supera il gate license) → `check_access_authorization(None, "CCBY_COMPLIANT", None)` (gruppo pubblico, nessun utente richiesto) → `datetime_min`/`datetime_max` assenti → **400**.
- **Setup**: nessuno (`arrange` costruisce solo la URL).
- **Assert**: `response.status_code == 400`.
- **Casi coperti**: error path di validazione reftime. Il test supera volutamente il gate `license` per arrivare a misurare **proprio** il controllo reftime.

### `test_observations_without_license_returns_bad_request`
- **Obiettivo**: una query **senza alcuna `license`** deve dare **400**.
- **Backend coinvolto**: `get` → ramo `if "license" not in query: raise BadRequest("License group parameter is mandatory")`.
- **Flusso**: `GET /observations` senza `q` e senza header → `q=""` (default) → blocco `if q:` saltato → niente `networks`/`stationDetails` → `license` assente → **400**, prima ancora del controllo reftime.
- **Setup**: nessuno.
- **Assert**: `response.status_code == 400`.
- **Casi coperti**: error path del gate license. È il **gate più a monte**: fallisce prima del controllo reftime.

## 5. Call chain

```
GET /api/observations?q=license:CCBY_COMPLIANT   (anonimo)
  → auth.optional() (user=None)
  → use_kwargs(ObservationsQuery)               (tutti opzionali → nessun 422)
  → MapsObservations.get
     → (bbox assente) → from_query_to_dic(q) → {"license": "CCBY_COMPLIANT"}
     → (networks assente) → (stationDetails False)
     → "license" in query? sì → check_access_authorization(None, "CCBY_COMPLIANT", None)  (gruppo pubblico)
     → datetime_min/datetime_max assenti → BadRequest("Reftime is missing")  → 400

GET /api/observations   (anonimo, nessun q)
  → MapsObservations.get
     → q == "" → parsing saltato
     → "license" not in query → BadRequest("License group parameter is mandatory")  → 400
```

## 6. Comportamenti nascosti

- **Schema permissivo**: `ObservationsQuery` non rende obbligatorio nulla; le 400 sono **logica applicativa** del controller, non rifiuti di marshmallow. Cambiare lo schema non cambierebbe questi rami.
- **Ordine dei gate**: `license` viene controllata **prima** di `reftime`. Per questo il primo test deve includere `license` per arrivare al ramo reftime, mentre il secondo si ferma prima.
- **`auth.optional()`**: l'endpoint accetta richieste anonime; nessuno dei due test richiede login. Il 400 non è quindi mascherato da un 401 di autenticazione.
- **`runtime_sensitive` ma deterministico**: a differenza del resto del dominio observed, questi test non hanno percorso di `skip` e non leggono dati reali.

## 7. Checklist di revisione

- [ ] Confermare che il contratto atteso sia **400** (e non 422) per input mancanti: dipende dal fatto che lo schema lasci i campi opzionali e deleghi la validazione al controller.
- [ ] Verificare che `"license:CCBY_COMPLIANT"` resti un gruppo **pubblico** nel runtime, così il primo test non incappi in un 401 anticipato (`check_access_authorization`) prima di raggiungere il controllo reftime.
- [ ] Valutare se il marker `runtime_sensitive` sia fuorviante per due test che non dipendono dal runtime.

## 8. Possibili criticità

- **Accoppiamento implicito alla pubblicità del gruppo licenza**: il primo test assume che `CCBY_COMPLIANT` sia pubblico; se diventasse privato, `check_access_authorization` solleverebbe `UnAuthorizedUser` → **401**, e il test fallirebbe pur restando "corretto" sul piano reftime. Il contratto verificato è quindi un po' più fragile di quanto sembri.
- **Marker fuorviante**: `runtime_sensitive` su test deterministici può confondere chi filtra la suite per marker.
- **Copertura volutamente minimale**: il modulo copre solo due rami di `BadRequest`; tutti gli altri (bbox incompleta, network inesistente, ecc.) sono coperti altrove (filters / edge cases EXT).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Skip silenzioso | Complessità |
|---|---|---|---|---|---|---|
| `test_observations_without_complete_reftime_returns_bad_request` | `get` → "Reftime is missing" | 400 su reftime incompleta (anonimo) | — | `client` | No | Bassa |
| `test_observations_without_license_returns_bad_request` | `get` → "License group parameter is mandatory" | 400 su license assente (anonimo) | — | `client` | No | Bassa |
