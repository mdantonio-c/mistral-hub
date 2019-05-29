
FROM arpaesimc/centos

MAINTAINER "Mattia D'Antonio <m.dantonio@cineca.it>"

RUN mkdir /docker-entrypoint.d/
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint

EXPOSE 8090

ENTRYPOINT ["docker-entrypoint"]
CMD ["docker-entrypoint"]