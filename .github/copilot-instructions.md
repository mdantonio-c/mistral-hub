# MeteoHub — Internalizzazione di Rapydo HTTP API

## Contesto

MeteoHub è un'applicazione Python/Flask basata su Rapydo 2.4. L'obiettivo attuale è **ridurre progressivamente la dipendenza da Rapydo**, in particolare dal submodule `http-api`, internalizzando nel repository MeteoHub il package `restapi`.

La strategia scelta è incrementale e operativa: mantenere il runtime attuale il più possibile invariato e trasferire il codice a blocchi, verificando a ogni passo che il sistema continui a funzionare.

## Struttura rilevante

```text
meteo-hub
├── projects
│   └── mistral
│       ├── backend
│       ├── builds
│       ├── commands
│       ├── confs
│       ├── nginx
│       ├── nifi
│       ├── project_configuration.yaml
│       └── scripts
└── submodules
    ├── build-templates
    ├── do
    ├── http-api
    │   └── restapi
    └── rapydo-angular
```

Il target principale è:

```text
submodules/http-api/restapi
```

che contiene l'implementazione generica della REST API Rapydo.

## Dipendenze attuali di MeteoHub da `restapi`

Il codice MeteoHub importa direttamente diversi moduli del package:

```text
restapi.connectors
restapi.connectors.celery
restapi.connectors.sqlalchemy
restapi.connectors.smtp
restapi.services.authentication
restapi.utilities.logs
restapi.config
restapi.env
restapi.tests
```

Questi import sono presenti sia nel runtime sia nei test.

In particolare:

- SQLAlchemy viene usato dal backend e dai test.
- Celery viene usato dai task e dai worker.
- RabbitMQ viene usato come broker Celery.
- Redis viene usato come backend Celery.
- `restapi.tests` è usato dai test API MeteoHub.
- `restapi.utilities.logs` viene usato da diversi task.
- `restapi.services.authentication` viene usato dagli endpoint e dai test.

Per ora non è opportuno separare o rimuovere prematuramente le parti del package: prima bisogna dimostrare che la copia completa funziona.

## Runtime Docker

Il backend viene eseguito in un container Docker e non viene avviato direttamente in modalità Flask development.

L'avvio avviene tramite:

```bash
restapi launch
```

Il compose di runtime è generato da Rapydo tramite:

```bash
rapydo dump
```

Il `docker-compose.yml` generato rappresenta quindi il baseline operativo da preservare durante la migrazione.

Il Dockerfile Rapydo installa inoltre `rapydo/http-api` tramite:

```dockerfile
pip3 install --upgrade --no-cache-dir     git+https://github.com/rapydo/http-api.git@$RAPYDO_VERSION#egg=rapydo_http[dev]
```

Tuttavia il compose generato monta il codice del submodule direttamente dentro il Python environment:

```text
submodules/http-api/restapi
    ->
/usr/local/lib/python3.10/dist-packages/restapi
```

Questo mount sovrascrive di fatto il package installato nell'immagine e fa sì che il codice presente nel submodule sia quello effettivamente utilizzato a runtime.

Lo stesso mount è presente nel backend e nei container worker che utilizzano `restapi`.

## Strategia di migrazione scelta

È stata creata/prevista una feature branch dedicata, ad esempio:

```bash
git checkout main
git pull --ff-only origin main
git checkout -b feature/internalize-http-api
```

La prima fase consiste nel:

1. mantenere invariato il compose generato come struttura;
2. copiare l'intero package `restapi`;
3. modificare soltanto il source del bind mount;
4. verificare che backend e worker continuino a funzionare;
5. solo dopo iniziare a rimuovere dipendenze Rapydo e codice non necessario.

La copia iniziale è:

```bash
cp -a submodules/http-api/restapi projects/mistral/
```

ottenendo:

```text
projects/mistral/restapi
```

Il mount viene quindi modificato da:

```text
submodules/http-api/restapi
```

a:

```text
projects/mistral/restapi
```

mantenendo invariato il target:

```text
/usr/local/lib/python3.10/dist-packages/restapi
```

In questa prima fase:

> **No functional changes are intended.**

L'obiettivo è solo dimostrare che il package internalizzato è equivalente a quello fornito dal submodule.

## Stato attuale

Dopo aver modificato il compose con il nuovo mount:

- il **backend funziona**;
- i container **Celery vanno in `restarting`**;
- RabbitMQ è raggiungibile e sano;
- il problema riguarda l'autenticazione AMQP.

Errore nei worker Celery:

```text
amqp.exceptions.AccessRefused:
(0, 0): (403) ACCESS_REFUSED -
Login was refused using authentication mechanism PLAIN.
```

Il log di RabbitMQ conferma:

```text
PLAIN login refused: user 'rabbit' - invalid credentials
```

Quindi:

- DNS/network verso RabbitMQ: OK
- connessione TCP: OK
- porta AMQP 5672: OK
- RabbitMQ: attivo
- autenticazione dell'utente `rabbit`: FALLISCE

## Configurazione RabbitMQ vista da Celery

Dal container Celery:

```text
RABBITMQ_USER=rabbit
RABBITMQ_PASSWORD=...
RABBITMQ_HOST=rabbit.dockerized.io
RABBITMQ_PORT=5672
RABBITMQ_VHOST=/
RABBITMQ_SSL_ENABLED=0
RABBITMQ_ENABLE=1
RABBITMQ_ENABLE_CONNECTOR=1
CELERY_BROKER_SERVICE=RABBIT
```

La password non deve essere riportata in documentazione pubblica o commit.

Il broker viene identificato da Rapydo come:

```text
rabbit.dockerized.io:5672
```

e il container RabbitMQ vede correttamente i tentativi di connessione provenienti dalla rete Docker.

## Verifiche già effettuate

È stato confrontato il codice dei connector tra il submodule originale e la copia internalizzata:

```bash
diff -ru   submodules/http-api/restapi/connectors/rabbitmq   projects/mistral/restapi/connectors/rabbitmq
```

e:

```bash
diff -ru   submodules/http-api/restapi/connectors/celery   projects/mistral/restapi/connectors/celery
```

**Entrambi i diff sono vuoti.**

Quindi i file relativi ai connector RabbitMQ e Celery sono identici tra:

```text
submodules/http-api/restapi
```

e:

```text
projects/mistral/restapi
```

Questo rende improbabile che il problema sia stato causato da una modifica accidentale durante la copia.

## Ultimo punto di analisi

Il prossimo controllo previsto è verificare quale package `restapi` viene effettivamente caricato nel container Celery e come viene costruita la configurazione Celery/RabbitMQ.

Per evitare l'entrypoint Rapydo, usare:

```bash
docker compose run --rm --entrypoint bash celery
```

e verificare:

```bash
python3 -c "import restapi; print(restapi.__file__)"
```

```bash
python3 -c "import restapi.connectors.celery as c; print(c.__file__)"
```

```bash
python3 -c "import restapi.connectors.rabbitmq as r; print(r.__file__)"
```

Poi verificare come vengono usate le variabili RabbitMQ:

```bash
grep -R "RABBITMQ_PASSWORD\|RABBITMQ_USER\|CELERY_BROKER_SERVICE"     -n /usr/local/lib/python3.10/dist-packages/restapi/connectors/
```

e, se possibile, verificare la configurazione effettiva di `celery_app`.

## Ipotesi da verificare

Poiché i connector sono identici, le possibilità principali sono:

1. il package effettivamente caricato non è quello atteso;
2. esiste una differenza di configurazione/runtime tra il vecchio e il nuovo mount;
3. il package installato nell'immagine e quello montato interagiscono in modo inatteso;
4. il compose o l'entrypoint inizializzano Celery/RabbitMQ in modo diverso rispetto a quanto ipotizzato;
5. il problema esisteva già nel runtime originale ma non era stato osservato nel contesto precedente.

Non modificare ancora password RabbitMQ o configurazioni del broker: prima bisogna isolare la causa.

## Test di regressione decisivo

Un test molto utile è ripristinare temporaneamente il vecchio mount:

```text
submodules/http-api/restapi
```

senza modificare altro, quindi:

```bash
docker compose up -d --force-recreate celery
docker compose logs -f celery
```

Se Celery funziona con il vecchio mount e fallisce con quello nuovo, si ha una forte evidenza che la differenza è nel modo in cui il package internalizzato viene risolto/usato a runtime.

Se invece fallisce anche con il vecchio mount, il problema non è stato introdotto dall'internalizzazione.

## Prossimi obiettivi della migrazione

Una volta stabilizzata la copia locale di `restapi`:

1. validare backend e tutti i worker;
2. mantenere i test esistenti funzionanti;
3. identificare le parti di `restapi` realmente usate da MeteoHub;
4. rimuovere progressivamente codice generico Rapydo non necessario;
5. rimuovere la dipendenza dal submodule `http-api`;
6. rimuovere progressivamente la dipendenza dal package `rapydo_http` installato via Git;
7. mantenere eventualmente `build-templates` e altri componenti Rapydo finché sono ancora utili all'infrastruttura;
8. solo successivamente procedere con l'upgrade/modernizzazione del codice Flask/API.

## Principio guida

La migrazione deve essere **incrementale e verificabile**.

Ogni passo deve cercare di modificare una sola cosa alla volta, mantenendo stabile il runtime e usando il compose generato da Rapydo come riferimento operativo.

L'obiettivo immediato non è "rimuovere Rapydo", ma ottenere:

```text
MeteoHub
   |
   +-- projects/mistral/restapi
   |
   +-- backend
   +-- Celery workers
   +-- RabbitMQ
   +-- Redis
   +-- PostgreSQL
```

con comportamento equivalente all'architettura attuale.
