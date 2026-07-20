# mer_regular_grid

Utility to extract station time series and create regular-grid GeoTIFF maps from MER NetCDF files.

In production, this script is invoked by:

- `mer_publish_maps.py` for map generation/publication
- `mer_publish_timeseries.py` for station time series publication

Station time-series values are corrected per station using a daily offsets file with:

`val_final = val_netcdf + m_obs - m_mod`

## Install micromamba

Linux (bash):

```bash
"$(curl -L micro.mamba.pm/install.sh)"
```

Initialize shell and reload:

```bash
micromamba shell init -s bash -r ~/micromamba
source ~/.bashrc
```

Create environment from this repository export:

```bash
micromamba create -n mer_env --file requirements.txt -c conda-forge
micromamba activate mer_env
```

## Usage

Generate both maps and station time series:

```bash
python water_level_processor.py /path/to/input.nc /path/to/station_list_MER.txt --station-offsets-file /path/to/msl_YYYYMMDD.dat --resolution 500m --output-dir /path/to/output
```

Generate both maps and station time series, forcing zero station offsets:

```bash
python water_level_processor.py /path/to/input.nc /path/to/station_list_MER.txt --resolution 500m --output-dir /path/to/output
```

Generate only maps (omit station list):

```bash
python water_level_processor.py /path/to/input.nc --resolution 500m --only-maps --output-dir /path/to/output
```

Generate only station time series (omit map resolution):

```bash
python water_level_processor.py /path/to/input.nc /path/to/station_list_MER.txt --station-offsets-file /path/to/msl_YYYYMMDD.dat --only-timeseries --output-dir /path/to/output
```

## Programmatic Usage (Class API)

Besides CLI usage, you can instantiate `WaterLevelProcessor` directly from Python.

Recommended constructors are:

- `WaterLevelProcessor.for_maps(...)`
- `WaterLevelProcessor.for_timeseries(...)`

### Why `for_maps` and `for_timeseries` exist

The class supports multiple output modes (`maps`, `timeseries`, `both`) and has mode-specific required parameters.
The two class methods exist to avoid manual argument combinations that are easy to get wrong.

In practice:

- `for_maps(...)` sets `output_mode="maps"` and automatically disables timeseries-only parameters.
- `for_timeseries(...)` sets `output_mode="timeseries"` and automatically disables map-only parameters.

This keeps call sites shorter and consistent with internal validation rules.

If you need to generate both maps and time series in a single run, instantiate `WaterLevelProcessor(...)` directly with `output_mode="both"` and provide all required map + timeseries parameters.

### Example: both maps and timeseries (direct constructor)

```python
from pathlib import Path
from water_level_processor import WaterLevelProcessor

processor = WaterLevelProcessor(
	netcdf_path=Path("/path/to/input.nc"),
	output_dir=Path("/path/to/output"),
	output_mode="both",
	resolution="500m",
	map_offset_hours=0.0,
	geotiff_field_offset=0.46,
	stations_path=Path("/path/to/station_list_MER.txt"),
	station_offsets_path=Path("/path/to/msl_YYYYMMDD.dat"),  # or None
	timeseries_offset_hours=0.0,
	max_time_steps=72,
	verbose=False,
)

result = processor.run()
print(result.map_dir, result.map_file_count, result.timeseries_file)
```

### Example: maps only

```python
from pathlib import Path
from water_level_processor import WaterLevelProcessor

processor = WaterLevelProcessor.for_maps(
    netcdf_path=Path("/path/to/input.nc"),
    output_dir=Path("/path/to/output"),
    resolution="500m",
    map_offset_hours=0.0,
    geotiff_field_offset=0.46,
    max_time_steps=72,
    verbose=False,
)

result = processor.run()
print(result.map_dir, result.map_file_count)
```

### Example: timeseries only

```python
from pathlib import Path
from water_level_processor import WaterLevelProcessor

processor = WaterLevelProcessor.for_timeseries(
    netcdf_path=Path("/path/to/input.nc"),
    stations_path=Path("/path/to/station_list_MER.txt"),
    station_offsets_path=Path("/path/to/msl_YYYYMMDD.dat"),  # or None
    output_dir=Path("/path/to/output"),
    timeseries_offset_hours=0.0,
    max_time_steps=72,
    verbose=False,
)

result = processor.run()
print(result.timeseries_file)
```

## Input File Formats

Station list file (`station_list_MER.txt`): one row per station

```text
Ancona ANC 13.49 43.624
Ravenna RAV 12.203 44.421
```

Columns: `name station_id longitude latitude`

Daily station offsets file (`msl_YYYYMMDD.dat`): one row per station id

```text
ANC 0.1596 -0.375684511586207
RAV 0.1120 -0.245100000000000
```

Columns: `station_id m_obs m_mod`

## Options

- `netcdf_path` (positional): input NetCDF file.
- `stations_path` (positional, optional): station list text file. If provided, station time series are generated.
- `--station-offsets-file`: daily station offsets file (`msl_YYYYMMDD.dat`). If missing or not found, zero offsets are used for all stations.
- `--resolution` (optional): output grid resolution, for example `500m` or `1km`. If provided, GeoTIFF maps are generated.
- `--only-maps`: explicit mode for maps only.
- `--only-timeseries`: explicit mode for station time series only.
- `--output-dir` (required): output folder.
- `--invalid-values`: custom list of numeric sentinels treated as invalid (default includes `-999`, `-9999`, `-32767`, `-1e20`, `1e20`).
- `--max-time-steps`: optional processing cap for quick tests.
- `--map-offset-hours`: ignore the first N hours for map generation (default `0`).
- `--timeseries-offset-hours`: ignore the first N hours for station time-series generation (default `0`).
- `--geotiff-field-offset`: constant added to the full water-level field before GeoTIFF generation (default `0.46`).
- `--verbose`: enable runtime logging with `true` or `false` (default `true`).

Generation logic:

- Default mode is both maps and time series.
- `--only-maps` forces maps only.
- `--only-timeseries` forces time series only.
- In default mode, provide both `stations_path` and `--resolution`.
- To generate maps at multiple resolutions, run the command multiple times (one `--resolution` value per run).
- When time series are produced, missing station rows in the offsets file default to `m_obs=0` and `m_mod=0`.
- If offsets file is missing or not provided, all stations use zero offsets.

## Outputs

- When run standalone, GeoTIFF maps are saved in folders named `geotiff_<input_stem>_<resolution>`.
- In the refactored workflow, published map files are copied to `/opt/nifi/MER/maps/<MODEL>/wl/` as timestamped files (`YYYYMMDDTHHMMSS.tif`) plus `timeregex.properties`.
- In the refactored workflow, station series JSON files are published as `<MODEL>_<RUN_DATE>_<variant>_station_timeseries.json` under `/opt/nifi/MER/maps/<MODEL>/json/`.
- GeoTIFF metadata tags include `sdr`, `origine`, `risoluzione`, and `photometric_interpretation`.
