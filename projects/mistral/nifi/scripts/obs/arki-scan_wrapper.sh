#!/bin/bash
CONFIG_PATH=${NIFI_ARKIMET_CONFIG_PATH}config
INPUT_FILE=/home/nifi/ingest/$1
/usr/bin/arki-scan --dispatch=${CONFIG_PATH} ${INPUT_FILE}