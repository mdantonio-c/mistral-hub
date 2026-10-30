# Review — `test_templates_listing_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/templates/test_templates_listing_EXT.py](projects/mistral/backend/tests/integration/templates/test_templates_listing_EXT.py)
- **Scopo**: verificare il contratto di `GET /api/templates` (listing): autenticazione obbligatoria, forma `grib`/`shp` con liste vuote, filtro `format`, ramo compatto `get_total`, e flag `max_allowed` quando il numero di template di un tipo raggiunge `max_templates`.
- **Tipologia**: test di **integrazione HTTP** (controller reale + **filesystem reale** sotto `/data/<uuid>/uploads` + lettura del campo `max_templates` dal DB). Marker: `integration`, `deterministic`.
- **Dati reali**: nessuno. I file `grib`/`shp` sono **byte sintetici** scritti solo nella directory dell'utente temporaneo; nessun dataset meteo viene letto. Nessun monkeypatch, nessun worker/broker.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Templates.get` | [endpoints/templates.py#L46](projects/mistral/backend/endpoints/templates.py#L46) | `GET /api/templates` — `glob` su `uploads/grib/*` e `uploads/shp/*.shp`, costruisce gli oggetti `grib`/`shp`, applica `format` e `get_total`. |
| Ramo `get_total` | [endpoints/templates.py#L63](projects/mistral/backend/endpoints/templates.py#L63) | Ritorna subito `{"total": counter}` (grib, shp o somma) **senza** costruire gli oggetti né leggere `max_templates`. |
| Calcolo `max_allowed` | [endpoints/templates.py#L83](projects/mistral/backend/endpoints/templates.py#L83) | `True` se `max_templates` è valorizzato **e** `len(files) >= int(max_templates)`; altrimenti `False`. |
| `TemplatesFormatter` | [endpoints/templates.py#L26](projects/mistral/backend/endpoints/templates.py#L26) | Schema query: `format` `OneOf(["grib","shp"])`, `perpage`, `currentpage`, `get_total` (Bool). |
| `SqlApiDbManager.get_user_permissions` | [services/sqlapi_db_manager.py#L665](projects/mistral/backend/services/sqlapi_db_manager.py#L665) | Per `param="templates"` ritorna `user.max_templates`. |
| `User.max_templates` | [models/sqlalchemy.py#L27](projects/mistral/backend/models/sqlalchemy.py#L27) | Colonna `Integer` **nullable senza default**: limite condiviso fra grib e shp. |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `client` | fixture | `restapi.tests` | `FlaskClient` di test. |
| `cleanup_registry` | fixture | [tests/conftest.py#L39](projects/mistral/backend/tests/conftest.py#L39) | Teardown **LIFO** (`CleanupRegistry`); non ingoia eccezioni. |
| `TEMPLATES_ENDPOINT_EXT` | costante | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | URL `{API_URI}/templates`. |
| `create_templates_user_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Crea utente via API admin con `max_templates`/`disk_quota` espliciti; registra cleanup dell'utente e di `/data/<uuid>`. |
| `seed_template_file_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Scrive un file sintetico in `uploads/grib` o `uploads/shp` (dedotto dall'estensione) e registra `uploads` nel cleanup. |
| `listed_filenames_EXT` | helper | [templates/support_EXT.py](projects/mistral/backend/tests/integration/templates/support_EXT.py) | Estrae i **soli nomi** dai `Path` serializzati come stringhe assolute. |
| `BaseTests().get_content` | helper | `restapi.tests` | Decodifica il body della risposta. |

> Infrastruttura condivisa solo referenziata: [tests/conftest.py](projects/mistral/backend/tests/conftest.py), helper di auth in [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py). Il dettaglio dei builder è in [support_EXT.py.review.md](projects/mistral/backend/tests/integration/templates/support_EXT.py.review.md).

## 4. Analisi dettagliata di ogni test

### `test_templates_listing_requires_authentication_EXT`
- **Obiettivo**: il listing non è accessibile senza login.
- **Backend coinvolto**: decoratore `@decorators.auth.require()` **prima** di `Templates.get`.
- **Flusso**: GET anonima, senza utenti né file.
- **Setup**: nessuno (solo `client`).
- **Assert**: `status_code == 401`.
- **Casi coperti**: error path / bordo auth. La GET non deve leggere alcuna cartella utente.

### `test_templates_listing_returns_empty_grib_and_shp_lists_EXT`
- **Obiettivo**: forma del listing quando l'utente non ha upload e **le directory non esistono**.
- **Backend coinvolto**: `Templates.get` (rami `grib_object`/`shp_object`, `max_allowed=False`).
- **Flusso**: crea utente `max_templates=3` senza scrivere file → GET → confronto **esatto** del payload.
- **Setup**: `create_templates_user_EXT(..., max_templates=3)`; nessun `seed`.
- **Assert**: `200` e `content == [{"type":"grib","files":[],"max_allowed":False},{"type":"shp","files":[],"max_allowed":False}]`.
- **Casi coperti**: happy path “vuoto”. Documenta che `glob` su directory **inesistente** ritorna lista vuota (non solleva), quindi non serve precreare `uploads/`.

### `test_templates_listing_filters_by_format_EXT`
- **Obiettivo**: `format=grib` limita il payload alla sola sezione grib.
- **Backend coinvolto**: `Templates.get` ramo `if format == "grib"`.
- **Flusso**: seed di `filter_ext.grib` (in `uploads/grib`) e `filter_ext.shp` (in `uploads/shp`) → GET con `query_string={"format":"grib"}`.
- **Setup**: `max_templates=5`; due `seed_template_file_EXT` (filesystem reale dell'utente).
- **Assert**: `200`; `len(content)==1`; `content[0]["type"]=="grib"`; `listed_filenames_EXT(content[0]["files"]) == {"filter_ext.grib"}`.
- **Casi coperti**: filtro positivo + isolamento del file shp dalla sezione grib. Il confronto sui **soli nomi** evita dipendenze dal prefisso assoluto `/data`.

### `test_templates_listing_get_total_counts_all_and_filtered_templates_EXT`
- **Obiettivo**: ramo compatto `get_total` su totale complessivo e su filtro grib.
- **Backend coinvolto**: `Templates.get` ramo `if get_total` (ritorno anticipato).
- **Flusso**: seed di un grib e uno shp → due GET (`get_total=True`, poi `get_total=True&format=grib`).
- **Setup**: `max_templates=5`; un file per tipo.
- **Assert**: entrambe `200`; `get_content(total)=={"total":2}`; `get_content(grib_total)=={"total":1}`.
- **Casi coperti**: conteggio aggregato e filtrato. Verifica che `get_total` **non** costruisca gli oggetti grib/shp.

### `test_templates_listing_marks_max_allowed_when_limit_is_reached_EXT`
- **Obiettivo**: `max_allowed=True` quando ciascun tipo raggiunge `max_templates`.
- **Backend coinvolto**: `Templates.get`, blocco `max_allowed` ([endpoints/templates.py#L83](projects/mistral/backend/endpoints/templates.py#L83)).
- **Flusso**: utente `max_templates=1`, seed di un grib e uno shp → GET singola.
- **Setup**: `max_templates=1`; un file per tipo.
- **Assert**: `200`; `by_type["grib"]["max_allowed"] is True` e `by_type["shp"]["max_allowed"] is True`.
- **Casi coperti**: soglia raggiunta su **entrambe** le famiglie con lo stesso limite (il campo `max_templates` è unico per i due tipi).

## 5. Call chain

```
GET /api/templates                 → auth.require()  → (anonimo → 401)
                                     → use_kwargs(TemplatesFormatter, location="query")
                                     → Templates.get(user, format, get_total, ...)
                                       → grib = glob(DATA_PATH/<uuid>/uploads/grib/*)
                                       → shp  = glob(DATA_PATH/<uuid>/uploads/shp/*.shp)
                                       → if get_total: response({"total": counter})        ← ramo compatto
                                       → max = get_user_permissions(user,"templates") = user.max_templates
                                       → grib_object{max_allowed: max and len(grib)>=max}
                                       → shp_object {max_allowed: max and len(shp)>=max}
                                       → format? grib | shp | entrambi → response([...]) 200
```

## 6. Comportamenti nascosti

- **`glob` su directory inesistente non solleva**: ritorna iteratore vuoto. È la ragione per cui il test “vuoto” funziona senza precreare `uploads/grib` e `uploads/shp`.
- **Glob asimmetrici**: grib usa `*` (qualsiasi file), shp usa `*.shp` (solo `.shp`). Un sidecar `.prj`/`.dbf` finito in `uploads/grib` **conterebbe** come template grib, mentre in `uploads/shp` no. I test usano file coerenti e non incappano nell'asimmetria.
- **`max_allowed` dipende solo da `max_templates`**: non esistono limiti separati grib/shp; lo stesso intero vale per entrambe le sezioni.
- **`max_templates` None/0 ⇒ `max_allowed` sempre `False`**: per via di `if max_user_templates and ...` (corto-circuito). I test usano valori `>=1`.
- **Path serializzati come stringhe assolute**: `files` contiene `Path` resi come stringhe `/data/...`; `listed_filenames_EXT` normalizza al solo `name`.
- **Cleanup ridondante ma sicuro**: `register_test_user_cleanup` registra `/data/<uuid>`, mentre `seed_template_file_EXT` registra anche `uploads`. Per via del LIFO viene rimosso prima `uploads`, poi l'intera `/data/<uuid>`.

## 7. Checklist di revisione

- [ ] Confermare che il listing legga davvero il **filesystem reale** dell'utente temporaneo e non uno stato condiviso (i `seed` scrivono sotto `/data/<uuid>/uploads`).
- [ ] Verificare che l'asimmetria dei glob (`*` vs `*.shp`) sia un comportamento accettato del backend, non un effetto collaterale del test.
- [ ] Verificare che il confronto **esatto** del payload “vuoto” resti valido se il serializer dovesse aggiungere campi.
- [ ] Confermare che `get_total` non debba mai esporre `max_allowed` (contratto del ramo compatto).

## 8. Possibili criticità

- **Accoppiamento al filesystem del container**: i test scrivono e leggono sotto `/data/<uuid>`; un permesso o un mount diverso in CI ne cambierebbe l'esito. Mitigato dal confinamento all'uuid temporaneo e dal cleanup LIFO.
- **Dipendenza dall'admin customizer**: `max_templates`/`disk_quota` sono impostati via API admin di creazione utente; se il customizer ignorasse i valori, gli assert su `max_allowed` perderebbero significato (qui non accade perché i valori sono espliciti).
- **Asimmetria glob non testata sul ramo limite**: nessun test verifica cosa accade con file “estranei” nelle cartelle (es. `.prj` in `uploads/grib`); ramo non coperto.
- **Confronto esatto fragile**: l'uguaglianza puntuale del payload vuoto è severa per definizione (intenzionale), ma sensibile a future aggiunte di campi nel contratto.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `..._requires_authentication_EXT` | `auth.require` | 401 anonimo | — | `client` | Bassa |
| `..._returns_empty_grib_and_shp_lists_EXT` | `Templates.get` | forma vuota, glob su dir assenti | — (FS reale) | `client`, `cleanup_registry` | Bassa |
| `..._filters_by_format_EXT` | `Templates.get` (format) | filtro grib + isolamento shp | — (FS reale) | `client`, `cleanup_registry` | Media |
| `..._get_total_counts_all_and_filtered_templates_EXT` | `Templates.get` (`get_total`) | conteggio totale e filtrato | — (FS reale) | `client`, `cleanup_registry` | Media |
| `..._marks_max_allowed_when_limit_is_reached_EXT` | `Templates.get` (`max_allowed`) | soglia raggiunta su grib e shp | — (DB+FS reali) | `client`, `cleanup_registry` | Media |
