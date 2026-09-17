# Review - `test_dataset_authorization.py`

> Suite autorizzativa deterministica con utenti e bundle dataset distinti per
> test. Non riusa o modifica dati catalogo seedati.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/dataset/test_dataset_authorization.py](projects/mistral/backend/tests/integration/dataset/test_dataset_authorization.py)
- **Scopo**: verificare separatamente accesso pubblico, grant privati, transizione di `open_dataset` e lookup inesistenti.
- **Marker**: `integration`, `deterministic`.
- **Numero di test**: 4, indipendenti dall'ordine.
- **Skip**: nessuno.

## 2. Test e contratti

| Test | Contratto protetto |
|---|---|
| `test_user_with_open_dataset_can_access_public_catalog` | Un utente con `open_dataset=True` vede nel catalogo il dataset pubblico controllato e puo leggerne il dettaglio. |
| `test_private_dataset_visibility_requires_explicit_grant` | Un privato non assegnato restituisce `404`; quello assegnato restituisce `200` e `is_public is False`. |
| `test_private_grant_survives_disabling_open_dataset` | Dopo `open_dataset=False`, il pubblico passa da `200` a `404`, mentre il grant privato continua a restituire `200`. |
| `test_unknown_dataset_lookups_return_404` | Nome UUID casuale, `error` e `duplicates` restituiscono tutti `404`. |

I lookup negativi restano in un solo test perche rappresentano lo stesso
contratto di `SingleDataset`; i tre comportamenti autorizzativi sono invece
isolati in test autonomi.

## 3. Backend esercitato

| Elemento | Ruolo |
|---|---|
| `Datasets.get` | Serve il catalogo autenticato filtrato. |
| `SingleDataset.get` | Restituisce il dettaglio soltanto se presente nel catalogo autorizzato. |
| `SqlApiDbManager.get_datasets` | Applica `GroupLicense.is_public`, `User.open_dataset` e `user.datasets`. |
| Endpoint admin users | Crea l'utente, applica `open_dataset=False` e lo elimina nel teardown. |
| `Datasets`, `License`, `GroupLicense`, `Attribution` | Costituiscono cataloghi pubblici e privati reali ma sintetici. |

Le chiamate HTTP, l'autenticazione, la serializzazione e il filtro SQLAlchemy
sono reali; non vengono usati mock delle autorizzazioni.

## 4. Setup e teardown

Ogni scenario chiama `create_test_dataset` per ogni catalog entry necessaria.
Ogni chiamata crea un bundle autonomo con group license, license e attribution
propri, quindi non esiste piu il prerequisito di almeno una license o
attribution seedata.

`_create_test_user` crea un utente distinto e registra immediatamente il DELETE
amministrativo. Grazie al teardown LIFO l'utente viene eliminato prima dei
bundle a cui e associato; ogni bundle stacca comunque eventuali associazioni
residue prima di cancellare dataset, license, gruppo e attribution.

Non vengono piu riusati `sa_dataset*`, non viene modificato alcun `license_id`
preesistente e non serve ripristinare stato del catalogo reale.

## 5. Call chain autorizzativa

```text
GET /datasets[/<id>]
  -> Datasets.get / SingleDataset.get
  -> SqlApiDbManager.get_datasets(db, user)
     -> privato: richiede ds.name in user.datasets
     -> pubblico: richiede user.open_dataset
  -> SingleDataset cerca l'id nel risultato gia filtrato
     -> assente o non autorizzato: 404
```

La transizione usa `PUT /admin/users/<uuid>` mantenendo il medesimo grant
privato e impostando `open_dataset=False`.

## 6. Limiti residui

- Non copre `licenceSpecs=True`.
- Il backend autorizza per `Datasets.name` e cerca il dettaglio per `arkimet_id`; i bundle usano intenzionalmente lo stesso valore per entrambi.
- La transizione dipende anche dal corretto funzionamento del PUT amministrativo utenti.
- Un arresto forzato del processo puo impedire l'esecuzione del teardown pytest.

## 7. Validazione

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --file tests/custom/integration/dataset/test_dataset_authorization.py'
```

Esito mirato: **4 passed, 0 skipped, 0 failed, 0 errors**.

```bash
.mhub-venv/bin/rapydo shell backend 'restapi tests --folder custom/integration/dataset'
```

Esito finale di cartella: **5 passed, 0 skipped, 0 failed, 0 errors**.