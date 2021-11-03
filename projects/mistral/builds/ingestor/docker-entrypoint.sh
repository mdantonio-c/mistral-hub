#!/bin/bash
set -e

if [ -z "$(ls ${NIFI_HOME}/conf)" ]; then
   echo "Default conf is missing, copying it..."
   cp ${NIFI_HOME}/default-conf/* ${NIFI_HOME}/conf/
   echo "Default conf copied"
else
   echo "Default conf already initialized"
fi

/opt/nifi/scripts/start.sh
