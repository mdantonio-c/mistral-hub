FROM rapydo/backendcentos:0.6.7

COPY build.sh /
COPY build.conf /
RUN /bin/bash /build.sh /build.conf centos:7
RUN /bin/bash -c "rm /build.{sh,conf}"
