#!/usr/bin/env bash

export PROJ_DATA=$CONDA_DIR/envs/$CONDA_ECCODES_ENV/share/proj/

exec $CONDA_DIR/envs/$CONDA_ECCODES_ENV/bin/python /home/nifi/ingest/obs/compdpc_hdf52grib2.py -i "$@"