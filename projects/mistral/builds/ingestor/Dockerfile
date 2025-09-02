
##### MULTISTAGE VERSION
FROM apache/nifi:2.3.0 as builder
FROM rapydo/backend:2.4

USER root



# This is the version installed on debian 10 with apt-get
ENV PYTHON_VERSION="3.10"

RUN apt-get update && apt-get install -y curl unzip bash \
    && rm -rf /var/lib/apt/lists/*


ENV NIFI_HOME=/opt/nifi/nifi-current
ENV NIFI_LOG_DIR=/opt/nifi/nifi-current/logs
ENV NIFI_BASE_DIR=/opt/nifi
ENV NIFI_PID_DIR=/opt/nifi/nifi-current/run
ENV NIFI_TOOLKIT_HOME=/opt/nifi/nifi-toolkit-current
ENV JAVA_HOME=/usr/lib/jvm/jdk-21.0.6-bellsoft-x86_64
ENV JAVA_VERSION=8u292S

ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY --from=builder /opt/nifi /opt/nifi
COPY --from=builder /usr/lib/jvm/jdk-21.0.6-bellsoft-x86_64 /usr/lib/jvm/jdk-21.0.6-bellsoft-x86_64

RUN echo "java -version"

ARG CURRENT_UID=1000
RUN test -n "$CURRENT_UID"

ARG CURRENT_GID=1000
RUN test -n "$CURRENT_GID"

RUN groupadd nifi && \
    useradd -m -g nifi nifi

# Identify the user with UID 1000 and store it in a variable
RUN old_user=$(getent passwd ${CURRENT_UID} | cut -d: -f1) && \
    if [ -n "$old_user" ]; then \
        echo "Old user with UID 1000: $old_user"; \
        new_uid=2000; \
        usermod -u $new_uid $old_user && groupmod -g $new_uid $old_user; \
        find / -user ${CURRENT_UID} -exec chown -h $new_uid {} \; || true; \
    else \
        echo "No existing user with UID 1000 found"; \
    fi

# Identify the group with GID 1000 and change it
RUN old_group=$(getent group ${CURRENT_GID} | cut -d: -f1) && \
    if [ -n "$old_group" ]; then \
        echo "Old group with GID 1000: $old_group"; \
        new_gid=2000; \
        groupmod -g $new_gid $old_group; \
        find / -group ${CURRENT_GID} -exec chgrp -h $new_gid {} \; || true; \
    else \
        echo "No existing group with GID 1000 found"; \
    fi

RUN usermod -u ${CURRENT_UID} nifi \
    && groupmod -og ${CURRENT_GID} nifi

#################################

#########################################################
# Dependencies
#########################################################

RUN apt-get update -qq && apt-get install wget
#
WORKDIR /tmp

#########################################################
# arpaesimc
#########################################################

RUN echo "deb [trusted=yes] https://simc.arpae.it/packages/debian jammy main" > /etc/apt/sources.list.d/arpae-simc.list \
    && apt-get update -qq \
    && apt-get install -y python3-wreport dballe python3-dballe arkimet libsim python3-eccodes eccodes-simc dba-qcfilter gdal-bin libeccodes-tools

#########################################################
# NIFI
#########################################################

# Create working directories
RUN mkdir -p /opt/nifi/nifi_ok_flowfile \
    /opt/nifi/nifi_error_flowfile \
    /opt/nifi/temp

RUN chown -R nifi:nifi /opt/nifi && chown -R nifi:nifi /usr/lib/jvm/jdk-21.0.6-bellsoft-x86_64


# Install database drivers
RUN mkdir /home/nifi/nifi-driver && \
    wget --quiet -O /home/nifi/nifi-driver/postgresql-42.2.19.jar https://jdbc.postgresql.org/download/postgresql-42.2.19.jar && \
    chown -R nifi:nifi /home/nifi/nifi-driver

RUN cp -r ${NIFI_HOME}/conf ${NIFI_HOME}/default-conf && chown -R nifi:nifi ${NIFI_HOME}/default-conf

COPY --chmod=700 docker-entrypoint.sh /usr/local/bin/docker-entrypoint

RUN chown -R nifi:nifi /opt/nifi/nifi-current/logs

WORKDIR ${NIFI_HOME}

ENV JAVA_OPTS="${JAVA_OPTS} -Dlog4j2.formatMsgNoLookups=true"

# Expose the necessary ports
EXPOSE 8080 8443

ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]
