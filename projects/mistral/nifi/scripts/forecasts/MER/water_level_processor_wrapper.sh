#!/usr/bin/env bash

set -euo pipefail

export PROJ_LIB="$CONDA_DIR/envs/$CONDA_ECCODES_ENV/share/proj"
export PROJ_DATA="$CONDA_DIR/envs/$CONDA_ECCODES_ENV/share/proj"

exec "$CONDA_DIR/envs/$CONDA_ECCODES_ENV/bin/python" /home/nifi/ingest/forecasts/MER/water_level_processor.py "$@"