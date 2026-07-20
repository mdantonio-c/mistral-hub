#!/usr/bin/env bash

export PROJ_DATA=$CONDA_DIR/envs/$CONDA_ECCODES_ENV/share/proj/
export PYTHONFAULTHANDLER=1
export MER_CRASH_LOG_PATH=${MER_CRASH_LOG_PATH:-/tmp/mer_workflow_manager_crash.log}
# configurable environment variable to control the execution mode of the MER workflow manager. Possible values are 'process' (default) and 'thread'.
export MER_TASK_EXECUTION_MODE=${MER_TASK_EXECUTION_MODE:-process}
export MER_NETCDF_MAX_WORKERS=${MER_NETCDF_MAX_WORKERS:-2}
# GeoTIFF write workers for map publishing. Use 1 to disable write parallelism.
export MER_MAP_WRITE_WORKERS=${MER_MAP_WRITE_WORKERS:-2}
# GeoTIFF compression profile (e.g. LZW, DEFLATE). LZW is safer, DEFLATE is often faster here.
export MER_MAP_TIFF_COMPRESS=${MER_MAP_TIFF_COMPRESS:-DEFLATE}
# Optional predictor for compressed float rasters. Typical value: 2. Leave empty to disable.
export MER_MAP_TIFF_PREDICTOR=${MER_MAP_TIFF_PREDICTOR:-2}

exec $CONDA_DIR/envs/$CONDA_ECCODES_ENV/bin/python  /home/nifi/ingest/forecasts/MER_refactored_inprocess/mer_workflow_manager.py "$@"