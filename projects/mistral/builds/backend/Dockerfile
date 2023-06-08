FROM rapydo/backend:2.4

ARG RAPYDO_VERSION
RUN test -n "$RAPYDO_VERSION"

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ENV APIUSER developer

RUN usermod -u $CURRENT_UID $APIUSER

RUN echo "deb [trusted=yes] https://simc.arpae.it/packages/debian jammy main" > /etc/apt/sources.list.d/arpae-simc.list \
    && apt-get update -qq \
    && apt-get install -y python3-wreport dballe python3-dballe arkimet libsim eccodes-simc dba-qcfilter

WORKDIR /code
