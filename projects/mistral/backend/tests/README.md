# Manuale pratico dei test backend Meteo-Hub

## A cosa serve questa documentazione

Usa questo manuale per orientarti, scegliere un comando, scrivere un test e
capire dove cercare quando qualcosa non funziona.

| Documento | Quando leggerlo |
|---|---|
| Questo README | Per capire **come** lavorare con la suite e con il suo ambiente. |
| [TEST_REVIEW_GUIDE.md](TEST_REVIEW_GUIDE.md) | Per sapere **cosa** è coperto, quali sono i limiti delle verifiche e quanto fidarsi dei risultati. Contiene anche l'indice e i riferimenti a conteggi ed esiti. |
| `*.py.review.md`, per esempio la [scheda del test access key](integration/access_key/test_access_key_api.py.review.md) | Per il dettaglio di un singolo file, delle sue precondizioni e di ciò che le sue asserzioni dimostrano. |

La documentazione vive in un repository separato; i percorsi dei sorgenti citati
qui sono relativi alla root del repository `meteo-hub`. Nell'indice della guida
trovi i file e i domini della suite, senza doverli cercare in questo manuale.

## Modello mentale in cinque minuti

La suite è un unico insieme di test, organizzato in quattro strati:

1. **Configurazione globale.**
   `projects/mistral/backend/tests/conftest.py` registra i marker e rende
   disponibili le fixture condivise dall'intera suite.
2. **Helper condivisi.**
   `projects/mistral/backend/tests/helpers/` contiene funzioni e componenti
   riusabili tra aree. Un helper si chiama esplicitamente: non è una fixture
   solo perché si trova in questa cartella.
3. **Test di integrazione.**
   `projects/mistral/backend/tests/integration/` raccoglie i test per area.
   `projects/mistral/backend/tests/integration/conftest.py` espone le fixture
   comuni a questo sottoalbero.
4. **Supporto di dominio.**
   Le fixture e le funzioni utili a una sola area stanno vicino ai suoi test.
   Un esempio è `projects/mistral/backend/tests/integration/access_key/conftest.py`,
   affiancato da `projects/mistral/backend/tests/integration/access_key/support.py`.

### Un esempio guidato

In `projects/mistral/backend/tests/integration/access_key/test_access_key_api.py`,
`test_02_get_existing_access_key` verifica la lettura di una chiave esistente:

1. Pytest prepara `client` e `fresh_access_key`. Quest'ultima usa
   `access_key_owner` per creare un proprietario temporaneo e una chiave.
2. Il test esegue la richiesta di lettura con gli header del proprietario.
3. Le asserzioni verificano la risposta HTTP e che la chiave restituita sia la
   stessa creata nel setup.
4. Il teardown revoca la chiave prima di eliminare l'utente temporaneo.

La [scheda del file](integration/access_key/test_access_key_api.py.review.md)
spiega il dettaglio dei singoli casi. Qui interessa riconoscere il percorso:
fixture, azione, asserzioni e pulizia.

## Glossario

| Termine | Significato pratico |
|---|---|
| Rapydo / `restapi` | Rapydo gestisce lo stack e i container; `restapi` fornisce il framework backend e il comando che avvia i test nel container. |
| Pytest / collection | Pytest raccoglie i casi e li esegue. La collection comprende anche le combinazioni dei test parametrizzati. |
| Fixture | Funzione richiesta per nome a pytest. Può preparare risorse, dipendere da altre fixture e avere un teardown dopo `yield`. |
| Helper / builder | Funzione chiamata dal codice del test. Un builder prepara, per esempio, un payload o uno scenario; non ha automaticamente il ciclo di vita di una fixture. |
| `client` / `FlaskClient` | Client HTTP nello stesso processo: attraversa l'app Flask, ma non verifica proxy, TLS o la rete esterna. |
| ORM / SQLAlchemy | Strato che collega oggetti Python e tabelle del database. Un `commit` può rendere persistenti le modifiche del test. |
| Fake / `monkeypatch` | Il fake sostituisce un componente con un comportamento controllato. `monkeypatch` applica sostituzioni temporanee nel processo del test, non nei worker separati. |
| Celery / broker / worker | Celery definisce i task; il broker trasporta i messaggi; un worker li esegue. Una chiamata locale non prova la consegna al worker. |
| Beat / RedBeat | Beat pianifica i task periodici; RedBeat conserva le voci dello scheduler in Redis. Una riga di schedule nel database non è la stessa cosa di una voce RedBeat. |
| Dataset / licenza / attribution | Il catalogo descrive i dati, le condizioni di accesso e la provenienza. Un dataset sintetico può essere solo una riga di catalogo, senza dati meteorologici. |
| Forecast / observed | Previsioni e osservazioni: i test possono dipendere rispettivamente da dati archiviati o da osservazioni disponibili nei servizi configurati. |
| `reftime` / `run` | Tempo di riferimento dei dati e identificativo dell'emissione. Servono, tra l'altro, a scegliere una finestra utile per una richiesta. |
| Schedule / request / `FileOutput` | Una schedule è una regola; una request è una singola estrazione; `FileOutput` rappresenta un file prodotto. Sono risorse distinte. |
| Opendata / ARCO | Opendata riguarda i pacchetti pubblicati per il download; ARCO espone anche catalogo e oggetti Zarr tramite storage S3. |
| GRIB / BUFR / shapefile | Formati meteorologici o geografici. Un file segnaposto con un suffisso corretto non prova che il contenuto sia valido. |

## Come lanciare i test

Lavora dalla root del repository, con `rapydo` disponibile nell'ambiente del
progetto e lo stack necessario avviato. Se usi un ambiente virtuale, attivalo
prima. Se devi attendere i servizi del backend:

```bash
rapydo shell backend 'restapi wait'
```

### Percorsi host e container

I test del progetto sono montati nel container sotto `tests/custom/`. Il
percorso da usare dipende anche dall'opzione del wrapper:

| Dove | Esempio |
|---|---|
| File sul repository host | `projects/mistral/backend/tests/integration/access_key/test_access_key_api.py` |
| File nel container, con `--file` | `tests/custom/integration/access_key/test_access_key_api.py` |
| Cartella nel container, con `--folder` | `custom/integration/access_key` |

`--file` deve indicare un file fisico: non aggiungere al percorso selettori
come `::Classe::metodo`. `--core`, `--file` e `--folder` sono alternative,
non opzioni da combinare. `--wait` attende l'inizializzazione dei servizi.

### Dal più stretto al più largo

Parti dal file che verifica il comportamento modificato. Questi sono esempi
alternativi, non una sequenza obbligatoria:

```bash
rapydo shell backend 'restapi tests --wait --file tests/custom/integration/access_key/test_access_key_api.py'
rapydo shell backend 'restapi tests --wait --file tests/custom/integration/observed/test_observations_filters.py'
rapydo shell backend 'restapi tests --wait --file tests/custom/integration/dataset/test_dataset_authorization.py'
rapydo shell backend 'restapi tests --wait --file tests/custom/integration/tasks/test_requests_cleanup_expiration.py'
rapydo shell backend 'restapi tests --wait --file tests/custom/integration/postprocessing/test_forecast_spatial.py'
```

Se cambi supporto condiviso da più file, allarga alla cartella interessata:

```bash
rapydo shell backend 'restapi tests --wait --folder custom/integration/observed'
```

Quando serve una regressione dell'intera suite del progetto:

```bash
rapydo shell backend 'restapi tests --wait --folder custom'
```

Senza una selezione di file o cartella, il runner include anche i test del
framework: non è equivalente alla sola suite custom. Il runner si ferma al
primo errore, applica un timeout per caso e raccoglie la coverage. Se si ferma
prima della fine, i casi successivi non sono stati verificati.

Evita `--destroy` su ambienti con dati da conservare: abilita la modalità
distruttiva usata da alcuni test del framework. Anche senza questa opzione,
i test possono scrivere nel database e nel filesystem configurati.

### Selezione per marker

Passa le opzioni di pytest attraverso `PYTEST_ADDOPTS`, mantenendo il wrapper:

```bash
rapydo shell backend "env PYTEST_ADDOPTS='-m \"integration and not async_real\" -rs' restapi tests --wait --folder custom"
```

`-rs` mostra i motivi degli skip. La sezione sul ciclo di vita spiega il
significato dei marker: selezionarne uno non crea da solo un ambiente isolato.

### Perché non chiamare pytest direttamente

Fuori dalla produzione, `restapi tests` imposta `APP_MODE=test` per il processo
dei test. In questa modalità il connettore SMTP usa il mock. Una chiamata
diretta a pytest su uno stack di sviluppo non offre la stessa protezione:
task ed endpoint eseguiti nel processo potrebbero inviare email reali.

Il wrapper modifica l'ambiente del processo avviato, **non** quello di worker
già in esecuzione. Per questo la protezione del processo di test non basta per
i casi con worker reali.

### Test con worker reali

I test `async_real` usano worker separati e possono coinvolgere broker,
Redis e Beat. Eseguili solo su uno stack **dedicato ai test**, senza dati
operativi o altri utenti: i worker e i task periodici possono agire anche su
risorse non create dal singolo test.

Su uno stack dedicato, configurato fuori produzione, avvia o ricrea tutti i
servizi con la modalità di test e poi seleziona i casi asincroni:

```bash
rapydo --testing start -f
rapydo shell backend "env PYTEST_ADDOPTS='-m async_real -rs' restapi tests --wait --folder custom"
```

`--testing` va applicato allo `start`; `-f` forza la ricreazione dei container,
inclusi i worker e Beat. Il comando può interrompere servizi già in uso: non
eseguirlo su uno stack condiviso. Dopo una modifica al codice dei task,
assicurati che anche tutti i worker interessati usino il codice aggiornato.

I worker devono avere `APP_MODE=test` per usare il mock SMTP. Il controllo della
suite è indiretto: verifica nel backend `PYTHONMALLOC=debug`,
`PYTHONASYNCIODEBUG=1` e `PYTHONFAULTHANDLER=1`, impostati dalla modalità di
test Rapydo fuori produzione. Non impostare queste variabili a mano per
aggirare lo skip: il controllo passerebbe anche se i worker usassero SMTP reale.
Verifica che backend e worker siano stati tutti ricreati con la configurazione
corretta; i soli segnali del backend non certificano l'ambiente dei worker.

## Ciclo di vita di un test

### Dal comando al teardown

Il percorso normale è il seguente:

1. `rapydo shell backend` esegue `restapi tests` nel container.
2. Il wrapper verifica la selezione e avvia il runner del framework, che vede
   i test del progetto come `tests/custom/...`.
3. Pytest raccoglie i casi, i marker e i parametri. Carica anche la
   configurazione del framework in `submodules/http-api/tests/conftest.py`.
4. Per il file selezionato, pytest rende visibili i `conftest.py` delle
   directory antenate e risolve le fixture necessarie.
5. Si eseguono setup, azione e asserzioni; poi i teardown delle fixture
   preparate vengono eseguiti secondo le loro dipendenze.

Il wrapper è definito in `submodules/http-api/restapi/__commands__.py`; il
runner è `submodules/http-api/tests/tests.sh`. Il fatto che un test arrivi al
teardown non implica un rollback generale delle modifiche persistenti.

### Visibilità, scope e ordine delle fixture

Un `conftest.py` vale per la propria directory e per le sue discendenti, non
per le directory sorelle:

| Livello | Esempio di ciò che rende disponibile |
|---|---|
| `projects/mistral/backend/tests/conftest.py` | `test_runtime` e `cleanup_registry`, disponibili nella suite custom. |
| `projects/mistral/backend/tests/integration/conftest.py` | `auth_headers`, `access_key_owner`, `fresh_access_key` e `requests_cleanup_perimeter` per i test di integrazione. |
| `projects/mistral/backend/tests/integration/access_key/conftest.py` | `fresh_access_key_with_expiration` per i test di quell'area. |

Una fixture non automatica parte se il test la richiede, direttamente o come
dipendenza. Una fixture `autouse` parte anche se non compare nella firma del
test: per esempio `schedules_endpoint_without_real_celery` in
`projects/mistral/backend/tests/integration/data_ready/conftest.py`.
Un helper importato, invece, non diventa una fixture.

Le fixture senza scope esplicito sono normalmente per funzione.
`test_runtime` è di sessione: conserva, tra le altre cose, una cache degli
identificativi dei dataset e permette override temporanei di attributi.
Lo scope stabilisce la durata del valore, non obbliga pytest a creare una
fixture che nessun test richiede.

Le dipendenze stabiliscono il setup: `fresh_access_key`, per esempio, richiede
`access_key_owner`, che a sua volta usa `cleanup_registry`. Una fixture che
dipende da un'altra termina prima della propria dipendenza. Non affidarti a un
ordine implicito fra fixture indipendenti: se l'ordine è importante, esprimilo
con una dipendenza o con un contesto esplicito.

Alcuni test parametrizzati scelgono una fixture per nome con
`request.getfixturevalue`: il nome deve comunque essere visibile al test.

### Pulizia e patch temporanee

`cleanup_registry` raccoglie callback nel registro implementato da
`projects/mistral/backend/tests/helpers/cleanup.py`. Le esegue in ordine LIFO:
l'ultima registrata è la prima eseguita. Registra quindi prima la pulizia del
proprietario e poi quella della risorsa che ne dipende.

Nel caso access key, la revoca è registrata dopo la cancellazione dell'utente:
parte prima, perché la FK di `AccessKey` verso l'utente non ammette NULL e
l'utente non si può eliminare finché la chiave esiste.
Il registro esegue il teardown anche dopo un'asserzione fallita, se il processo
arriva normalmente a quel punto.

`monkeypatch` ripristina i simboli al proprio teardown. Se una fixture con
patch viene preparata prima del registro, il cleanup può girare **mentre la
patch è ancora attiva**. Nel sottoalbero data-ready la fixture automatica
richiede `monkeypatch` prima delle fixture non automatiche: il registro viene
quindi ripulito prima del ripristino della patch. Non generalizzare questo
ordine a due fixture indipendenti.

Prima di sostituire un servizio, verifica quali chiamate avverranno anche nel
cleanup. Preferisci, quando possibile, sostituire il nome usato dal singolo
modulo sotto test invece del connettore condiviso: una patch globale potrebbe
intercettare anche le cancellazioni via API. Se usi un helper che applica
patch, controllane durata ed effetti.

La pulizia non è infallibile: un errore in una callback interrompe le azioni
successive; la rimozione delle directory registrate con `add_path` è
best-effort. Un errore prima della registrazione o l'interruzione del processo
possono lasciare risorse. Controlla il teardown e registra le pulizie appena le
risorse esistono.

### Autenticazione e risorse reali

`auth_headers` usa l'account predefinito condiviso: è adatto a letture e
operazioni che non cambiano quell'account. Per operazioni invasive usa un
utente temporaneo, come `access_key_owner` per creare o revocare chiavi.
Verifica ruoli e permessi richiesti dallo scenario: creare un utente di test
non implica automaticamente che sia privo di privilegi amministrativi.

Fixture e fake non rendono automaticamente finti database e filesystem.
La suite può eseguire commit reali, creare utenti e scrivere file nelle root
configurate. Per testare visibilità e permessi del catalogo, preferisci risorse
sintetiche al cambiamento di dataset o licenze già presenti.

### Task globali: prima il perimetro

Alcuni task percorrono risorse dell'intero progetto. Non chiamarli in-process
senza aver ristretto ciò che possono vedere:

| Task | Perimetro da predisporre |
|---|---|
| `automatic_cleanup` | Usa `requests_cleanup_perimeter` e il suo metodo `allow` per registrare solo utenti e request del test. La ricerca degli orfani usa una root temporanea. |
| `launch_all_on_data_ready_extractions` | Usa `trigger_data_ready_inline` con `schedule_ids` oppure `confine_data_ready_schedules`, passando solo gli identificativi delle schedule del test. |

Il perimetro è implementato in
`projects/mistral/backend/tests/helpers/task_perimeter.py`; il trigger è in
`projects/mistral/backend/tests/helpers/data_ready.py`. La logica del task e
le scritture ORM restano reali. Gli accessi non previsti sollevano
`OutsideTestPerimeterError` invece di ripiegare su una query globale.

Il perimetro non controlla che gli identificativi forniti appartengano davvero
al test: sceglili con cura. Nel cleanup, solo la scansione degli orfani usa la
root temporanea; i file delle request ammesse possono trovarsi nelle directory
reali degli utenti temporanei. Le patch di questo processo non confinano i
worker esterni.

Anche gli endpoint possono avviare effetti esterni. Una schedule
`on-data-ready` può accodare subito una prima estrazione; una schedule
periodica può creare una voce RedBeat. Se la voce è reale, cancella la schedule
tramite l'API con Celery reale: eliminare soltanto la riga SQL o l'utente non
garantisce la rimozione della voce periodica.

### Diretto, inline, finto o asincrono?

Leggi quale percorso usa il test prima di dedurre che cosa copra:

| Percorso | Che cosa esegue | Che cosa non dimostra |
|---|---|---|
| Chiamata diretta a una funzione o a `task.run()` | Il codice invocato nel processo del test; un task può comunque avere effetti su database, file o notifiche. | La consegna tramite broker e worker. |
| `BaseTests.send_task` | Cerca il task nel registro Celery e lo chiama nel processo corrente. | L'accodamento e l'esecuzione su un worker separato. |
| `AcceptTasksWithoutRunningCelery` | Registra gli invii accettati dal fake. | L'esecuzione del task o la produzione di file. |
| `InlineDataReadyExtractionCelery` | Simula l'effetto sul database con una request riuscita. | Un'estrazione meteorologica o un file di output. |
| `InlineDataExtractCelery` | Esegue subito il vero task di estrazione nel processo del test. | Il trasporto tramite broker e worker; gli effetti su dati e file restano possibili. |
| Worker reale | Il task attraversa il broker ed è eseguito da un processo separato; i casi periodici possono coinvolgere anche Beat e RedBeat. | L'isolamento tramite `monkeypatch` del processo pytest. |

I fake sono definiti in `projects/mistral/backend/tests/helpers/celery_fakes.py`.
Una risposta di accettazione o una request sintetica non dimostrano da sole
che un'estrazione sia stata eseguita o che il contenuto di un file sia corretto.

### Marker e ambiente

I marker sono registrati nel `conftest.py` globale:

| Marker | Come leggerlo |
|---|---|
| `integration` | Classifica un test nella suite di integrazione; non implica che ogni servizio o la rete esterna siano reali. |
| `deterministic` | Il flusso è controllato nel runtime del test, senza attendere la catena asincrona reale. Non garantisce da solo l'isolamento di dati e servizi. |
| `async_real` | Il test attende l'esecuzione asincrona tramite worker e, quando necessario, Beat. Richiede lo stack dedicato descritto sopra. |
| `runtime_sensitive` | L'esito dipende anche da dati o infrastruttura presenti nell'ambiente. |

I marker sono etichette per selezione e lettura, non avviano servizi e non
rendono innocui gli effetti collaterali. Per `async_real` esiste anche un
controllo in collection: se mancano i segnali della modalità di test, il caso
viene saltato prima di eseguire test e fixture. Uno skip non è una verifica
riuscita del comportamento.

La configurazione del progetto in
`projects/mistral/project_configuration.yaml` dichiara PostgreSQL, Redis,
RabbitMQ, Celery e Beat. La configurazione dichiarata non prova che i servizi
siano avviati, raggiungibili o privi di override locali.

### Dati e risorse fuori dalla cartella dei test

Alcuni scenari usano righe sintetiche; altri richiedono dati meteorologici,
metadati, servizi e strumenti installati nell'ambiente. La presenza di un
dataset nel catalogo o di metadati in `/api/fields` non garantisce che esista
una finestra di dati utile per l'estrazione.

Le fixture degli osservati cercano scenari disponibili nel runtime. Alcuni
casi richiedono anche un secondo prodotto; se manca la precondizione, il test
può essere saltato con un motivo esplicito. Altri casi dipendono da
connessioni DB-All.e, archivi Arkimet o template esterni. Leggi il motivo
dello skip e il supporto del dominio prima di cambiare l'asserzione.

Lo script `.gitlab/scripts/setup-backend-and-datasets.sh` mostra come la CI
prepara metadati, dati di esempio e template. Comprende anche una pulizia
distruttiva di DB-All.e: non eseguirlo su dati da conservare.

Per i worker reali, `create_data_ready_user` prepara un utente temporaneo con
notifiche di successo disattivate e un indirizzo non consegnabile. Serve
comunque il mock SMTP sui worker, anche per le notifiche di errore.
Registra `register_wait_for_user_requests` dopo il cleanup dell'utente:
grazie al LIFO, l'attesa dei task precede la cancellazione di request, file e
account. Se necessario l'helper ferma i task dell'utente di test; se i worker
non confermano, il cleanup fallisce senza cancellare quelle risorse.
Gli helper in `projects/mistral/backend/tests/helpers/real_workers.py` includono
anche `wait_for_mock_email` per le notifiche e `read_periodic_task` per
controllare la voce RedBeat di una schedule.

## Modificare o aggiungere test

### Regole pratiche

1. Definisci il contratto da verificare e scegli il livello necessario:
   funzione, endpoint con fake, estrazione inline o worker reale. Non attribuire
   a un fake le garanzie di un servizio reale.
2. Tieni riconoscibili **arrange**, **act** e **assert**: prepara lo scenario,
   esegui il comportamento e verifica effetti osservabili e risultato. Copri
   anche i rifiuti pertinenti, senza confondere un errore di setup con il
   contratto.
3. Metti una fixture globale in
   `projects/mistral/backend/tests/conftest.py` solo se serve davvero a tutta
   la suite. Per più aree di integrazione usa
   `projects/mistral/backend/tests/integration/conftest.py`; per una sola area
   usa il suo `conftest.py`.
4. Metti gli helper usati tra aree in
   `projects/mistral/backend/tests/helpers/`. Se servono a una sola area,
   tienili nel relativo modulo di supporto. Evita di copiare builder o
   preparazioni già disponibili.
5. Crea risorse temporanee e registra subito il teardown con
   `cleanup_registry`. Considera relazioni tra risorse, ordine LIFO, file,
   schedule e task ancora in corso. Non usare l'account condiviso come risorsa
   sacrificabile.
6. Attendi una condizione osservabile con timeout, non con una pausa fissa.
   `wait_until` in `projects/mistral/backend/tests/helpers/polling.py` restituisce
   il primo risultato utile o fallisce con un messaggio alla scadenza.
7. Confina i task globali prima della chiamata. Per i test di validazione,
   impedisci anche l'invio a servizi reali se la validazione viene superata
   per errore: un fallimento esplicito è preferibile a un effetto esterno.
   In `projects/mistral/backend/tests/integration/schedules/test_schedule_validation.py`
   si usa `pytest.fail` per fermare l'invio; un `AssertionError` nell'endpoint
   potrebbe invece essere convertito in una risposta HTTP.
8. Applica i marker corrispondenti al percorso effettivo e verifica i motivi
   degli skip. Per un worker reale usa lo stack dedicato e il cleanup che attende
   i task.

Come traccia per la forma di un test puoi leggere
`projects/mistral/backend/tests/helpers/templates/endpoint_template.py`: è un
esempio strutturale, non un test raccolto da pytest.

### Modifiche tipiche e prima selezione

Usa le opzioni della tabella con `rapydo shell backend 'restapi tests ...'`.
I percorsi indicati qui sono quelli del container. Parti dal file pertinente e
allarga solo ai consumatori o alle aree coinvolte dal cambiamento.

| Modifica | Prima selezione utile e successivo allargamento |
|---|---|
| Contratto di un endpoint o validazione | `--file tests/custom/integration/access_key/test_access_key_api.py` per un cambiamento a quel contratto; poi `--folder custom/integration/access_key` se coinvolge anche gli altri casi dell'area. |
| Autorizzazione o visibilità del catalogo | `--file tests/custom/integration/dataset/test_dataset_authorization.py`; poi la cartella `custom/integration/dataset` se cambiano anche le letture. |
| Cleanup, ORM o file delle request | `--file tests/custom/integration/tasks/test_requests_cleanup_expiration.py`; allarga a `custom/integration/requests` se cambia il ciclo di vita delle request. |
| Decisioni data-ready o perimetro delle schedule | Parti dai file interessati in `custom/integration/data_ready`; allarga alle schedule e ai consumatori del perimetro. |
| Postprocessing o formato di output | `--file tests/custom/integration/postprocessing/test_forecast_spatial.py` per il percorso spaziale; scegli il file relativo al formato o all'errore modificato. |
| Broker, worker o scheduler reale | Il file interessato con `async_real`, per esempio `--file tests/custom/integration/schedules/test_schedule_on_data_ready_real_worker.py`, su stack dedicato. Per Beat serve anche un caso che lo attraversi: il primo invio on-data-ready non lo verifica. |
| Fixture o helper condivisi | Prima i file che li usano, poi le cartelle coinvolte. Se cambia una fixture globale, considera infine `--folder custom`. |
| Inizializzazione e seed | Parti da `--folder custom/integration/initializer`, distinguendo preparazione dei dati e verifica dell'applicazione. |

Aggiorna la scheda `*.py.review.md` del file di test o di supporto toccato.
Se cambia la copertura o cambiano i conteggi, aggiorna anche
[TEST_REVIEW_GUIDE.md](TEST_REVIEW_GUIDE.md).

## Diagnosi di un test rosso o saltato

Prima di cambiare il test, riproduci il caso più stretto e distingui:

- **Contratto:** l'azione è arrivata al comportamento previsto, ma risposta o
  effetto non rispettano ciò che il test chiede.
- **Setup:** fixture, dati, permessi, fake o cleanup non hanno preparato lo
  scenario previsto.
- **Ambiente:** mancano o non rispondono servizi, worker, dati, strumenti o
  risorse esterne richieste.

Leggi l'intero errore, incluso il teardown; per gli skip usa `-rs`. Il primo
sintomo non identifica sempre la causa.

| Sintomo | Cosa controllare prima di intervenire |
|---|---|
| File o cartella non trovati | Traduci il percorso host in `tests/custom/...` per `--file` o `custom/...` per `--folder`. Non aggiungere un selettore di metodo a `--file`. |
| Fixture non trovata | Controlla nome e visibilità dei `conftest.py`, compreso il lookup dinamico. Importare un helper non registra una fixture. |
| Errore di autenticazione inatteso | Controlla credenziali, tipo di autenticazione, ruoli e permessi dell'utente. Distingui l'account condiviso dall'utente temporaneo. |
| `async_real` saltato | Leggi il motivo con `-rs`; verifica modalità di test e ricreazione di backend, worker e Beat. Non forzare i segnali nel solo backend. |
| Dataset o osservazioni non disponibili | Controlla catalogo, metadati, finestra, prodotti e dati effettivi. Uno skip per precondizioni mancanti non dimostra il contratto dell'endpoint. |
| Metadati presenti ma osservazioni vuote | Verifica rete, prodotti, connessione DB-All.e e licenza: i metadati non provano la presenza dei dati richiesti. |
| `OutsideTestPerimeterError` | Il task ha richiesto un accesso non ammesso. Verifica gli identificativi e adegua il perimetro in modo stretto, senza tornare a query globali. |
| Task non trovato | Se usi `BaseTests.send_task`, controlla l'app e il nome nel registro Celery prima di cercare un guasto del broker. |
| Invio accettato ma nessun file | Controlla quale fake è attivo: un'accettazione o una request sintetica non eseguono necessariamente l'estrazione. |
| Request inattesa dopo la creazione di una schedule | Verifica se l'opzione `on-data-ready` ha già inviato la prima estrazione e quale trasporto era attivo durante il setup. |
| Timeout con worker reale | Distingui schedule e voce RedBeat, Beat, broker, routing, worker e stato della request. Consulta i log e confronta, se utile, il percorso inline. |
| Risorse residue o errore in teardown | Controlla registrazione, ordine LIFO, patch ancora attive e prima callback fallita. La rimozione best-effort di una directory può non essere riuscita. |
| File presente ma contenuto inatteso | Verifica quali proprietà sono davvero asserite: nome, suffisso o presenza non certificano il contenuto meteorologico. |

Non allargare subito l'esecuzione: chiarisci prima se è cambiato il contratto,
se il test ha preparato lo scenario corretto o se l'ambiente non soddisfa le
precondizioni. Poi ripeti la selezione minima e amplia la verifica se serve.
