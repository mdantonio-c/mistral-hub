#!/bin/bash
set -e

# add cert creation here

if [ -z "$(ls ${NIFI_HOME}/conf)" ]; then
   echo "Default conf is missing, copying it..."
   cp ${NIFI_HOME}/default-conf/* ${NIFI_HOME}/conf/
   chown -R nifi:nifi ${NIFI_HOME}/conf/
   echo "Default conf copied"
else
   echo "Default conf already initialized"
fi

HOME=/home/nifi su -p nifi -c '/opt/nifi/scripts/start.sh'