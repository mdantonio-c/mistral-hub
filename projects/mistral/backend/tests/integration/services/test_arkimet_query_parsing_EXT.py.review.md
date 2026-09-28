# Review — `test_arkimet_query_parsing_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/services/test_arkimet_query_parsing_EXT.py](projects/mistral/backend/tests/integration/services/test_arkimet_query_parsing_EXT.py)
- **Scopo**: verificare i parser **puri** del service Arkimet — `is_filter_allowed` (allow-list), `parse_reftime` (bounds ISO → matcher reftime inclusivo), `parse_matchers` (filtri strutturati → sintassi matcher) e `decode_run` (run `MINUTE` → `HH:MM`, con i rami d'errore `TypeError`/`ValueError`).
- **Tipologia**: **unit / pure-function**, nonostante il marker. Le funzioni sotto test sono `@staticmethod` che trasformano dict/stringhe in stringhe: **non** chiamano `arki-query`, **non** aprono configurazioni dataset, **non** eseguono estrazioni e non usano `client`/DB. Marker dichiarati: `integration`, `deterministic` (vedi §6 per la discrepanza marker↔natura reale).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `BeArkimet.is_filter_allowed` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L135) | `True` se `filter_name in BeArkimet.allowed_filters`, altrimenti `False`. |
| `BeArkimet.allowed_filters` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L22) | Tupla di 10 nomi: `area, level, origin, proddef, product, quantity, run, task, timerange, network`. |
| `BeArkimet.parse_reftime` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L143) | `dateutil.parser.parse` su entrambi i bound, poi `strftime("%Y-%m-%d %H:%M")` → `"reftime: >={gt},<={lt}"`. |
| `BeArkimet.parse_matchers` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L160) | Per ogni chiave nota join dei valori con `" or "`; concatena i matcher con `"; "`; chiavi ignote → `log.warning` + `continue`. |
| `BeArkimet.decode_run` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L621) | Non-dict → `TypeError`; style `MINUTE` con `value` int → `MINUTE,HH:MM` (`floor(v/60)`, `v%60`); valore non-int → `TypeError`; style diverso → `ValueError`. |
| `BeArkimet.__decode_quantity` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L612) | Privato (name-mangled), invocato **indirettamente** da `parse_matchers`: join di `value` con `","`. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `BeArkimet` | classe service | [services/arkimet.py](projects/mistral/backend/services/arkimet.py) | Solo metodi statici esercitati; **nessuna** sessione `arki.dataset` aperta. |
| `dateutil.parser.parse` | libreria | `python-dateutil` (in `arkimet.py`) | Parsing dei bound in `parse_reftime`; il suffisso `Z` produce un datetime tz-aware **poi ignorato** da `strftime` (vedi §6). |
| `math.floor` | stdlib | `math` (in `arkimet.py`) | Conversione minuti → ore in `decode_run`. |
| `pytest.raises` | meccanismo | `pytest` | Verifica `TypeError`/`ValueError` nei due test negativi di `decode_run`. |
| `pytest.mark.integration` / `deterministic` | marker | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L8) | Solo classificazione. |

> **Nota infra**: nessun `conftest.py`/`support` locale in `integration/services/`; il file **non richiede fixture** (i metodi sono statici e puri). Le fixture condivise ([`test_runtime`/`cleanup_registry`](projects/mistral/backend/tests/conftest.py#L31)) non sono autouse e non vengono usate.

## 4. Analisi dettagliata di ogni test

> Tutti i test sono metodi della classe `TestArkimetQueryParsing` (semplice raggruppamento, nessun setup di classe).

### `test_is_filter_allowed_accepts_known_filter_and_rejects_unknown`
- **Obiettivo**: contratto booleano dell'allow-list.
- **Backend coinvolto**: `is_filter_allowed` + `allowed_filters`.
- **Flusso**: `is_filter_allowed("run")` e `is_filter_allowed("not-a-filter")`.
- **Setup**: nessuna fixture.
- **Assert**: `known_result is True`, `unknown_result is False` (identità su bool, non solo truthiness).
- **Casi coperti**: happy path + reject. Verifica un solo filtro noto (`run`) sui 10 disponibili.

### `test_parse_reftime_formats_inclusive_arkimet_bounds`
- **Obiettivo**: conversione bounds ISO → matcher reftime con operatori inclusivi.
- **Backend coinvolto**: `parse_reftime`.
- **Flusso**: `parse_reftime("2026-05-28T00:00:00Z", "2026-05-28T03:30:00Z")`.
- **Setup**: date sintetiche (non finestre dataset reali).
- **Assert**: `matcher == "reftime: >=2026-05-28 00:00,<=2026-05-28 03:30"`.
- **Casi coperti**: happy path. **Importante**: il suffisso `Z` viene parsato come UTC ma `strftime` formatta solo i campi wall-clock → **nessuna conversione di fuso** (vedi §6); il test passa perché input già in UTC.

### `test_parse_matchers_decodes_run_and_quantity_filters`
- **Obiettivo**: comporre più filtri nella sintassi matcher attesa.
- **Backend coinvolto**: `parse_matchers` → `decode_run` (per `run`) e `__decode_quantity` (per `quantity`).
- **Flusso**: filtri `run` (due valori `MINUTE` 360 e 0) e `quantity` (lista `["B13011","B11001"]`).
- **Setup**: dict letterale; **l'ordine delle chiavi è significativo** (run prima di quantity).
- **Assert**: `matcher == "run:MINUTE,06:00 or MINUTE,00:00; quantity:B13011,B11001"` → join valori con `" or "`, join matcher con `"; "`, quantity join con `","`.
- **Casi coperti**: happy path multi-filtro + multi-valore. Dipende dall'ordine d'inserzione del dict (vedi §6).

### `test_decode_run_valid_minute_style_returns_hour_minute`
- **Obiettivo**: normalizzazione `MINUTE` → `HH:MM` zero-padded.
- **Backend coinvolto**: `decode_run`, ramo `style == "MINUTE"`.
- **Flusso**: `decode_run({"style": "MINUTE", "value": 75})`.
- **Setup**: 75 minuti (copre sia quoziente ora sia resto minuti).
- **Assert**: `decoded_run == "MINUTE,01:15"` (`floor(75/60)=1`, `75%60=15`).
- **Casi coperti**: happy path con valore non-tondo (intercetta regressioni su padding/divisione).

### `test_decode_run_invalid_input_type_raises_type_error`
- **Obiettivo**: input non-dict rifiutato prima del parsing per style.
- **Backend coinvolto**: `decode_run`, guardia `if not isinstance(i, dict)`.
- **Flusso**: `decode_run("MINUTE,01:00")` dentro `pytest.raises(TypeError)`.
- **Setup**: stringa al posto del dict.
- **Assert**: solleva `TypeError`.
- **Casi coperti**: error path (tipo errato). Non asserisce il messaggio.

### `test_decode_run_invalid_style_raises_value_error`
- **Obiettivo**: style non supportato fallisce esplicitamente.
- **Backend coinvolto**: `decode_run`, ramo `else: raise ValueError`.
- **Flusso**: `decode_run({"style": "HOUR", "value": 1})` dentro `pytest.raises(ValueError)`.
- **Setup**: style `HOUR` (non gestito).
- **Assert**: solleva `ValueError`.
- **Casi coperti**: error path (style non valido). Non asserisce il messaggio.

## 5. Call chain

```
is_filter_allowed(name)                                  [test_is_filter_allowed]
  → name in BeArkimet.allowed_filters  → True/False

parse_reftime(from_str, to_str)                          [test_parse_reftime]
  → dateutil.parse(from_str) / dateutil.parse(to_str)    (Z → tz-aware, poi ignorato)
  → strftime("%Y-%m-%d %H:%M")
  → "reftime: >={gt},<={lt}"

parse_matchers(filters)                                   [test_parse_matchers]
  ├─ k == "run"      → " or ".join(decode_run(i) for i in values)
  ├─ k == "quantity" → " or ".join(__decode_quantity(i) ...)  (join value con ",")
  ├─ else            → log.warning + continue
  → "; ".join("k:q")

decode_run(i)                                             [test_decode_run_*]
  ├─ not dict                 → TypeError
  ├─ style == "MINUTE"
  │     ├─ value not int      → TypeError("Run value must be a number")
  │     └─ floor(v/60):v%60   → "MINUTE,HH:MM"
  └─ else                     → ValueError("Invalid <run> style ...")
```

## 6. Comportamenti nascosti

- **Marker fuorviante**: classificati `integration` ma sono **unit puri**: nessun `arki-query`, nessuna sessione dataset, nessun I/O. La toolchain Arkimet reale è coperta altrove (smoke).
- **`parse_reftime` non normalizza il fuso**: `dateutil` parsa `...Z` come tz-aware, ma `strftime("%Y-%m-%d %H:%M")` stampa i campi wall-clock **senza** convertire in UTC. Con input già UTC il risultato coincide; con un offset diverso (`+02:00`) il matcher conterrebbe l'ora locale, **non** quella UTC. Comportamento non testato su offset ≠ Z.
- **`parse_matchers` dipende dall'ordine del dict**: l'ordine dei matcher in output segue l'ordine d'inserzione delle chiavi (Python 3.7+). Il test asserisce `run` prima di `quantity` perché così è costruito il dict; un cambio d'ordine cambierebbe la stringa attesa.
- **`decode_run` ha un ramo TypeError aggiuntivo non coperto**: con `style == "MINUTE"` ma `value` non-int viene sollevato `TypeError("Run value must be a number")`; i test coprono il non-dict e lo style errato, **non** questo sotto-caso.
- **Notazione "vecchia" non esercitata**: `decode_run` e `__decode_quantity` gestiscono chiavi legacy (`s`/`va`) con **mutazione in-place** del dict d'ingresso; i test usano solo la notazione nuova (`style`/`value`), quindi quel ramo (e il side effect) non è coperto.
- **`__decode_quantity` testato solo indirettamente** via `parse_matchers`; non c'è un test diretto sul decoder quantity (es. join di un solo valore o input non-dict).
- **Nessuno `skip`**: tutti e sei i test eseguono sempre.

## 7. Checklist di revisione

- [ ] Confermare che la natura **unit** sia voluta nonostante marker/collocazione `integration`.
- [ ] Valutare un test su `parse_reftime` con offset diverso da `Z` per fissare (o correggere) il comportamento di non-conversione del fuso.
- [ ] Aggiungere copertura sul ramo `decode_run` `MINUTE` + `value` non-int (`TypeError "Run value must be a number"`).
- [ ] Considerare un test diretto su `__decode_quantity` e sulla notazione legacy (`s`/`va`) con verifica dell'eventuale mutazione del dict.
- [ ] Verificare che la dipendenza dall'ordine delle chiavi in `parse_matchers` sia un'assunzione accettata e documentata.
- [ ] Eventualmente asserire i messaggi nei `pytest.raises` (oggi si verifica solo il tipo dell'eccezione).

## 8. Possibili criticità

- **Fuso orario silenzioso in `parse_reftime`**: il `Z` viene parsato ma `strftime` lo scarta; un bound con offset non-zero produrrebbe un reftime errato (ora locale spacciata per UTC). I test non lo rilevano.
- **Accoppiamento all'ordine del dict** in `parse_matchers`: il contratto stringa è sensibile all'ordine d'inserzione; in casi reali (filtri assemblati altrove) l'ordine potrebbe non essere garantito.
- **Mutazione in-place nei decoder legacy** (`decode_run`/`__decode_quantity` quando manca `style`/`value`): potenziale side effect sull'input del chiamante, non coperto dai test.
- **Allow-list coperta parzialmente**: solo `run` è verificato come "ammesso"; gli altri 9 nomi non sono asseriti (regressioni su tupla `allowed_filters` non intercettate).
- **Messaggi d'errore non asseriti**: i test negativi accettano qualsiasi `TypeError`/`ValueError`, anche se sollevato per un motivo diverso da quello atteso.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_is_filter_allowed_accepts_known_filter_and_rejects_unknown` | `is_filter_allowed` | `run`→True, ignoto→False | — | — | Bassa |
| `test_parse_reftime_formats_inclusive_arkimet_bounds` | `parse_reftime` | bounds ISO → matcher inclusivo | — | — | Bassa |
| `test_parse_matchers_decodes_run_and_quantity_filters` | `parse_matchers` (+`decode_run`/`__decode_quantity`) | join multi-filtro/multi-valore | — | — | Media |
| `test_decode_run_valid_minute_style_returns_hour_minute` | `decode_run` | `MINUTE,75` → `01:15` | — | — | Bassa |
| `test_decode_run_invalid_input_type_raises_type_error` | `decode_run` | non-dict → `TypeError` | — | — | Bassa |
| `test_decode_run_invalid_style_raises_value_error` | `decode_run` | style ignoto → `ValueError` | — | — | Bassa |
