#!/usr/bin/env python3
"""Generate and publish MER station time series into the refactored target tree."""

import json
import shutil
import tempfile
from pathlib import Path

from mer_inspect_netcdf import inspect_netcdf
from water_level_processor import WaterLevelProcessor


def publish_with_replace(source_file: Path, target_file: Path) -> None:
    target_dir = target_file.parent
    temp_file = target_dir / f".{target_file.name}.tmp"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, temp_file)
        target_dir.mkdir(parents=True, exist_ok=True)
        temp_file.replace(target_file)
    except Exception as exc:  # noqa: BLE001
        try:
            temp_file.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
        raise RuntimeError(f"Failed publish to {target_file}: {exc}") from exc


def publish_timeseries(
    model: str,
    run_date: str,
    variant: str,
    netcdf_path: Path,
    msl_path: Path | None,
    station_list: Path,
    maps_model_dir: Path,
    max_hours: int = 72,
) -> dict[str, str | bool]:

    if not netcdf_path.is_file():
        raise ValueError(f"Missing netcdf file: {netcdf_path}")
    if not station_list.is_file():
        raise ValueError(f"Missing station list file: {station_list}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        staging_dir = Path(tmpdir_str)
        inspect_data = inspect_netcdf(netcdf_path, run_date, max_hours)
        if int(inspect_data.get("steps_from_midnight", 0)) <= 0:
            raise RuntimeError(
                "No valid timesteps from midnight for timeseries generation"
            )

        target_json = (
            maps_model_dir
            / "json"
            / f"{model}_{run_date}_{variant}_station_timeseries.json"
        )

        warnings: list[str] = []
        offsets = msl_path if msl_path is not None and msl_path.is_file() else None
        if offsets is None:
            warnings.append(
                f"Timeseries output {target_json} generated without station offsets: using zero offsets for all stations"
            )

        processor = WaterLevelProcessor.for_timeseries(
            netcdf_path=netcdf_path,
            stations_path=station_list,
            station_offsets_path=offsets,
            output_dir=staging_dir,
            timeseries_offset_hours=float(inspect_data["timeseries_offset_hours"]),
            verbose=False,
            max_time_steps=int(inspect_data["max_time_steps"]),
        )
        run_result = processor.run()
        source_json = run_result.timeseries_file
        if source_json is None:
            raise RuntimeError(
                f"No station_timeseries_*.json produced under: {staging_dir}"
            )
        publish_with_replace(source_json, target_json)

        output: dict[str, str | bool | list[str]] = {
            "published": True,
            "model": model,
            "run_date": run_date,
            "variant": variant,
            "target": str(target_json),
            "source": str(source_json),
        }
        if warnings:
            output["warnings"] = warnings

        return output
