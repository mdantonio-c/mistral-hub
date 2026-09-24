# Review - `helpers/datasets.py`

> Modulo di supporto condiviso. Non contiene test e non decide piu di saltare
> scenari in base al catalogo disponibile nel runtime.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py)
- **Scopo**: creare un dataset sintetico completo, pubblico o privato, per i test di integrazione.
- **Consumatori attuali**: i test `integration/dataset`, `integration/opendata/test_download.py` e gli environment builder in `integration/opendata/support.py`.
- **Dipendenze runtime**: connettore SQLAlchemy gia inizializzato e fixture `cleanup_registry`.

## 2. Elementi definiti

### `create_test_dataset(db, cleanup_registry, *, is_public, prefix="dataset_test")`

Crea sempre un bundle relazionale nuovo con nomi univoci basati su UUID:

1. `GroupLicense` con il valore `is_public` richiesto;
2. `Attribution` sintetica;
3. `License` collegata al gruppo;
4. `Datasets` OBS/BUFR collegato a licenza e attribution.

Il dataset usa lo stesso valore univoco per `name` e `arkimet_id`, viene
committato prima delle richieste HTTP e viene restituito al test chiamante.
Non legge license, attribution o dataset seedati e non contiene
`pytest.skip`.

### `_delete_test_dataset_bundle(...)`

Callback privata registrata in `cleanup_registry`. Esegue prima un rollback
difensivo della sessione, poi:

1. stacca tutte le associazioni `dataset.users`;
2. elimina il dataset;
3. elimina la license;
4. elimina il group license;
5. elimina l'attribution;
6. esegue il commit finale.

Ogni lookup e difensivo: il cleanup resta valido anche se una risorsa fosse
gia stata rimossa dal test. Dopo il commit, quattro assert verificano che
dataset, license, group license e attribution non siano piu presenti; un
teardown incompleto diventa quindi un errore visibile della suite.

## 3. Contratto e isolamento

- Ogni chiamata crea un bundle distinto, quindi i test non dipendono dall'ordine.
- Pubblico e privato sono governati esclusivamente da `GroupLicense.is_public`, come nel backend reale.
- Gli ID necessari al teardown vengono acquisiti subito dopo il commit e passati al callback.
- Il teardown LIFO permette ai test di eliminare prima eventuali utenti che referenziano il dataset.
- Negli scenari opendata, response streamate, file, request e utenti vengono rimossi prima del bundle dataset.
- Non vengono alterati `license_id` o metadati di dataset reali.

## 4. Limiti residui

- Il helper usa direttamente l'ORM: non verifica gli endpoint CRUD amministrativi di catalogo.
- Un arresto forzato del processo puo impedire l'esecuzione di qualsiasi teardown pytest.
- Categoria e formato sono fissati a `OBS` e `bufr`, sufficienti per i contratti di visibilita attuali.

## 5. Validazione

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/dataset'
```

Esito: **5 passed, 0 skipped, 0 failed, 0 errors**. La cartella e stata
raccolta correttamente anche dopo la rimozione del vecchio `dataset/support.py`.

Il riuso nel dominio opendata è stato validato con:

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/opendata'
```

Esito: **18 passed, 0 skipped, 0 failed, 0 errors**, inclusi i teardown di
request, file, utenti e bundle dataset.