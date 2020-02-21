Mistral Meteo-hub
===================

HOWTO Get started
-----------------

Install rapydo framework last version 0.7.2 (at the moment not available in PyPI yet)

`$ sudo pip3 install --upgrade git+https://github.com/rapydo/do.git@0.7.2`

or ugprade to rapydo 0.7.2  
`$ rapydo install 0.7.2`

####Clone the project
```
$ git clone https://gitlab.hpc.cineca.it/mistral/meteo-hub.git
```

####Init & start
```
$ cd meteo-hub
$ git checkout 0.2.2
$ rapydo init
$ rapydo pull
$ rapydo start
```

First time it takes a while as it builds some docker images. Finally you should see:  
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
`$ rapydo shell backend --command "restapi launch"`

Now open your browser and type http://localhost in the address bar.  
You can enter the app with the following username and password  
```
user@nomail.org
test
```

####Execute frontend only
You can configure your instance to only execute frontend container by connecting to a remove server for all backend services.

Edit you .projectrc file and add the folowing lines:

```
services: frontend
```
in the main section

and
```
   BACKEND_URI: https://remote.host.url
   BACKEND_API_PORT: 443
```
in the project_configuration>variables>env section

Your .projectrc will be something like:

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

Use rapydo command as usual

