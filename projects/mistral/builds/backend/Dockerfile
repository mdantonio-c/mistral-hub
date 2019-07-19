FROM rapydo/backendcentos:0.6.7

RUN git clone https://github.com/ARPA-SIMC/simc-docker-image
RUN cp simc-docker-image/centos-7/build.sh simc-docker-image/centos-7/build.conf /
RUN /bin/bash /build.sh /build.conf centos:7
RUN /bin/bash -c "rm /build.{sh,conf}"


ENV ECCODES_DEFINITION_PATH="/usr/share/eccodes-simc/definitions/:/usr/share/eccodes/definitions/"

ENV DATASET_ROOT="/arkimet/datasets/"