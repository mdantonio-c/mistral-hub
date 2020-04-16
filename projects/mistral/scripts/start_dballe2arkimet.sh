#!/bin/bash

echo "" >> /logs/dballe2arkimet.log
echo "" >> /logs/dballe2arkimet.log
echo '#################################################' >> /logs/dballe2arkimet.log
echo "Date: $(date) " >> /logs/dballe2arkimet.log
echo "" >> /logs/dballe2arkimet.log

LIMIT_DATE=`date -ud '10 days ago' +"%Y-%m-%d"`

ARKIMET_CONFIG_FILE=/arkimet/config/arkimet.conf

cd /scripts

./dballe2arkimet --dsn="postgresql://$ALCHEMY_USER:$ALCHEMY_PASSWORD@$ALCHEMY_HOST:$ALCHEMY_PORT/DBALLE" --arkiconf=$ARKIMET_CONFIG_FILE --date=$LIMIT_DATE >> /logs/dballe2arkimet.log 2>&1

