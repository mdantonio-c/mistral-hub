#!/bin/bash
set -e

NIFI_USER="nifi"

DEVID=$(id -u ${NIFI_USER})
if [[ "${DEVID}" != "${CURRENT_UID}" ]]; then
    echo "Fixing uid of user ${NIFI_USER} from ${DEVID} to ${CURRENT_UID}..."
    usermod -u ${CURRENT_UID} ${NIFI_USER}
fi

GROUPID=$(id -g ${NIFI_USER})
if [[ "${GROUPID}" != "${CURRENT_GID}" ]]; then
    echo "Fixing gid user ${NIFI_USER} from ${GROUPID} to ${CURRENT_GID}..."
    groupmod -og ${CURRENT_GID} ${NIFI_USER}
fi

if [ "${APP_MODE}" == "production" ]; then
   openssl pkcs12 -export -out ${KEYSTORE_PATH} -in /ssl/real/fullchain1.pem -inkey /ssl/real/privkey1.pem -passin pass:${KEYSTORE_PASSWORD} -passout pass:${KEYSTORE_PASSWORD}
   chown nifi ${KEYSTORE_PATH}
fi

if [ -z "$(ls ${NIFI_HOME}/conf)" ]; then
   echo "Default conf is missing, copying it..."
   cp ${NIFI_HOME}/default-conf/* ${NIFI_HOME}/conf/
   chown -R nifi:nifi ${NIFI_HOME}/conf/
   echo "Default conf copied"
else
   echo "Default conf already initialized"
fi

HOME=/home/${NIFI_USER} su -p ${NIFI_USER} -c '/opt/nifi/scripts/start.sh'
