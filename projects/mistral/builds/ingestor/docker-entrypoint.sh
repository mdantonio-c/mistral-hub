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

# add cert creation here

if [ -z "$(ls ${NIFI_HOME}/conf)" ]; then
   echo "Default conf is missing, copying it..."
   cp ${NIFI_HOME}/default-conf/* ${NIFI_HOME}/conf/
   chown -R nifi:nifi ${NIFI_HOME}/conf/
   echo "Default conf copied"
else
   echo "Default conf already initialized"
fi

PROPS="/opt/nifi/nifi-current/conf/nifi.properties"
CUSTOM_PROPS="/opt/nifi/nifi-current/conf/nifi.custom.properties"

touch ${CUSTOM_PROPS}
sed -i -e "s|^nifi\.variable\.registry\.properties=.*$|nifi.variable.registry.properties=${CUSTOM_PROPS}|g" $PROPS

HOME=/home/${NIFI_USER} su -p ${NIFI_USER} -c '/opt/nifi/scripts/start.sh'