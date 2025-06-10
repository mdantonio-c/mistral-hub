#!/bin/bash

# Usage: ./setup-backend-and-datasets.sh <project_name> <dataset_url>

set -e

# Check number of arguments
if [ "$#" -ne 2 ]; then
  echo "Error: incorrect number of arguments."
  echo "Usage: $0 <project_name> <dataset_url>"
  exit 1
fi

PROJECT="$1"
DATASET_URL="$2"

# Check URL format (simplified regex)
if [[ ! "$DATASET_URL" =~ ^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/[^ ]*)?$ ]]; then
    echo "Error: URL format not valid."
    exit 1
fi

echo "Installing dataset from: $DATASET_URL"

mkdir -p data/arkimet_conf
mkdir -p data/user_repo/templates_for_pp

wget --quiet "${DATASET_URL}/arkimet.conf" -O data/arkimet_conf/arkimet.conf
wget --quiet "${DATASET_URL}/arkimet_summary_CCBY_COMPLIANT.json" -O data/arkimet_conf/arkimet_summary_CCBY_COMPLIANT.json
wget --quiet "${DATASET_URL}/dballe_summary_CCBY_COMPLIANT.json" -O data/arkimet_conf/dballe_summary_CCBY_COMPLIANT.json
wget --quiet "${DATASET_URL}/sample.bufr" -O data/arkimet_conf/sample.bufr
wget --quiet "${DATASET_URL}/arkimet.zip" -O arkimet.zip

unzip -q arkimet.zip -d data/

ls -l data/arkimet || true
ls -l data/arkimet_conf || true

wget --quiet "${DATASET_URL}/template_for_spare_point.zip" -O data/user_repo/templates_for_pp/template_for_spare_point.zip

echo "Initializing project with Rapydo..."
rapydo --testing -e FTP_USER=ftpuser init --force
rapydo pull --quiet
rapydo install buildx
rapydo build --force
rapydo add task test_task
rapydo start
rapydo shell backend 'restapi wait'

echo "Initializing DBALLE with BUFR sample"

cat <<EOF > init.sh
dbadb wipe --dsn=postgresql://\$ALCHEMY_USER:\$ALCHEMY_PASSWORD@\$ALCHEMY_HOST:\$ALCHEMY_PORT/DBALLE
dbadb import --dsn=postgresql://\$ALCHEMY_USER:\$ALCHEMY_PASSWORD@\$ALCHEMY_HOST:\$ALCHEMY_PORT/DBALLE --type=bufr /arkimet/config/sample.bufr
EOF

cname=$(docker ps --format '{{.Names}}' | grep "backend")
docker cp init.sh ${cname}:/tmp/init.sh
rapydo shell backend 'bash /tmp/init.sh'

echo "Dataset and backend setup complete"
