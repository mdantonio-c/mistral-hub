#FROM centos:7
FROM rapydo/backendcentos:0.6.6

COPY build.sh /
COPY build.conf /
RUN /bin/bash /build.sh /build.conf centos:7
RUN /bin/bash -c "rm /build.{sh,conf}"
