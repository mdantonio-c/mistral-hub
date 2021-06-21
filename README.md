# Mistral Meteo-Hub

## HOWTO Get started

Install rapydo framework last version 2.0

`$ sudo pip3 install --upgrade git+https://github.com/rapydo/do.git@2.0`

or ugprade to rapydo 2.0
`$ rapydo install 2.0`

####Clone the project

```
$ git clone https://gitlab.hpc.cineca.it/mistral/meteo-hub.git
```

####Init & start

```
$ cd meteo-hub
$ git checkout 0.4.3
$ rapydo init
$ rapydo pull
$ rapydo start
```

First time it takes a while as it builds some docker images. Finally, you should see:

```
...
Creating mistral_frontend_1 ... done
Creating mistral_postgres_1 ... done
Creating mistral_mongodb_1  ... done
Creating mistral_rabbit_1   ... done
Creating mistral_backend_1  ... done
Creating mistral_celery_1   ... done
2019-05-16 15:12:44,631 [INFO    controller.app:1338] Stack started
```

In dev mode you need to start api service by hand. Open a terminal and run  
`$ rapydo shell backend "restapi launch"`

Now open your browser and type http://localhost in the address bar.  
You can enter the app with the following username and password

```
user@nomail.org
test
```

## Execute frontend only

You can configure your instance to only execute frontend container by connecting to a remove server for all backend services.

Edit you .projectrc file and add the following lines:

```
services: frontend
```

in the main section and:

```
BACKEND_URI: https://remote.host.url
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
      BACKEND_URI: https://remote.host.url
      BACKEND_API_PORT: 443
```

Use `rapydo` command as usual.

## Meteo-Hub Data Ingestion

At the moment, a Meteo-Hub installation does not come with the data ingestor component.
The latter can be installed by following the instructions described in the section
[NiFi-based ingestion component](docs/README.md#nifi-based-ingestion-component)
of the documentation.

Its task is to feed the dataset repository, taking care of preserving the integrity of the data.
Currently, it only affects the observed data from ground stations and radars.

Data from ground stations are provided in two different ways:

- made available and retrieved from an FTP Server
- directly transferred by data provider via AMQP protocol

Differently, radar data is harvested by querying a web service.

The ingestion process is coordinated by an orchestrator which channels the data into the right pipeline and ensures that
they are properly stored. This process, also called harmonization, requires data interpretation and may
involve transformations and normalizations for quality assurance.

Source code is available [here](https://gitlab.hpc.cineca.it/mistral/meteo-hub-ingestion).

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
