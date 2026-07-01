# Review — `dataset/support.py` (infrastruttura di dominio)

> File di review per modulo di supporto. Non contiene test.
> Struttura **ADATTATA**: il modulo espone una sola utility helper, non costanti.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/dataset/support.py](projects/mistral/backend/tests/integration/dataset/support.py)
- **Scopo dichiarato**: fornire una utility locale per scegliere "quale dataset pubblico posso usare in sicurezza nel runtime corrente".
- **Tipologia**: modulo di supporto (una sola funzione, nessuno stato).

## 2. Elementi definiti

| Elemento | Firma | Comportamento |
|---|---|---|
| `first_public_dataset_id` | `(datasets: list[dict]) -> str` | Itera la lista del catalogo e ritorna `str(id)` del **primo** dataset con `is_public is True` e `id` valorizzato; se nessuno, esegue `pytest.skip("No public dataset is available in this environment")`. |

- Dipende solo da `pytest` (per lo `skip`) e dal payload già deserializzato passato dal chiamante.

## 3. Comportamenti nascosti

- **⚠️ Modulo non importato dai test del dominio (probabile duplicato morto)**: i due test della cartella (`test_dataset_authorization.py`, `test_dataset_visibility.py`) importano `first_public_dataset_id` da **`mistral.tests.helpers.datasets`**, non da questo `support.py`. Una ricerca testuale su `tests/` non trova alcun import di `dataset/support.py`. La funzione locale è quindi, allo stato attuale, **codice non utilizzato** che duplica l'omonimo helper condiviso ([tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py#L16)).
- **Skip silenzioso incorporato**: la funzione decide autonomamente di saltare lo scenario; chi la usa eredita un `pytest.skip` non esplicito al call site. È lo stesso comportamento dell'helper condiviso.
- **Equivalenza funzionale con l'helper condiviso**: logica e messaggio di skip coincidono con `tests/helpers/datasets.first_public_dataset_id`; una divergenza futura tra le due copie passerebbe inosservata proprio perché quella locale non è collegata ai test.

## 4. Checklist di revisione

- [ ] Decidere se **rimuovere** `dataset/support.py` (duplicato non importato) oppure **ricablare** i test affinché usino la versione locale invece dell'helper condiviso.
- [ ] Se il modulo resta, documentarne lo scopo per evitare che un revisore lo creda attivo.
- [ ] Verificare che non esista un import dinamico/indiretto (per nome) che lo renda comunque raggiungibile (non risulta dal codice).

## 5. Possibili criticità

- **Duplicazione silenziosa**: avere due `first_public_dataset_id` (locale + helper) con la stessa responsabilità ma una sola realmente usata è una fonte di confusione e di drift; un fix applicato all'helper condiviso non si rifletterebbe qui (e viceversa).
- **Falsa percezione di copertura**: il nome `support.py` suggerisce un ruolo attivo nel dominio dataset, mentre la sua utility non partecipa ad alcun test — rischio di manutenzione orientata al file sbagliato.
