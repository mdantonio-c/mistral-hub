#!/usr/bin/env python3
"""Extract station time series and remap unstructured water level to regular GeoTIFF grids."""

from __future__ import annotations

import argparse
import json
import math
import os
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Tuple

import matplotlib.tri as mtri
import numpy as np
import rasterio
import xarray as xr
from loguru import logger
from rasterio.transform import from_origin
from scipy.spatial import cKDTree

EARTH_RADIUS_M = 6_371_000.0
DEFAULT_INVALID_VALUES = (-999.0, -9999.0, -32767.0, -1.0e20, 1.0e20)


@dataclass(frozen=True)
class Station:
    name: str
    station_id: str
    latitude: float
    longitude: float


@dataclass
class StationMatch:
    station: Station
    node_index: int
    distance_m: float


@dataclass
class GridSpec:
    label: str
    meters: float
    dx_deg: float
    dy_deg: float
    lon_values: np.ndarray
    lat_values_desc: np.ndarray
    mesh_lon: np.ndarray
    mesh_lat: np.ndarray
    transform: rasterio.transform.Affine


@dataclass(frozen=True)
class ProcessorRunResult:
    map_file: Path | None
    map_dir: Path | None
    map_file_count: int
    timeseries_file: Path | None


def parse_resolution_to_meters(text: str) -> float:
    token = text.strip().lower()
    if token.endswith("km"):
        return float(token[:-2]) * 1000.0
    if token.endswith("m"):
        return float(token[:-1])
    raise ValueError(
        f"Unsupported resolution format '{text}'. Use values like 500m or 1km."
    )


def parse_resolution(value: str) -> tuple[str, float]:
    meters = parse_resolution_to_meters(value)
    if meters <= 0:
        raise ValueError(f"Resolution must be > 0: {value}")
    return value, meters


def sanitize_values(values: np.ndarray, invalid_values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    arr[~np.isfinite(arr)] = np.nan

    for bad in invalid_values:
        arr[np.isclose(arr, bad)] = np.nan

    arr[np.abs(arr) > 1.0e10] = np.nan
    return arr


def load_stations(path: Path) -> list[Station]:
    """Read station list rows formatted as: <name> <station_id> <lon> <lat>."""
    stations: list[Station] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 4:
                raise ValueError(
                    f"Invalid station row at line {line_no} in {path}: expected '<name> <id> <lon> <lat>'."
                )

            name = parts[0]
            station_id = parts[1]
            lon = float(parts[2])
            lat = float(parts[3])
            stations.append(
                Station(
                    name=name,
                    station_id=station_id,
                    latitude=lat,
                    longitude=lon,
                )
            )

    if not stations:
        raise ValueError(f"No stations found in station list file: {path}")
    return stations


def load_station_offsets(path: Path) -> dict[str, tuple[float, float]]:
    """Read daily station offsets rows formatted as: <station_id> <m_obs> <m_mod>."""
    offsets: dict[str, tuple[float, float]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 3:
                raise ValueError(
                    f"Invalid offset row at line {line_no} in {path}: expected '<id> <m_obs> <m_mod>'."
                )

            station_id = parts[0]
            m_obs = float(parts[1])
            m_mod = float(parts[2])
            offsets[station_id] = (m_obs, m_mod)

    return offsets


def get_station_correction(
    station_id: str,
    station_offsets: dict[str, tuple[float, float]],
) -> float:
    m_obs, m_mod = station_offsets.get(station_id, (0.0, 0.0))
    return m_obs - m_mod


def get_station_offset_pair(
    station_id: str,
    station_offsets: dict[str, tuple[float, float]],
) -> tuple[float, float]:
    return station_offsets.get(station_id, (0.0, 0.0))


def load_stations_json(path: Path) -> list[Station]:
    """Legacy loader kept for backward compatibility (unused)."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    stations: list[Station] = []
    for name, coords in data.items():
        if "latitude" not in coords or "longitude" not in coords:
            raise ValueError(f"Station '{name}' must contain latitude and longitude.")
        stations.append(
            Station(
                name=str(name),
                station_id=str(name),
                latitude=float(coords["latitude"]),
                longitude=float(coords["longitude"]),
            )
        )

    if not stations:
        raise ValueError("No stations found in station JSON file.")
    return stations


def parse_bool(value: str) -> bool:
    token = value.strip().lower()
    if token in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def sanitize_token(value: str) -> str:
    safe = []
    for ch in value:
        safe.append(ch if ch.isalnum() or ch in {"_", "-"} else "_")
    return "".join(safe).strip("_") or "dataset"


class WaterLevelProcessor:
    def __init__(
        self,
        netcdf_path: Path,
        output_dir: Path,
        output_mode: Literal["both", "maps", "timeseries"],
        # Map-specific
        resolution: str | None,
        map_offset_hours: float | None,
        geotiff_field_offset: float | None,
        # Timeseries-specific
        stations_path: Path | None,
        station_offsets_path: Path | None,
        timeseries_offset_hours: float | None,
        # Common
        verbose: bool = True,
        invalid_values: Iterable[float] = DEFAULT_INVALID_VALUES,
        max_time_steps: int | None = None,
    ) -> None:
        self.netcdf_path = netcdf_path
        self.output_dir = output_dir
        self.output_mode = output_mode

        # Map-specific
        self.resolution = resolution
        self.map_offset_hours = map_offset_hours
        self.geotiff_field_offset = geotiff_field_offset

        # Timeseries-specific
        self.stations_path = stations_path
        self.station_offsets_path = station_offsets_path
        self.timeseries_offset_hours = timeseries_offset_hours

        # Common
        self.verbose = verbose
        self.invalid_values = np.asarray(list(invalid_values), dtype=np.float64)
        self.max_time_steps = max_time_steps
        self.source_tag = sanitize_token(self.netcdf_path.stem)
        self.produce_maps = self.output_mode in {"both", "maps"}
        self.produce_timeseries = self.output_mode in {"both", "timeseries"}

        if self.produce_maps:
            if self.resolution is None:
                raise ValueError(
                    "Map output selected but no --resolution was provided."
                )
            if self.map_offset_hours is None:
                raise ValueError(
                    "Map output selected but map_offset_hours was not provided."
                )
            if self.geotiff_field_offset is None:
                raise ValueError(
                    "Map output selected but geotiff_field_offset was not provided."
                )

        if self.produce_timeseries:
            if self.stations_path is None:
                raise ValueError(
                    "Timeseries output selected but stations_path was not provided."
                )
            if self.timeseries_offset_hours is None:
                raise ValueError(
                    "Timeseries output selected but timeseries_offset_hours was not provided."
                )

        logger.remove()
        if self.verbose:
            logger.add(lambda msg: print(msg, end=""), level="INFO")
        else:
            logger.add(lambda msg: print(msg, end=""), level="WARNING")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ds = xr.open_dataset(self.netcdf_path)
        self.stations = (
            load_stations(self.stations_path) if self.stations_path is not None else []
        )

        self.station_offsets: dict[str, tuple[float, float]] = {}
        if self.produce_timeseries and self.station_offsets_path is None:
            logger.warning(
                "No station offsets file provided: using zero offsets for all stations."
            )
        elif (
            self.produce_timeseries
            and self.station_offsets_path is not None
            and not self.station_offsets_path.exists()
        ):
            logger.warning(
                "Station offsets file not found ({}): using zero offsets for all stations.",
                self.station_offsets_path,
            )
        elif self.produce_timeseries and self.station_offsets_path is not None:
            self.station_offsets = load_station_offsets(self.station_offsets_path)

        logger.info("Opened dataset: {}", self.netcdf_path)

        self.node_lon = np.asarray(self.ds["Mesh2_node_x"].values, dtype=np.float64)
        self.node_lat = np.asarray(self.ds["Mesh2_node_y"].values, dtype=np.float64)

        triangles = np.asarray(self.ds["Mesh2_face_nodes"].values, dtype=np.int64)
        if triangles.min() == 1:
            triangles = triangles - 1
        if triangles.min() < 0 or triangles.max() >= self.node_lon.size:
            raise ValueError("Invalid triangle connectivity in Mesh2_face_nodes.")
        self.triangles = triangles

        self.file_time_values = np.asarray(self.ds["time"].values)
        self._summarize_file_timesteps(self.file_time_values)

        self.time_values = self.file_time_values.copy()
        if self.max_time_steps is not None:
            self.time_values = self.time_values[: self.max_time_steps]
            logger.info("Applied max-time-steps limit: {}", self.max_time_steps)

        self.map_time_indices = (
            self._time_indices_after_offset(self.map_offset_hours)
            if self.map_offset_hours is not None
            else np.array([])
        )
        self.timeseries_time_indices = (
            self._time_indices_after_offset(self.timeseries_offset_hours)
            if self.timeseries_offset_hours is not None
            else np.array([])
        )

        self.static_valid = self._build_static_valid_mask()
        self.triangulation = self._build_triangulation() if self.produce_maps else None
        self.station_matches = (
            self._match_stations_to_nodes() if self.produce_timeseries else []
        )
        self.grid_spec = self._build_grid_spec() if self.produce_maps else None

        if self.produce_maps:
            logger.info(
                "Configured for maps: {} timesteps after {}h",
                len(self.map_time_indices),
                self.map_offset_hours,
            )
            logger.info(
                "Value offsets: geotiff_field_offset={}",
                self.geotiff_field_offset,
            )
            self._summarize_indices("Maps", self.time_values, self.map_time_indices)

        if self.produce_timeseries:
            logger.info(
                "Configured for time series: {} timesteps after {}h",
                len(self.timeseries_time_indices),
                self.timeseries_offset_hours,
            )
            self._summarize_indices(
                "Time series", self.time_values, self.timeseries_time_indices
            )

    @classmethod
    def for_maps(
        cls,
        netcdf_path: Path,
        output_dir: Path,
        resolution: str,
        map_offset_hours: float,
        geotiff_field_offset: float,
        verbose: bool = True,
        invalid_values: Iterable[float] = DEFAULT_INVALID_VALUES,
        max_time_steps: int | None = None,
    ) -> WaterLevelProcessor:
        return cls(
            netcdf_path=netcdf_path,
            output_dir=output_dir,
            output_mode="maps",
            resolution=resolution,
            map_offset_hours=map_offset_hours,
            geotiff_field_offset=geotiff_field_offset,
            stations_path=None,
            station_offsets_path=None,
            timeseries_offset_hours=None,
            verbose=verbose,
            invalid_values=invalid_values,
            max_time_steps=max_time_steps,
        )

    @classmethod
    def for_timeseries(
        cls,
        netcdf_path: Path,
        stations_path: Path,
        station_offsets_path: Path | None,
        output_dir: Path,
        timeseries_offset_hours: float,
        verbose: bool = True,
        invalid_values: Iterable[float] = DEFAULT_INVALID_VALUES,
        max_time_steps: int | None = None,
    ) -> WaterLevelProcessor:
        return cls(
            netcdf_path=netcdf_path,
            output_dir=output_dir,
            output_mode="timeseries",
            resolution=None,
            map_offset_hours=None,
            geotiff_field_offset=None,
            stations_path=stations_path,
            station_offsets_path=station_offsets_path,
            timeseries_offset_hours=timeseries_offset_hours,
            verbose=verbose,
            invalid_values=invalid_values,
            max_time_steps=max_time_steps,
        )

    def _time_indices_after_offset(self, offset_hours: float) -> np.ndarray:
        if offset_hours < 0:
            raise ValueError("Offsets must be >= 0 hours.")
        if self.time_values.size == 0:
            return np.array([], dtype=np.int64)

        start_time = self.time_values[0] + np.timedelta64(
            int(round(offset_hours * 3600.0)), "s"
        )
        selected = np.flatnonzero(self.time_values >= start_time)

        if selected.size == 0:
            logger.warning(
                "Offset {}h selects no timesteps (requested start {}). No data will be produced for this offset.",
                offset_hours,
                np.datetime_as_string(start_time, unit="s"),
            )

        #    logger.warning(
        #        "Offset {}h selects no timesteps (requested start {}). Falling back to all available timesteps.",
        #        offset_hours,
        #        np.datetime_as_string(start_time, unit="s"),
        #    )
        #    return np.arange(self.time_values.size, dtype=np.int64)

        return selected

    @staticmethod
    def _summarize_file_timesteps(time_values: np.ndarray) -> None:
        if time_values.size == 0:
            logger.info("File timesteps: no timesteps found in the dataset")
            return

        first_all = np.datetime_as_string(time_values[0], unit="s")
        last_all = np.datetime_as_string(time_values[-1], unit="s")
        logger.info(
            "File timesteps: start={}, end={}, count={}",
            first_all,
            last_all,
            time_values.size,
        )

    @staticmethod
    def _summarize_indices(
        label: str, time_values: np.ndarray, indices: np.ndarray
    ) -> None:
        if time_values.size == 0:
            logger.info("{}: no available timesteps", label)
            return

        first_all = np.datetime_as_string(time_values[0], unit="s")
        last_all = np.datetime_as_string(time_values[-1], unit="s")

        if indices.size == 0:
            logger.info(
                "{}: selected 0 timesteps from available {} ({} -> {})",
                label,
                time_values.size,
                first_all,
                last_all,
            )
            return

        first_sel = np.datetime_as_string(time_values[int(indices[0])], unit="s")
        last_sel = np.datetime_as_string(time_values[int(indices[-1])], unit="s")
        logger.info(
            "{}: selected {} of {} timesteps (available {} -> {}, selected {} -> {})",
            label,
            indices.size,
            time_values.size,
            first_all,
            last_all,
            first_sel,
            last_sel,
        )

    def _build_static_valid_mask(self) -> np.ndarray:
        static_valid = np.ones(self.node_lon.shape, dtype=bool)
        static_valid &= np.isfinite(self.node_lon) & np.isfinite(self.node_lat)

        if "total_depth" in self.ds:
            depth = np.asarray(self.ds["total_depth"].values, dtype=np.float64)
            static_valid &= np.isfinite(depth) & (depth > 0.0)

        if not static_valid.any():
            raise ValueError("No valid sea nodes detected for interpolation.")
        return static_valid

    def _build_triangulation(self) -> mtri.Triangulation:
        tri_mask = ~self.static_valid[self.triangles].all(axis=1)
        return mtri.Triangulation(
            self.node_lon, self.node_lat, triangles=self.triangles, mask=tri_mask
        )

    def _match_stations_to_nodes(self) -> list[StationMatch]:
        valid_indices = np.flatnonzero(self.static_valid)
        mean_lat = float(np.nanmean(self.node_lat[valid_indices]))

        node_x_m, node_y_m = lonlat_to_local_meters(
            self.node_lon[valid_indices], self.node_lat[valid_indices], mean_lat
        )
        tree = cKDTree(np.column_stack((node_x_m, node_y_m)))

        matches: list[StationMatch] = []
        for station in self.stations:
            sx, sy = lonlat_to_local_meters(
                np.asarray([station.longitude], dtype=np.float64),
                np.asarray([station.latitude], dtype=np.float64),
                mean_lat,
            )
            distance_m, idx = tree.query(np.column_stack((sx, sy)), k=1)
            matches.append(
                StationMatch(
                    station=station,
                    node_index=int(valid_indices[int(idx[0])]),
                    distance_m=float(distance_m[0]),
                )
            )
        return matches

    def _build_grid_spec(self) -> GridSpec:
        valid_lon = self.node_lon[self.static_valid]
        valid_lat = self.node_lat[self.static_valid]

        lon_min = float(np.nanmin(valid_lon))
        lon_max = float(np.nanmax(valid_lon))
        lat_min = float(np.nanmin(valid_lat))
        lat_max = float(np.nanmax(valid_lat))
        mean_lat = float(np.nanmean(valid_lat))

        if self.resolution is None:
            raise RuntimeError(
                "Internal error: resolution must be set when map output is enabled."
            )

        label, meters = parse_resolution(self.resolution)
        dy_deg = meters / 111_320.0
        dx_deg = meters / (111_320.0 * max(math.cos(math.radians(mean_lat)), 1.0e-6))

        lon_values = np.arange(lon_min, lon_max + dx_deg, dx_deg, dtype=np.float64)
        lat_values_asc = np.arange(lat_min, lat_max + dy_deg, dy_deg, dtype=np.float64)
        lat_values_desc = lat_values_asc[::-1]

        mesh_lon, mesh_lat = np.meshgrid(lon_values, lat_values_desc)
        transform = from_origin(
            west=lon_values[0] - dx_deg / 2.0,
            north=lat_values_desc[0] + dy_deg / 2.0,
            xsize=dx_deg,
            ysize=dy_deg,
        )

        return GridSpec(
            label=label,
            meters=meters,
            dx_deg=dx_deg,
            dy_deg=dy_deg,
            lon_values=lon_values,
            lat_values_desc=lat_values_desc,
            mesh_lon=mesh_lon,
            mesh_lat=mesh_lat,
            transform=transform,
        )

    def run(self) -> ProcessorRunResult:
        logger.info("Starting processing")
        map_file: Path | None = None
        map_dir: Path | None = None
        map_file_count = 0
        timeseries_file: Path | None = None
        station_series: dict[str, dict[str, object]] = {}
        for match in self.station_matches:
            m_obs, m_mod = get_station_offset_pair(
                match.station.station_id, self.station_offsets
            )
            station_correction = get_station_correction(
                match.station.station_id, self.station_offsets
            )
            station_series[match.station.name] = {
                "station": {
                    "id": match.station.station_id,
                    "latitude": match.station.latitude,
                    "longitude": match.station.longitude,
                },
                "station_offset": {
                    "m_obs": m_obs,
                    "m_mod": m_mod,
                    "correction": station_correction,
                },
                "nearest_node": {
                    "index": match.node_index,
                    "latitude": float(self.node_lat[match.node_index]),
                    "longitude": float(self.node_lon[match.node_index]),
                    "distance_m": match.distance_m,
                },
                "time": [],
                "water_level": [],
            }

        if self.produce_maps:
            if self.grid_spec is None:
                raise RuntimeError(
                    "Internal error: map output enabled without a grid specification."
                )
            map_dir = (
                self.output_dir / f"geotiff_{self.source_tag}_{self.grid_spec.label}"
            )
            map_dir.mkdir(parents=True, exist_ok=True)

        water_level_da = self.ds["water_level"]
        if "level" in water_level_da.dims:
            water_level_da = water_level_da.isel(level=0)
        # Materialize once to avoid repeated xarray indexing overhead in tight loops.
        water_level_values = np.asarray(water_level_da.values, dtype=np.float64)

        if self.produce_maps:
            if self.grid_spec is None:
                raise RuntimeError(
                    "Internal error: map output enabled without a grid specification."
                )
            if map_dir is None:
                raise RuntimeError(
                    "Internal error: map output enabled without map output directory."
                )

            spec = self.grid_spec
            mesh_lon = spec.mesh_lon
            mesh_lat = spec.mesh_lat
            static_valid = self.static_valid
            geotiff_field_offset = float(self.geotiff_field_offset)
            write_workers = self._parse_positive_int_env(
                "MER_MAP_WRITE_WORKERS", default=1
            )
            tiff_profile_overrides = self._map_tiff_profile_overrides()

            pending_writes: list[tuple[Future[None], Path, str]] = []

            def drain_one_pending() -> None:
                nonlocal map_file, map_file_count
                future, out_file_done, timestamp_done = pending_writes.pop(0)
                future.result()
                map_file = out_file_done
                map_file_count += 1
                logger.info("Wrote map for timestep {}", timestamp_done)

            def flush_pending() -> None:
                while pending_writes:
                    drain_one_pending()

            if write_workers <= 1:
                for t_idx in self.map_time_indices:
                    t_idx = int(t_idx)
                    timestamp = np.datetime_as_string(self.time_values[t_idx], unit="s")
                    safe_ts = timestamp.replace(":", "").replace("-", "")

                    values = sanitize_values(
                        water_level_values[t_idx],
                        self.invalid_values,
                    )
                    values = values + geotiff_field_offset

                    z = np.ma.array(values, mask=(~np.isfinite(values) | ~static_valid))
                    interpolator = mtri.LinearTriInterpolator(self.triangulation, z)

                    grid_values = interpolator(mesh_lon, mesh_lat)
                    grid_data = np.asarray(
                        np.ma.filled(grid_values, np.nan), dtype=np.float32
                    )
                    grid_data[~np.isfinite(grid_data)] = np.nan

                    out_file = map_dir / f"{safe_ts}.tif"
                    self._write_geotiff(
                        out_file, grid_data, spec, tiff_profile_overrides
                    )
                    map_file = out_file
                    map_file_count += 1
                    logger.info("Wrote map for timestep {}", timestamp)
            else:
                with ThreadPoolExecutor(max_workers=write_workers) as writer_pool:
                    for t_idx in self.map_time_indices:
                        t_idx = int(t_idx)
                        timestamp = np.datetime_as_string(
                            self.time_values[t_idx], unit="s"
                        )
                        safe_ts = timestamp.replace(":", "").replace("-", "")

                        values = sanitize_values(
                            water_level_values[t_idx],
                            self.invalid_values,
                        )
                        values = values + geotiff_field_offset

                        z = np.ma.array(
                            values, mask=(~np.isfinite(values) | ~static_valid)
                        )
                        interpolator = mtri.LinearTriInterpolator(self.triangulation, z)

                        grid_values = interpolator(mesh_lon, mesh_lat)
                        grid_data = np.asarray(
                            np.ma.filled(grid_values, np.nan), dtype=np.float32
                        )
                        grid_data[~np.isfinite(grid_data)] = np.nan

                        out_file = map_dir / f"{safe_ts}.tif"
                        fut = writer_pool.submit(
                            self._write_geotiff,
                            out_file,
                            grid_data,
                            spec,
                            tiff_profile_overrides,
                        )
                        pending_writes.append((fut, out_file, timestamp))

                        # Keep a bounded queue to overlap compute and I/O without unbounded memory growth.
                        if len(pending_writes) >= write_workers * 2:
                            drain_one_pending()

                    flush_pending()

            if self.map_time_indices.size > 0 and map_file_count == 0:
                raise RuntimeError(
                    "Map mode enabled with selected timesteps but no GeoTIFFs were written."
                )

        if self.produce_timeseries:
            timeseries_indices = {int(v) for v in self.timeseries_time_indices}
            for t_idx in sorted(timeseries_indices):
                timestamp = np.datetime_as_string(self.time_values[t_idx], unit="s")

                values = sanitize_values(
                    water_level_values[t_idx],
                    self.invalid_values,
                )

                for match in self.station_matches:
                    station_entry = station_series[match.station.name]
                    station_entry["time"].append(timestamp)
                    val = values[match.node_index]
                    if not np.isfinite(val):
                        station_entry["water_level"].append(None)
                        continue

                    correction = station_entry["station_offset"]["correction"]
                    station_entry["water_level"].append(float(val + correction))

            if timeseries_indices:
                first_ts = np.datetime_as_string(
                    self.time_values[min(timeseries_indices)], unit="s"
                )
                last_ts = np.datetime_as_string(
                    self.time_values[max(timeseries_indices)], unit="s"
                )
                ts_suffix = f"{first_ts.replace(':', '').replace('-', '')}_{last_ts.replace(':', '').replace('-', '')}"
            else:
                ts_suffix = "empty"

            ts_out = (
                self.output_dir
                / f"station_timeseries_{self.source_tag}_{ts_suffix}.json"
            )
            with ts_out.open("w", encoding="utf-8") as f:
                json.dump(station_series, f, indent=2)
            logger.info("Wrote station time series: {}", ts_out)
            timeseries_file = ts_out

        logger.info("Processing completed")
        return ProcessorRunResult(
            map_file=map_file,
            map_dir=map_dir,
            map_file_count=map_file_count,
            timeseries_file=timeseries_file,
        )

    @staticmethod
    def _parse_positive_int_env(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            parsed = int(raw)
        except ValueError:
            return default
        return max(1, parsed)

    @staticmethod
    def _map_tiff_profile_overrides() -> dict[str, object]:
        compress = (os.getenv("MER_MAP_TIFF_COMPRESS", "LZW") or "LZW").strip().upper()
        predictor_raw = (os.getenv("MER_MAP_TIFF_PREDICTOR", "") or "").strip()

        overrides: dict[str, object] = {"compress": compress}
        if predictor_raw:
            try:
                overrides["predictor"] = int(predictor_raw)
            except ValueError:
                pass
        return overrides

    @staticmethod
    def _write_geotiff(
        path: Path,
        data: np.ndarray,
        spec: GridSpec,
        profile_overrides: dict[str, object],
    ) -> None:
        profile = {
            "driver": "GTiff",
            "height": data.shape[0],
            "width": data.shape[1],
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:4326",
            "transform": spec.transform,
            "compress": "LZW",
            "photometric": "MINISBLACK",
            "nodata": np.nan,
        }
        profile.update(profile_overrides)

        with rasterio.open(path, "w", **profile) as dst:
            dst.write(data, 1)
            dst.update_tags(
                sdr="water_level",
                origine=path.stem,
                risoluzione=spec.label,
                **{"photometric interpretation": "MINISBLACK"},
                photometric_interpretation="MINISBLACK",
            )


def lonlat_to_local_meters(
    lon_deg: np.ndarray, lat_deg: np.ndarray, ref_lat_deg: float
) -> tuple[np.ndarray, np.ndarray]:
    lon_rad = np.radians(lon_deg)
    lat_rad = np.radians(lat_deg)
    ref_lat_rad = math.radians(ref_lat_deg)

    x = EARTH_RADIUS_M * lon_rad * math.cos(ref_lat_rad)
    y = EARTH_RADIUS_M * lat_rad
    return x, y


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract station water-level time series and interpolate unstructured triangular mesh "
            "to regular-grid GeoTIFF maps."
        )
    )
    parser.add_argument("netcdf_path", type=Path, help="Path to source NetCDF file.")
    parser.add_argument(
        "stations_path",
        type=Path,
        nargs="?",
        default=None,
        help="Optional path to station list file (e.g. station_list_MER.txt). Needed for time series output.",
    )
    parser.add_argument(
        "--station-offsets-file",
        type=Path,
        default=None,
        help="Optional path to station offsets file (e.g. msl_YYYYMMDD.dat). Missing file/rows default to zero offsets.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--only-maps",
        action="store_true",
        help="Generate only GeoTIFF maps.",
    )
    mode_group.add_argument(
        "--only-timeseries",
        action="store_true",
        help="Generate only station time series.",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default=None,
        help="Map resolution (e.g. 500m or 1km).",
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="Output directory path."
    )
    parser.add_argument(
        "--invalid-values",
        nargs="*",
        type=float,
        default=list(DEFAULT_INVALID_VALUES),
        help="Explicit invalid numeric values to be treated as NaN.",
    )
    parser.add_argument(
        "--max-time-steps",
        type=int,
        default=None,
        help="Optional cap on processed time steps (useful for fast tests).",
    )
    parser.add_argument(
        "--map-offset-hours",
        type=float,
        default=0.0,
        help="Ignore initial hours before producing maps.",
    )
    parser.add_argument(
        "--timeseries-offset-hours",
        type=float,
        default=0.0,
        help="Ignore initial hours before producing station time series.",
    )
    parser.add_argument(
        "--geotiff-field-offset",
        type=float,
        default=0.46,
        help="Constant value added to water level before GeoTIFF generation.",
    )
    parser.add_argument(
        "--verbose",
        type=parse_bool,
        default=True,
        help="Enable runtime logging (true/false). Default: true.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    output_mode: Literal["both", "maps", "timeseries"] = "both"
    if args.only_maps:
        output_mode = "maps"
    elif args.only_timeseries:
        output_mode = "timeseries"

    processor = WaterLevelProcessor(
        netcdf_path=args.netcdf_path,
        stations_path=args.stations_path,
        station_offsets_path=args.station_offsets_file,
        output_dir=args.output_dir,
        resolution=args.resolution,
        output_mode=output_mode,
        map_offset_hours=args.map_offset_hours,
        timeseries_offset_hours=args.timeseries_offset_hours,
        geotiff_field_offset=args.geotiff_field_offset,
        verbose=args.verbose,
        invalid_values=args.invalid_values,
        max_time_steps=args.max_time_steps,
    )
    processor.run()


if __name__ == "__main__":
    main()
