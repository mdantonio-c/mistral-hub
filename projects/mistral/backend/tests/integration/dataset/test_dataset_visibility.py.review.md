# Review - `test_dataset_visibility.py`

> Test deterministico del catalogo anonimo con dataset pubblico sintetico e
> teardown automatico.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/dataset/test_dataset_visibility.py](projects/mistral/backend/tests/integration/dataset/test_dataset_visibility.py)
- **Scopo**: verificare lista e dettaglio pubblici senza autenticazione, oltre al `404` per un identificatore inesistente.
- **Marker**: `integration`, `deterministic`.
- **Numero di test**: 1.
- **Skip**: nessuno.

## 2. Scenario coperto

### `test_dataset_endpoints_expose_public_catalog_without_login`

Arrange:

- ottiene il connettore SQLAlchemy reale;
- usa `create_test_dataset(..., is_public=True)` per creare dataset, group license, license e attribution isolati;
- affida il teardown completo a `cleanup_registry`.

Act e assert:

1. `GET /api/datasets` anonimo restituisce `200` e una lista;
2. la lista contiene esattamente l'`arkimet_id` sintetico con `is_public is True`;
3. `GET /api/datasets/<arkimet_id>` restituisce `200` e un oggetto;
4. un identificatore casuale inesistente restituisce `404`.

Il test non seleziona piu il primo dataset del runtime e non usa
`pytest.skip`: il target pubblico viene sempre preparato dal test.

## 3. Backend esercitato

| Elemento | Ruolo |
|---|---|
| `Datasets.get` | Serve il catalogo anonimo e ne serializza la lista. |
| `SingleDataset.get` | Cerca il dataset nel catalogo visibile e restituisce `404` quando manca. |
| `SqlApiDbManager.get_datasets` | Nel ramo `user=None` include solo gruppi con `is_public=True`. |
| `Datasets`, `License`, `GroupLicense`, `Attribution` | Forniscono il bundle relazionale reale usato dalle richieste. |

Non vengono usati mock di routing, autorizzazione o serializzazione.

## 4. Cleanup e rischi residui

Il callback condiviso stacca eventuali utenti e rimuove dataset, license,
group license e attribution in ordine FK-safe. Il test non modifica cataloghi
seedati e non dipende dall'ordine di esecuzione.

Restano fuori scope `licenceSpecs=True` e il ramo `503` prodotto da errori
interni di `get_datasets`.

## 5. Validazione

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/dataset/test_dataset_visibility.py'
```

Esito mirato: **1 passed, 0 skipped, 0 failed, 0 errors**.

La validazione finale di cartella ha prodotto **5 passed, 0 skipped**.