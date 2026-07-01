# Review — `requests/conftest.py` (infrastruttura di dominio)

> File di review per modulo di supporto (fixture locali). Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/requests/conftest.py](projects/mistral/backend/tests/integration/requests/conftest.py)
- **Scopo**: fornire le fixture specifiche del dominio *pending-request* — un utente temporaneo dedicato e una coppia di richieste con età diverse — così che [test_delete_pending_request.py](projects/mistral/backend/tests/integration/requests/test_delete_pending_request.py) si concentri sulle regole del grace period invece che sul setup grezzo delle righe.
- **Tipologia**: `conftest.py` di dominio (solo fixture locali, visibili a `integration/requests/**`).
- **Consumatori**: i tre test di [test_delete_pending_request.py](projects/mistral/backend/tests/integration/requests/test_delete_pending_request.py). **Non** usato dal modulo `*_EXT` (che definisce in proprio `requests_user`/`seed_request_row`).

## 2. Backend realmente esercitato

- **In setup (via helper):** creazione utente attraverso l'admin user-creation + `do_login` (dentro `create_authenticated_test_user`, [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py)).
- **Seeding diretto del modello `Request`** ([models/sqlalchemy.py](projects/mistral/backend/models/sqlalchemy.py#L36)) tramite `create_pending_delete_requests` ([requests/support.py](projects/mistral/backend/tests/integration/requests/support.py)). Nessuna chiamata diretta agli endpoint `/requests` (quelle stanno nei test).

## 3. Elementi definiti

| Elemento | Tipo | Dipende da | Cosa fa | Usato da |
|---|---|---|---|---|
| `pending_request_user` | fixture | `client`, `cleanup_registry` | Crea un utente temporaneo autenticato (senza permessi speciali) via `create_authenticated_test_user` e registra il cleanup utente/cartelle via `register_test_user_cleanup`; ritorna `AuthenticatedTestUser`. | Tutti i test di delete; **base** di `pending_delete_requests`. |
| `pending_delete_requests` | fixture | `faker`, `pending_request_user`, `cleanup_registry` | Chiama `create_pending_delete_requests(faker, db, user_id)` → crea **due** `Request` (una vecchia `STARTED`, una recente `PENDING`); registra il cleanup `delete_request_rows(db, ...)`; ritorna `(deletable_id, undeletable_id)`. | I tre test di delete/cleanup. |

## 4. Comportamenti nascosti

- **Catena di fixture transitiva**: `pending_delete_requests` richiede `pending_request_user`, che a sua volta crea un utente via `client`. Un test che chiede solo `pending_delete_requests` (es. il test di cleanup, che non usa `client` direttamente) crea comunque l'utente.
- **Ordine di teardown LIFO**: il cleanup delle righe `Request` è registrato **dopo** quello dell'utente, quindi gira **prima** (LIFO) — le richieste vengono rimosse prima dell'utente che le possiede, evitando vincoli di FK pendenti.
- **`faker` come fixture**: i nomi delle richieste sono randomici; nessun valore atteso dipende dal nome (solo dagli `id` ritornati).
- **Contratto della tupla**: l'ordine `(deletable_id, undeletable_id)` è significativo e i test fanno unpacking posizionale; la semantica (quale è cancellabile) è decisa in `support.py`.
- **Seeding diretto sul DB**: le righe sono scritte con `db.session` bypassando l'endpoint; gli `args` sono `{}` (vedi review di `support.py`), quindi queste righe **non** sarebbero sicure per `GET /requests` (che fa `pop("datasets")`).

## 5. Checklist di revisione

- [ ] Verificare che il cleanup delle righe sia registrato dopo quello dell'utente (LIFO → righe prima dell'utente).
- [ ] Confermare che `pending_request_user` non richieda permessi dataset (i test di delete/cleanup non li usano).
- [ ] Verificare l'allineamento ordine-tupla ↔ unpacking nei test consumatori.
- [ ] Confermare che la fixture non lasci residui se la creazione delle richieste fallisce a metà (cleanup registrato subito dopo il commit).

## 6. Possibili criticità

- **Accoppiamento alla coppia fissa di richieste**: la fixture impone esattamente due righe con stato/età predefiniti; scenari che servissero combinazioni diverse dovrebbero duplicare il setup invece di parametrizzarlo.
- **Logica del grace period delegata a `support.py`**: la fixture non rende esplicita la regola età↔stato; chi rivede deve aprire `support.py` per capire perché una richiesta è "cancellabile" e l'altra no.
- **Dipendenza dal wall-clock**: le date sono calcolate con `datetime.now()` in `support.py`; la fixture eredita questa sensibilità temporale.
