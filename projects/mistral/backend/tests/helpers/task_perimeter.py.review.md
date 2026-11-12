# Review — `helpers/task_perimeter.py` (helper condiviso)

> File di review per l'infrastruttura che confina i task globali eseguiti dai test. Non contiene test.

## 1. Informazioni generali

- **Percorso**: `projects/mistral/backend/tests/helpers/task_perimeter.py`
- **Scopo**: eseguire in-process task globali per progetto senza che tocchino righe o file non creati dal test.
- **Tipologia**: infrastruttura di suite. `confine_requests_cleanup` è esposto tramite la fixture `requests_cleanup_perimeter` di `projects/mistral/backend/tests/integration/conftest.py`; `confine_data_ready_schedules` è chiamato da `projects/mistral/backend/tests/helpers/data_ready.py` e dai test che lanciano il launcher data-ready.

## 2. Task confinati

| Task | Cosa visiterebbe senza perimetro | Cosa vede nel perimetro |
|---|---|---|
| `automatic_cleanup` (`projects/mistral/backend/tasks/requests_cleanup.py`) | Tutti gli utenti, tutte le request e l'intera root `DOWNLOAD_DIR` | Solo utenti/request registrati con `allow(...)`; `FileOutput` delle sole request registrate; root download temporanea |
| `launch_all_on_data_ready_extractions` (`projects/mistral/backend/tasks/on_data_ready_extractions.py`) | Tutte le schedule del DB | Solo le schedule passate a `confine_data_ready_schedules` e le loro request |

## 3. Come funziona

- Sostituisce con `monkeypatch` il nome `sqlalchemy` **nel modulo del task**, non nel connettore `restapi`: endpoint, autenticazione e test continuano a usare il DB reale.
- La facciata conserva codice del task e scritture ORM reali (`commit`, `delete`, `merge`), ma espone solo gli attributi usati oggi dal task.
- **Fail-closed**: un attributo o una forma di query non prevista solleva `OutsideTestPerimeterError`, invece di leggere l'intera tabella. Dentro un task `restapi` l'errore arriva al test come `celery.exceptions.Ignore` con lo stesso messaggio.
- Un perimetro vuoto produce zero righe (`filter(false())`), non la tabella completa.
- Per il cleanup sostituisce anche `DOWNLOAD_DIR` del task: la scansione degli orfani vede solo la root temporanea. I file delle request registrate restano nelle directory degli utenti temporanei e vengono rimossi dal vero `delete_request_record`.
- **Facciata di accesso, non DB finto**: la sostituzione riguarda solo `get_instance` del nome `sqlalchemy` del modulo task; dietro c'è sempre il DB reale. Le scritture sugli oggetti caricati e i metodi del repository restano reali: il perimetro limita *cosa il task trova*, non controlla ogni side effect possibile.
- **Perimetro cleanup vivo, perimetro data-ready congelato**: `RequestsCleanupPerimeter.allow` converte gli id in `int` e i `registered_*_ids` ne ritornano copie lette a ogni query, quindi un `allow` successivo vale anche dopo la patch. `confine_data_ready_schedules` congela invece gli id alla chiamata; le `Request` sono filtrate per `schedule_id`, non per id di request.
- **Dove intervenire se un refactor ORM rompe la facciata** (nomi privati):
  - `_as_ids`, `_restrict`: conversione degli id e filtro `IN` (insieme vuoto -> `false()`);
  - `_ScopedModel`: inoltra le colonne, filtra `query`;
  - `_RequestLookupModel` e `_LookupByRegisteredId`: per il cleanup ammettono solo `get(id)` di id registrati, nessuna query globale;
  - `_CleanupSession`: ammette solo `query(Request.id)` e `query(Request)` sul proxy, più `commit` e `delete`; `_RequestsCleanupDatabase` espone `User`, `Request`, `FileOutput` ristretti;
  - `_ForwardOnly`: blocca gli attributi non previsti; `_DataReadyDatabase` espone `Schedule` e `Request` filtrati e una sessione che ammette solo `merge`.
- **Consumatori**: `requests/test_delete_pending_request.py` e `tasks/test_requests_cleanup_expiration.py` (cleanup), `tasks/test_on_data_ready_task_edges.py` (launcher), `trigger_data_ready_inline` di `helpers/data_ready.py` e il bridge `schedules/test_schedule_opendata_bridge.py`. Il ripristino delle patch è affidato a `monkeypatch`.

## 4. Checklist di revisione

- [ ] Se `automatic_cleanup` o il launcher data-ready cambiano il modo di leggere il DB, verificare che l'eventuale errore fail-closed venga risolto estendendo la facciata, non rimuovendo il perimetro.
- [ ] Verificare che ogni test che esegue questi task registri tutte e sole le righe che crea.

## 5. Possibili criticità

- **Accoppiamento con l'implementazione dei task**: la facciata conosce le query attuali; un refactor del task richiede di aggiornarla (fallimento visibile, non silenzioso).
- **Solo esecuzioni in-process**: worker Celery, beat e cron reali girano in processi separati e non vedono il `monkeypatch`; i test `async_real` richiedono uno stack di test dedicato.
