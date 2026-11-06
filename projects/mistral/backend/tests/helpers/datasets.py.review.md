# Review - `helpers/datasets.py`

> Modulo di supporto condiviso. Non contiene test e non decide piu di saltare
> scenari in base al catalogo disponibile nel runtime.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/datasets.py](projects/mistral/backend/tests/helpers/datasets.py)
- **Scopo**: creare un dataset sintetico completo, pubblico o privato, per i test di integrazione, ed eventualmente una rete sintetica che punta a un dataset privato.
- **Consumatori attuali**: i test `integration/dataset`, `integration/opendata/test_download.py`, gli environment builder in `integration/opendata/support.py`, e (per la rete privata) `integration/fields/test_fields_api_EXT.py` e `integration/observed/test_observations_download_EXT.py`.
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

### `create_private_test_network(db, cleanup_registry, monkeypatch, *, prefix="private_network_test")`

Crea un dataset privato con `create_test_dataset(is_public=False)` e restituisce
una rete sintetica `<arkimet_id>_net`. Tramite `monkeypatch` sostituisce
`BeArkimet.from_network_to_dataset` solo per quella rete, delegando ogni altra
rete alla mappatura reale; `check_dataset_authorization` resta reale. Serve a
costruire un 401 portabile su `/fields` e `POST /observations` senza modificare
dataset reali come agrmet. Il patch viene annullato dal teardown di `monkeypatch`,
il bundle dal `cleanup_registry`.

### `delete_test_dataset_bundle(...)`

Callback pubblica registrata in `cleanup_registry` da `create_test_dataset` e da
`create_fields_synthetic_dataset` di `integration/fields/support_EXT.py`, che prima
aveva una copia locale (`delete_fields_dataset_bundle`). Esegue prima un rollback
difensivo della sessione, poi:

1. stacca tutte le associazioni `dataset.users`;
2. elimina il dataset;
3. elimina la license;
4. elimina il group license;
5. elimina l'attribution, solo se `attribution_id` non e `None` (i dataset
   sintetici di `fields` riusano un'attribution reale quando esiste e la passano
   come `None` per non cancellarla);
6. esegue il commit finale.

Ogni lookup e difensivo: il cleanup resta valido anche se una risorsa fosse
gia stata rimossa dal test. Dopo il commit, le assert verificano che
dataset, license, group license e (se gestita) attribution non siano piu presenti; un
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