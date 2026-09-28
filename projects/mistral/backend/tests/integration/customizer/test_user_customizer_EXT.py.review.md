# Review — `test_user_customizer_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/customizer/test_user_customizer_EXT.py](projects/mistral/backend/tests/integration/customizer/test_user_customizer_EXT.py)
- **Scopo**: coprire direttamente il `Customizer` di Meteo-Hub — default e separazione `datasets` nel pre hook (`custom_user_properties_pre`), risoluzione/validazione degli id dataset nel post hook (`custom_user_properties_post`), serializzazione del profilo (`manipulate_profile`), e schema custom per scope (`get_custom_input_fields` ADMIN/PROFILE/REGISTRATION + `get_custom_output_fields`).
- **Tipologia**: **mista**. Tre test sono **unit puri** (`pre`, `manipulate_profile`, schema by-scope) che invocano gli static method del customizer con un **dummy user dataclass** e `request=None`. Due test sono **integrazione DB** (`post`): usano `sqlalchemy.get_instance()` reale (uno crea un bundle dataset sintetico, l'altro fa una sola read). **Nessun monkeypatch**; **nessun passaggio dagli endpoint HTTP profilo** — gli hook reali sono chiamati direttamente. Marker dichiarati: `integration`, `deterministic` (vedi §6 per la discrepanza marker↔natura reale).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Customizer.custom_user_properties_pre` | [customization.py](projects/mistral/backend/customization.py#L18) | Estrae `datasets` in `extra_properties`; `setdefault` dei campi custom (open_dataset, disk_quota, requests_expiration_*, max_*, allowed_*, request_par_hour, notify_on_successful_request). |
| `Customizer.custom_user_properties_post` | [customization.py](projects/mistral/backend/customization.py#L40) | Per ogni id in `extra_properties["datasets"]`: `db.Datasets.query.filter_by(id=int(id)).first()` → `NotFound` se assente; assegna `user.datasets`. |
| `Customizer.manipulate_profile` | [customization.py](projects/mistral/backend/customization.py#L55) | Copia gli attributi custom dell'utente nel dict `data` del profilo; `ref` (EndpointResource) non usato. |
| `Customizer.get_custom_input_fields` | [customization.py](projects/mistral/backend/customization.py#L73) | Schema marshmallow per scope; interroga i dataset **solo se `request`** è truthy; `required = request and method=="POST"`. |
| `Customizer.get_custom_output_fields` | [customization.py](projects/mistral/backend/customization.py#L217) | Mappa di output con `datasets = Nested(Datasets(many=True))`. |
| `Datasets` (Schema) | [customization.py](projects/mistral/backend/customization.py#L11) | Schema `{id, name}` annidato in output. |
| `db.Datasets` / `GroupLicense` / `License` / `Attribution` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py) | Modelli reali creati/risolti dagli helper di seeding e dal post hook. |
| `DatasetCategories.FOR` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py) | Enum categoria per il dataset sintetico. |
| `NotFound` | [exceptions](projects/mistral/backend/customization.py#L6) (`restapi.exceptions`) | Sollevata dal post hook su id dataset inesistente. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `cleanup_registry` | fixture | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L38) | Teardown **LIFO**; usata solo dal test "associates valid" per rimuovere il bundle sintetico. |
| `sqlalchemy.get_instance()` | connettore | `restapi.connectors` | Istanza DB **reale** (read/write su tabelle dataset/license/group/attribution). |
| `DummyCustomizerUser_EXT` | dataclass | (questo file) | Utente fittizio con i soli attributi custom; **non** è un model ORM. |
| `seed_customizer_dataset_EXT` | helper | (questo file) | Crea group→license→attribution→dataset (commit) e registra il cleanup; ritorna `dataset.id`. |
| `delete_customizer_dataset_EXT` | helper | (questo file) | Stacca eventuali `dataset.users`, poi elimina dataset/license/group/attribution. |
| `BaseCustomizer.ADMIN/PROFILE/REGISTRATION` | costanti | `restapi.customizer` | Selettori di scope per `get_custom_input_fields`. |
| `NotFound` | eccezione | `restapi.exceptions` | Target di `pytest.raises`. |
| `uuid4` | stdlib | `uuid` | Nomi unici per evitare collisioni con dati iniziali / test paralleli. |
| `pytest.mark.integration` / `deterministic` | marker | [tests/conftest.py](projects/mistral/backend/tests/conftest.py#L9) | Solo classificazione. |

> **Nota infra**: nessun `conftest.py`/`support` locale in `integration/customizer/`. L'unica fixture condivisa usata è [`cleanup_registry`](projects/mistral/backend/tests/conftest.py#L38); `auth_headers`/`fresh_access_key` ([integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py#L15)) **non** sono richieste, perché i test non passano da HTTP.

## 4. Analisi dettagliata di ogni test

> I test sono funzioni a livello di modulo (nessuna classe), più due helper di seeding/cleanup.

### `test_custom_user_properties_pre_sets_defaults_and_extracts_datasets_EXT` — **unit**
- **Obiettivo**: il pre hook deve estrarre `datasets` e popolare i default custom senza sovrascrivere valori espliciti.
- **Backend coinvolto**: `custom_user_properties_pre` (pop `datasets` → `extra_properties`; `setdefault` dei campi).
- **Flusso**: input `{"datasets": ["1","2"], "disk_quota": 99}`.
- **Setup**: nessuno (chiamata diretta, niente DB).
- **Assert**: `"datasets" not in updated_properties`; `extra_properties == {"datasets": ["1","2"]}`; `disk_quota == 99` (**preservato** da `setdefault`); `open_dataset is True`; `requests_expiration_days == 180`; `requests_expiration_delete is False`; `max_templates == 1`; `allowed_schedule is True`; `notify_on_successful_request is True`.
- **Casi coperti**: separazione `datasets` + default custom + non-override dei valori espliciti. (Il default `disk_quota=1073741824` non è esercitato perché il test passa `99`.)

### `test_custom_user_properties_post_associates_valid_datasets_EXT` — **integrazione DB**
- **Obiettivo**: il post hook risolve id dataset validi e li assegna all'utente.
- **Backend coinvolto**: `custom_user_properties_post` → `db.Datasets.query.filter_by(id=...).first()` → `user.datasets = [...]`.
- **Flusso**: `seed_customizer_dataset_EXT` crea un bundle reale; utente dummy con `datasets=[]`; `post(user, {}, {"datasets": [str(dataset_id)]}, db)`.
- **Setup**: `cleanup_registry` (rimozione bundle in teardown), `db = sqlalchemy.get_instance()`.
- **Assert**: `user.datasets is not None`; `[d.id for d in user.datasets] == [dataset_id]`.
- **Casi coperti**: happy path risoluzione id reali. **Nota**: `user.datasets = [...]` su un dataclass è un'assegnazione **in-memory**, non una relazione ORM persistita (vedi §6); il test verifica solo l'attributo, non la scrittura DB lato utente.

### `test_custom_user_properties_post_missing_dataset_raises_notfound_EXT` — **integrazione DB (read)**
- **Obiettivo**: id dataset inesistente → `NotFound`.
- **Backend coinvolto**: `custom_user_properties_post`, ramo `if not dat: raise NotFound`.
- **Flusso**: id `987654321`; precondizione `db.Datasets.query.get(987654321) is None`; post con quell'id.
- **Setup**: `db = sqlalchemy.get_instance()`; **nessun** dato creato, **nessun** cleanup.
- **Assert**: `pytest.raises(NotFound)`.
- **Casi coperti**: error path validazione. La read sul DB conferma l'assenza prima di misurare l'eccezione.

### `test_manipulate_profile_includes_all_custom_fields_EXT` — **unit**
- **Obiettivo**: il profilo serializzato deve includere tutti i campi custom.
- **Backend coinvolto**: `manipulate_profile(ref=None, user, data)`.
- **Flusso**: utente dummy con valori non-default; `data={"email": "user@example.com"}`.
- **Setup**: nessuno (pura funzione, `ref` ignorato).
- **Assert**: `email` invariata + 13 campi custom uguali agli attributi dell'utente (`disk_quota`, `amqp_queue`, `requests_expiration_days`, `requests_expiration_delete`, `open_dataset`, `datasets`, `max_templates`, `max_output_size`, `allowed_postprocessing`, `allowed_schedule`, `allowed_obs_archive`, `request_par_hour`, `notify_on_successful_request`).
- **Casi coperti**: contratto di serializzazione del profilo (copertura 1:1 dei campi).

### `test_custom_input_and_output_fields_by_scope_EXT` — **unit**
- **Obiettivo**: schema custom corretti per ADMIN, PROFILE, REGISTRATION e output.
- **Backend coinvolto**: `get_custom_input_fields(None, scope)` e `get_custom_output_fields(None)` con `request=None` (evita query a startup).
- **Flusso**: chiamate dirette per ogni scope.
- **Setup**: nessuno; `request=None` → `datasets=[]`, `required` falsy.
- **Assert**: ADMIN → set operativo completo **issubset** (12 chiavi); PROFILE → **uguaglianza esatta** `{requests_expiration_days, requests_expiration_delete, notify_on_successful_request}`; REGISTRATION → `{}`; output → set completo **issubset** (incl. `datasets`).
- **Casi coperti**: presenza campi per scope. Non copre il ramo `request` truthy (POST → `required=True`, `datasets` popolati, `OneOf` dinamica) — vedi §6.

## 5. Call chain

```
custom_user_properties_pre(properties)                        [test_pre]
  → for p in ("datasets",): extra_properties[p] = properties.pop(p)
  → properties.setdefault(open_dataset=True, disk_quota=1073741824, requests_expiration_days=180,
        requests_expiration_delete=False, max_output_size=1073741824, max_templates=1,
        allowed_postprocessing=False, allowed_schedule=True, allowed_obs_archive=True,
        request_par_hour=10, notify_on_successful_request=True)
  → return properties, extra_properties

custom_user_properties_post(user, properties, extra_properties, db)   [test_post_*]
  → for id in extra_properties.get("datasets", []):
        dat = db.Datasets.query.filter_by(id=int(id)).first()   (DB REALE)
        not dat? → NotFound(f"Dataset {id} not found")
        datasets.append(dat)
  → user.datasets = datasets        (assegnazione su DUMMY: in-memory, non ORM)

manipulate_profile(ref, user, data)                           [test_manipulate_profile]
  → data[<campo custom>] = user.<campo>  (x13) → return data   (ref ignorato)

get_custom_input_fields(request, scope)                       [test_fields_by_scope]
  → request? db.Datasets.query.all() : datasets = []          (request=None → [])
  → required = request and request.method=="POST"             (None → falsy)
  → scope ADMIN → 12 campi ; PROFILE → 3 campi ; REGISTRATION → {} ; else {}

get_custom_output_fields(request)                             [test_fields_by_scope]
  → dict statico con datasets = Nested(Datasets(many=True))
```

## 6. Comportamenti nascosti

- **Marker fuorviante / natura mista**: classificato `integration`, ma 3/5 test sono **unit puri** e 2/5 toccano il DB **direttamente** (non via HTTP). Nessun endpoint profilo, nessun auth, nessun worker.
- **Hook chiamati direttamente con dummy user**: `DummyCustomizerUser_EXT` è un dataclass, non un model ORM. In `post`, `user.datasets = [...]` imposta un attributo Python: **non** persiste alcuna associazione user↔dataset nel DB. La copertura riguarda la **SELECT** dei dataset e l'assegnazione in-memory, non la scrittura ORM lato utente.
- **`setdefault` ⇒ non-override**: in `pre` i valori espliciti vincono (es. `disk_quota=99` resta). I default scattano solo per chiavi assenti.
- **`int(dataset_id)` cast**: il post hook converte l'id a intero; un id non numerico solleverebbe `ValueError` (non `NotFound`) — non coperto.
- **`request=None` evita query a startup**: con `request` truthy e `method=="POST"`, `required` diventa `True` e `datasets` è popolato dal DB, costruendo una `OneOf` dinamica per il campo `datasets` ADMIN. Questo ramo **non** è testato.
- **REGISTRATION → `{}`**: oltre al ramo esplicito, esiste anche un `return {}` finale di default; entrambi danno dizionario vuoto.
- **Asserzioni asimmetriche**: ADMIN e output sono verificati con `issubset` (campi extra non verrebbero rilevati), mentre PROFILE e REGISTRATION sono verificati con **uguaglianza esatta**.
- **`manipulate_profile` ignora `ref`**: il primo parametro (EndpointResource) non è usato; passare `None` è coerente con il corpo.
- **Cleanup relazionale**: `delete_customizer_dataset_EXT` stacca prima `dataset.users` (qui vuoto, dato l'utente dummy), poi elimina in ordine dataset→license→group→attribution; registrato subito dopo la creazione (LIFO).
- **Nessuno `skip`**: tutti e cinque i test eseguono sempre.

## 7. Checklist di revisione

- [ ] Confermare che testare gli hook **direttamente** (senza HTTP profilo/registrazione) sia il livello di copertura voluto.
- [ ] Confermare l'accettabilità del **dummy user**: la persistenza ORM di `user.datasets` (lato `post`) **non** è verificata.
- [ ] Valutare un test di `get_custom_input_fields` con `request` reale (POST → `required=True`, `datasets` popolati, `OneOf` dinamica).
- [ ] Valutare l'edge `int(dataset_id)` con id non numerico (`ValueError` vs `NotFound`).
- [ ] Confermare che la semantica `setdefault` (valori espliciti preservati) sia intenzionale.
- [ ] Confermare la scelta `issubset` per ADMIN/output vs uguaglianza esatta per PROFILE/REGISTRATION.

## 8. Possibili criticità

- **Natura mista mascherata dal marker**: alcuni test sono unit, altri toccano il DB; chi rivede potrebbe assumere copertura end-to-end del profilo che qui **non** esiste.
- **Persistenza ORM non coperta in `post`**: l'assegnazione su dataclass dà un **falso senso** che l'associazione user↔dataset sia salvata; il path reale (model `User`, commit) non è esercitato.
- **Ramo dinamico di `get_custom_input_fields` non testato**: la `OneOf` su `datasets` e i flag `required=True` (caso POST con `request`) restano scoperti.
- **Edge `int(dataset_id)`**: un id non numerico produce `ValueError` invece del `NotFound` atteso dal contratto; non verificato.
- **Asserzioni `issubset` su ADMIN/output**: campi aggiuntivi o rinominati non verrebbero intercettati (regressione silenziosa possibile).
- **Dipendenza dal DB reale per 2 test**: richiedono uno stato DB pulito; pur isolati da `uuid4` e cleanup LIFO, restano sensibili a fallimenti infrastrutturali rispetto ai 3 test puri.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_custom_user_properties_pre_sets_defaults_and_extracts_datasets_EXT` | `custom_user_properties_pre` | estrazione `datasets` + default + non-override | dummy (input dict) | — | Bassa |
| `test_custom_user_properties_post_associates_valid_datasets_EXT` | `custom_user_properties_post` | risoluzione id reali → `user.datasets` | dummy user + DB reale | `cleanup_registry` | Media |
| `test_custom_user_properties_post_missing_dataset_raises_notfound_EXT` | `custom_user_properties_post` | id assente → `NotFound` | dummy user + DB reale (read) | — | Bassa |
| `test_manipulate_profile_includes_all_custom_fields_EXT` | `manipulate_profile` | profilo con tutti i 13 campi custom | dummy user | — | Bassa |
| `test_custom_input_and_output_fields_by_scope_EXT` | `get_custom_input_fields` / `get_custom_output_fields` | campi per ADMIN/PROFILE/REGISTRATION/output | `request=None` | — | Media |
