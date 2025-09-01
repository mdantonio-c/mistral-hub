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
else
  # add lines related to the http configuration in the original start.sh file
 START_SCRIPT="/opt/nifi/scripts/start.sh"

 # Insert HTTP configuration after line 60
  sed -i "60r /dev/stdin" "$START_SCRIPT" <<'EOF'

# Custom HTTP Configuration
if [ -n "${NIFI_WEB_HTTP_PORT}" ]; then
    prop_replace 'nifi.web.https.port'                        ''
    prop_replace 'nifi.web.https.host'                        ''
    prop_replace 'nifi.web.http.port'                         "${NIFI_WEB_HTTP_PORT}"
    prop_replace 'nifi.web.http.host'                         "${NIFI_WEB_HTTP_HOST:-$HOSTNAME}"
    prop_replace 'nifi.remote.input.secure'                   'false'
    prop_replace 'nifi.cluster.protocol.is.secure'            'false'
    prop_replace 'nifi.security.keystore'                     ''
    prop_replace 'nifi.security.keystoreType'                 ''
    prop_replace 'nifi.security.truststore'                   ''
    prop_replace 'nifi.security.truststoreType'               ''
    prop_replace 'nifi.security.user.login.identity.provider' ''
    prop_replace 'keystore'                                   '' ${nifi_toolkit_props_file}
    prop_replace 'keystoreType'                               '' ${nifi_toolkit_props_file}
    prop_replace 'truststore'                                 '' ${nifi_toolkit_props_file}
    prop_replace 'truststoreType'                             '' ${nifi_toolkit_props_file}
    prop_replace 'baseUrl' "http://${NIFI_WEB_HTTP_HOST:-$HOSTNAME}:${NIFI_WEB_HTTP_PORT}" ${nifi_toolkit_props_file}
fi
EOF
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
