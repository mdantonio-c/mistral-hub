#!/usr/bin/env python3
# Rileva lo spin-up di un NetCDF MER e calcola i parametri di crop da passare a
# water_level_processor.py, in modo che l'output parta dalla mezzanotte della
# run e non superi 72 timestep.
#
# NB: richiede l'ambiente conda (xarray/netcdf4). Da NiFi va lanciato con:
#   Command Path = /opt/conda/envs/eccodes_env/bin/python
#   Command Arguments = mer_inspect_netcdf.py;<netcdf_path>;<run_date_YYYYMMDD>

from pathlib import Path

import numpy as np
import xarray as xr


def inspect_netcdf(
    netcdf_path: Path, run_date: str, max_hours: int
) -> dict[str, object]:

    try:
        ds = xr.open_dataset(netcdf_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Cannot open dataset {netcdf_path}: {exc}") from exc

    try:
        if "time" not in ds.variables and "time" not in ds.coords:
            raise RuntimeError("Dataset has no 'time' variable")
        time_values = np.asarray(ds["time"].values)
    finally:
        ds.close()

    if time_values.size == 0:
        raise RuntimeError("Dataset has no timesteps")

    midnight = np.datetime64(
        f"{run_date[0:4]}-{run_date[4:6]}-{run_date[6:8]}T00:00:00"
    )

    first_ts = time_values[0]

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

    return {
        "steps_from_midnight": steps_from_midnight,
        "map_offset_hours": offset_hours,
        "timeseries_offset_hours": offset_hours,
        "max_time_steps": int(max_time_steps),
    }
