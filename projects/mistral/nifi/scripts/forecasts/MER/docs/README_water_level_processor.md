# mer_regular_grid

Small utility to extract station time series and create regular-grid GeoTIFF maps from MER NetCDF files.

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
python water_level_processor.py /path/to/input.nc /path/to/station_list_MER.txt --station-offsets-file /path/to/msl_YYYYMMDD.dat --resolutions 500m 1km --output-dir /path/to/output
```

Generate both maps and station time series, forcing zero station offsets:

```bash
python water_level_processor.py /path/to/input.nc /path/to/station_list_MER.txt --resolutions 500m 1km --output-dir /path/to/output
```

Generate only maps (omit station list):

```bash
python water_level_processor.py /path/to/input.nc --resolutions 500m 1km --only-maps --output-dir /path/to/output
```

Generate only station time series (omit resolutions):

```bash
python water_level_processor.py /path/to/input.nc /path/to/station_list_MER.txt --station-offsets-file /path/to/msl_YYYYMMDD.dat --only-timeseries --output-dir /path/to/output
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
- `--resolutions` (optional): list of output grid resolutions, for example `500m 1km` or `"[\"500m\",\"1km\"]"`. If provided, GeoTIFF maps are generated.
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
- In default mode, provide both `stations_path` and `--resolutions`.
- When time series are produced, missing station rows in the offsets file default to `m_obs=0` and `m_mod=0`.
- If offsets file is missing or not provided, all stations use zero offsets.

## Outputs

- GeoTIFF maps are saved in folders named `geotiff_<input_stem>_<resolution>`.
- Each map includes input stem, resolution, and timestep in the file name.
- Station series JSON includes input stem and covered time range in the file name.
- GeoTIFF metadata tags include `sdr`, `origine`, `risoluzione`, and `photometric_interpretation`.
