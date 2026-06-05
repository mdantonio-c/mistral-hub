# Problems And Bugs Discovered In Extension

Scopo del file:

- Tenere traccia dei bug backend e dei comportamenti anomali scoperti durante l'estensione della suite.
- Registrare ogni skip forzato introdotto al posto di un `xfail`, con analisi tecnica sufficiente a riattivare il test quando il backend verra corretto.

Regola mandatoria:

- Ogni volta che un prompt o un test `_EXT` scopre un bug backend o introduce uno skip forzato, questo file deve essere aggiornato nella stessa lavorazione.

## OBSERVED-001 - `stationDetails` restituisce `200` vuoto invece di `404`

Data emersione:

- 2026-05-29.

Superficie coinvolta:

- Endpoint observed GET `stationDetails` in `projects/mistral/backend/endpoints/maps_observed.py`.
- Test di copertura: `projects/mistral/backend/tests/integration/observed/test_observations_edge_cases_EXT.py`.

Finestra dati usata:

- `agrmet` DBALLE `2020-04-06 00:00-01:00`.

Sintomo osservato:

- Con `stationDetails=true`, network `agrmet` valido e stazione inesistente, il runtime non costruisce il `404` atteso.
- Il test ha provato due strade:
  - `ident="missing-station-ext"`, dove `ident` e correttamente trattato come stringa dal controller.
  - Fallback senza `ident`, usando `lat/lon` lontane da una stazione reale scoperta nella stessa finestra DBALLE.
- In entrambi i casi il backend ha restituito `200` con payload vuoto invece di `404`.

Analisi tecnica:

- Il controller prepara `query_station_data` con `ident` oppure con `lat/lon` in `MapsObservations.get`.
- Dopo la query DBALLE, il controller fa:

```python
res = dballe.parse_obs_maps_response(raw_res, last)
if not res and stationDetails:
    raise NotFound("Station data not found")
```

- Il ramo `404` scatta solo se `res` e falsy.
- Nel runtime attuale, pero, la risposta finale e strutturata ma senza dati utili, quindi il payload resta truthy e il `NotFound` non viene sollevato.

Impatto sulla suite:

- La suite non usa `xfail`.
- Il test fa quindi `skip` esplicito solo dopo avere tentato sia il path con `ident` sia il path con `lat/lon`.

Condizione di riattivazione del test:

- Il test potra tornare completamente verde quando il backend restituira `404` per `stationDetails` su stazione inesistente, non `200` con payload vuoto.

Fix backend atteso:

- In `MapsObservations.get`, trattare come assenza di stazione anche il caso in cui `res` esista ma `data` sia vuoto, non solo il caso `not res`.

## FIELDS-001 - Forecast `/fields?SummaryStats=false` usa `resulting_fields` non inizializzato

Data emersione:

- 2026-05-29.

Superficie coinvolta:

- Endpoint `projects/mistral/backend/endpoints/fields.py`.
- Test di copertura: `projects/mistral/backend/tests/integration/fields/test_fields_api_EXT.py`.

Finestre dati usate:

- Forecast `lm5` `2021-10-19`.
- Forecast `lm2.2` `2019-09-10` come alternativa portabile tra locale e CI.

Sintomo osservato:

- Nel ramo forecast, `GET /api/fields?...&SummaryStats=false` genera `UnboundLocalError: local variable 'resulting_fields' referenced before assignment`.
- Nel runtime attuale il wrapper restapi espone il difetto come `400 BAD REQUEST`.

Analisi tecnica:

- `Fields.get` inizializza `resulting_fields` solo nel ramo OBS.
- Il ramo FOR usa invece `summary = arki.load_summary(...)` e non crea `resulting_fields`.
- Nel blocco finale condiviso il controller esegue comunque:

```python
if not SummaryStats:
    resulting_fields.pop("summarystats", None)
```

- Sul forecast questa variabile non esiste, quindi il controller cade in `UnboundLocalError`.

Impatto sulla suite:

- La suite non usa `xfail`.
- Il test esegue il probe reale del ramo forecast e, quando il bug si riproduce, usa uno `skip` esplicito e documentato.

Condizione di riattivazione del test:

- Il test dovra tornare verde quando il backend restituira `200` e un payload forecast senza `summarystats` per `SummaryStats=false`.

Fix backend atteso:

- Rendere il blocco finale indipendente da `resulting_fields` oppure inizializzare la stessa struttura in entrambi i rami OBS/FOR.
- La correzione piu diretta e rimuovere `summarystats` da `summary["items"]` nel blocco finale, invece di usare una variabile definita solo per OBS.

## TEMPLATES-001 - `Template.get` inverte il controllo di esistenza del file

Data emersione:

- 2026-05-29.

Superficie coinvolta:

- Endpoint `projects/mistral/backend/endpoints/templates.py`.
- Test di copertura: `projects/mistral/backend/tests/integration/templates/test_templates_upload_delete_EXT.py`.

Finestra dati usata:

- Nessun dato meteorologico reale; il test usa file template sintetici sotto `/data/<uuid>/uploads`.

Sintomo osservato:

- `GET /api/templates/<template_name>` restituisce `404` quando il file esiste.
- Lo stesso ramo puo restituire `200` con un filepath inesistente quando il file manca.

Analisi tecnica:

- In `Template.get`, il controllo corrente è (alla riga 256):

```python
if filepath.exists():
    raise NotFound("The template doesn't exist")
```

- La condizione e invertita rispetto al contratto atteso: il `NotFound` dovrebbe essere
  sollevato quando il path non esiste, non quando esiste.

Impatto sulla suite:

- La suite non usa `xfail`.
- I test EXT eseguono la chiamata HTTP reale e usano `pytest.skip(...)` esplicito solo
  quando il bug si riproduce, lasciando gia in sede gli assert verdi attesi dopo il fix.

Condizione di riattivazione del test:

- Il test sul file esistente dovra restituire `200` con `filepath` e `format`.
- Il test sul file mancante dovra restituire `404`.

Fix backend atteso:

- Invertire la condizione in `Template.get` usando `if not filepath.exists(): raise NotFound(...)`.

## TEMPLATES-002 - Upload con estensione non ammessa maschera il messaggio di validazione

Data emersione:

- 2026-05-29.

Superficie coinvolta:

- Endpoint `projects/mistral/backend/endpoints/templates.py`.
- Test di copertura: `projects/mistral/backend/tests/integration/templates/test_templates_upload_delete_EXT.py`.

Finestra dati usata:

- Nessun dato meteorologico reale; il test usa un upload multipart sintetico con file `.txt`.

Sintomo osservato:

- `POST /api/templates` con estensione non ammessa restituisce correttamente `400`.
- Il body atteso `File extension not allowed` viene pero mascherato da una risposta
  generica con `FileNotFoundError`.

Analisi tecnica:

- `Uploader.upload` solleva `BadRequest("File extension not allowed")` prima di creare
  la directory `uploads/shp`.
- Il blocco `except` di `Template.post` prova comunque a iterare `subfolder.iterdir()`
  per rimuovere eventuali `.zip` o `.geojson`.
- Quando `subfolder` non esiste, il cleanup solleva `FileNotFoundError` e il messaggio
  di validazione originale viene perso.

Impatto sulla suite:

- La suite non usa `xfail`.
- Il test mantiene attivo l'assert sul codice `400` e usa `pytest.skip(...)` esplicito
  solo per il body finche il cleanup interno continua a mascherare il messaggio.

Condizione di riattivazione del test:

- Il test potra tornare completamente verde quando l'upload `.txt` restituira `400` con
  body `File extension not allowed`.

Fix backend atteso:

- Nel blocco `except` di `Template.post`, verificare `subfolder.exists()` prima di
  iterare la directory, oppure preservare il `BadRequest` originale senza sostituirlo
  con l'errore del cleanup.

## ADMIN-001 - `AdminLicenses` non espone `404` per group license mancante

Data emersione:

- 2026-05-29.

Superficie coinvolta:

- Endpoint `projects/mistral/backend/endpoints/admin_licenses.py`.
- Test di copertura: `projects/mistral/backend/tests/integration/admin/test_admin_licenses_EXT.py`.

Finestra dati usata:

- Nessun dato meteorologico reale; il test usa solo metadata admin sintetici o un id
  volutamente inesistente.

Sintomo osservato:

- Il contratto documentato dell'endpoint prevede `404` quando una license viene creata
  o aggiornata con un group license mancante.
- Nel runtime corrente, la schema dinamica costruita da `getPOSTInputSchema` intercetta
  prima il valore non presente nella `OneOf` degli id esistenti e restituisce `400`.
- Il ramo applicativo che dovrebbe sollevare `NotFound` non viene quindi raggiunto dal
  normale percorso HTTP.

Analisi tecnica:

- `getInputSchema` popola `group_license` con `validate.OneOf(choices=lgroup_keys)`.
- Un id inesistente e quindi respinto a livello schema, prima di entrare in
  `AdminLicenses.post` o `AdminLicenses.put`.
- Nel controller, inoltre, il controllo di esistenza usa `.first` senza chiamarlo:

```python
lic_group = db.GroupLicense.query.filter_by(id=lgroup_id).first
if not lic_group:
    raise NotFound("This license group")
```

- Anche se la validazione fosse bypassata, quel controllo resterebbe truthy perche
  `lic_group` e il metodo bound, non il risultato della query.

Impatto sulla suite:

- La suite non usa `xfail`.
- Il test esegue la chiamata HTTP reale e, quando riceve il `400` di validazione, usa
  `pytest.skip(...)` esplicito e documentato invece di lasciare un failure stabile fuori
  dal perimetro correggibile dei test.

Condizione di riattivazione del test:

- Il test potra tornare completamente verde quando il backend esporra un contratto
  coerente per group license mancante, idealmente `404` come dichiarato nelle response
  dell'endpoint.

Fix backend atteso:

- Allineare schema e controller: oppure mantenere `400` e aggiornare il contratto
  documentato, oppure permettere al controller di gestire l'id mancante e restituire
  `404`.
- In ogni caso correggere `.first` in `.first()` nei rami `post` e `put` di
  `AdminLicenses`.

## ARCO-001 - ClientError S3 non `NoSuchKey` viene esposto come `400`

Data emersione:

- 2026-05-29.

Superficie coinvolta:

- Endpoint proxy ARCO in `projects/mistral/backend/endpoints/arco.py`.
- Test di copertura: `projects/mistral/backend/tests/integration/arco/test_arco_edge_cases_EXT.py`.

Finestra dati usata:

- Nessun dato meteorologico reale; il test usa un fake S3 locale e un
  `botocore.exceptions.ClientError` sintetico con codice `InternalError`.

Sintomo osservato:

- Il prompt 08 richiede che un `ClientError` S3 diverso da `NoSuchKey` venga esposto
  come errore server del proxy ARCO.
- Nel runtime attuale il controller rilancia una `Exception` generica e il wrapper
  restapi la serializza come `400 BAD REQUEST` con body generico `Unknown error`.

Analisi tecnica:

- In `ArcoResource.get`, il ramo e:

```python
except botocore.exceptions.ClientError as e:
    if e.response["Error"]["Code"] == "NoSuchKey":
        raise NotFound(...)
    else:
        raise Exception from e
```

- Il wrapper HTTP non trasforma questa `Exception` in un `500`, ma in un `400`.
- La suite non puo correggere il controller perche il Prompt 08 limita le modifiche a
  `projects/mistral/backend/tests`.

Impatto sulla suite:

- La suite non usa `xfail`.
- Il test esegue comunque il ramo con fake S3 e usa `pytest.skip(...)` esplicito solo
  quando osserva lo status diverso da `500`.

Condizione di riattivazione del test:

- Il test potra tornare completamente verde quando il proxy ARCO restituira un vero
  errore server, idealmente `500`, per `ClientError` S3 non `NoSuchKey`.

Fix backend atteso:

- Sostituire il `raise Exception from e` con una eccezione restapi coerente con errore
  server, oppure lasciare propagare un errore gestito dal framework come `500`.