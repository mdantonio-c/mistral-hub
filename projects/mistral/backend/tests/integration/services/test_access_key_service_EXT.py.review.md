# Review — `test_access_key_service_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/services/test_access_key_service_EXT.py](projects/mistral/backend/tests/integration/services/test_access_key_service_EXT.py)
- **Scopo**: verificare in modo deterministico la logica di `AccessKey.generate` (token + scadenza default vs `lifetime_seconds=None`), `AccessKey.is_valid` (stati di scadenza assente/futura/passata) e l'helper di service `is_access_key_valid` (record assente, scaduto, chiave errata).
- **Tipologia**: **unit / pure-function**, nonostante il marker. I test costruiscono istanze `AccessKey` **in memoria, non persistite** e invocano direttamente metodi del modello e una funzione di service; **nessun** `client` HTTP, **nessuna** sessione DB, **nessuna** `request` Flask. Marker dichiarati: `integration`, `deterministic` (vedi §6 per la discrepanza marker↔natura reale).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `AccessKey.generate` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L192) | `@staticmethod` che crea (senza salvare) un'istanza `AccessKey` con `key=secrets.token_urlsafe(32)`, `creation=datetime.utcnow()` (**naive**), `expiration=now+lifetime` oppure `None`, `scope="read:arco"`. |
| `AccessKey.is_valid` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L186) | Metodo del modello: `expiration is None` → `True`; altrimenti `return self.expiration > now` con `now = datetime.utcnow()` (**naive**, confronto stretto `>`). |
| `is_access_key_valid` | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py#L10) | Helper di service: `if not key_record: return False`; se `expiration` non `None` confronta con `datetime.now(timezone.utc)` (**aware**, `expiration < now` → scaduta); poi `return key_record.key == provided_key`. |
| Modello `AccessKey` (colonne) | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L167) | `key` unique/index, `creation` non null, `expiration` nullable tz-aware, `scope` default `read:arco`, `user_id` FK unique. Le istanze del test **non** vengono aggiunte alla sessione. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `AccessKey` | modello | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L167) | Istanziato in memoria; nessun INSERT, nessun commit. |
| `is_access_key_valid` | funzione | [services/access_key_service.py](projects/mistral/backend/services/access_key_service.py#L10) | Funzione pura sul record passato: non interroga il DB, non legge la `request`. |
| `datetime` / `timedelta` / `timezone` | stdlib | `datetime` | Costruzione degli stati di scadenza; il test sceglie **naive** per il modello e **aware** per il service (vedi §6). |
| `pytest.mark.integration` / `deterministic` | marker | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L8) | Solo classificazione; nessun effetto runtime qui. |

> **Nota infra**: in `tests/integration/services/` **non** esiste `conftest.py`/`support` locale. Le fixture condivise ([`test_runtime`/`cleanup_registry`](projects/mistral/backend/tests/conftest.py#L31), [`auth_headers`/`fresh_access_key`](projects/mistral/backend/tests/integration/conftest.py)) **non sono autouse e non vengono richieste**: questo file non dipende da alcuna fixture.

## 4. Analisi dettagliata di ogni test

### `test_access_key_generate_sets_default_and_null_expiration_EXT`
- **Obiettivo**: contratto di `AccessKey.generate` con lifetime default (3600s) e con `lifetime_seconds=None`.
- **Backend coinvolto**: `AccessKey.generate` (puro rispetto al DB).
- **Flusso**: genera `default_key = generate(user_id=42)` e `no_expiration_key = generate(user_id=42, lifetime_seconds=None)`.
- **Setup**: nessuna fixture; due chiamate dirette.
- **Assert**:
  - default: `user_id == 42`, `key` truthy, `creation is not None`, `expiration is not None`, `expiration > creation`, `scope == "read:arco"`.
  - null: `user_id == 42`, `key` truthy, `expiration is None`, `scope == "read:arco"`.
- **Casi coperti**: happy path + edge (scadenza disattivata). Non verifica `ip`/`location` (parametri accettati ma **mai usati** dal metodo — vedi §6).

### `test_access_key_model_is_valid_handles_expiration_states_EXT`
- **Obiettivo**: `AccessKey.is_valid()` deve distinguere scadenza assente / futura / passata.
- **Backend coinvolto**: `AccessKey.is_valid` (usa `datetime.utcnow()` **naive**).
- **Flusso**: costruisce tre istanze in memoria con `expiration` `None`, `now+1h`, `now-1h` (tutte **naive**, coerenti con `utcnow()` del modello).
- **Setup**: nessuna fixture; `now = datetime.utcnow()`.
- **Assert**: `without_expiration.is_valid() is True`, `future_expiration.is_valid() is True`, `past_expiration.is_valid() is False`.
- **Casi coperti**: i tre rami di `is_valid`. Non copre il bordo esatto `expiration == now` (con `>` stretto risulterebbe non valida — non testato).

### `test_access_key_service_rejects_wrong_key_EXT`
- **Obiettivo**: `is_access_key_valid` deve rifiutare una chiave che non combacia.
- **Backend coinvolto**: `is_access_key_valid`, ramo finale `key_record.key == provided_key`.
- **Flusso**: record valido con `expiration=None` (isola il ramo wrong-key dalla logica temporale), poi confronto con `"wrong-service-key-ext"`.
- **Setup**: nessuna fixture; `creation=datetime.utcnow()`.
- **Assert**: `is_access_key_valid(key_record, "wrong-service-key-ext") is False`.
- **Casi coperti**: error path (mismatch token). Con `expiration=None` il controllo di scadenza è saltato.

### `test_access_key_service_handles_missing_and_expired_records_EXT`
- **Obiettivo**: `is_access_key_valid` deve rifiutare sia il record assente sia quello scaduto.
- **Backend coinvolto**: `is_access_key_valid`, rami `if not key_record` e `expiration < now`.
- **Flusso**: record scaduto con `creation`/`expiration` **timezone-aware** (`datetime.now(timezone.utc)`), coerenti col `now` aware del service.
- **Setup**: nessuna fixture.
- **Assert**: `is_access_key_valid(None, "whatever") is False` **e** `is_access_key_valid(expired_key, "expired-service-key-ext") is False`.
- **Casi coperti**: due error path nello stesso test (assenza record + scadenza passata). La chiave fornita combacia col token, quindi il `False` deriva **solo** dalla scadenza.

## 5. Call chain

```
AccessKey.generate(user_id, lifetime_seconds)            [test_generate]
  → key = secrets.token_urlsafe(32)
  → creation = datetime.utcnow()            (naive)
  → expiration = now + timedelta  |  None   (se lifetime_seconds is None)
  → AccessKey(...)  (NON persistito)

AccessKey.is_valid()                                      [test_is_valid]
  ├─ expiration is None            → True
  └─ datetime.utcnow() (naive)     → expiration > now ?  True : False

is_access_key_valid(record, provided_key)                [test_wrong_key / test_missing_expired]
  ├─ not record                    → False
  ├─ expiration not None
  │     └─ datetime.now(tz.utc) (aware) → expiration < now ? False : (continua)
  └─ record.key == provided_key    → True/False
```

## 6. Comportamenti nascosti

- **Marker fuorviante**: `integration` + collocazione in `integration/services/`, ma i test sono **unit puri**: nessun DB, nessun HTTP, nessuna `request`. Le `AccessKey` sono oggetti in memoria mai aggiunti alla sessione. Chi rivede deve sapere che qui non si esercita persistenza né autenticazione end-to-end.
- **Naive vs aware deliberato**: il modello `is_valid` usa `datetime.utcnow()` (**naive**), il service usa `datetime.now(timezone.utc)` (**aware**). I test costruiscono datetime **naive** per il test del modello e **aware** per il test del service, proprio per **non** incrociare i due mondi (un confronto naive↔aware solleverebbe `TypeError`). Questa attenzione maschera una reale fragilità del backend (vedi §8).
- **`generate` ignora `ip` e `location`**: la firma è `generate(user_id, lifetime_seconds=3600, ip=None, location=None, scope="read:arco")` ma `ip`/`location` **non vengono mai usati né salvati**. Il test correttamente non li verifica, ma sono parametri morti.
- **Token non verificato nel formato**: il test controlla solo che `key` sia truthy, non la lunghezza/entropia di `secrets.token_urlsafe(32)`.
- **Nessuno `skip`**: il file non contiene `pytest.skip`; tutti e quattro i test eseguono sempre.

## 7. Checklist di revisione

- [ ] Confermare che la natura **unit** di questi test sia voluta nonostante il marker `integration` (eventualmente valutare un marker dedicato).
- [ ] Verificare la coerenza naive/aware fra `AccessKey.is_valid` (modello) e `is_access_key_valid` (service): i test la aggirano, ma il backend resta esposto a `TypeError` se un `expiration` persistito tz-aware finisse nel confronto naive del modello (o viceversa).
- [ ] Decidere se il bordo `expiration == now` debba avere un comportamento esplicito e testato (oggi modello `>` → non valida, service `<` → valida: **asimmetria**, vedi §8).
- [ ] Valutare se `ip`/`location` di `generate` vadano rimossi o effettivamente persistiti.
- [ ] Aggiungere (eventualmente) un test che leghi service↔modello su una stessa `expiration` per scoprire la divergenza tz.

## 8. Possibili criticità

- **Asimmetria di scadenza modello vs service**: a parità di istante `expiration == now`, `AccessKey.is_valid` ritorna `False` (`> now` stretto) mentre `is_access_key_valid` ritorna valido (`< now` falso). Due definizioni di "scaduta" coesistono; nessun test copre questo bordo.
- **Naive/aware non allineati**: il modello confronta con `utcnow()` naive, il service con `now(timezone.utc)` aware. Il DB definisce `expiration` come `DateTime(timezone=True)`: un record reale potrebbe essere aware e mandare in `TypeError` il path del modello. I test non lo rilevano perché costruiscono datetime ad hoc.
- **Copertura senza persistenza**: non viene verificato il round-trip DB (default colonna `scope`, vincolo `key` unique, FK `user_id`): tutto è in memoria, quindi i default/vincoli SQLAlchemy non sono esercitati qui.
- **`ip`/`location` parametri morti** in `generate`: rischio di falsa aspettativa (sembrano tracciati ma non lo sono).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_access_key_generate_sets_default_and_null_expiration_EXT` | `AccessKey.generate` | token/scope/scadenza default e `lifetime=None` | — | — | Bassa |
| `test_access_key_model_is_valid_handles_expiration_states_EXT` | `AccessKey.is_valid` (naive) | None/futura/passata | — | — | Bassa |
| `test_access_key_service_rejects_wrong_key_EXT` | `is_access_key_valid` | mismatch token → False | — | — | Bassa |
| `test_access_key_service_handles_missing_and_expired_records_EXT` | `is_access_key_valid` (aware) | record assente + scaduto → False | — | — | Bassa |
