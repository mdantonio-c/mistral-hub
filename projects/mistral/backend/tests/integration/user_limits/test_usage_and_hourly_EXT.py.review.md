# Review — `test_usage_and_hourly_EXT.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.
> Modulo `*_EXT.py`: copertura **di estensione** sopra la baseline legacy.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/user_limits/test_usage_and_hourly_EXT.py](projects/mistral/backend/tests/integration/user_limits/test_usage_and_hourly_EXT.py)
- **Scopo**: verificare `GET /api/usage` (quota disco + uso reale misurato con `du`) e `GET /api/hourly` (richieste residue nell'ora corrente), inclusi i bordi auth, directory assente, file presente, profilo senza limite orario e conteggio nella finestra dell'ora.
- **Tipologia**: test di **integrazione HTTP** con **DB reale** (mutazione diretta dei campi quota e seeding di righe `Request`) e **filesystem reale** sotto `/data/<uuid>`. Marker: `integration`, `deterministic`.
- **Builder locali**: il modulo **non** ha un `support.py` dedicato; definisce in-line i propri builder e un `datetime` fisso (vedi §3).
- **Dati reali**: nessuno. File e `Request` sono sintetici e confinati all'utente temporaneo. Un solo `monkeypatch` sul `datetime` dell'endpoint hourly; nessun worker/broker.

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| `Usage.get` | [endpoints/usage.py](projects/mistral/backend/endpoints/usage.py) | `GET /api/usage` — `used=0` se `/data/<uuid>` non è dir; altrimenti `du -sb`; ritorna `{"quota": user.disk_quota, "used": used}`. |
| `HourlyReport.get` | [endpoints/request_hourly_report.py](projects/mistral/backend/endpoints/request_hourly_report.py) | `GET /api/hourly` — `{}` se `user.request_par_hour` è **falsy**; altrimenti conta le `Request` dell'utente con `last_hour < submission_date < now`. |
| Check `if user.request_par_hour` | [endpoints/request_hourly_report.py](projects/mistral/backend/endpoints/request_hourly_report.py) | **Truthy check**: `None` e `0` producono entrambi `{}` (indistinguibili). |
| Finestra temporale hourly | [endpoints/request_hourly_report.py](projects/mistral/backend/endpoints/request_hourly_report.py) | `now = datetime.datetime.utcnow()`, `last_hour = now.replace(minute=0, second=0, microsecond=0)`; filtri **stretti** `>` e `<`. |
| `User.disk_quota` | [models/sqlalchemy.py#L11](projects/mistral/backend/models/sqlalchemy.py#L11) | BigInteger, default 1 GB. |
| `User.request_par_hour` | [models/sqlalchemy.py#L32](projects/mistral/backend/models/sqlalchemy.py#L32) | Integer **nullable senza default**. |
| Modello `Request` | [models/sqlalchemy.py#L36](projects/mistral/backend/models/sqlalchemy.py#L36) | `user_id`, `name` (NOT NULL), `args` (JSONB NOT NULL), `submission_date`, `status` — campi seedati direttamente. |

## 3. Builder locali e fixture

| Elemento | Tipo | Ruolo / effetti collaterali |
|---|---|---|
| `USAGE_ENDPOINT_EXT` / `HOURLY_ENDPOINT_EXT` | costanti | `{API_URI}/usage` e `{API_URI}/hourly`. |
| `create_user_limits_user_EXT` | builder | Crea utente via API admin **poi forza** `disk_quota` e `request_par_hour` **direttamente sul record DB** (commit); registra cleanup utente + `/data/<uuid>`. |
| `user_root_EXT` | helper path | `Path(DOWNLOAD_DIR, user.uuid)` = `/data/<uuid>`. |
| `write_usage_file_EXT` | seeding FS | Scrive un file sotto `/data/<uuid>/outputs/...`; registra la radice utente nel cleanup **prima** della scrittura. |
| `seed_hourly_request_EXT` | seeding DB | Inserisce una `Request` (commit) con `submission_date` controllata; registra cleanup DB **dopo** quello dell'utente (ordine LIFO ⇒ request rimossa prima dell'utente). |
| `delete_hourly_request_EXT` | cleanup DB | Rimozione **idempotente** della `Request` (no-op se già assente). |
| `FixedHourlyDateTime_EXT` | fake | Sottoclasse di `datetime` con `utcnow()` fisso a **2026-05-29 10:30:00** (lontano dai bordi dell'ora). |
| `client` | fixture | `FlaskClient` (`restapi.tests`). |
| `cleanup_registry` | fixture | Teardown **LIFO** ([tests/conftest.py#L39](projects/mistral/backend/tests/conftest.py#L39)). |
| `monkeypatch` | fixture | Patcha `datetime.datetime` visto dall'endpoint hourly (vedi §6). |

> Helper di auth riusati: `create_authenticated_test_user`, `register_test_user_cleanup`, `AuthenticatedTestUser` da [tests/helpers/auth.py](projects/mistral/backend/tests/helpers/auth.py).

## 4. Analisi dettagliata di ogni test

### `test_usage_endpoint_requires_authentication_EXT`
- **Obiettivo**: `/usage` richiede login.
- **Backend coinvolto**: `auth.require()` prima di `Usage.get`.
- **Flusso**: GET anonima.
- **Setup**: nessuno.
- **Assert**: `401`.
- **Casi coperti**: bordo auth.

### `test_usage_returns_zero_when_user_directory_is_absent_EXT`
- **Obiettivo**: `used=0` quando `/data/<uuid>` non esiste.
- **Backend coinvolto**: `Usage.get` ramo `if user_dir.is_dir()` falso.
- **Flusso**: crea utente `disk_quota=12345` → `shutil.rmtree(user_root)` (forza l'assenza) → GET.
- **Setup**: `create_user_limits_user_EXT`; rimozione esplicita della radice utente.
- **Assert**: `200`; `get_content == {"quota": 12345, "used": 0}`.
- **Filesystem**: rimuove (best-effort) `/data/<uuid>` se presente.
- **Casi coperti**: ramo directory assente; `quota` proviene dal **valore DB forzato**.

### `test_usage_returns_positive_used_when_user_directory_has_files_EXT`
- **Obiettivo**: `/usage` misura i file reali sotto la directory utente.
- **Backend coinvolto**: `Usage.get` ramo `du -sb`.
- **Flusso**: crea utente `disk_quota=67890` → `write_usage_file_EXT` (file in `/data/<uuid>/outputs`) → GET.
- **Setup**: `create_user_limits_user_EXT` + seeding file.
- **Assert**: `200`; `content["quota"]==67890`; `content["used"] >= file_path.stat().st_size`; `content["used"] > 0`.
- **Filesystem**: scrive un file reale sotto `/data/<uuid>/outputs/`.
- **Casi coperti**: ramo uso positivo. Assert **non tautologico**: il file è creato dal test e l'assert pretende che `du` includa **almeno** la sua dimensione (tollerante all'overhead di directory).

### `test_hourly_endpoint_requires_authentication_EXT`
- **Obiettivo**: `/hourly` richiede login.
- **Backend coinvolto**: `auth.require()` prima di `HourlyReport.get`.
- **Flusso**: GET anonima.
- **Setup**: nessuno.
- **Assert**: `401`.
- **Casi coperti**: bordo auth.

### `test_hourly_returns_empty_object_when_user_has_no_hourly_limit_EXT`
- **Obiettivo**: `{}` quando `request_par_hour` è assente.
- **Backend coinvolto**: `HourlyReport.get` ramo `if user.request_par_hour` **falsy**.
- **Flusso**: crea utente con `request_par_hour=None` (forzato su DB) → GET.
- **Setup**: `create_user_limits_user_EXT(..., request_par_hour=None)`.
- **Assert**: `200`; `get_content == {}`.
- **Casi coperti**: ramo “nessun limite”. **Nota**: per il truthy check, anche `request_par_hour=0` darebbe `{}` — “nessun limite” e “limite zero” sono **indistinguibili** (vedi §6).

### `test_hourly_reports_submitted_total_and_remaining_in_current_hour_EXT`
- **Obiettivo**: conteggio corretto con richieste dentro/fuori l'ora corrente.
- **Backend coinvolto**: `HourlyReport.get` (count su `last_hour < submission_date < now`).
- **Flusso**: `monkeypatch` di `datetime.datetime` → `FixedHourlyDateTime_EXT` (utcnow = 10:30); utente `request_par_hour=3`; seed di tre `Request`: 10:20 (now−10m), 10:10 (now−20m), 09:59 → GET.
- **Setup**: `create_user_limits_user_EXT` + tre `seed_hourly_request_EXT` (righe DB reali).
- **Assert**: `200`; `get_content == {"submitted": 2, "total": 3, "remaining": 1}`.
- **DB**: tre righe `Request` inserite e rimosse nel teardown (LIFO, prima delle request poi l'utente).
- **Casi coperti**: conteggio nella finestra + esclusione del bordo `09:59`. Assert **non tautologico**: usa righe DB reali e la `count()` reale; `last_hour=10:00` esclusivo separa la riga 09:59.

## 5. Call chain

```
GET /api/usage    → auth.require()  → (anonimo → 401)
                  → Usage.get(user)
                    → user_dir = /data/<uuid>
                    → user_dir.is_dir()? → du -sb : used=0
                    → response({"quota": user.disk_quota, "used": used}) 200
GET /api/hourly   → auth.require()  → (anonimo → 401)
                  → HourlyReport.get(user)
                    → if user.request_par_hour:           ← falsy (None/0) → {}
                        now = datetime.datetime.utcnow()   ← monkeypatch nel test (10:30)
                        last_hour = now.replace(minute=0, second=0, microsecond=0)  (10:00)
                        count = Request[user] con last_hour < submission_date < now
                        data = {submitted, total=request_par_hour, remaining}
                    → response(data) 200
```

## 6. Comportamenti nascosti

- **Mutazione DB diretta nel builder**: `create_user_limits_user_EXT` crea l'utente via API admin **e poi sovrascrive** `disk_quota`/`request_par_hour` sul record con `db.session.commit()`. È un **seeding reale del DB**, necessario per rappresentare `request_par_hour=None` (il customizer assegnerebbe altrimenti un default). Gli assert su `quota`/`{}` dipendono da questo bypass.
- **Truthy check su `request_par_hour`**: `None` e `0` producono **entrambi** `{}`. Il test del ramo vuoto usa `None`, ma il contratto non distingue “senza limite” da “limite 0”.
- **Bersaglio del `monkeypatch`**: `monkeypatch.setattr(hourly_endpoint_module.datetime, "datetime", FixedHourlyDateTime_EXT)`. `hourly_endpoint_module.datetime` **è** l'oggetto modulo standard `datetime` (singleton condiviso), quindi si sta patchando `datetime.datetime` **globalmente** per la durata del test, non solo nell'endpoint. Il commento nel test (“non il modulo datetime globale”) è **fuorviante**: l'isolamento è garantito solo dal **ripristino automatico** di `monkeypatch` a fine test, non da un patch locale. Effetto collaterale: qualunque altro codice eseguito nel test che usi `datetime.datetime.utcnow()` vedrebbe l'istante fisso.
- **Finestra hourly con bordi stretti**: filtri `> last_hour` e `< now`. Una richiesta esattamente alle 10:00 o esattamente all'istante `now` **non** verrebbe contata.
- **Ordine di cleanup LIFO**: la `Request` viene registrata **dopo** il cleanup utente ⇒ rimossa **prima** dell'utente (evita FK pendenti). `delete_hourly_request_EXT` è idempotente.
- **`Usage.get` usa `du -sb` sull'intera `/data/<uuid>`**: l'uso include qualsiasi file sotto la radice utente, non solo `outputs/`; per questo l'assert è `>=` e non un valore esatto.

## 7. Checklist di revisione

- [ ] Confermare che la **mutazione diretta del DB** in `create_user_limits_user_EXT` sia accettabile come tecnica di seeding (bypassa l'admin customizer per `request_par_hour=None`).
- [ ] Valutare se il truthy check su `request_par_hour` debba distinguere `None` da `0` (oggi indistinguibili).
- [ ] Verificare la portata reale del `monkeypatch` sul `datetime` condiviso e correggere/chiarire il commento fuorviante nel test.
- [ ] Confermare i bordi stretti `>`/`<` della finestra hourly (richieste esattamente a `last_hour`/`now` escluse) come comportamento voluto.
- [ ] Verificare che l'assert `used >= file_size` resti adeguato rispetto all'overhead di `du` su directory.

## 8. Possibili criticità

- **Accoppiamento al DB reale**: i test scrivono direttamente su `User` e `Request`; un fallimento a metà si affida al cleanup LIFO per non lasciare righe orfane. La `Request` ha FK verso `user_id`: l'ordine di teardown è critico.
- **Commento fuorviante sul monkeypatch**: la nota “non il modulo datetime globale” non riflette il comportamento reale (patch globale ripristinato). Possibile fonte di confusione in revisione/manutenzione.
- **Contratto ambiguo `None`/`0`**: l'endpoint non distingue assenza di limite da limite nullo; nessun test copre `request_par_hour=0` esplicitamente.
- **Dipendenza dal filesystem del container**: `du -sb` e la creazione/cancellazione sotto `/data/<uuid>` dipendono da mount e permessi; mitigato dal confinamento all'uuid temporaneo.
- **Assert su `du` tollerante**: corretto evitare il valore esatto, ma significa che il test non verifica la dimensione precisa, solo la monotonia (`used>0` e `>= file_size`).

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock | Fixture | Complessità |
|---|---|---|---|---|---|
| `..._usage_endpoint_requires_authentication_EXT` | `auth.require` | 401 anonimo | — | `client` | Bassa |
| `..._usage_returns_zero_when_user_directory_is_absent_EXT` | `Usage.get` | `used=0` dir assente | — (FS+DB reali) | `client`, `cleanup_registry` | Bassa |
| `..._usage_returns_positive_used_when_user_directory_has_files_EXT` | `Usage.get` (`du`) | `used>0` con file reale | — (FS+DB reali) | `client`, `cleanup_registry` | Media |
| `..._hourly_endpoint_requires_authentication_EXT` | `auth.require` | 401 anonimo | — | `client` | Bassa |
| `..._hourly_returns_empty_object_when_user_has_no_hourly_limit_EXT` | `HourlyReport.get` | `{}` con `request_par_hour=None` | — (DB forzato) | `client`, `cleanup_registry` | Bassa |
| `..._hourly_reports_submitted_total_and_remaining_in_current_hour_EXT` | `HourlyReport.get` (count) | finestra ora: 2/3/1 | **monkeypatch datetime** | `client`, `cleanup_registry`, `monkeypatch` | Alta |
