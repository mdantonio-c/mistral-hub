# Review — `test_dballe_query_parsing_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/services/test_dballe_query_parsing_EXT.py](projects/mistral/backend/tests/integration/services/test_dballe_query_parsing_EXT.py)
- **Scopo**: verificare i parser di query/filtri del service DB-All.e — da stringa a dict (`from_query_to_dic`), da filtri/query a liste ordinate di campi DB-All.e (`from_filters_to_lists`, `from_query_to_lists`), traduzione per le mappe (`parse_query_for_maps`), parsing per l'estrazione observed con validazione delle reti (`parse_query_for_data_extraction`), routing del DSN aggregazioni pluvio (`is_query_for_pluvio_aggregations`) ed espansione itertools delle combinazioni multi-valore (`get_queries_and_dsn_list_with_itertools`).
- **Tipologia**: **unit / service-level**, nonostante il marker. I metodi sono trasformazioni Python deterministiche: **non** aprono DB-All.e, **non** leggono summary JSON, **non** interrogano dataset reali. Quattro test usano `monkeypatch` per sostituire **solo** la mappa dataset→reti e il DSN aggregazioni (contratti dipendenti dalla config runtime), restando comunque locali. Marker dichiarati: `integration`, `deterministic` (vedi §6 per la discrepanza marker↔natura reale).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `BeDballe.from_query_to_dic` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2283) | Stringa query → dict; `reftime` parsato in `datetimemin`/`datetimemax`, `license` scalare, gli altri param → liste via split `" or "`. |
| `BeDballe.from_filters_to_lists` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2476) | Dict di filtri `{code}` → `(fields, queries)`; rinomina `network→rep_memo`, `product→var`, `timerange→trange`; `level`/`timerange` → tuple; chiavi non ammesse **saltate**. |
| `BeDballe.from_query_to_lists` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2510) | Dict query già parsato → `(fields, queries)` mantenendo ordine; `level`/`timerange` → tuple, `datetimemin`/`max` → `[value]`. |
| `BeDballe.parse_query_for_maps` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2419) | Query API → dict con nomi cursore DB-All.e; `timerange`/`level` → tuple, `latmin`/… passthrough. |
| `BeDballe.parse_query_for_data_extraction` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2615) | Costruisce `(fields, queries)` per l'estrazione observed; valida che le reti richieste siano nel dataset, altrimenti `InvalidFiltersException`; aggiunge reftime. |
| `BeDballe.parse_data_extraction_reftime` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2575) | `from`/`to` → datetime **naive** (`replace(tzinfo=None)`). |
| `BeDballe.is_query_for_pluvio_aggregations` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L2985) | `product[0]=="B13011"` + `timerange` con `p2` multiplo orario di 3600 (1..24) → `AGGREGATIONS_DSN`, altrimenti `None`. |
| `BeDballe.get_queries_and_dsn_list_with_itertools` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L3005) | Separa param singoli/multipli; `itertools.product` sui multipli → lista di `{query, aggregations_dsn}`. |
| `arki_service.get_observed_dataset_params` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L22) (alias di `BeArkimet`) | Mappa dataset→reti; **monkeypatchata** nei test di estrazione. |
| `BeDballe.AGGREGATIONS_DSN` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L35) | `Env.get("AGGREGATIONS_DSN", "")`; **monkeypatchato** nei test di aggregazione. |
| `InvalidFiltersException` | [exceptions.py](projects/mistral/backend/exceptions.py) | Sollevata quando una rete richiesta non è nel dataset. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `BeDballe` | classe service | [services/dballe.py](projects/mistral/backend/services/dballe.py) | Solo metodi statici di parsing esercitati; nessuna connessione DB-All.e. |
| `dballe_service.arki_service` | alias | [services/dballe.py](projects/mistral/backend/services/dballe.py#L22) | `BeArkimet as arki_service`; `get_observed_dataset_params` sostituito via `monkeypatch.setattr`. |
| `monkeypatch` | fixture | `pytest` (built-in) | Usata in 4/8 test; ripristino automatico a fine test (nessun cleanup manuale). |
| `InvalidFiltersException` | eccezione | [exceptions.py](projects/mistral/backend/exceptions.py) | Atteso in `pytest.raises` nel test di rete fuori dataset. |
| `itertools.product` | stdlib | `itertools` (in `dballe.py`) | Espansione combinazioni multi-valore. |
| `datetime` (`dt`) | stdlib | `datetime` | Confronto esatto dei `datetime` parsati (naive). |
| `pytest.mark.integration` / `deterministic` | marker | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L8) | Solo classificazione. |

> **Nota infra**: nessun `conftest.py`/`support` locale in `integration/services/`. L'unica fixture usata è la built-in `monkeypatch`; le fixture condivise ([`test_runtime`/`cleanup_registry`](projects/mistral/backend/tests/conftest.py#L31)) non sono autouse e non vengono richieste.

## 4. Analisi dettagliata di ogni test

> Tutti i test sono metodi della classe `TestDballeQueryParsing` (raggruppamento, nessun setup di classe).

### `test_from_query_to_dic_parses_reftime_and_multi_value_filters`
- **Obiettivo**: stringa query (con `reftime`, filtri multi-valore, `license` scalare) → dict downstream.
- **Backend coinvolto**: `from_query_to_dic`.
- **Flusso**: stringa con `reftime: >=… ,<=…; level…; product…; timerange…; network…; license:public`.
- **Setup**: nessun monkeypatch; stringa sintetica.
- **Assert**: `datetimemin`/`datetimemax` = `dt.datetime` esatti; `level`/`product`/`timerange`/`network` = liste (split `" or "`); `license == "public"` (scalare, **non** lista).
- **Casi coperti**: happy path parsing. `reftime` → `datetimemin`/`max`; gli altri param via `params_list`.

### `test_from_filters_to_lists_maps_frontend_codes_to_dballe_fields`
- **Obiettivo**: dict di filtri `{code}` → fields ordinati + liste valori; conferma che i filtri non ammessi vengono saltati.
- **Backend coinvolto**: `from_filters_to_lists`.
- **Flusso**: filtri `level/network/product/timerange` + `ignored`.
- **Setup**: dict letterale (l'ordine determina l'ordine dei `fields`).
- **Assert**: `fields == ["level", "rep_memo", "var", "trange"]` (chiave `ignored` **assente**); `queries == [[(1,None,None,None)], ["agrmet"], ["B13011"], [(1,0,3600)]]`.
- **Casi coperti**: rinomina campi, conversione tuple, skip filtri ignoti. Nota: in `level` lo `"0"` → `None`; in `timerange` lo `0` resta `0` (asimmetria, §6).

### `test_from_query_to_lists_maps_query_dictionary_to_dballe_lists`
- **Obiettivo**: dict query già parsato → liste mantenendo ordine e conversioni tuple.
- **Backend coinvolto**: `from_query_to_lists`.
- **Flusso**: query con `network` (2 valori), `timerange`, `level`, `datetimemin`.
- **Setup**: nessun monkeypatch.
- **Assert**: `fields == ["rep_memo", "trange", "level", "datetimemin"]`; `queries == [["agrmet","fidupo"], [(1,0,3600)], [(1,None,None,None)], [datetimemin]]` (il `datetime` incapsulato in lista).
- **Casi coperti**: happy path; `datetimemin` → `[value]`, niente accesso a summary DB-All.e.

### `test_parse_query_for_maps_translates_api_names_to_dballe_names`
- **Obiettivo**: parametri query mappe → nomi campo cursore DB-All.e.
- **Backend coinvolto**: `parse_query_for_maps`.
- **Flusso**: query con `network/product/timerange/level/datetimemin/latmin`.
- **Setup**: nessun monkeypatch.
- **Assert**: dict esatto `{rep_memo:"agrmet", var:"B13011", trange:(1,0,3600), level:(1,None,None,None), datetimemin:dt, latmin:44.0}` (`latmin` passa come `allowed_key`).
- **Casi coperti**: traduzione nomi + tuple per `timerange`/`level` + passthrough chiavi ammesse. (Vedi §6 per la precedenza `or`/`and` su `level`.)

### `test_parse_query_for_data_extraction_uses_dataset_networks_and_reftime` — **monkeypatch**
- **Obiettivo**: parsing estrazione observed con mappa dataset→reti fittizia (ramo positivo).
- **Backend coinvolto**: `parse_query_for_data_extraction` → `from_filters_to_lists` + `parse_data_extraction_reftime`.
- **Flusso**: `monkeypatch` di `arki_service.get_observed_dataset_params` → `dataset-a: ["agrmet","urbane"]`; filtri `network=agrmet`, `product=B13011`; reftime `2020-04-06T00:00:00Z`→`02:00:00Z`.
- **Setup**: `monkeypatch.setattr(dballe_service.arki_service, "get_observed_dataset_params", fake)`.
- **Assert**: `fields == ["rep_memo","var","datetimemin","datetimemax"]`; `queries == [["agrmet"],["B13011"],[2020-04-06 00:00],[2020-04-06 02:00]]` (reftime **naive**). `agrmet ⊆ {agrmet,urbane}` → nessuna eccezione; poiché `rep_memo` è già nei fields, le reti del dataset **non** vengono aggiunte.
- **Casi coperti**: happy path estrazione + validazione reti superata + reftime appeso.

### `test_parse_query_for_data_extraction_rejects_network_outside_dataset` — **monkeypatch**
- **Obiettivo**: rifiutare una rete non dichiarata dal dataset.
- **Backend coinvolto**: `parse_query_for_data_extraction`, ramo `if not all(elem in dataset_nets ...) → InvalidFiltersException`.
- **Flusso**: `monkeypatch` → `dataset-a: ["agrmet"]`; filtro `network=outside`.
- **Setup**: `monkeypatch.setattr(... get_observed_dataset_params ...)`.
- **Assert**: `pytest.raises(InvalidFiltersException)`.
- **Casi coperti**: error path validazione reti. Nessun reftime (ramo `reftime` saltato).

### `test_is_query_for_pluvio_aggregations_selects_configured_dsn` — **monkeypatch**
- **Obiettivo**: instradare i timerange orari di `B13011` verso il DSN aggregazioni.
- **Backend coinvolto**: `is_query_for_pluvio_aggregations`.
- **Flusso**: `monkeypatch` di `BeDballe.AGGREGATIONS_DSN = "dballe-aggregations"`; query `B13011`/`1,0,3600` vs `B11001`/`1,0,3600`.
- **Setup**: `monkeypatch.setattr(BeDballe, "AGGREGATIONS_DSN", "dballe-aggregations")`.
- **Assert**: `aggregation_dsn == "dballe-aggregations"` (p2=3600 ∈ multipli orari) e `normal_dsn is None` (product ≠ B13011).
- **Casi coperti**: selezione su product + `p2` orario. Non testa B13011 con `p2` non-orario (es. 1800).

### `test_get_queries_and_dsn_list_with_itertools_expands_filter_combinations` — **monkeypatch**
- **Obiettivo**: espandere i filtri multi-valore in query indipendenti, marcando solo la combinazione pluvio oraria.
- **Backend coinvolto**: `get_queries_and_dsn_list_with_itertools` → `is_query_for_pluvio_aggregations`.
- **Flusso**: `monkeypatch` del DSN; query con `network=[agrmet]` (singolo), `product=[B13011,B11001]` (multiplo), `timerange=[1,0,3600 ; 1,0,1800]` (multiplo).
- **Setup**: `monkeypatch.setattr(BeDballe, "AGGREGATIONS_DSN", "dballe-aggregations")`.
- **Assert**: lista di **4** dict `{query, aggregations_dsn}` nell'ordine `itertools.product(product, timerange)`; solo `B13011 + 1,0,3600` ha `aggregations_dsn == "dballe-aggregations"`, gli altri `None`; `network` resta `["agrmet"]` in ogni combinazione.
- **Casi coperti**: prodotto cartesiano + routing DSN per combinazione. `network` (len 1) trattato come param singolo.

## 5. Call chain

```
from_query_to_dic(q)                                     [test_from_query_to_dic]
  → split(";") → match params_list
  → reftime: >= → datetimemin ; <= → datetimemax ; = → entrambi
  → license → scalare ; altri → split(" or ") → lista

from_filters_to_lists(filters)                           [test_from_filters_to_lists]
  → key in {level,network,product,timerange} → rinomina dballe_keys
  → level/timerange → tuple (level "0"→None) ; else code string
  → key ignota → continue (skip)

from_query_to_lists(query)                               [test_from_query_to_lists]
  → analogo, con datetimemin/max → [value]

parse_query_for_maps(query)                              [test_parse_query_for_maps]
  → to_parse → dballe_keys ; (timerange) or (level and not tuple) → tuple
  → allowed_keys/dballe_keys → passthrough

parse_query_for_data_extraction(datasets, filters, reftime)   [test_data_extraction_*]
  → dataset_nets = arki_service.get_observed_dataset_params(ds)   (MONKEYPATCH)
  → filters → from_filters_to_lists
  → rep_memo presente? reti ⊄ dataset_nets → InvalidFiltersException
  → reftime → parse_data_extraction_reftime (naive) → append datetimemin/max
  → rep_memo assente? → append dataset_nets

is_query_for_pluvio_aggregations(query_dict)             [test_is_query_for_pluvio]
  → product[0]=="B13011" and timerange and p2 in [3600..86400] → AGGREGATIONS_DSN  (MONKEYPATCH)
  → else None

get_queries_and_dsn_list_with_itertools(original_query)  [test_get_queries_itertools]
  → split single_params (scalar / len==1) vs list_params (multi)
  → itertools.product(*list_params) → per combinazione {query, dsn}   (dsn via MONKEYPATCH)
```

## 6. Comportamenti nascosti

- **Marker fuorviante**: classificati `integration` ma sono **unit/service-level**; nessun DB-All.e, nessun summary, nessun dataset reale. Il `monkeypatch` sostituisce contratti runtime ma la logica resta locale.
- **`level "0"` → `None`, `timerange "0"` → `0`**: asimmetria voluta nel codice (`if key == "level" and v == "0"`). Visibile nei risultati attesi `(1,None,None,None)` per `level` vs `(1,0,3600)` per `timerange`. Facile da fraintendere in revisione.
- **`license` scalare** in `from_query_to_dic`: a differenza degli altri param non viene incapsulato in lista.
- **Precedenza `or`/`and` in `parse_query_for_maps`**: la condizione `key == "timerange" or key == "level" and not isinstance(value, tuple)` si valuta come `(timerange) or (level and not tuple)`. Quindi `timerange` è **sempre** convertito a tuple, `level` solo se non è già una tuple. Sottigliezza non evidente; il test passa valori-lista, non tuple.
- **reftime naive nell'estrazione**: `parse_data_extraction_reftime` fa `replace(tzinfo=None)`; il `Z` in input viene scartato (datetime naive), coerente con i confronti del test.
- **`monkeypatch` sull'alias di modulo**: il patch agisce su `dballe_service.arki_service.get_observed_dataset_params` (cioè `BeArkimet`); usa l'alias importato, non il nome originale della classe. Da tenere presente se il riferimento cambiasse.
- **`AGGREGATIONS_DSN` default `""`**: in produzione vale `Env.get("AGGREGATIONS_DSN", "")` (stringa vuota). I test lo monkeypatchano, quindi **non** dipendono dall'ambiente; ma il comportamento con DSN vuoto/non configurato non è testato.
- **itertools: liste `len==1` trattate come singole**: in `get_queries_and_dsn_list_with_itertools` un valore `[x]` finisce in `single_params`, non nel prodotto cartesiano (per questo `network=["agrmet"]` non moltiplica le combinazioni).
- **`is_query_for_pluvio_aggregations` legge `product[0]`/`timerange[0]`**: assume liste non vuote; query senza `product`/`timerange` o con liste vuote non sono testate (potenziale `IndexError`/`KeyError`).
- **Nessuno `skip`**: tutti e otto i test eseguono sempre; i monkeypatch sono ripristinati automaticamente.

## 7. Checklist di revisione

- [ ] Confermare che la natura **unit/service** sia voluta nonostante marker/collocazione `integration`.
- [ ] Verificare che l'asimmetria `level "0"→None` vs `timerange "0"→0` sia intenzionale (è coerente fra `from_filters_to_lists`, `from_query_to_lists`, `parse_query_for_maps`).
- [ ] Rivedere la precedenza `or`/`and` in `parse_query_for_maps`: confermare che `level` debba essere convertito solo se non già tuple e `timerange` sempre.
- [ ] Valutare copertura per `is_query_for_pluvio_aggregations` con `B13011` + `p2` non-orario (es. 1800) e per query senza `product`/`timerange`.
- [ ] Verificare il comportamento con `AGGREGATIONS_DSN` vuoto/non configurato (oggi sempre monkeypatchato).
- [ ] Confermare che il `monkeypatch` su `dballe_service.arki_service` sia il punto d'aggancio corretto e stabile.
- [ ] Considerare un test del ramo `parse_query_for_data_extraction` **senza** filtri (append di `dataset_nets`) e **senza** `rep_memo`.

## 8. Possibili criticità

- **Robustezza degli accessi indicizzati**: `is_query_for_pluvio_aggregations` e i parser accedono a `value[0]`/`split(",")[2]` assumendo struttura ben formata; input degeneri (liste vuote, chiavi mancanti) non sono coperti e potrebbero sollevare `IndexError`/`KeyError`.
- **Dipendenza dall'ordine d'inserzione**: `from_filters_to_lists`/`from_query_to_lists`/`get_queries_and_dsn_list_with_itertools` producono ordini che derivano dall'ordine delle chiavi del dict d'ingresso; cambi a monte potrebbero rompere asserzioni che confrontano liste posizionali.
- **Precedenza booleana sottile** in `parse_query_for_maps`: comportamento corretto ma non ovvio; rischio di regressione se qualcuno "normalizzasse" la condizione con parentesi diverse.
- **Config runtime mascherata dai monkeypatch**: i contratti reali (`get_observed_dataset_params`, `AGGREGATIONS_DSN`) sono sostituiti; eventuali rotture lato configurazione non emergono qui (sono demandate agli smoke/integration veri).
- **`p2` orario hard-coded** (`range(1,25)` × 3600): la finestra "oraria" è cablata; un cambio dei multipli ammessi non sarebbe intercettato dal test, che verifica solo 3600.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_from_query_to_dic_parses_reftime_and_multi_value_filters` | `from_query_to_dic` | stringa → dict (reftime/liste/license scalare) | — | — | Media |
| `test_from_filters_to_lists_maps_frontend_codes_to_dballe_fields` | `from_filters_to_lists` | rinomina campi, tuple, skip ignoti | — | — | Media |
| `test_from_query_to_lists_maps_query_dictionary_to_dballe_lists` | `from_query_to_lists` | liste ordinate + tuple + datetime | — | — | Media |
| `test_parse_query_for_maps_translates_api_names_to_dballe_names` | `parse_query_for_maps` | nomi cursore + tuple + passthrough | — | — | Media |
| `test_parse_query_for_data_extraction_uses_dataset_networks_and_reftime` | `parse_query_for_data_extraction` | estrazione + reti valide + reftime naive | `monkeypatch` (`get_observed_dataset_params`) | `monkeypatch` | Media |
| `test_parse_query_for_data_extraction_rejects_network_outside_dataset` | `parse_query_for_data_extraction` | rete fuori dataset → `InvalidFiltersException` | `monkeypatch` (`get_observed_dataset_params`) | `monkeypatch` | Media |
| `test_is_query_for_pluvio_aggregations_selects_configured_dsn` | `is_query_for_pluvio_aggregations` | B13011+orario → DSN, altrimenti None | `monkeypatch` (`AGGREGATIONS_DSN`) | `monkeypatch` | Bassa |
| `test_get_queries_and_dsn_list_with_itertools_expands_filter_combinations` | `get_queries_and_dsn_list_with_itertools` | prodotto cartesiano + routing DSN | `monkeypatch` (`AGGREGATIONS_DSN`) | `monkeypatch` | Alta |
