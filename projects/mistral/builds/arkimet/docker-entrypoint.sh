#!/bin/bash
set -e

echo "Reading datasets to build configuration"

datasets=""
for dir in /datasets/*; do
    if [ -d $dir ]; then
        datasets="${datasets} ${dir}"
    fi
done

if [ -z "$datasets" ]; then
    echo "No dataset found, starting Arki-server with empty configuration "
else
    echo "Datasets found: [$datasets]"

    echo "Merging datasets configuration..."

    arki-mergeconf $datasets --output=/datasets/arkimet.conf

    echo "Launching Arki-server"
fi

exec arki-server --url=http://localhost:8090 --host=0.0.0.0 --port=8090 /datasets/arkimet.conf
