# Review — `data/support_EXT.py` (infrastruttura di dominio)

> File di review per modulo di supporto. Non contiene test. Non modifica codice.
> Modulo `*_EXT.py`: infrastruttura introdotta **solo** per i nuovi test di estensione del dominio `integration/data` (contratto HTTP di `POST /data` e `GET /data/<filename>`). Non sposta fixture in `conftest.py` e non tocca il baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/data/support_EXT.py](projects/mistral/backend/tests/integration/data/support_EXT.py)
- **Scopo**: centralizzare builder di payload, creazione di utenti temporanei con permessi di estrazione, dataset/licenze sintetici, fake locali per Celery/RabbitMQ/Arkimet e helper di cleanup, così i test del dominio `data` restano confinati al backend di test senza avviare worker reali, broker AMQP o estrazioni meteorologiche pesanti.
- **Tipologia**: modulo di supporto **puro** — definisce dataclass, classi fake e funzioni helper. **Non definisce nessuna fixture e nessun comportamento `autouse`**: ogni effetto è attivato esplicitamente dal test che chiama l'helper.
- **Caratteristica chiave**: i fake Celery/Rabbit sono **locali a questo modulo** e **non** riusano `tests/helpers/celery_fakes.py`. L'isolamento dai servizi reali avviene via `monkeypatch` sui simboli importati dal modulo endpoint ([endpoints/data.py](projects/mistral/backend/endpoints/data.py)).

## 2. Backend realmente esercitato

Il modulo non testa nulla, ma gli helper esercitano (in fase di arrange/teardown) backend reale:

| Elemento | Path | Ruolo |
|---|---|---|
| Modelli SQLAlchemy reali | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py) | `User`, `Datasets`, `License`, `GroupLicense`, `Attribution`, `Request`, `FileOutput` creati/cancellati direttamente sul DB di test via `sqlalchemy.get_instance()`. |
| `create_authenticated_test_user` / `register_test_user_cleanup` / `AuthenticatedTestUser` | [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py) | Creazione utente via API admin reale + login reale + cleanup. |
| `BaseTests` | `restapi.tests` | `create_user`, `do_login` (dentro l'helper auth). |
| `DOWNLOAD_DIR` | [endpoints/\_\_init\_\_.py](projects/mistral/backend/endpoints/__init__.py) | Radice del path filesystem per output utente (`DOWNLOAD_DIR/<uuid>/outputs`). |
| `DatasetCategories` | [models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L132) | Enum `FOR/OBS/RAD/SEA` per la categoria del dataset sintetico. |
| `celery.states` | `celery` | Solo le costanti `PENDING` / `SUCCESS` (nessun broker). |
| `data_endpoint_module.arki / celery / rabbitmq` | [endpoints/data.py](projects/mistral/backend/endpoints/data.py) | Bersagli del `monkeypatch` (vedi `patch_data_endpoint_runtime`). |

**Non** esercitato (volutamente fakeato/aggirato): Arkimet reale (config `arkimet_conf`), DBALLE, broker RabbitMQ, worker Celery, task `data_extract`.

## 3. Elementi definiti

| Elemento | Tipo | Cosa fa / contratto |
|---|---|---|
| `DEFAULT_BOUNDING` | costante | WKT `POLYGON` sintetico assegnato a ogni dataset (`bounding`). |
| `DataEndpointDataset` | dataclass `frozen` | Tiene insieme `id` (numerico, per auth/cleanup) e `arkimet_id` (stringa, da usare nel payload HTTP) + `name`, `category`, `fileformat`. Esplicita quale identificatore va usato dove. |
| `FakeTaskResult` | dataclass `frozen` | AsyncResult sintetico con **solo** `id` e `status` — esattamente i due attributi che `Data.post` copia sul record `Request` dopo `send_task`. |
| `RecordingCelery` | classe fake | Sostituisce il connettore Celery: espone `.celery_app` e accumula le submission in `sent_tasks` senza eseguirle. `task_id` configurabile. |
| `_RecordingCeleryApp` | classe fake | `send_task(name, args, **kwargs)` → registra `{name, args, kwargs}` in `sent_tasks` e ritorna `FakeTaskResult(id=task_id, status=PENDING)`. |
| `FakeRabbit` | classe fake | `queue_exists(queue_name)` → ritorna l'`exists` configurato e registra `checked_queues`. Copre il **solo** controllo richiesto dal ramo push. |
| `create_data_endpoint_user(client, cleanup_registry, dataset_ids, *, allowed_postprocessing, amqp_queue, disk_quota, max_output_size)` | helper | Crea utente via API con permessi espliciti (`open_dataset=True`, `datasets` come lista di id numerici stringificati, quota, ecc.), poi **forza `db_user.amqp_queue` sul record reale** e committa; registra cleanup utente + directory output. |
| `create_synthetic_dataset(db, cleanup_registry, *, category, fileformat, is_public, group_name, prefix)` | helper | Crea (o riusa la **prima** `Attribution` esistente) + `GroupLicense` + `License` + `Datasets`; registra cleanup del bundle; ritorna `DataEndpointDataset`. |
| `build_data_payload(dataset_names, *, request_name, reftime_from, reftime_to, **overrides)` | helper | Body JSON per `POST /data`: `request_name`, `dataset_names`, `reftime {from,to}`, `filters {}`; gli `overrides` iniettano il solo campo dello scenario (es. `output_format`, `postprocessors`, `only_reliable`). |
| `patch_data_endpoint_runtime(monkeypatch, data_endpoint_module, *, dataset_format, dataset_category, celery_fake, rabbit_fake)` | helper | `monkeypatch.setattr` su `arki.get_datasets_format/get_datasets_category/is_filter_allowed`, `celery.get_instance` (→ `RecordingCelery`) e opzionalmente `rabbitmq.get_instance` (→ `FakeRabbit`). Ritorna il `RecordingCelery` usato. |
| `create_file_download_record(db, cleanup_registry, user, *, content)` | helper | Crea `Request(status=SUCCESS, opendata=False)` + `FileOutput`; se `content` non è `None` scrive il file fisico in `DOWNLOAD_DIR/<uuid>/outputs/<filename>` e registra `add_path`. Con `content=None` lascia **apposta** il record DB senza file (ramo 404). Ritorna `filename`. |
| `latest_request_for_user(db, user_id)` | helper | Ultima `Request` dell'utente per `id` desc (collega risposta HTTP all'effetto persistito). |
| `delete_request_row(db, request_id)` | helper | Rimuove `Request` (+ `FileOutput` per cascade) se ancora presente (idempotente). |
| `delete_dataset_bundle(db, *, dataset_id, license_id, group_license_id, attribution_id)` | helper | Stacca le associazioni `dataset.users` (M2M) poi cancella dataset/license/group e — **solo se creata** — l'attribution. |
| `delete_requests_for_user(db, user_id)` | helper | Cancella tutte le `Request` dell'utente (idempotente; copre sia happy path che rami che non creano request). |

## 4. Comportamenti nascosti

- **Nessuna fixture, nessun `autouse`**: a differenza di un `conftest.py`, qui non c'è iniezione automatica. Tutto l'isolamento dai servizi reali esiste **solo se il test chiama** `patch_data_endpoint_runtime` (o passa i fake). Un test che dimentica il patch finirebbe per chiamare Arkimet/DBALLE/RabbitMQ reali — da tenere presente in revisione di nuovi test.
- **Fake locali ≠ `celery_fakes.py`**: il dominio `data` **non** usa i transport-fake condivisi (`AcceptTasksWithoutRunningCelery`, `InlineDataExtractCelery`, …). Usa `RecordingCelery`/`FakeRabbit` locali, montati via `monkeypatch` su `data_endpoint_module.celery/rabbitmq`. Il task `data_extract` **non viene mai eseguito**: viene solo registrato. Nessun worker, broker, estrazione.
- **Monkeypatch sui simboli di modulo**: `patch_data_endpoint_runtime` patcha `data_endpoint_module.arki/celery/rabbitmq` (oggetti importati a livello modulo in [endpoints/data.py](projects/mistral/backend/endpoints/data.py)). Funziona perché l'endpoint risolve quei nomi a runtime dai globals del modulo. Se l'endpoint cambiasse stile di import (es. import locale dentro la funzione), il patch potrebbe **mancare silenziosamente** il bersaglio.
- **`amqp_queue` forzata sul record DB**: `create_data_endpoint_user` sovrascrive `db_user.amqp_queue` dopo la creazione via API (il faker/schema admin potrebbe generarne una casuale). Serve a distinguere in modo deterministico i tre stati del ramo push: queue assente (`None`), queue presente ma inesistente lato broker, queue valida. Effetto collaterale: il percorso “assegnazione queue via schema admin” **non** viene validato.
- **`open_dataset=True` sempre attivo**: in [services/sqlapi_db_manager.py#L482](projects/mistral/backend/services/sqlapi_db_manager.py#L482) i dataset **pubblici** sono visibili se l'utente ha `open_dataset=True`; l'autorizzazione esplicita per nome (`ds.name in user.datasets`) serve **solo ai dataset privati**. Poiché `create_synthetic_dataset` crea dataset **pubblici** di default, la lista `datasets` (id numerici) passata come permesso è di fatto **ridondante** e il ramo di autorizzazione su dataset privati **non è coperto**.
- **Cleanup condizionale dell'Attribution**: `create_synthetic_dataset` riusa la **prima** `Attribution` esistente se presente (`created_attribution_id=None`) e in tal caso **non** la cancella; crea+cancella un'attribution solo su catalogo vuoto. Il teardown del bundle dipende quindi dallo stato DB iniziale.
- **`create_file_download_record` e i due livelli DB/FS**: con `content=None` il record `FileOutput` esiste ma il file fisico no e **non** viene registrato `add_path`; resta comunque registrato il cleanup della request. È il setup esatto del ramo “record presente, file mancante → 404”.
- **`Request.args` arbitrari**: in `create_file_download_record` la request usa `args={"datasets": [], "reftime": {}, "filters": {}}` e `status=SUCCESS` — sufficiente perché `FileOutput.request_id` sia valido senza dipendere da un task reale.
- **`FakeTaskResult` minimale**: espone solo `id`/`status`. Se `Data.post` iniziasse a leggere altri attributi dell'AsyncResult, il fake si romperebbe (contratto implicito stretto).
- Tutti i dataset sintetici hanno `source="arkimet"`, `supports_variable_browsing=False`, `bounding=DEFAULT_BOUNDING`.

## 5. Checklist di revisione

- [ ] Confermare che l'assenza di fixture `autouse` sia voluta: ogni nuovo test del dominio **deve** ricordarsi di chiamare `patch_data_endpoint_runtime`, altrimenti contatta servizi reali.
- [ ] Verificare che la duplicazione dei fake locali rispetto a `tests/helpers/celery_fakes.py` sia una scelta consapevole (rischio di drift fra le due infrastrutture Celery di test).
- [ ] Confermare che il `monkeypatch` su `data_endpoint_module.arki/celery/rabbitmq` resti valido se [endpoints/data.py](projects/mistral/backend/endpoints/data.py) cambia stile di import.
- [ ] Verificare che `open_dataset=True` non mascheri la **mancata copertura** del ramo di autorizzazione su dataset privati (lista `datasets` di fatto inutilizzata).
- [ ] Confermare che il cleanup condizionale dell'Attribution non lasci residui o non cancelli per errore un'attribution condivisa, a seconda dello stato del catalogo.
- [ ] Verificare che i fake (`RecordingCelery.send_task`, `FakeRabbit.queue_exists`, `FakeTaskResult`) restino allineati al contratto reale chiamato da `Data.post`.

## 6. Possibili criticità

- **Doppia infrastruttura Celery di test**: fake locali qui + `celery_fakes.py` condivisi altrove. Manutenzione divergente: una modifica al contratto `send_task` va replicata in due punti.
- **Isolamento non garantito by-design**: senza `autouse`, l'isolamento dipende dalla disciplina del singolo test. Un test mal scritto può silenziosamente uscire dal perimetro fake.
- **Path di autorizzazione privata non esercitato**: la combinazione `is_public=True` + `open_dataset=True` rende inerte la lista `datasets`; la copertura reale dell'autorizzazione per nome resta scoperta in questo dominio.
- **Teardown sensibile allo stato del DB**: il riuso/non-cancellazione della prima Attribution rende il cleanup non perfettamente simmetrico tra ambiente vuoto e ambiente popolato.
- **Override diretto di `amqp_queue`**: bypassa il percorso applicativo di assegnazione queue; comodo per i test ma lascia non validato quel percorso admin.
- **Contratti impliciti stretti** (`FakeTaskResult` con soli `id`/`status`, `RecordingCelery.celery_app.send_task`): robusti finché l'endpoint non legge altro; fragili a refactor del dispatch.
