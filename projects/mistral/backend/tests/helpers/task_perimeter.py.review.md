# Review — `helpers/task_perimeter.py` (helper condiviso)

> File di review per l'infrastruttura che confina i task globali eseguiti dai test. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/task_perimeter.py](projects/mistral/backend/tests/helpers/task_perimeter.py)
- **Scopo**: eseguire in-process task globali per progetto senza che tocchino righe o file non creati dal test.
- **Tipologia**: infrastruttura di suite. `confine_requests_cleanup` è esposto tramite la fixture `requests_cleanup_perimeter` di [integration/conftest.py](projects/mistral/backend/tests/integration/conftest.py); `confine_data_ready_schedules` è chiamato da [helpers/data_ready.py](projects/mistral/backend/tests/helpers/data_ready.py) e dai test che lanciano il launcher data-ready.

## 2. Task confinati

| Task | Cosa visiterebbe senza perimetro | Cosa vede nel perimetro |
|---|---|---|
| `automatic_cleanup` ([tasks/requests_cleanup.py](projects/mistral/backend/tasks/requests_cleanup.py)) | Tutti gli utenti, tutte le request e l'intera root `DOWNLOAD_DIR` | Solo utenti/request registrati con `allow(...)`; `FileOutput` delle sole request registrate; root download temporanea |
| `launch_all_on_data_ready_extractions` ([tasks/on_data_ready_extractions.py](projects/mistral/backend/tasks/on_data_ready_extractions.py)) | Tutte le schedule del DB | Solo le schedule passate a `confine_data_ready_schedules` e le loro request |

## 3. Come funziona

- Sostituisce con `monkeypatch` il nome `sqlalchemy` **nel modulo del task**, non nel connettore `restapi`: endpoint, autenticazione e test continuano a usare il DB reale.
- La facciata conserva codice del task e scritture ORM reali (`commit`, `delete`, `merge`), ma espone solo gli attributi usati oggi dal task.
- **Fail-closed**: un attributo o una forma di query non prevista solleva `OutsideTestPerimeterError`, invece di leggere l'intera tabella. Dentro un task `restapi` l'errore arriva al test come `celery.exceptions.Ignore` con lo stesso messaggio.
- Un perimetro vuoto produce zero righe (`filter(false())`), non la tabella completa.
- Per il cleanup sostituisce anche `DOWNLOAD_DIR` del task: la scansione degli orfani vede solo la root temporanea. I file delle request registrate restano nelle directory degli utenti temporanei e vengono rimossi dal vero `delete_request_record`.

## 4. Checklist di revisione

- [ ] Se `automatic_cleanup` o il launcher data-ready cambiano il modo di leggere il DB, verificare che l'eventuale errore fail-closed venga risolto estendendo la facciata, non rimuovendo il perimetro.
- [ ] Verificare che ogni test che esegue questi task registri tutte e sole le righe che crea.

## 5. Possibili criticità

- **Accoppiamento con l'implementazione dei task**: la facciata conosce le query attuali; un refactor del task richiede di aggiornarla (fallimento visibile, non silenzioso).
- **Solo esecuzioni in-process**: worker Celery, beat e cron reali girano in processi separati e non vedono il `monkeypatch`; i test `async_real` richiedono uno stack di test dedicato.
