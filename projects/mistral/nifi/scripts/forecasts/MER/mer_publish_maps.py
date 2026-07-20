#!/usr/bin/env python3
"""Generate and publish MER maps into the refactored target tree."""

import re
import shutil
import tempfile
import time
from pathlib import Path

from mer_inspect_netcdf import inspect_netcdf
from water_level_processor import WaterLevelProcessor

MAX_RETRIES = 3
TIMESTAMP_TIF_RE = re.compile(r"^\d{8}T\d{6}\.tif$")


def _is_managed_map_file(path: Path) -> bool:
    return path.is_file() and (
        path.name == "timeregex.properties" or bool(TIMESTAMP_TIF_RE.match(path.name))
    )


def publish_maps_to_wl_with_replace(source_dir: Path, wl_dir: Path) -> None:
    if not source_dir.is_dir():
        raise RuntimeError(f"Missing source map directory: {source_dir}")

    backup_dir = wl_dir / ".maps_publish_bak"
    published_files: list[Path] = []

    try:
        wl_dir.mkdir(parents=True, exist_ok=True)
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        for target_file in wl_dir.iterdir():
            if _is_managed_map_file(target_file):
                target_file.replace(backup_dir / target_file.name)

        for source_file in sorted(source_dir.iterdir()):
            if not _is_managed_map_file(source_file):
                continue

            temp_file = wl_dir / f".{source_file.name}.tmp"
            shutil.copyfile(source_file, temp_file)
            target_file = wl_dir / source_file.name
            temp_file.replace(target_file)
            published_files.append(target_file)

        shutil.rmtree(backup_dir, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        try:
            for published_file in published_files:
                published_file.unlink(missing_ok=True)

            if backup_dir.exists():
                for backup_file in backup_dir.iterdir():
                    backup_file.replace(wl_dir / backup_file.name)
                shutil.rmtree(backup_dir, ignore_errors=True)

            for tmp_file in wl_dir.glob(".*.tmp"):
                tmp_file.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

        raise RuntimeError(f"Failed publish to {wl_dir}: {exc}") from exc


def publish_maps(
    model: str,
    run_date: str,
    assim_path: Path,
    maps_model_dir: Path,
    wait_for_geoserver_ready: bool = False,
    wait_timeout_sec: int = 30,
    wait_interval_sec: int = 10,
    resolution: str = "500m",
    geotiff_field_offset: float = 0.46,
    max_hours: int = 72,
) -> dict[str, str | bool]:
    if not assim_path.is_file():
        raise ValueError(f"Missing assim file: {assim_path}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        staging_dir = Path(tmpdir_str)

        inspect_data = inspect_netcdf(assim_path, run_date, max_hours)
        if int(inspect_data.get("steps_from_midnight", 0)) <= 0:
            raise RuntimeError("No valid timesteps from midnight for map generation")

        processor = WaterLevelProcessor.for_maps(
            netcdf_path=assim_path,
            output_dir=staging_dir,
            resolution=resolution,
            map_offset_hours=float(inspect_data["map_offset_hours"]),
            geotiff_field_offset=geotiff_field_offset,
            verbose=False,
            max_time_steps=int(inspect_data["max_time_steps"]),
        )
        run_result = processor.run()
        geotiff_source_dir = run_result.map_dir
        if geotiff_source_dir is None:
            raise RuntimeError(f"No GeoTIFF folder produced under: {staging_dir}")
        if run_result.map_file_count <= 0:
            raise RuntimeError(f"No GeoTIFF files produced under: {geotiff_source_dir}")

        timeregex_file = geotiff_source_dir / "timeregex.properties"
        timeregex_file.write_text(
            "regex=[0-9]{8}T[0-9]{6}\nformat=yyyyMMdd'T'HHmmss\n", encoding="utf-8"
        )

        if wait_for_geoserver_ready:
            geoserver_marker = maps_model_dir / f"{run_date}.GEOSERVER.READY"
            started = time.monotonic()
            retries = 0
            while not geoserver_marker.exists():
                if (time.monotonic() - started) >= wait_timeout_sec:
                    raise RuntimeError(
                        f"Timeout while waiting for GEOSERVER READY marker: {geoserver_marker}"
                    )
                if retries >= MAX_RETRIES:
                    raise RuntimeError(
                        f"Max retries ({retries}) reached while waiting for GEOSERVER READY marker: {geoserver_marker}"
                    )
                time.sleep(wait_interval_sec)
                retries += 1

        target_dir = maps_model_dir / "wl"
        publish_maps_to_wl_with_replace(geotiff_source_dir, target_dir)

        return {
            "published": True,
            "model": model,
            "run_date": run_date,
            "target_dir": str(target_dir),
            "source_dir": str(geotiff_source_dir),
            "map_files": str(run_result.map_file_count),
        }
