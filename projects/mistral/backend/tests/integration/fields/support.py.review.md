# Review — `fields/support.py` (infrastruttura di dominio)

> File di review per modulo di supporto. Non contiene test.
> Modulo: supporta **solo** i test `test_fields_api.py`, senza creare fixture globali.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/integration/fields/support.py`
- **Scopo**: centralizzare URL, **finestre dati ammesse**, utenti temporanei, dataset/licenze sintetici, override runtime e cleanup per coprire i rami OBS/map, OBS/dataset e FOR/Arkimet di `Fields.get`.
- **Tipologia**: modulo di supporto (costanti + dataclass + factory/helper con effetti su DB e su `cleanup_registry`).

## 2. Elementi definiti

### Costanti (finestre e identificatori)

| Costante | Valore | Ruolo |
|---|---|---|
| `FIELDS_ENDPOINT` | `{API_URI}/fields` | Base URL. |
| `OBSERVED_DATASET_NAME` / `OBSERVED_NETWORK` | `agrmet` | Dataset/network observed di riferimento. |
| `OBSERVED_LICENSE_GROUP` | `CCBY_COMPLIANT` | Gruppo licenza atteso per agrmet. |
| `OBSERVED_MISMATCH_LICENSE_GROUP` | `CCBY-SA_COMPLIANT` | Gruppo "sbagliato" per il test mismatch. |
| `OBS_DBALLE_FROM/TO` | `2020-04-06 00:00 / 01:00` | Finestra DBALLE recente. |
| `OBS_ARKIMET_FROM/TO` | `2020-03-31 / 2020-04-01` | Finestra archiviata. |
| `OBS_DBALLE_QUERY` / `..._WITHOUT_LICENSE` / `OBS_ARCHIVE_QUERY` | stringhe `q` | Query precostruite OBS. |
| `FORECAST_WINDOWS` | `(lm5 2021-10-19), (lm2.2 2019-09-10)` | Finestre forecast ammesse. |

### Dataclass

| Dataclass | Campi | Ruolo |
|---|---|---|
| `FieldsSyntheticDataset` | `id, arkimet_id, name, category, group_license_id, license_id` | Record minimo per i soli rami di validazione multi-dataset. |
| `ForecastFieldsCase` | `dataset_name, query, headers, content` | Scenario forecast reale autorizzato su una sola finestra. |

### Funzioni / factory

| Funzione | Effetti | Note di revisione |
|---|---|---|
| `fields_url(**params)` | `api_url(FIELDS_ENDPOINT, ...)` | wrapper di dominio su `helpers/observed_windows.py`. |
| `OBS_DBALLE_QUERY`, `OBS_DBALLE_QUERY_WITHOUT_LICENSE`, `OBS_ARCHIVE_QUERY` | query `/fields` costruite dalle costanti condivise | finestre e licenze vengono da `helpers/observed_windows.py`. |
| `create_dataset_test_user(...)` (da `helpers/auth.py`) | crea utente via API admin + cleanup | permessi `open_dataset`/`allowed_obs_archive`/`datasets`; sostituisce il vecchio `create_fields_user` locale. |
| `create_fields_synthetic_dataset(...)` | crea `GroupLicense`+`License`+`Datasets` (+ eventuale `Attribution`) e registra `delete_test_dataset_bundle` (helpers/datasets.py) | bundle relazionale completo; l'attribution viene eliminata solo se creata dal helper. |
| `get_or_create_multim_forecast_dataset(...)` | riusa il record reale `multim-forecast` o ne crea uno sintetico | per il ramo multi-dataset 400. |
| `create_private_observed_dataset_for_all_available_products(...)` | crea gruppo OBS **privato** sintetico (controllo negativo) | ritorna il nome del gruppo. |
| `require_forecast_fields_case(...)` | prova lm5 poi lm2.2, utente autorizzato, verifica `c>0` | **`pytest.skip`** se nessuna finestra forecast espone dati. |

Helper non piu definiti qui e spostati in moduli condivisi, riusati anche dalla cartella `observed`:

- `projects/mistral/backend/tests/helpers/observed_windows.py`: costanti `OBSERVED_*`/`OBS_*`, `api_url`, `parse_response`, `dballe_window_override` (override di `BeDballe.LASTDAYS`, vedi §3), `require_observed_dataset_user`, `require_dballe_product`;
- `projects/mistral/backend/tests/helpers/datasets.py`: `require_dataset` (lookup per `name` o `arkimet_id`, **`pytest.skip`** se assente), `create_private_test_network` e `delete_test_dataset_bundle` (cleanup del bundle sintetico, che sostituisce il vecchio `delete_fields_dataset_bundle` locale).

## 3. Comportamenti nascosti

- **Override di `BeDballe.LASTDAYS` (cuore della portabilità OBS)**: `dballe_window_override` calcola `LASTDAYS` in modo che il cutoff cada il giorno **prima** del 2020-04-06, così `get_db_type` classifica quella data come **dballe** (recente) invece che archiviata. Riproduce la strategia della suite observed esistente e resta confinato al context manager `test_runtime.override_attr` (ripristino automatico in uscita). Senza, gli OBS happy path otterrebbero 401 (ramo archivio).
- **Nessuna mutazione del catalogo reale**: il vecchio helper che spostava agrmet su una licenza privata con commit (visibile a tutti per la durata del test e persistente se il teardown saltava) e stato sostituito da `create_private_test_network` in `helpers/datasets.py`: il dataset privato è sintetico (cleanup completo tramite `create_test_dataset`); il `monkeypatch` di `from_network_to_dataset` riguarda solo la rete sintetica e delega ogni altra rete alla funzione reale. `check_dataset_authorization` resta reale.
- **Skip silenziosi centralizzati**: `require_dataset` e `require_forecast_fields_case` decidono autonomamente di saltare; i test che li usano ereditano lo skip senza un `pytest.skip` esplicito al proprio interno. `require_forecast_fields_case` può skippare **anche** dopo aver ottenuto 200 ma con `summarystats.c <= 0` (continua a provare la finestra successiva e infine skippa).
- **Dataset sintetici "sufficienti"**: i rami multi-dataset falliscono **prima** del caricamento Arkimet reale; per questo il fake corretto è un catalogo SQL minimo (più, nei test, un monkeypatch del solo `get_datasets_category`). `dballe_dsn="DBALLE"` marca semanticamente un gruppo come OBS senza che alcun dato venga mai interrogato.
- **Cleanup difensivo e idempotente**: `delete_test_dataset_bundle` (helper condiviso di `helpers/datasets.py`) e i restore controllano l'esistenza di ogni riga prima di eliminarla (`query.get(...) is not None`), così un fallimento a metà setup non genera errori secondari che mascherino la causa.
- **Creazione utente via API admin**: `create_dataset_test_user` (`projects/mistral/backend/tests/helpers/auth.py`) usa `create_authenticated_test_user` + `register_test_user_cleanup`; il cleanup elimina utente e cartella output anche in caso di failure.
- **Attribution opzionale**: `create_fields_synthetic_dataset` riusa un'`Attribution` reale se esiste, altrimenti ne crea una temporanea e la marca per cleanup (`created_attribution_id`), evitando di toccare attribution reali quando già presenti.

## 4. Checklist di revisione

- [ ] Confermare che l'override di `LASTDAYS` resti allineato alla logica di `get_db_type` (soglia `LASTDAYS-1` + correzione orari notturni) e non diverga in futuro.
- [ ] Verificare che `create_private_test_network` (helpers/datasets.py) mappi solo la rete sintetica e deleghi tutte le altre alla mappatura Arkimet reale.
- [ ] Valutare la robustezza degli `pytest.skip` centralizzati: in CI senza finestre dati, quanti test del modulo diventano no-op?
- [ ] Confermare che i dataset sintetici non interferiscano con il catalogo reale (nomi `fields_ext_*`/uuid, cleanup relazionale completo).
- [ ] Verificare che `get_or_create_multim_forecast_dataset` non alteri un eventuale record `multim-forecast` reale (lo riusa in sola lettura, senza cleanup distruttivo).

## 5. Possibili criticità

- **Accoppiamento forte alle finestre dati hardcoded**: agrmet/lm5/lm2.2 e le date sono incise nel supporto; qualsiasi variazione del seed o dei dati runtime richiede modifiche qui e propaga skip/fail nei test.
- **Stato sintetico condiviso**: dataset/rete privati sono sintetici; agrmet e la sua licenza non vengono alterati. Resta il rischio di residui del bundle sintetico se il teardown non viene eseguito; la mappatura della sola rete sintetica è ripristinata da `monkeypatch` (vedi §3).
- **Skip "invisibili"**: spostare la decisione di skip nei helper rende i test più leggibili ma nasconde, a livello di singolo test, la condizione che porta al no-op — da tenere presente nei report CI.
- **Override basato su `datetime.now()`**: `dballe_window_override` calcola `LASTDAYS` rispetto alla data corrente; è corretto per la finestra fissa 2020-04-06, ma è una dipendenza implicita dall'orologio di sistema (gestita, non eliminata).
