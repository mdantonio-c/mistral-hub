# Review — `helpers/celery_fakes.py` (fake/mock condivisi)

> File di review per i fake Celery condivisi. Non contiene test.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/helpers/celery_fakes.py`
- **Scopo**: sostituire il solo strato di trasporto Celery (broker/worker) mantenendo l'esecuzione in-process, per testare la logica di submission/scheduling senza RabbitMQ né worker esterni.
- **Tipologia**: modulo di **fake** (test double) condiviso.

## 2. Backend realmente esercitato

| Elemento | Path | Ruolo |
|---|---|---|
| `data_extraction.data_extract` | `projects/mistral/backend/tasks/data_extraction.py` | Task reale eseguito inline da `InlineDataExtractCelery`. |
| `SqlApiDbManager.create_request_record` / `get_schedule_name` | `projects/mistral/backend/services/sqlapi_db_manager.py` | Creazione del record `Request` sintetico in `InlineDataReadyExtractionCelery`. |
| `db.Request` | `projects/mistral/backend/models/sqlalchemy.py` | Riga richiesta che i test ispezionano. |

## 3. Elementi definiti

| Classe | Cosa sostituisce | Comportamento |
|---|---|---|
| `AcceptTasksWithoutRunningCelery(*names)` | wrapper Celery | `send_task` **registra** la submission in `sent_tasks` senza inviarla; opzionalmente verifica che il nome sia tra quelli attesi. `delete_periodic_task` → `True`. |
| `InlineDataReadyExtractionCelery(db)` | wrapper Celery | `send_task` valida `name=="data_extract"` e `data_ready is True`, poi salta i duplicati per reftime o crea una `Request` `SUCCESS` nel DB. |
| `InlineDataExtractCelery()` | wrapper Celery | `send_task` esegue **realmente** `data_extract.run(*args)` inline (side effect reali: file, opendata). |
| `_AcceptingCeleryApp`, `_InlineDataReadyExtractionApp`, `_InlineDataExtractApp` | `celery_app` interni | Facade minimali con `send_task`. |

## 4. Comportamenti nascosti

- **`AcceptTasksWithoutRunningCelery` asserisce sul nome del task** dentro `send_task`: se il codice sotto test sottomette un task non atteso, il fallimento appare **dentro il fake**, non nel corpo del test.
- **`InlineDataReadyExtractionCelery` riproduce la logica di de-duplicazione per reftime**: confronta l'ultima `Request` `SUCCESS` della schedule; questa logica vive nel fake, non nel test — il test verifica un comportamento implementato dal test double.
- **`InlineDataExtractCelery` esegue il task vero**: i test che lo usano hanno side effect reali (creazione file, pubblicazione opendata) pur evitando broker/worker.
- **Disallineamento potenziale**: la logica del fake (es. dedup) deve restare allineata al backend reale; se il backend cambia, il fake può divergere silenziosamente.
- **Tre contratti diversi, da non scambiare**:
  - `AcceptTasksWithoutRunningCelery`: salva `name`, `args`, `kwargs` in `sent_tasks` e ritorna `None`; senza nomi nel costruttore accetta qualunque task. Nessuna estrazione. Usato dal trigger data-ready (`helpers/data_ready.py`, sia per il submit del launcher sia nel conftest `data_ready`) e dalla creazione schedule nel bridge `schedules/test_schedule_opendata_bridge.py`.
  - `InlineDataReadyExtractionCelery`: spacchetta i 12 argomenti posizionali di `data_extract` e crea solo la riga `Request` `SUCCESS`; nessun `FileOutput` né dato estratto. Usato da `trigger_data_ready_inline` per i test periodici e di gating data-ready. Replica parte della deduplicazione: non è una prova indipendente del worker.
  - `InlineDataExtractCelery`: chiama `data_extract.run(*args)` ignorando i `kwargs` di `send_task` (semantica temporale e routing di coda). Usato solo dal bridge opendata.
- **`delete_periodic_task` non tocca RedBeat**: tutti e tre ritornano sempre `True`; i fake espongono anche `celery_app` come il wrapper reale.

## 5. Checklist di revisione

- [ ] Verificare che la logica di dedup in `_InlineDataReadyExtractionApp` rispecchi quella reale del path data-ready in `projects/mistral/backend/tasks/on_data_ready_extractions.py`.
- [ ] Distinguere i test che usano il fake "accept-only" (verificano la decisione) da quelli con `InlineDataExtractCelery` (verificano side effect reali).
- [ ] Verificare che gli `assert` interni ai fake non mascherino regressioni del backend come errori di helper.

## 6. Possibili criticità

- **Rischio di falso positivo**: `InlineDataReadyExtractionCelery` *implementa* la decisione di creare/saltare la richiesta. Un test che usa questo fake verifica in parte la logica del fake stesso, non solo quella di produzione.
- **Accoppiamento al contratto degli args** di `data_extract` (tupla a 12 elementi): un cambio di firma del task rompe i fake in modo non ovvio.
