# Review — `test_queue_sorting_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy (fase quick wins).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tasks/test_queue_sorting_EXT.py](projects/mistral/backend/tests/integration/tasks/test_queue_sorting_EXT.py)
- **Scopo**: verificare il contratto di routing di `queue_sorting`, cioè la scelta della coda Celery (`operational_*` / `archived_*`) in base alla **categoria dataset** e alla **freschezza** del `reftime` rispetto a una finestra operativa di 3 giorni.
- **Tipologia**: test di **unità pura** su helper deterministico. Marker dichiarati: `integration`, `deterministic`; in pratica **non** tocca DB, broker, filesystem o Celery reale (vedi §8).
- **Conteggio**: 3 metodi di test, **10 casi** parametrizzati complessivi. Nessun `pytest.skip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `queue_sorting(dataset_type, reftime=None)` | [tasks/data_extraction_utilities.py](projects/mistral/backend/tasks/data_extraction_utilities.py#L5) | Mappa `(dataset_type, is_operational)` → nome coda; normalizza il `date_from` naive a UTC; `is_operational = date_from is not None and (now - date_from) < 3 giorni`. |

- Backend **realmente eseguito**: l'intera funzione (lookup `queue_map`, normalizzazione tz, confronto temporale).
- Backend **non** coinvolto: dispatch Celery, connessione broker, lettura dataset reali.

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `_FixedQueueSortingDateTime` | classe locale | nel file di test | Sottoclasse di `datetime` con `now()` congelato al `2026-05-28 12:00 UTC` (gestisce sia il ramo `tz=None` sia `tz` esplicito). |
| `frozen_queue_sorting_now` | fixture locale | nel file di test | `monkeypatch.setattr(data_extraction_utilities, "datetime", _FixedQueueSortingDateTime)`; ritorna l'istante congelato. |
| `monkeypatch` | fixture | `pytest` | Applica/ripristina il patch sul simbolo `datetime` del **modulo target**. |
| `data_extraction_utilities` | modulo | [tasks/data_extraction_utilities.py](projects/mistral/backend/tasks/data_extraction_utilities.py) | Modulo sotto test; importa direttamente `datetime`, quindi il patch va applicato al suo simbolo. |

## 4. Analisi dettagliata di ogni test

### `test_queue_sorting_dataset_type_routes_recent_and_old_reftimes` (param. ×4)
- **Obiettivo**: per ogni categoria (`FOR`, `SEA`, `RAD`, `OBS`) un reftime recente va sulla coda operativa, uno vecchio sulla archiviata.
- **Backend coinvolto**: `queue_sorting` completo (lookup + confronto temporale).
- **Flusso**: costruisce `recent_reftime` (now − 2 giorni) e `old_reftime` (now − 4 giorni) → chiama la funzione due volte → confronta con le code attese.
- **Setup**: `frozen_queue_sorting_now` (orologio congelato); `date_from` già `datetime` aware/naive secondo il caso.
- **Assert**: `recent_queue == expected_recent` e `old_queue == expected_old`.
- **Casi coperti**: matrice categoria × (operativo/archiviato); confine dei 3 giorni superato in entrambe le direzioni.

### `test_queue_sorting_naive_reftime_is_treated_as_utc` (param. ×2)
- **Obiettivo**: un `datetime` **naive** (senza tzinfo) viene promosso a UTC prima del confronto.
- **Backend coinvolto**: ramo `if date_from.tzinfo is None ...: replace(tzinfo=utc)`.
- **Flusso**: passa `date_from = datetime(2026,5,27,12,0,0)` (naive, recente) → attende coda operativa.
- **Setup**: usa la fixture **solo per il side effect** (`del frozen_queue_sorting_now`).
- **Assert**: `queue == expected_queue` (`operational_forecast` / `operational_observed`).
- **Casi coperti**: normalizzazione tz su input naive.

### `test_queue_sorting_missing_reftime_routes_to_archived_queue` (param. ×4)
- **Obiettivo**: `reftime=None` non può essere operativo → routing archiviato per ogni categoria.
- **Backend coinvolto**: ramo `reftime is None` → `is_operational=False`.
- **Flusso**: chiama `queue_sorting(dataset_type, reftime=None)`.
- **Setup**: fixture attiva per simmetria ma **non letta** (`del`); il ramo non legge alcuna data.
- **Assert**: `queue == expected_queue` (`archived_*`).
- **Casi coperti**: input mancante → fallback archiviato.

## 5. Call chain

```
queue_sorting(dataset_type, reftime)
  → now = datetime.now(timezone.utc)            # datetime monkeypatchato → 2026-05-28 12:00 UTC
  → date_from = reftime["date_from"] (se presente)
       → se naive: date_from.replace(tzinfo=utc)
  → is_operational = date_from is not None and (now - date_from) < timedelta(days=3)
  → queue_map[(dataset_type, is_operational)]   # FOR/SEA→forecast, RAD/OBS→observed
  → return "<operational|archived>_<forecast|observed>"
```

## 6. Comportamenti nascosti

- **Patch sul simbolo del modulo, non sul `datetime` globale**: poiché `data_extraction_utilities` fa `from datetime import datetime`, il test sostituisce `data_extraction_utilities.datetime`. Patchare `datetime` standard non avrebbe effetto.
- **Fixture usata per il solo side effect**: due test su tre fanno `del frozen_queue_sorting_now`; l'orologio congelato serve a rendere deterministico il confine dei 3 giorni anche quando il valore di ritorno non viene usato.
- **Confine esatto non testato**: i casi usano −2 e −4 giorni; la soglia è `< 3 giorni` **stretta**, ma il punto esatto (esattamente 3 giorni / 72h) non è coperto.
- **Categorie non mappate**: una `dataset_type` non presente in `queue_map` solleverebbe `KeyError`; non è coperta (vedi §8).

## 7. Checklist di revisione

- [ ] Confermare che i marker `integration`/`deterministic` siano voluti per un test che è di fatto **unità pura** (nessuna risorsa esterna).
- [ ] Valutare se aggiungere un caso al **confine esatto** dei 3 giorni (uguaglianza) per fissare la semantica `<` stretta.
- [ ] Verificare che il comportamento su `dataset_type` sconosciuta (`KeyError`) sia intenzionale e, se sì, considerarne un test esplicito.
- [ ] Confermare che il formato `reftime` reale dei chiamanti usi davvero la chiave `date_from` con un oggetto `datetime` (non stringa ISO).

## 8. Possibili criticità

- **Marker fuorviante**: etichettato `integration` ma non esercita alcuna integrazione; un reviewer potrebbe sovrastimare la copertura d'integrazione delle code.
- **Contratto d'input assunto**: i test passano `date_from` come oggetto `datetime`; se in produzione il `reftime` arriva con stringhe ISO, la `(now - date_from)` fallirebbe e questo non sarebbe rilevato qui.
- **Robustezza mancante su chiave sconosciuta**: `queue_map[lookup_key]` non ha fallback; categorie nuove o errate causerebbero `KeyError` non testato.
- **Copertura del confine**: assenza del caso esattamente-3-giorni lascia ambigua la semantica del limite operativo.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `..._routes_recent_and_old_reftimes` (×4) | `queue_sorting` | recente→operational, vecchio→archived per categoria | clock locale | `frozen_queue_sorting_now` | Bassa |
| `..._naive_reftime_is_treated_as_utc` (×2) | `queue_sorting` (ramo naive→UTC) | normalizzazione tz | clock locale (solo side effect) | `frozen_queue_sorting_now` | Bassa |
| `..._missing_reftime_routes_to_archived_queue` (×4) | `queue_sorting` (ramo `None`) | `reftime=None`→archived | clock locale (non letto) | `frozen_queue_sorting_now` | Bassa |
