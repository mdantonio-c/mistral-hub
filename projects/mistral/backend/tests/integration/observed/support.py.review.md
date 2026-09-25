# Review — `observed/support.py` (infrastruttura di dominio observed)

> File di review per modulo di supporto. Non contiene test. Struttura **ADATTATA** (niente "Call chain" o "Analisi per test").
> Modulo **attivo e fortemente runtime-dipendente**: apre una connessione **DBALLE reale a basso livello**, legge l'archivio Arkimet e interroga `/fields` per scoprire uno scenario osservato utilizzabile.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/observed/support.py](projects/mistral/backend/tests/integration/observed/support.py)
- **Scopo**: centralizzare la **scoperta** di uno "slice" osservato realmente disponibile nel runtime e la sua esposizione riusabile ai test, più i builder di query/URL e le utility di parsing. Gli scenari osservati dipendono da disponibilità DBALLE, finestre archiviate, network, prodotti e regole sui gruppi licenza: questa logica vive tutta qui.
- **Tipologia**: modulo di supporto **attivo** (connessione DBALLE diretta + archivio Arkimet + DB + chiamate HTTP a `/fields`). **Nessun mock dei dati**; l'unica patch è la soglia mobile `BeDballe.LASTDAYS`.
- **Nota trasversale**: è il cuore "runtime-sensitive" del dominio observed; **tutti** gli `skip` degli scenari parametrizzati nascono qui.

## 2. Backend realmente esercitato

| Elemento backend | Path | Come viene esercitato |
|---|---|---|
| `BeArkimet.get_obs_datasets` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L308) | **Letto**: elenco dataset osservati dal config Arkimet. |
| `BeArkimet.get_observed_dataset_params` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L238) | **Letto**: network per dataset (per prioritizzare `agrmet`). |
| `BeArkimet.load_summary` | [services/arkimet.py](projects/mistral/backend/services/arkimet.py#L74) | **Letto**: summary archivio per ricavare la finestra `b`/`e`. |
| `BeDballe.LASTDAYS` | [services/dballe.py](projects/mistral/backend/services/dballe.py#L117) | **Patchato** temporaneamente (`override_attr`) per allineare la classificazione `get_db_type`. |
| connessione **DBALLE** | (libreria `dballe`) | **`dballe.DB.connect(...)`** con DSN costruito dalle `db.variables` (`dbtype/user/password/host/port` → `/DBALLE`); poi `transaction.query_data(...)`. |
| `sqlalchemy.get_instance()` | `restapi.connectors` | **Letto**: solo per ricavare i parametri di connessione DBALLE (`db.variables`). |
| `GET /api/fields` | [endpoints/maps_observed.py](projects/mistral/backend/endpoints/maps_observed.py) | **Chiamato** durante la scoperta per validare la finestra ed estrarre `network`/`product`. |

## 3. Elementi definiti

| Nome | Tipo | Ruolo / effetti |
|---|---|---|
| `ObservedQueryParams` | dataclass (frozen) | Bundle: `date_from`, `date_to`, `network`, `product_1`, `product_2` (opz.). |
| `ObservedCase` | dataclass (frozen) | Scenario completo: `db_type`, `headers`, `params`. È ciò che il test riceve via fixture. |
| `ALL_CASES` | costante | `[dballe, arkimet, mixed]` come `pytest.param` con i **nomi** delle fixture. |
| `RECENT_CASES` | costante | `[dballe, mixed]` (scenari con dato recente). |
| `ARCHIVE_CASES` | costante | `[arkimet, mixed]` (scenari con dato archiviato). |
| `PREFERRED_OBSERVED_NETWORK` | costante | `"agrmet"` — network/dataset preferito perché ricco di prodotti. |
| `ITALY_BOUNDING_BOX` | costante | Dizionario `lonmin`/`lonmax`/`latmin`/`latmax` dell'area italiana, riusato dai test dei filtri spaziali. |
| `_prioritized_observed_datasets` | privato | Ordina i dataset mettendo prima quelli che espongono `agrmet`. |
| `_prioritized_networks` | privato | Ordina i network di un dataset preferendo `agrmet`. |
| `_dballe_network_window` | privato | Scorre `transaction.query_data({"rep_memo": network})` e ritorna la finestra **più ampia** (min→max+1h) o `None`. |
| `_summary_datetime` | privato | Converte una lista timestamp summary in `datetime`. |
| `_arkimet_dataset_window` | privato | Da `load_summary` ricava `(b, e)` o `None` se mancano. |
| `_lastdays_override_for_dballe_window` | privato | Calcola il valore `LASTDAYS` per far classificare la finestra storica come "recente". |
| `yield_observed_case` | generator | Scopre i parametri, applica l'eventuale override `LASTDAYS` e **`yield`** l'`ObservedCase`. |
| `discover_observed_params` | funzione | **Cuore della scoperta** (vedi §4); ritorna `(params, lastdays_override)` o esegue `pytest.skip`/`pytest.fail`. |
| `build_reftime_query` | builder | Compone la `q` `reftime:…;[product:…];license:CCBY_COMPLIANT`. |
| `build_observations_endpoint` | builder | Compone l'URL `/observations` con network/bbox/lat-lon/onlyStations/stationDetails. |
| `fetch_observations` | helper | `client.get` + `BaseTests().get_content` → `(response, content)`. |
| `extract_products` | utility | Estrae i `var` dei prodotti da `data[].prod[]`. |
| `extract_station_coordinates` | utility | `lat`/`lon` della **prima** stazione (`data[0]["stat"]`). |
| `fetch_station_sample` | helper | Esegue una query reale, **asserisce 200 + dict**, ritorna `lat`/`lon`. |
| `require_secondary_product` | gate | **`pytest.skip`** se `product_2 is None`. |

## 4. Comportamenti nascosti

- **Quattro punti di uscita "silenziosa" in `discover_observed_params`**: dopo aver camminato dataset×network e tentato `/fields`, se nessuno produce una finestra con ≥2 prodotti, la funzione esegue `pytest.skip` con messaggio specifico per `dballe`, `arkimet` o `mixed`; un quarto ramo `pytest.fail("No observed dataset returned usable fields…")` resta come rete di sicurezza teoricamente irraggiungibile. **Conseguenza**: ogni scenario parametrizzato che dipende da queste fixture è **silenziosamente saltabile**.
- **Requisito implicito "≥2 prodotti"**: la scoperta scarta finestre/network con meno di 2 prodotti (`if len(products) < 2: continue`). Questo è ciò che rende possibile `require_secondary_product` e spiega perché alcuni ambienti, pur avendo dati, **skippano** comunque.
- **Connessione DBALLE diretta a basso livello**: `discover_observed_params` apre `dballe.DB.connect(...)` usando le credenziali estratte da `db.variables` del connettore SQLAlchemy. Non passa dall'API: legge direttamente il database DBALLE per individuare la finestra reale. È un accoppiamento forte all'infrastruttura (DSN, rete, permessi DB).
- **Override `LASTDAYS` applicato due volte**: dentro la scoperta avvolge il probe `/fields`, e in `yield_observed_case` avvolge la **vita della fixture** (quindi l'esecuzione del test). Serve perché una finestra storica (es. agrmet 2020) venga classificata come "dballe recente" da `get_db_type`; senza, lo scenario `dballe`/`mixed` non vedrebbe quei dati. È ripristinato in `finally` da `override_attr`.
- **License group hardcoded**: `build_reftime_query` aggiunge **sempre** `license:CCBY_COMPLIANT`. L'intero dominio observed assume quindi che `agrmet` (o il dataset scoperto) appartenga a quel gruppo pubblico; un mismatch farebbe fallire la scoperta o le query.
- **Oracolo geografico condiviso**: `ITALY_BOUNDING_BOX` centralizza la bbox tarata sui dati osservati italiani. Il test della bbox esterna ne scambia volutamente assi e intervalli invece di duplicarne i numeri.
- **`mixed` combina due mondi**: per `mixed` la finestra è `date_from = arkimet_window[0]` e `date_to = dballe_window[1]`, con override `LASTDAYS` calcolato sul lato dballe — costruisce volutamente un intervallo che attraversa il taglio archivio/recente.
- **Assert nel setup di `fetch_station_sample`**: `assert response.status_code == 200` e `assert isinstance(content, dict)` avvengono **dentro l'helper**; un problema dell'endpoint si manifesta come errore in fase di arrange del test che lo usa.
- **`extract_station_coordinates` indicizza `data[0]` senza guard**: presuppone almeno una stazione; combinato con `fetch_station_sample`, un payload vuoto darebbe `IndexError` invece di uno skip leggibile.
- **`network=""`, `product_1=""` iniziali**: durante la scoperta i `params` sono costruiti prima con campi vuoti e poi **ri-creati** con `network`/`product` reali presi da `response_data["items"]`; la versione "vuota" è solo intermedia per la chiamata `/fields`.
- **Commenti decorativi uniformi**: i commenti italiani sono auto-generati e ripetitivi; non vanno letti come documentazione puntuale della logica.

## 5. Checklist di revisione

- [ ] Confermare che i quattro esiti di `discover_observed_params` (3× `skip` + `fail`) siano accettabili; monitorare in CI il tasso di `skip`.
- [ ] Verificare la robustezza della connessione DBALLE diretta (DSN da `db.variables`): è il punto di rottura infrastrutturale più probabile.
- [ ] Confermare che `CCBY_COMPLIANT` resti il gruppo licenza corretto/pubblico per i dataset osservati scoperti.
- [ ] Valutare un guard su `extract_station_coordinates`/`extract_products` per evitare `IndexError` su payload vuoti.
- [ ] Verificare che l'override `LASTDAYS` in `yield_observed_case` non interferisca con test concorrenti (stato di classe `BeDballe`, ripristinato ma globale).
- [ ] Confermare che il requisito "≥2 prodotti" sia voluto (è ciò che abilita `require_secondary_product`).

## 6. Possibili criticità

- **Copertura fragile e condizionata**: la combinazione "scoperta + ≥2 prodotti + license fissa + DBALLE raggiungibile" rende molti scenari skippabili; la suite observed può apparire verde eseguendo poco.
- **Accoppiamento infrastrutturale forte**: connessione DBALLE a basso livello e lettura archivio Arkimet legano i test alla configurazione reale del runtime, non solo al contratto HTTP.
- **Stato di processo condiviso (`LASTDAYS`)**: l'override è globale sulla classe per la durata della fixture; sicuro grazie al ripristino, ma non isolato per-test.
- **Oracoli impliciti hardcoded**: `agrmet` preferito e `CCBY_COMPLIANT` fisso sono assunzioni nascoste; un reseeding diverso degrada silenziosamente in skip.
- **Assert nel setup e indicizzazioni non protette**: spostano alcuni fallimenti in fase di arrange e introducono possibili `IndexError` poco diagnostici.
- **Logica di scoperta complessa**: `discover_observed_params` è lunga e con molti `continue`/rami; il rischio è che un ambiente "quasi valido" salti per un dettaglio difficile da diagnosticare dai messaggi di skip.
