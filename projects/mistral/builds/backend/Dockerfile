FROM arpaesimc/centos

FROM rapydo/backend:0.7.0

ARG CURRENT_UID
RUN test -n "$CURRENT_UID"
ENV APIUSER developer

RUN usermod -u $CURRENT_UID $APIUSER

# required to install libjasper-dev
RUN apt-get install -y software-properties-common
RUN add-apt-repository "deb http://security.ubuntu.com/ubuntu xenial-security main"

RUN apt-get install -y libhdf5-serial-dev libpq-dev libssl1.0.0 libssl-dev libpopt-dev liblua5.1-0-dev libgeos-dev liblzo2-2 libreadline6-dev libpng16-16 libjasper-dev

COPY --from=0 /usr/bin/arki-* /usr/bin/

COPY --from=0 /etc/arkimet/format /etc/arkimet/format
COPY --from=0 /usr/share/eccodes /usr/share/

COPY --from=0 /usr/lib64/libarkimet.* /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libdballe.* /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libmeteo-vm2.* /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libwreport.* /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libeccodes.* /lib/x86_64-linux-gnu/

COPY --from=0 /usr/lib64/mysql /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libcrypto.so.10 /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libssl.so.10 /lib/x86_64-linux-gnu/
COPY --from=0 /usr/lib64/libpng15.so.15 /lib/x86_64-linux-gnu/

ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/hdf5/serial"

WORKDIR /usr/lib/x86_64-linux-gnu/hdf5/serial

RUN ln -s libhdf5.so libhdf5.so.8
RUN ln -s libhdf5_hl.so libhdf5_hl.so.8

WORKDIR /usr/lib/x86_64-linux-gnu

RUN ln -s libmysqlclient.so.20 libmysqlclient.so.18
RUN ln -s libssl.so.1.0.0 libssl.so.10
RUN ln -s libcrypto.so.1.0.0 libcrypto.so.10
RUN ln -s liblua5.1.so liblua-5.1.so
RUN ln -s libgeos-3.6.2.so libgeos-3.4.2.so
RUN ln -s libpng16.so.16 libpng15.so.15
RUN ln -s libjpeg.so.8 libjpeg.so.62
RUN ln -s libreadline.so libreadline.so.6

ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes/definitions/"

ENV DATASET_ROOT="/arkimet/datasets/"

WORKDIR /code
