# Review — `helpers/cleanup.py` (helper condiviso)

> File di review per l'infrastruttura di teardown. Non contiene test.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/cleanup.py](projects/mistral/backend/tests/helpers/cleanup.py)
- **Scopo**: registro deterministico di azioni di teardown eseguite in ordine LIFO.
- **Tipologia**: infrastruttura di suite (usata dalla fixture `cleanup_registry`).

## 2. Elementi definiti

### Classe `CleanupRegistry`
| Metodo | Cosa fa |
|---|---|
| `add(fn)` | Accoda una callback di teardown. |
| `add_path(path)` | Accoda una `shutil.rmtree(..., ignore_errors=True)` best-effort per il path (solo se esiste). |
| `run()` | Esegue le azioni in **ordine inverso** (LIFO) e svuota lo stack; **non** ingoia eccezioni. |

## 3. Comportamenti nascosti

- **LIFO deliberato**: risorse dipendenti (file → directory, request → utente) vengono rimosse nell'ordine corretto.
- **`add_path` è best-effort** (`ignore_errors=True`) ma valuta `p.exists()` al momento della `run()`, non della registrazione.
- **`run()` propaga le eccezioni**: un teardown rotto fa fallire il test (scelta di igiene).
- **La fixture `cleanup_registry`** ([tests/conftest.py](projects/mistral/backend/tests/conftest.py)) chiama `run()` dopo lo `yield`: il collegamento test→teardown è automatico.

## 4. Checklist di revisione

- [ ] Verificare che l'ordine di registrazione produca un teardown LIFO corretto per le dipendenze.
- [ ] Considerare che `run()` non isola i fallimenti: un cleanup rotto può nascondere l'esito reale del test.

## 5. Possibili criticità

- **Nessun isolamento degli errori**: se la prima azione LIFO solleva, le successive **non** vengono eseguite → possibile stato sporco residuo nonostante l'intento "strict".
