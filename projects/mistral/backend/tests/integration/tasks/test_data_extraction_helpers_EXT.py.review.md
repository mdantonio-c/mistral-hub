# Review — `test_data_extraction_helpers_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy (fase quick wins).

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/tasks/test_data_extraction_helpers_EXT.py](projects/mistral/backend/tests/integration/tasks/test_data_extraction_helpers_EXT.py)
- **Scopo**: documentare e proteggere il contratto degli **helper puri** del task di data extraction: `human_size` (formattazione byte), `package_data_license` (tar.gz output+LICENSE con cancellazione del sorgente) e `adapt_reftime` (avanzamento della finestra reftime per schedule periodiche/crontab).
- **Tipologia**: prevalentemente **unità** (helper a contratto locale). Marker dichiarati: `integration`, `deterministic`; in pratica niente DB/Celery/broker, solo `tmp_path` per il filesystem e un orologio congelato (vedi §8).
- **Conteggio**: 5 metodi di test (di cui 1 parametrizzato ×4 su `human_size`), **8 casi** complessivi. Nessun `pytest.skip`.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `human_size(bytes, units=[...])` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L751) | Formattatore **ricorsivo** byte→stringa; usa shift `>> 10` (intero, nessun decimale). |
| `package_data_license(user_dir, out_file, license_file)` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L860) | Crea `data-<utc>.tar.gz` con output (`arcname=out_file.name`) + `LICENSE`; **cancella** `out_file`. |
| `adapt_reftime(schedule, reftime)` | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L758) | Avanza la finestra reftime in base a periodo/crontab, submission e `utcnow`; restituisce `{"from","to"}`. |

- Backend **realmente eseguito**: i tre helper per intero (tar reale su disco, ricorsione, aritmetica delle date).
- Backend **non** coinvolto: estrazione Arkimet/DB-All.e, DB, scheduler RedBeat (la `schedule` è un `SimpleNamespace`).

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `_FixedDataExtractionDateTime` | classe locale | nel file di test | Sottoclasse di `datetime` con `utcnow()` congelato al `2026-05-28 12:30:00`. |
| `frozen_data_extraction_clock` | fixture locale | nel file di test | `monkeypatch.setattr(data_extraction, "datetime", SimpleNamespace(datetime=..., timedelta=...))`; ritorna l'istante `utcnow`. |
| `SimpleNamespace` | builder | `types` | Costruisce la `schedule` fake (period/every/time_delta/args/submission_date) e il **namespace datetime** sostitutivo. |
| `tmp_path` | fixture | `pytest` | Isola i file del test tar; pytest rimuove la directory a fine test. |
| `tarfile` | stdlib | — | Verifica del contenuto reale dell'archivio prodotto. |
| `data_extraction` | modulo | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py) | Modulo sotto test; il patch sostituisce il suo simbolo `datetime`. |

## 4. Analisi dettagliata di ogni test

### `test_human_size_formats_existing_thresholds` (param. ×4)
- **Obiettivo**: fissare il contratto **storico** di `human_size` ai confini byte/KB/MB.
- **Backend coinvolto**: ricorsione `str(bytes)+units[0] if bytes<1024 else human_size(bytes>>10, units[1:])`.
- **Flusso**: chiama `human_size(byte_count)` per `0`, `1023`, `1024`, `1024*1024`.
- **Setup**: nessuna fixture; input puramente sintetici.
- **Assert**: `0→"0 bytes"`, `1023→"1023 bytes"`, `1024→"1KB"`, `1048576→"1MB"`.
- **Casi coperti**: soglia di unità senza decimali. **Non** copre valori intermedi (es. 1500 → `1KB` per troncamento `>>10`).

### `test_package_data_license_archives_license_and_removes_source_file`
- **Obiettivo**: verificare archiviazione di output+LICENSE e il **side effect** di cancellazione del file dati originale.
- **Backend coinvolto**: `package_data_license` completo (tar reale + `out_file.unlink()`).
- **Flusso**: crea `forecast.grib` e `license.txt` in `tmp_path` → chiama l'helper → riapre il tar e verifica i membri.
- **Setup**: `tmp_path`; contenuti sintetici (nessun dato meteo reale).
- **Assert**: nome `data-...tar.gz`; tar esiste; `out_file` **non** esiste più; membri `["LICENSE","forecast.grib"]`; il contenuto di `LICENSE` è quello del sorgente.
- **Casi coperti**: happy path filesystem/tar + cancellazione sorgente. Nome verificato per prefisso/suffisso, **non** per timestamp.

### `test_adapt_reftime_daily_periodic_schedule_moves_window_forward`
- **Obiettivo**: schedule **giornaliera** periodica preserva l'offset originale della richiesta.
- **Backend coinvolto**: ramo non-crontab `period.name="days"`, normalizzazione `first_submission` su ore/minuti del now, calcolo `time_delta_to`.
- **Flusso**: `schedule` con `time_delta=6h`, reftime iniziale `to=2026-05-24T12:30`, submission `2026-05-25 12:30` → chiama `adapt_reftime`.
- **Setup**: `frozen_data_extraction_clock` (usata **solo** per il side effect: `del` del valore di ritorno).
- **Assert**: `{"from":"2026-05-27T06:30:00.000000Z","to":"2026-05-27T12:30:00.000000Z"}` (finestra di 6h, `to` un giorno prima del fake now).
- **Casi coperti**: ramo `days`.

### `test_adapt_reftime_hourly_periodic_schedule_moves_window_forward`
- **Obiettivo**: schedule **oraria** periodica avanza per intervalli orari trascorsi.
- **Backend coinvolto**: ramo `period.name="hours"`, normalizzazione dei soli minuti/secondi della submission.
- **Flusso**: `time_delta=1h`, reftime iniziale `to=2026-05-28T07:30`, submission `2026-05-28 08:30` → `adapt_reftime`.
- **Setup**: `frozen_data_extraction_clock` (solo side effect).
- **Assert**: `{"from":"2026-05-28T10:30:00.000000Z","to":"2026-05-28T11:30:00.000000Z"}`.
- **Casi coperti**: ramo `hours`.

### `test_adapt_reftime_base_crontab_schedule_uses_daily_interval`
- **Obiettivo**: un crontab “semplice” (senza chiavi week/month) si comporta come schedule **giornaliera**.
- **Backend coinvolto**: ramo `is_crontab=True` con `crontab_settings="{}"` → `schedule_interval = timedelta(days=1)`.
- **Flusso**: `time_delta=12h`, reftime iniziale `to=2026-05-25T12:30`, submission `2026-05-26 12:30` → `adapt_reftime`.
- **Setup**: `frozen_data_extraction_clock` (solo side effect); JSON crontab valido.
- **Assert**: `{"from":"2026-05-27T00:30:00.000000Z","to":"2026-05-27T12:30:00.000000Z"}`.
- **Casi coperti**: ramo crontab base. **Non** coperti i rami `day_of_week`/`day_of_month`/`month of year`.

## 5. Call chain

```
human_size(n)            → ricorsione con units[1:] e bytes>>10            → "<int><unit>"
package_data_license(dir, out, lic)
                         → tarfile.open(w:gz) → add(out, arcname=out.name) → add(lic, arcname="LICENSE")
                         → out.unlink()                                    → return "data-<utc>.tar.gz"
adapt_reftime(schedule, reftime)
                         → (datetime monkeypatchato → utcnow=2026-05-28 12:30)
                         → calcola schedule_interval (period/every | crontab)
                         → normalizza first_submission su now (days|hours)
                         → time_delta_to = interval * float((now-first_submission)/interval) [+ aggiustamento ±1 unità]
                         → new_to = first_reftime_to + time_delta_to ; new_from = new_to - schedule.time_delta
                         → return {"from","to"} (formattati "...%fZ")
```

## 6. Comportamenti nascosti

- **Patch dell'intero namespace `datetime`**: la fixture sostituisce `data_extraction.datetime` con un `SimpleNamespace(datetime=_Fixed..., timedelta=dt.timedelta)`. Tutto il modulo, durante la chiamata, vede `datetime.datetime` (con `utcnow` congelato e `strptime` ereditato) e `datetime.timedelta`; **altri** attributi di `datetime` non esistono più nel namespace (qui non servono).
- **Fixture usata per il solo side effect**: i tre test `adapt_reftime` fanno `del frozen_data_extraction_clock`; serve solo a congelare `utcnow`, non il valore di ritorno.
- **`human_size` tronca, non arrotonda**: `>> 10` è uno shift intero → 1500 byte = `1KB`, 2047 byte = `1KB`. I test scelgono solo confini esatti, quindi questa caratteristica **non** è esplicitata da un caso.
- **`package_data_license` cancella sempre l'output**: il `LICENSE` sorgente resta, ma `out_file` viene rimosso anche se il chiamante volesse riusarlo.
- **`adapt_reftime` ha rami non esercitati**: l'aggiustamento `±1 giorno/ora` (`first_submission - first_reftime_to_wout_delta < minor_delta`) e i rami crontab settimanale/mensile/annuale non sono coperti.

## 7. Checklist di revisione

- [ ] Confermare che i marker `integration`/`deterministic` siano voluti per test sostanzialmente **unitari**.
- [ ] Valutare un caso `human_size` **intermedio** (es. 1500) per documentare il troncamento `>>10`.
- [ ] Verificare che la cancellazione incondizionata di `out_file` in `package_data_license` sia il contratto desiderato.
- [ ] Considerare copertura dei rami `adapt_reftime` non testati (crontab `day_of_week`/`day_of_month`/`month of year`, aggiustamento ±1 unità).
- [ ] Confermare che la sostituzione del namespace `datetime` non nasconda usi del modulo non previsti (oggi solo `datetime`/`timedelta`).

## 8. Possibili criticità

- **Marker fuorviante**: `integration` su test puramente unitari (nessun DB/servizio); rischio di sovrastimare la copertura d'integrazione dei task.
- **Copertura `adapt_reftime` parziale**: la funzione è complessa e fragile (aritmetica di date con casi limite ±1 unità); i 3 casi happy non esercitano i rami di correzione né il crontab avanzato. Regressioni in quei rami **non** verrebbero rilevate.
- **Asserzioni su stringhe formattate**: gli output reftime sono confrontati come stringhe `"...%fZ"`; un cambio innocuo di formato (es. precisione microsecondi) romperebbe i test pur preservando la semantica.
- **`human_size` senza decimali non documentato**: l'assenza di un caso intermedio lascia implicito il troncamento.
