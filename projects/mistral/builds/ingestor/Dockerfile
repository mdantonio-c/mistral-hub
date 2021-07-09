FROM arpaesimc/centos:8

LABEL maintainer="Giuseppe Trotta <g.trotta@cineca.it>"
ENV NIFI_VERSION="1.13.2" \
    JAVA_VERSION="1.8.0"

RUN dnf -y repository-packages copr:copr.fedorainfracloud.org:simc:stable upgrade

# Install Java Open JDK 1.8
RUN yum -y update && \
    yum -y install java-$JAVA_VERSION-openjdk
ENV JAVA_HOME="/usr/lib/jvm/jre"

# Install NiFi
RUN mkdir /downloads/apache-nifi -p && \
    cd /downloads/apache-nifi && \
    yum -y install wget && \
    wget https://downloads.apache.org/nifi/$NIFI_VERSION/nifi-$NIFI_VERSION-bin.tar.gz && \
    tar -zxvf nifi-$NIFI_VERSION-bin.tar.gz && \
    mv nifi-$NIFI_VERSION /opt/ && \
    ln -s /opt/nifi-$NIFI_VERSION/ /opt/nifi

# Create working directories
RUN mkdir -p /home/nifi/ingest/radar \
    /home/nifi/ingest/obs \
    /opt/nifi/nifi_ok_flowfile \
    /opt/nifi/nifi_error_flowfile \
    /opt/nifi/temp

# clone python scripts for the ingestor in the dedicated folder
RUN yum -y install git
RUN cd /tmp && git clone https://gitlab.hpc.cineca.it/mistral/meteo-hub-ingestion.git && mv meteo-hub-ingestion/amqp2dballe_nifi_6.py meteo-hub-ingestion/dpc_bufr2dballe_4.py meteo-hub-ingestion/json2jsonl_nifi_2.py meteo-hub-ingestion/jsonl2bufr_nifi_3.py /home/nifi/ingest/obs && rm -rf meteo-hub-ingestion

WORKDIR /opt/nifi

# install database drivers
RUN mkdir /home/nifi/nifi-driver && \
    wget --quiet -O /home/nifi/nifi-driver/postgresql-42.2.19.jar https://jdbc.postgresql.org/download/postgresql-42.2.19.jar

# Enable Network
RUN sed -ie 's/^nifi\.web\.http\.host=.*/nifi.web.http.host=0.0.0.0/' conf/nifi.properties

# Start NiFi
ENTRYPOINT ["/bin/bash", "bin/nifi.sh", "run"]
EXPOSE 8080
