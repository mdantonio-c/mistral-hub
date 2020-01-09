#!/bin/bash
set -e

dbadb wipe --dsn=postgresql://${ALCHEMY_USER}:${ALCHEMY_PASSWORD}@${ALCHEMY_HOST}:${ALCHEMY_PORT}/DBALLE
echo 'Db-All.e database initilized'
