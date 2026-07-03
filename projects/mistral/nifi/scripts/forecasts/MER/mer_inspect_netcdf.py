#!/usr/bin/env python3
# Rileva lo spin-up di un NetCDF MER e calcola i parametri di crop da passare a
# water_level_processor.py, in modo che l'output parta dalla mezzanotte della
# run e non superi 72 timestep.
#
# NB: richiede l'ambiente conda (xarray/netcdf4). Da NiFi va lanciato con:
#   Command Path = /opt/conda/envs/eccodes_env/bin/python
#   Command Arguments = mer_inspect_netcdf.py;<netcdf_path>;<run_date_YYYYMMDD>
#
# Uso:
#   mer_inspect_netcdf.py <netcdf_path> <run_date_YYYYMMDD> [max_hours]
#
# Stampa su stdout un JSON con (fra gli altri):
#   map_offset_hours, timeseries_offset_hours  -> --map-offset-hours / --timeseries-offset-hours
#   max_time_steps                             -> --max-time-steps
#   steps_from_midnight                        -> 0 => nessun dato utile dopo la mezzanotte
#
# Exit code:
#   0  ok (leggere il JSON su stdout)
#   2  argomenti errati
#   60 file non apribile / variabile time assente
#   61 nessun timestep nel file

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

EXIT_BAD_ARGS = 2
EXIT_OPEN_ERROR = 60
EXIT_NO_TIMESTEPS = 61

DEFAULT_MAX_HOURS = 72


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        eprint(f"Usage: {Path(sys.argv[0]).name} <netcdf_path> <run_date_YYYYMMDD> [max_hours]")
        return EXIT_BAD_ARGS

    netcdf_path = Path(argv[0])
    run_date = argv[1]
    max_hours = int(argv[2]) if len(argv) == 3 else DEFAULT_MAX_HOURS

    if len(run_date) != 8 or not run_date.isdigit():
        eprint(f"Invalid run_date, expected YYYYMMDD: {run_date}")
        return EXIT_BAD_ARGS

    try:
        ds = xr.open_dataset(netcdf_path)
    except Exception as exc:  # noqa: BLE001 - vogliamo un exit code pulito per NiFi
        eprint(f"Cannot open dataset {netcdf_path}: {exc}")
        return EXIT_OPEN_ERROR

    try:
        if "time" not in ds.variables and "time" not in ds.coords:
            eprint("Dataset has no 'time' variable")
            return EXIT_OPEN_ERROR
        time_values = np.asarray(ds["time"].values)
    finally:
        ds.close()

    if time_values.size == 0:
        eprint("Dataset has no timesteps")
        return EXIT_NO_TIMESTEPS

    midnight = np.datetime64(f"{run_date[0:4]}-{run_date[4:6]}-{run_date[6:8]}T00:00:00")

    first_ts = time_values[0]
    last_ts = time_values[-1]

    # Ore dallo spin-up: dal primo timestep alla mezzanotte della run (0 se il
    # file inizia già alla mezzanotte o dopo).
    delta_seconds = (midnight - first_ts) / np.timedelta64(1, "s")
    offset_hours = float(max(0.0, delta_seconds / 3600.0))

    steps_before_midnight = int(np.count_nonzero(time_values < midnight))
    steps_from_midnight = int(np.count_nonzero(time_values >= midnight))

    steps_after = min(max_hours, steps_from_midnight)
    # --max-time-steps tronca PRIMA di applicare l'offset: quindi sommiamo i
    # timestep di spin-up ai timestep utili post-mezzanotte.
    max_time_steps = steps_before_midnight + steps_after

    result = {
        "run_date": run_date,
        "midnight": str(midnight),
        "first_timestep": np.datetime_as_string(first_ts, unit="s"),
        "last_timestep": np.datetime_as_string(last_ts, unit="s"),
        "n_timesteps": int(time_values.size),
        "steps_before_midnight": steps_before_midnight,
        "steps_from_midnight": steps_from_midnight,
        "map_offset_hours": offset_hours,
        "timeseries_offset_hours": offset_hours,
        "max_time_steps": int(max_time_steps),
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
