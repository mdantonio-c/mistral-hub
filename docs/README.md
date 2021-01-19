**MISTRAL**

**Documentation**



Author: CINECA

Date: 15 January 2021

Status: draft



# **Web Frontend features**
<TODO Bea e Cinzia>
##
## **Data**

### **Data Extraction**

The user can obtain data from one or more datasets of the platform through the Web Frontend feature of the Data Extraction.

In the first step, the user must select one or more datasets (multiple selection is allowed only with datasets of the same category: observation, forecast, radar).

In the second step, the user can filter respect the provided parameters that are specific for the dataset category:


|Observation|Reftime, Level, Product, Timerange|
| :- | :- |
|Forecast|Reftime, Area, Level, Origin, Proddef, Product, Run, Timerange|
|Radar|Reftime, Area, Level, Origin, Proddef, Product, Run, Timerange|

In the third step, the user can apply a set of post-processing that is specific for the dataset category:


|Observation|Derived Variables, Time Post Processing, Quality Control Filter, Format Conversion|
| :- | :- |
|Forecast|Derived Variables, Time Post Processing, Space Post Process|
|Radar|Derived Variables, Time Post Processing, Space Post Process|

In the fourth and last step, the user must enter a name for the current request and submit the request to the system.

Before submitting the request, the user can schedule the request by clicking on the "Schedule" button and can redirect the result of the request to an AMQP queue through the switch “Data Pushing”.

### **My Requests**
After submitting a request, the user is led to the "My Requests" page.

There is a list of all requests submitted by the user. The first request on the list is the one just submitted: the status is PENDING because the execution of the request is still in progress.

By clicking on the icon:

![](icon1.png)

the information on the page is updated. When the status of the request becomes SUCCESS, it means that the execution has finished successfully.

The user can download the output data of the request by clicking the icon:

![](icon2.png)

The user can expand the request box information by clicking the icon:

![](icon3.png)

Moreover the user can delete a request by clicking the trash bin icon.

Also on this page, the situation of the user disk quota occupation is shown on the left.

By clicking on the Schedules tab, the page will show the list of the scheduled query of the user.
### **Scheduled queries**
<TODO>
### **Data pushing**
<TODO>

## **Visualisation**
### **Observation map**
### **Forecast map**
### **Italy Flash Flood map**
### **Multi-layer map**

## **Admin guide**
<TODO Bea>
###
### **User roles**
The roles implemented are:

- *Administrators* 
- *Institutional*
- *User*

By assigning a role to an account, you enable that account to a certain profile and to a set of functionalities.

In the following table are outlined the functionalities for each profile:

<link alla tabella>

The role *User* is the default one. It corresponds to the profile “Auto-registrato”. The Demo profile has the same permissions as the “Auto-registrato” profile and therefore it corresponds to the role *User*.
### **Create a new user**

### **How To**
- **How to enable a user to “Data Pushing”**

To enable a user for "Data Pushing", the administrator must connect to the "Rabbit mq" console and create a dedicated AMQP queue for the user.

- **How to give a user access to a dataset**

The authorization to access a dataset is implemented at the user level: it is the administrator who enables each account to access certain datasets, at the time of creating the account or modifying it later.

The abilitation is managed in two ways:

- enabling access to all open datasets
- enabling additional datasets one by one

## **User guide**
<TODO Marghe>

### **User profile**
By clicking on the user profile icon, the Frontend shows to the user the list of information that make up the user's profile.

By clicking on the “Edit your profile” icon, users can modify some of the configurations of their profile: Name and Surname and “Requests expiration”. The “Requests expiration” parameter is described in the following paragraph.

Users can change their password by clicking on the button “CHANGE” near Last password change.
### **Requests expiration**
The “Requests expiration” parameter allows users to activate the automatic cleaning of their old submitted requests by setting the number N of days of expiration: requests with “End date” older than N days are deleted.

By default, N=0 that means the cleaning is not active.
### **Disk quota**
### **How To**



# **API**

<TODO Mattia>





# **Installation guide**
## **Data portal**
<TODO Giuse e Mattia>

Sarebbe meteo-hub
### **Meteo Hub v0.4.0**
<TODO Giuse e Mattia>

## **Open Data Catalogue**
### **Installing CKAN with docker compose**
The stack is based on Docker containers deployed with docker-compose, as described in the following documentation:

[https](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[://](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[docs](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[.](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[ckan](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[.](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[org](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[en](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[/2.8/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[maintaining](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[installing](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[install](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[from](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[docker](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[compose](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[.](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)[html](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html)

The following tools are required:

\1.     **Docker Engine**: the containerization runtime

\2.     **Docker Compose**: multi-container orchestration tool

The following container have been created:

|**Service Name**|**image**|**Network**|**Volumes**|**notes**|
| :- | :- | :- | :- | :- |
|webserver|nginx:alpine|<p>80:8080</p><p>443:8443</p>|webserver\_config:/etc/nginx|<p>Reverse proxy, remaps:</p><p>/catalog -> ckan:5000</p><p>/datapusher -> datapusher:8800</p>|
|ckan|Built from source. v2.8.2|Internally on :5000|<p>ckan\_config: /etc/ckan</p><p>ckan\_home:/usr/lib/ckan</p><p>ckan\_storage:/var/lib/ckan</p>|[https](https://github.com/ckan/ckan/tree/ckan-2.8.2)[://](https://github.com/ckan/ckan/tree/ckan-2.8.2)[github](https://github.com/ckan/ckan/tree/ckan-2.8.2)[.](https://github.com/ckan/ckan/tree/ckan-2.8.2)[com](https://github.com/ckan/ckan/tree/ckan-2.8.2)[/](https://github.com/ckan/ckan/tree/ckan-2.8.2)[ckan](https://github.com/ckan/ckan/tree/ckan-2.8.2)[/](https://github.com/ckan/ckan/tree/ckan-2.8.2)[ckan](https://github.com/ckan/ckan/tree/ckan-2.8.2)[/](https://github.com/ckan/ckan/tree/ckan-2.8.2)[tree](https://github.com/ckan/ckan/tree/ckan-2.8.2)[/](https://github.com/ckan/ckan/tree/ckan-2.8.2)[ckan](https://github.com/ckan/ckan/tree/ckan-2.8.2)[-2.8.2](https://github.com/ckan/ckan/tree/ckan-2.8.2)|
|db|Built from source, starting from *mdillon/postgis*|Internally on :5432|pg\_data:/var/lib/postgresql/data|[https](https://hub.docker.com/r/mdillon/postgis)[://](https://hub.docker.com/r/mdillon/postgis)[hub](https://hub.docker.com/r/mdillon/postgis)[.](https://hub.docker.com/r/mdillon/postgis)[docker](https://hub.docker.com/r/mdillon/postgis)[.](https://hub.docker.com/r/mdillon/postgis)[com](https://hub.docker.com/r/mdillon/postgis)[/](https://hub.docker.com/r/mdillon/postgis)[r](https://hub.docker.com/r/mdillon/postgis)[/](https://hub.docker.com/r/mdillon/postgis)[mdillon](https://hub.docker.com/r/mdillon/postgis)[/](https://hub.docker.com/r/mdillon/postgis)[postgis](https://hub.docker.com/r/mdillon/postgis)|
|<p>solr</p><p> </p><p> </p>|Built from source, starting from *solr:6.6.2*|Internally on :8983| |[https](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[://](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[hub](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[.](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[docker](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[.](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[com](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[/](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[layers](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[/](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[solr](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[/](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[library](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[/](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[solr](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)[/6.6.2](https://hub.docker.com/layers/solr/library/solr/6.6.2/images/sha256-02c52d10a1e0c505b203051c416b0fa16d3f0aed36ed5c71b83b4b492802eae5?context=explore)|
|redis|redis:latest|internally on :6379| | |


**CONTAINER ID    	IMAGE                   	COMMAND              	   PORTS            NAMES**

9c5a904ea8c8    	docker\_ckan             	"/ckan-entrypoint.sh…"   5000/tcp           ckan

b30ff54f9106    	nginx:alpine            	"nginx -g 'daemon of…"   80/tcp, 0.0.0.0:80->8080/tcp, 0.0.0.0:443->8443/tcp                                                               webserver

c390866ab566    	redis:latest            	"docker-entrypoint.s…"   6379/tcp          redis

27e4074af172    	clementmouchet/datapusher   "python datapusher/m…"          datapusher

11eee4e9e787    	docker\_solr             	"docker-entrypoint.s…"   8983/tcp          solr

2d560a0a08ae    	docker\_db               	"docker-entrypoint.s…"   0.0.0.0:5432

->5432/tcp          	                                                                                                  db

### **Ckan extensions**
A CKAN extension is a Python package that modifies or extends CKAN. Each extension contains one or more plugins that must be added to your CKAN config file to activate the extension’s features.

The **ckanext-mistral** extension has been created to customize the CKAN template.

The following extensions have been installed:

|**extension**|**Url**|**version**|**Plugin attivati**|
| :- | :- | :- | :- |
|*Plugin in ckan core*| | |<p>Stats</p><p>Image\_view</p><p>Text\_view</p><p>Recline\_view</p>|
|Datastore|*Ckan core*| |datastore|
|Datapusher|https://github.com/ckan/datapusher|2019-01-18|datapusher|
|Ckanext-spatial|https://github.com/ckan/ckanext-spatial|2019-03-15|<p>resource\_proxy</p><p>spatial\_metadata</p><p>spatial\_query</p><p>csw\_harvester</p>|
|Ckanext-dcat|https://github.com/ckan/ckanext-dcat|<p>2019-06-25</p><p> </p>|dcat dcat\_json\_interface structured\_data|
|Ckanext-dcatapit|https://github.com/geosolutions-it/ckanext-dcatapit|2019-12-09|<p>dcatapit\_pkg</p><p>dcatapit\_org</p><p>dcatapit\_config</p><p>dcatapit\_csw\_harvester</p>|
|Ckanext-mistral|Mistral extensions|1.0.0|mistral|
|Ckanext-geoview|https://github.com/ckan/ckanext-geoview/|2019-04-09|geo\_view|
|Ckanext-harvest|https://github.com/ckan/ckanext-harvest|2019-07-01|harvest ckan\_harvester|
|Ckanext-multilang|https://github.com/geosolutions-it/ckanext-multilang|2019-02-01|multilang|

### **Web server**
The webserver, running on the nginx:latest image, works as a reverse proxy for the environment.

Two **upstreams** are configured:

**1.** Upstream **ckan** toward ckan:5000

Proxy\_pass under location **/catalog** and **/catalog/**

**2.** Upstream **datapusher** toward datapusher:8800

Proxy\_pass under location **/datapusher** and **/datapusher/**
### **Ckan configuration**
The following **environment variables** are set by docker-compose and overrides the configuration file’s settings. The variable propagation is described at[ ](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[https](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[://](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[docs](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[.](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[ckan](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[.](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[org](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[en](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[/2.8/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[maintaining](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[installing](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[/](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[install](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[from](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[docker](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[compose](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[.](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[html](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[#](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[environment](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[-](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)[variables](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html#environment-variables)

|**Variable name**|**Config equivalent**|**Set value**|
| :- | :- | :- |
|CKAN\_SQLALCHEMY\_URL|sqlalchemy.url|postgresql://ckan:${POSTGRES\_PASSWORD}@db/ckan|
|CKAN\_DATASTORE\_WRITE\_URL|ckan.datastore.write\_url|postgresql://ckan:${POSTGRES\_PASSWORD}@db/datastore|
|'CKAN\_DATASTORE\_READ\_URL'|ckan.datastore.read\_url|postgresql://datastore\_ro:${DATASTORE\_READONLY\_PASSWORD}@db/datastore|
|CKAN\_REDIS\_URL|ckan.redis.url|redis://redis:6379/1|
|CKAN\_SOLR\_URL|solr\_url|http://solr:8983/solr/ckan|
|CKAN\_DATAPUSHER\_URL|ckan.datapusher.url|http://datapusher:8800|
|CKAN\_SITE\_URL|ckan.site\_url|https://www.mistralportal.it|


The full list of effective environment variable is available at[ ](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[https](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[://](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[docs](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[.](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[ckan](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[.](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[org](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[/](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[en](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[/2.8/](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[maintaining](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[/](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[configuration](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[.](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[html](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[#](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[environment](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[-](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)[variables](https://docs.ckan.org/en/2.8/maintaining/configuration.html#environment-variables)

The CKAN configuration file is located at **“/etc/ckan/production.ini**” in the CKAN container. The changes applied to the config setting are:
**
` `## Site Settings

ckan.site\_url = https://mistralportal.it

ckan.root\_path = /catalog

\## Search Settings

ckan.site\_id = default

solr\_url = http://solr:8983/solr

\## Redis Settings

\# URL to your Redis instance, including the database to be used.

ckan.redis.url = redis://redis:6379/0

\## CORS Settings

\# If cors.origin\_allow\_all is true, all origins are allowed.

\# If false, the cors.origin\_whitelist is used.

ckan.cors.origin\_allow\_all = true

\# cors.origin\_whitelist is a space separated list of allowed domains.

\# ckan.cors.origin\_whitelist = http://example1.com http://example2.com

\## Plugins Settings

ckan.plugins = stats text\_view image\_view recline\_view datastore datapusher resource\_proxy spatial\_metadata spatial\_query geo\_view harvest ckan\_harvester mistral dcat dcat\_json\_interface structured\_data dcatapit\_pkg dcatapit\_org dcatapit\_config

` `## Dcatapit Extension settings

ckanext.dcat.rdf.profiles = euro\_dcat\_ap it\_dcat\_ap

ckanext.dcat.base\_uri = https://www.mistralportal.it/catalog

ckanext.dcatapit.form\_tabs = False

\## Spatial Extension settings

ckanext.spatial.search\_backend = solr-spatial-field

ckan.spatial.srid = 4326

\## Front-End Settings

ckan.site\_title = CKAN

ckan.site\_logo = /images/logo-mistral-bianco-web-300x127.png

ckan.site\_description =

\## Internationalisation Settings

ckan.locale\_default = it

ckan.locale\_order = it en

ckan.locales\_offered = en it
### **Volumes**

|**Name**|**Mount point(s)**|
| :- | :- |
|webserver\_config|Webserver-> webserver\_config:/etc/nginx|
|ckan\_config|ckan -> ckan\_config:/etc/ckan|
|ckan\_home|ckan -> ckan\_home:/usr/lib/ckan|
|ckan\_storage|ckan -> ckan\_storage:/var/lib/ckan|
|pg\_data|db -> pg\_data:/var/lib/postgresql/data|

## **NiFi-based ingestion component**
<TODO Dedagroup>
###
### **DPC observed data flow**
### **Arpae observed data flow**
### **DPC radar data flow**
### **Arpap Multimodel data flow**

