# Review - `helpers/observed_windows.py`

> Modulo di supporto condiviso. Non contiene test. Raccoglie le finestre osservate
> reali e i piccoli helper HTTP che prima erano duplicati nei test di
> `/fields` e `/observations`.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/observed_windows.py](projects/mistral/backend/tests/helpers/observed_windows.py)
- **Scopo**: fissare in un solo punto le slice reali di agrmet usate dai test osservati (DBALLE 2020-04-06 00:00-01:00, Arkimet 2020-03-31/2020-04-01), l'override di `BeDballe.LASTDAYS` che fa apparire "recente" la slice DBALLE storica, e gli helper di URL, parsing e prerequisiti runtime.
- **Consumatori attuali**:
  - `integration/fields/support.py` e `integration/fields/test_fields_api.py`;
  - `integration/observed/test_observations_download.py` e `integration/observed/test_observations_edge_cases.py`;
  - `integration/observed/support.py`, solo per `lastdays_for_dballe_window` (sostituisce la funzione privata `_lastdays_override_for_dballe_window`).
- **Dipendenze runtime**: connettore SQLAlchemy inizializzato, fixture `cleanup_registry` e `test_runtime`, dataset `agrmet` presente nel catalogo e dati reali DBALLE/Arkimet nelle finestre fissate.
- **Dipendenze tra helper**: `create_dataset_test_user` da [helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py), `require_dataset` da [helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py).

## 2. Backend realmente esercitato

- `GET /api/fields` ([endpoints/fields.py](projects/mistral/backend/endpoints/fields.py)), solo da `require_dballe_product`, per scoprire un prodotto reale nella finestra DBALLE.
- `BeDballe.get_db_type` ([services/dballe.py](projects/mistral/backend/services/dballe.py)) in modo indiretto: legge `BeDballe.LASTDAYS`, che `dballe_window_override` sostituisce temporaneamente.
- Creazione e cancellazione di utenti temporanei con le API admin, tramite `create_dataset_test_user`.

## 3. Elementi definiti

### Costanti

| Simbolo | Valore | Uso |
|---|---|---|
| `FIELDS_ENDPOINT` / `OBSERVATIONS_ENDPOINT` | `{API_URI}/fields`, `{API_URI}/observations` | Endpoint sotto test. |
| `OBSERVED_DATASET_NAME` / `OBSERVED_NETWORK` | `agrmet` | Dataset e rete osservati reali. |
| `OBSERVED_LICENSE_GROUP` | `CCBY_COMPLIANT` | Licenza compatibile con agrmet. |
| `OBSERVED_MISMATCH_LICENSE_GROUP` | `CCBY-SA_COMPLIANT` | Licenza esistente ma incompatibile con la rete, per i casi 400. |
| `OBS_DBALLE_FIRST_DAY` | `datetime(2020, 4, 6)` | Primo giorno della slice DBALLE, base del calcolo di `LASTDAYS`. |
| `OBS_DBALLE_FROM` / `OBS_DBALLE_TO` | `2020-04-06 00:00` / `01:00` | Finestra DBALLE "recente" (con override). |
| `OBS_ARKIMET_FROM` / `OBS_ARKIMET_TO` | `2020-03-31 00:00` / `2020-04-01 23:59` | Finestra archiviata servita da Arkimet. |

Prima queste costanti erano ricopiate in `fields/support.py`,
`test_observations_download.py` e `test_observations_edge_cases.py`, con
nomi leggermente diversi (`OBSERVED_ENDPOINT` contro `OBSERVATIONS_ENDPOINT`).

### Funzioni

| Simbolo | Cosa fa |
|---|---|
| `api_url(endpoint, **params)` | Costruisce l'URL con `urlencode`, che esegue l'escape di `;`, `>=`, `<=` e degli spazi nel parametro `q`. Sostituisce `fields_url` e le `_url` locali. |
| `parse_response(response)` | Decodifica il payload con `BaseTests().get_content`. Sostituisce le `_parse_response` locali. |
| `lastdays_for_dballe_window(first_dballe_day)` | Restituisce il valore di `LASTDAYS` che pone il cutoff DBALLE/Arkimet al giorno prima di `first_dballe_day`, calcolato rispetto a `datetime.now()`. |
| `dballe_window_override(test_runtime, first_dballe_day=OBS_DBALLE_FIRST_DAY)` | Context manager basato su `test_runtime.override_attr(BeDballe, "LASTDAYS", ...)`: per la durata del blocco la slice DBALLE storica risulta recente. Sostituisce `observed_dballe_override` e le `_dballe_window_override` locali. |
| `require_observed_dataset_user(client, cleanup_registry, *, allowed_obs_archive=False)` | Recupera agrmet con `require_dataset` (skip se manca) e crea un utente temporaneo con grant esplicito su agrmet, con cleanup registrato. |
| `require_dballe_product(client, headers, test_runtime, query)` | Interroga `/fields` sotto `dballe_window_override` e restituisce il `code` del primo prodotto reale; skip se la risposta non e 200, se `summarystats.c <= 0` o se non ci sono prodotti. |

## 4. Contratto e isolamento

- L'override di `LASTDAYS` passa da `test_runtime.override_attr`, quindi viene ripristinato all'uscita dal blocco `with`, anche se l'assert interno fallisce.
- Il calcolo del valore avviene al momento della chiamata: non dipende da una data fissa scritta nel codice.
- `require_observed_dataset_user` concede agrmet in modo esplicito, quindi lo scenario resta portabile anche nei runtime dove agrmet e privato. L'utente viene cancellato dal `cleanup_registry`.
- Il modulo non modifica dataset, licenze o reti reali: i casi di rete privata usano `create_private_test_network` di `helpers/datasets.py`.
- `require_dballe_product` documenta che la `query` deve gia contenere finestra DBALLE, rete e licenza: l'helper non la costruisce.

## 5. Comportamenti nascosti

- **Skip automatici**: `require_observed_dataset_user` salta se agrmet non e nel catalogo; `require_dballe_product` salta se `/fields` non espone prodotti nella finestra DBALLE. In un runtime senza questi dati i test a valle risultano skipped, non falliti.
- **Dipendenza dall'orologio**: `lastdays_for_dballe_window` usa `datetime.now()`. Un test che chiama l'helper a cavallo della mezzanotte potrebbe ottenere un cutoff spostato di un giorno; con la slice di un'ora a inizio giornata il margine e comunque ampio.
- **Finestre fisse**: le date 2020 rispecchiano i dati caricati nell'ambiente di sviluppo/CI; se il dataset reale venisse ricaricato con un altro intervallo i test diventerebbero skipped o fallirebbero.

## 6. Checklist di revisione

- [ ] Verificare che le finestre `OBS_*` coincidano ancora con i dati agrmet caricati nel runtime di test.
- [ ] Verificare che ogni uso di `dballe_window_override` racchiuda tutte e sole le chiamate che devono vedere la slice DBALLE come recente.
- [ ] Verificare che nessun test osservato ridefinisca localmente costanti o helper gia presenti in questo modulo.

## 7. Limiti residui

- Le finestre e la rete sono specifiche di agrmet: altri dataset osservati richiederebbero nuove costanti.
- `parse_response` crea un `BaseTests` a ogni chiamata; il costo e trascurabile, ma l'istanza non e condivisa.

## 8. Validazione

```bash
.mhub-venv/bin/rapydo shell backend "env PYTEST_ADDOPTS='-rs -q' restapi tests --folder custom/integration/fields"
```

Esito: **20 passed, 1 skipped, 0 failed, 0 errors**. Lo skip e il bug backend noto di
`Fields.get` con `SummaryStats=False` sul ramo forecast, non legato a questo helper.

```bash
.mhub-venv/bin/rapydo shell backend "env PYTEST_ADDOPTS='-rs -q' restapi tests --folder custom/integration/observed"
```

Esito: **65 passed, 1 skipped, 0 failed, 0 errors**. Lo skip riguarda il ramo 404 di
`stationDetails`, che il backend non produce sulla slice agrmet DBALLE 2020-04-06 (risponde con un 200 vuoto).
