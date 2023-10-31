# Mistral Meteo-Hub

## HOWTO Get started

#### Clone the project

```
$ git clone https://gitlab.hpc.cineca.it/mistral/meteo-hub.git
$ cd meteo-hub
$ git checkout 0.4.8
```

### Install the controller

```
$ sudo pip3 install --upgrade git+https://github.com/rapydo/do.git@2.4`

$ rapydo install
```

### Init & start

```
$ rapydo init
$ rapydo pull
$ rapydo build
$ rapydo start
```

First time it takes a while as it builds some docker images. Finally, you should see:

```
...
Creating mistral-frontend-1 ... done
Creating mistral-postgres-1 ... done
Creating mistral-rabbit-1   ... done
Creating mistral-redis-1  ... done
Creating mistral-backend-1  ... done
Creating mistral-celery-1   ... done
2019-05-16 15:12:44,631 [INFO    controller.app:1338] Stack started
```

In dev mode you need to start api service by hand. Open a terminal and run  
`$ rapydo shell backend "restapi launch"`

Now open your browser and type http://localhost in the address bar.  
You will find the default credentials into the .projectrc file

## Execute frontend only

You can configure your instance to only execute frontend container by connecting to a remove server for all backend services.

Edit you .projectrc file and add the following lines:

```
services: frontend
```

in the main section and:

```
BACKEND_URL: https://remote.host.url
BACKEND_API_PORT: 443
```

in the project_configuration>variables>env section

Your `.projectrc` will be something like:

```
[...]
services: frontend

project_configuration:
  variables:
    env:
      [...]
      BACKEND_URL: https://remote.host.url
      BACKEND_API_PORT: 443
```

Use `rapydo` commands as usual.

## Meteo-Hub Data Ingestion

To install the ingestor component, enabled it from your `.projectrc`:

```
ACTIVATE_NIFI: 1
```

Its task is to feed the dataset repository, taking care of preserving the integrity of the data.
Currently, it only affects the observed data from ground stations and radars.

Data from ground stations are provided in two different ways:

- made available and retrieved from an FTP Server
- directly transferred by data provider via AMQP protocol

Differently, radar data is harvested by querying a web service.

The ingestion process is coordinated by an orchestrator which channels the data into the right pipeline and ensures that
they are properly stored. This process, also called harmonization, requires data interpretation and may
involve transformations and normalizations for quality assurance.

The ingestor component needs an operational DB. Its table structure can be created using the provided [SQL script](https://gitlab.hpc.cineca.it/mistral/meteo-hub-ingestion/-/blob/master/nifi_db_create_script.sql)

The Nifi’s XML templates to set up the ingestion processes are available in the dedicated [repository](https://gitlab.hpc.cineca.it/mistral/meteo-hub-ingestion)

## Meteo-Hub API

The HTTP APIs, written in Python by using the Flask framework, are used by the graphic user interface
as well as by programmatic access to the data. All the endpoints are described as OpenAPI specifications
by adopting the Swagger framework.

The API specifications are available at  
https://meteohub.mistralportal.it:7777

## Meteo-Hub CLI

A simple command line client can be used to directly interact with the API for data request submission and for pushing
data to the ingestor as well.

Source code is available [here](https://gitlab.hpc.cineca.it/mistral/meteo-hub-cli).
