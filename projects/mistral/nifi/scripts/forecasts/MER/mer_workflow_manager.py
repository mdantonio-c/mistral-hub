#!/usr/bin/env python3
"""Orchestrate MER workflow using in-process task functions."""

from __future__ import annotations

import faulthandler
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

EXIT_OK = 0
EXIT_INVALID_INPUT = 20
EXIT_NO_NETCDF = 31
EXIT_STAGE_FAILED = 21
EXIT_RAW_FAILED = 22
EXIT_PROCESSING_FAILED = 23
EXIT_WAIT_TIMEOUT = 24
EXIT_MARKER_FAILED = 25


ALLOWED_MODELS = {"BOLAM", "ICON", "ECMWF"}

MAPS_ROOT = Path("/opt/nifi/nfs/MER")
NETCDF_ROOT = Path("/opt/nifi/MER/netcdf_extraction")

MAPS_RESOLUTION = "500m"  # TODO: make this configurable if needed
MAPS_OFFSET = 0.46  # TODO: make this configurable if needed
MAPS_MAX_TIMESTEP = 72  # TODO: make this configurable if needed

CRASH_LOG_ENV = "MER_CRASH_LOG_PATH"
DEFAULT_CRASH_LOG = "/tmp/mer_workflow_manager_crash.log"

TASK_EXECUTION_MODE_ENV = "MER_TASK_EXECUTION_MODE"
TASK_EXECUTION_MODE_DEFAULT = "process"
TASK_EXECUTION_MODES = {"process", "serial", "thread"}
NETCDF_MAX_WORKERS_ENV = "MER_NETCDF_MAX_WORKERS"
NETCDF_MAX_WORKERS_DEFAULT = 2

_FAULT_LOG_HANDLE: Any | None = None


@dataclass
class Task:
    name: str
    fn: Callable[..., Any]
    kwargs: dict[str, Any]


def utc_timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def setup_crash_diagnostics() -> None:
    """Enable fault dumps for native crashes (e.g. exit 139)."""
    global _FAULT_LOG_HANDLE

    crash_log_path = Path(os.getenv(CRASH_LOG_ENV, DEFAULT_CRASH_LOG))
    try:
        crash_log_path.parent.mkdir(parents=True, exist_ok=True)
        _FAULT_LOG_HANDLE = crash_log_path.open("a", encoding="utf-8")
        _FAULT_LOG_HANDLE.write(
            f"\n=== run start {utc_timestamp()} pid={os.getpid()} ===\n"
        )
        _FAULT_LOG_HANDLE.flush()
        faulthandler.enable(file=_FAULT_LOG_HANDLE, all_threads=True)
    except Exception:  # noqa: BLE001
        # Fallback keeps diagnostics on stderr if file logging is unavailable.
        faulthandler.enable(all_threads=True)


class RunTrace:
    def __init__(
        self, run_id: str, model: str | None = None, run_date: str | None = None
    ) -> None:
        self.run_id = run_id
        self.model = model
        self.run_date = run_date
        self.performed_steps: list[str] = []
        self.step_results: list[dict[str, Any]] = []

    def set_context(self, run_id: str, model: str, run_date: str) -> None:
        self.run_id = run_id
        self.model = model
        self.run_date = run_date

    def add_step(
        self,
        step: str,
        status: str,
        message: str,
        *,
        error: str | None = None,
        rc: int | None = None,
        output: dict[str, Any] | None = None,
    ) -> None:
        if step not in self.performed_steps:
            self.performed_steps.append(step)

        entry: dict[str, Any] = {
            "step": step,
            "status": status,
            "message": message,
        }
        if error is not None:
            entry["error"] = error
        if rc is not None:
            entry["rc"] = rc
        if output:
            entry["output"] = output

        self.step_results.append(entry)

    def build_summary(
        self,
        *,
        status: str,
        exit_code: int,
        reason: str,
        degraded: bool,
        warnings: list[str],
        duration_ms: int,
        run_class: str | None,
        latest_run: str | None,
        outputs: dict[str, Any],
        marker_actions: list[str],
    ) -> dict[str, Any]:
        return {
            "event_type": "summary",
            "timestamp": utc_timestamp(),
            "run_id": self.run_id,
            "model": self.model,
            "run_date": self.run_date,
            "run_class": run_class,
            "latest_run": latest_run,
            "status": status,
            "exit_code": exit_code,
            "reason": reason,
            "degraded": degraded,
            "warnings": warnings,
            "duration_ms": duration_ms,
            "performed_steps": self.performed_steps,
            "step_results": self.step_results,
            "outputs": outputs,
            "marker_actions": marker_actions,
        }


def is_valid_zip_name(zip_name: str) -> tuple[str, str]:
    match = re.match(r"^([A-Za-z]+)_(\d{8})\.zip$", zip_name)
    if not match:
        raise ValueError(f"Invalid zip filename format: {zip_name}")

    model, run_date = match.groups()
    if model not in ALLOWED_MODELS:
        raise ValueError(f"Invalid model {model}, allowed: {sorted(ALLOWED_MODELS)}")

    datetime.strptime(run_date, "%Y%m%d")
    return model, run_date


def find_latest_run(exposed_dir: Path) -> str | None:
    latest: str | None = None
    ready_re = re.compile(r"^(\d{8})\.READY$")
    if exposed_dir.is_dir():
        run_dates = []
        for entry in exposed_dir.iterdir():
            if not entry.is_file():
                continue
            match = ready_re.match(entry.name)
            if match:
                run_dates.append(match.group(1))
        if run_dates:
            latest = max(run_dates)
    return latest


def classify_run(run_date: str, latest_run: str | None) -> str:
    if latest_run is None:
        return "new"
    if run_date > latest_run:
        return "new"
    if run_date == latest_run:
        return "current"
    return "past"


def clear_ready_markers(maps_model_dir: Path) -> None:
    if not maps_model_dir.is_dir():
        return

    for entry in maps_model_dir.iterdir():
        if not entry.is_file():
            continue
        if re.match(r"^\d{8}\.READY$", entry.name):
            entry.unlink(missing_ok=True)
        if re.match(r"^\d{8}\.GEOSERVER\.READY$", entry.name):
            entry.unlink(missing_ok=True)


def write_ready_marker(maps_model_dir: Path, run_date: str) -> None:
    maps_model_dir.mkdir(parents=True, exist_ok=True)
    marker = Path(maps_model_dir, f"{run_date}.READY")
    marker.touch(exist_ok=True)


def remove_geoserver_marker(maps_model_dir: Path, run_date: str) -> None:
    marker = maps_model_dir / f"{run_date}.GEOSERVER.READY"
    marker.unlink(missing_ok=True)


def build_timeseries_variants(
    run_class: str, has_assim: bool, has_noassim: bool
) -> list[str]:
    variants: list[str] = []
    if run_class == "past":
        return variants

    if has_assim:
        variants.append("assim")
    if has_noassim:
        variants.append("noassim")
    return variants


def publish_raw_files(
    extract_dir: Path, netcdf_model_dir: Path, nc_stem: str
) -> dict[str, str | bool]:
    netcdf_model_dir.mkdir(parents=True, exist_ok=True)

    for name in [f"{nc_stem}_assim.nc", f"{nc_stem}_noassim.nc"]:
        source_file = extract_dir / name
        if not source_file.is_file():
            # TODO this should not happens, but maybe this can raise a warning or something
            continue

        target_file = netcdf_model_dir / name
        # create a temp file to prevent the file to be read while is being copied, then replace the target file with the temp file
        temp_file = netcdf_model_dir / f".{name}.tmp"
        shutil.copyfile(source_file, temp_file)
        temp_file.replace(target_file)

    return {"published": True, "target_dir": str(netcdf_model_dir)}


def ensure_publish_directories(maps_model_dir: Path) -> None:
    """Create publish directories and raise a detailed error on failure."""
    publish_dirs = [maps_model_dir, maps_model_dir / "json", maps_model_dir / "wl"]
    for directory in publish_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            nearest_existing = directory
            while (
                not nearest_existing.exists()
                and nearest_existing != nearest_existing.parent
            ):
                nearest_existing = nearest_existing.parent
            raise RuntimeError(
                "Cannot create publish directory tree for "
                f"{directory}. Nearest existing ancestor: {nearest_existing} "
                f"(is_dir={nearest_existing.is_dir()}). Original error: {exc}"
            ) from exc


def launch_task(task: Task) -> dict[str, Any]:
    try:
        payload = task.fn(**task.kwargs)
        stdout = json.dumps(payload) if payload is not None else ""
        return {
            "task": task.name,
            "returncode": 0,
            "stdout": stdout,
            "stderr": "",
            "payload": payload,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "task": task.name,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }


def normalize_execution_mode(value: str | None) -> str:
    mode = (value or TASK_EXECUTION_MODE_DEFAULT).strip().lower()
    if mode not in TASK_EXECUTION_MODES:
        return TASK_EXECUTION_MODE_DEFAULT
    return mode


def is_netcdf_task(task: Task) -> bool:
    return task.name != "publish_raw"


def parse_netcdf_max_workers(value: str | None) -> int:
    if value is None:
        return NETCDF_MAX_WORKERS_DEFAULT
    try:
        parsed = int(value)
    except ValueError:
        return NETCDF_MAX_WORKERS_DEFAULT
    return max(1, parsed)


def with_elapsed(result: dict[str, Any], started: float) -> dict[str, Any]:
    result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return result


def launch_tasks_serial(tasks: list[Task]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for task in tasks:
        started = time.monotonic()
        result = launch_task(task)
        results.append(with_elapsed(result, started))
    return results


def launch_tasks_threaded(tasks: list[Task]) -> list[dict[str, Any]]:
    if not tasks:
        return []

    results: list[dict[str, Any]] = []
    starts: dict[Any, float] = {}
    with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as executor:
        futures = {}
        for task in tasks:
            future = executor.submit(launch_task, task)
            futures[future] = task
            starts[future] = time.monotonic()

        for future in as_completed(futures):
            started = starts.get(future, time.monotonic())
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                task = futures[future]
                result = {
                    "task": task.name,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": f"Thread execution failed: {exc}",
                }
            results.append(with_elapsed(result, started))

    return results


def launch_tasks_process(tasks: list[Task], max_workers: int) -> list[dict[str, Any]]:
    if not tasks:
        return []

    results: list[dict[str, Any]] = []
    starts: dict[Any, float] = {}
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for task in tasks:
            future = executor.submit(launch_task, task)
            futures[future] = task
            starts[future] = time.monotonic()

        for future in as_completed(futures):
            started = starts.get(future, time.monotonic())
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                task = futures[future]
                result = {
                    "task": task.name,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": f"Process execution failed: {exc}",
                }
            results.append(with_elapsed(result, started))

    return results


def execute_tasks(
    tasks: list[Task], requested_mode: str
) -> tuple[list[dict[str, Any]], str, str | None]:
    raw_tasks = [task for task in tasks if not is_netcdf_task(task)]
    netcdf_tasks = [task for task in tasks if is_netcdf_task(task)]

    results = launch_tasks_serial(raw_tasks)

    if not netcdf_tasks:
        return results, requested_mode, None

    if requested_mode == "serial":
        results.extend(launch_tasks_serial(netcdf_tasks))
        return results, requested_mode, None

    if requested_mode == "thread":
        results.extend(launch_tasks_threaded(netcdf_tasks))
        return results, requested_mode, None

    max_workers = min(
        parse_netcdf_max_workers(os.getenv(NETCDF_MAX_WORKERS_ENV)), len(netcdf_tasks)
    )
    try:
        results.extend(launch_tasks_process(netcdf_tasks, max_workers=max_workers))
        return results, requested_mode, None
    except Exception as exc:  # noqa: BLE001
        fallback_reason = f"process_mode_unavailable: {exc}"
        results.extend(launch_tasks_serial(netcdf_tasks))
        return results, "serial", fallback_reason


def summarize_task_output(task_result: dict[str, Any]) -> dict[str, Any]:
    task_name = task_result["task"]
    payload = task_result.get("payload")

    if not isinstance(payload, dict):
        return {}

    if task_name == "publish_raw":
        target_dir = payload.get("target_dir")
        return {"target_dir": target_dir} if target_dir else {}

    if task_name == "publish_maps":
        out: dict[str, Any] = {}
        for key in ("target_dir", "source_dir", "map_files"):
            value = payload.get(key)
            if value is not None:
                out[key] = value
        return out

    if task_name.startswith("publish_timeseries_"):
        out = {}
        target = payload.get("target")
        source = payload.get("source")
        variant = payload.get("variant")
        if variant is not None:
            out["variant"] = variant
        if target is not None:
            out["target"] = target
        if source is not None:
            out["source"] = source
        return out

    return {}


def collect_outputs(results: list[dict[str, Any]]) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    timeseries: dict[str, Any] = {}

    for result in results:
        if result.get("returncode") != 0:
            continue
        payload = result.get("payload")
        if not isinstance(payload, dict):
            continue

        task_name = result["task"]
        if task_name == "publish_raw":
            target_dir = payload.get("target_dir")
            if target_dir is not None:
                outputs["raw_dir"] = target_dir
        elif task_name == "publish_maps":
            maps_out: dict[str, Any] = {}
            for key in ("target_dir", "source_dir", "map_files"):
                value = payload.get(key)
                if value is not None:
                    maps_out[key] = value
            if maps_out:
                outputs["maps"] = maps_out
        elif task_name.startswith("publish_timeseries_"):
            variant = payload.get("variant")
            target = payload.get("target")
            if variant and target:
                timeseries[variant] = target

    if timeseries:
        outputs["timeseries"] = timeseries

    return outputs


def extend_unique_warnings(target: list[str], values: list[Any]) -> None:
    for value in values:
        if isinstance(value, str) and value and value not in target:
            target.append(value)


def build_task_list(
    model: str,
    run_date: str,
    nc_stem: str,
    run_class: str,
    has_assim: bool,
    has_noassim: bool,
    assim_path: Path,
    noassim_path: Path,
    msl_path: Path,
    extract_dir: Path,
    maps_model_dir: Path,
    netcdf_model_dir: Path,
    station_list: Path,
) -> list[Task]:
    from mer_publish_maps import publish_maps
    from mer_publish_timeseries import publish_timeseries

    tasks: list[Task] = [
        Task(
            name="publish_raw",
            fn=publish_raw_files,
            kwargs={
                "extract_dir": extract_dir,
                "netcdf_model_dir": netcdf_model_dir,
                "nc_stem": nc_stem,
            },
        )
    ]

    enable_maps = run_class in {"new", "current"} and has_assim
    variants = build_timeseries_variants(run_class, has_assim, has_noassim)

    if enable_maps:
        tasks.append(
            Task(
                name="publish_maps",
                fn=publish_maps,
                kwargs={
                    "model": model,
                    "run_date": run_date,
                    "assim_path": assim_path,
                    "maps_model_dir": maps_model_dir,
                    "wait_for_geoserver_ready": run_class == "current",
                    "wait_timeout_sec": 30,
                    "wait_interval_sec": 10,
                    "resolution": MAPS_RESOLUTION,
                    "geotiff_field_offset": MAPS_OFFSET,
                    "max_hours": MAPS_MAX_TIMESTEP,
                },
            )
        )

    for variant in variants:
        netcdf_path = assim_path if variant == "assim" else noassim_path
        tasks.append(
            Task(
                name=f"publish_timeseries_{variant}",
                fn=publish_timeseries,
                kwargs={
                    "model": model,
                    "run_date": run_date,
                    "variant": variant,
                    "netcdf_path": netcdf_path,
                    "msl_path": msl_path,
                    "station_list": station_list,
                    "maps_model_dir": maps_model_dir,
                    "max_hours": MAPS_MAX_TIMESTEP,
                },
            )
        )

    return tasks


def main(argv: list[str]) -> int:
    setup_crash_diagnostics()

    started = time.monotonic()
    run_id = f"UNKNOWN_UNKNOWN_{int(time.time())}"
    trace = RunTrace(run_id=run_id)

    final_status = "failure"
    exit_code = EXIT_INVALID_INPUT
    reason = "invalid_input"
    degraded = False
    run_class: str | None = None
    latest_run: str | None = None
    marker_actions: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []

    try:
        if len(argv) != 1:
            trace.add_step(
                "input_validation",
                "failure",
                "Invalid command input",
                error=f"Arguments sent: {sys.argv}",
            )
            exit_code = EXIT_INVALID_INPUT
            reason = "invalid_args"
            return exit_code

        s3_key = argv[0]
        zip_name = Path(s3_key).name

        try:
            model, run_date = is_valid_zip_name(zip_name)
        except ValueError as exc:
            trace.add_step(
                "input_validation", "failure", "Invalid ZIP filename", error=str(exc)
            )
            exit_code = EXIT_INVALID_INPUT
            reason = "invalid_zip_name"
            return exit_code

        run_id = f"{model}_{run_date}_{int(time.time())}"
        trace.set_context(run_id=run_id, model=model, run_date=run_date)
        trace.add_step("input_validation", "success", "Input validated")

        zip_bytes = sys.stdin.buffer.read()
        if not zip_bytes:
            trace.add_step(
                "input_validation", "failure", "Empty FlowFile content on stdin"
            )
            exit_code = EXIT_INVALID_INPUT
            reason = "empty_stdin"
            return exit_code

        nc_stem = f"{model}_{run_date}"
        maps_model_dir = Path(MAPS_ROOT, model)
        netcdf_model_dir = Path(NETCDF_ROOT, run_date, model)
        station_list = Path("/opt/nifi/MER/work_dir/station_list_MER.txt")

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            archive_path = Path(tmpdir, zip_name)
            extract_dir = Path(tmpdir, "staging")

            archive_path.write_bytes(zip_bytes)
            if not archive_path.is_file():
                trace.add_step(
                    "stage_archive",
                    "failure",
                    "Archive was not persisted",
                    error=str(archive_path),
                )
                exit_code = EXIT_INVALID_INPUT
                reason = "archive_not_found"
                return exit_code

            extract_dir.mkdir(parents=True, exist_ok=True)
            trace.add_step(
                "stage_archive",
                "success",
                "Archive persisted",
                output={"archive_path": str(archive_path)},
            )

            try:
                with zipfile.ZipFile(archive_path, "r") as z:
                    z.extractall(extract_dir)
            except zipfile.BadZipFile:
                trace.add_step(
                    "stage_archive",
                    "failure",
                    "Invalid ZIP file",
                    error=str(archive_path),
                )
                exit_code = EXIT_INVALID_INPUT
                reason = "invalid_zip"
                return exit_code

            assim_path = Path(extract_dir, f"{nc_stem}_assim.nc")
            noassim_path = Path(extract_dir, f"{nc_stem}_noassim.nc")
            msl_path = Path(extract_dir, f"{nc_stem}_msl.dat")

            has_assim = bool(assim_path.is_file())
            has_noassim = bool(noassim_path.is_file())
            has_msl = bool(msl_path.is_file())

            if not has_assim and not has_noassim:
                trace.add_step(
                    "stage_archive",
                    "failure",
                    "No NetCDF found in archive",
                    error="no NetCDF found in archive (only msl or empty)",
                )
                exit_code = EXIT_NO_NETCDF
                reason = "no_netcdf"
                return exit_code

            probe_warnings: list[str] = []
            if not has_assim and has_noassim:
                probe_warnings.append(
                    f"Missing assim NetCDF in archive: {assim_path.name}; processing noassim only"
                )
            if has_assim and not has_noassim:
                probe_warnings.append(
                    f"Missing noassim NetCDF in archive: {noassim_path.name}; processing assim only"
                )
            extend_unique_warnings(warnings, probe_warnings)

            probe_output: dict[str, Any] = {
                "has_assim": has_assim,
                "has_noassim": has_noassim,
                "has_msl": has_msl,
            }
            if probe_warnings:
                probe_output["warnings"] = probe_warnings

            trace.add_step(
                "probe_archive",
                "success",
                "Archive staged and probed",
                output=probe_output,
            )

            try:
                ensure_publish_directories(maps_model_dir)
                trace.add_step(
                    "prepare_publish_dirs",
                    "success",
                    "Publish directories are ready",
                    output={"maps_model_dir": str(maps_model_dir)},
                )
            except Exception as exc:  # noqa: BLE001
                trace.add_step(
                    "prepare_publish_dirs",
                    "failure",
                    "Publish directory preflight failed",
                    error=str(exc),
                )
                exit_code = EXIT_PROCESSING_FAILED
                reason = "publish_directory_preflight_failed"
                return exit_code

            latest_run = find_latest_run(maps_model_dir)
            run_class = classify_run(run_date, latest_run)
            trace.add_step(
                "classify_run",
                "success",
                "Run class computed",
                output={"latest_run": latest_run, "run_class": run_class},
            )

            tasks = build_task_list(
                model=model,
                run_date=run_date,
                nc_stem=nc_stem,
                run_class=run_class,
                has_assim=has_assim,
                has_noassim=has_noassim,
                assim_path=assim_path,
                noassim_path=noassim_path,
                msl_path=msl_path,
                extract_dir=extract_dir,
                maps_model_dir=maps_model_dir,
                netcdf_model_dir=netcdf_model_dir,
                station_list=station_list,
            )

            trace.add_step(
                "plan_tasks",
                "success",
                "Execution plan created",
                output={"tasks": [task.name for task in tasks], "run_class": run_class},
            )

            requested_mode = normalize_execution_mode(
                os.getenv(TASK_EXECUTION_MODE_ENV)
            )
            trace.add_step(
                "execute_tasks",
                "success",
                "Running tasks",
                output={"task_count": len(tasks), "requested_mode": requested_mode},
            )

            run_results, effective_mode, fallback_reason = execute_tasks(
                tasks, requested_mode
            )
            results.extend(run_results)

            if fallback_reason is not None:
                trace.add_step(
                    "execute_tasks",
                    "failure",
                    "Process mode failed, switched to serial",
                    error=fallback_reason,
                    output={
                        "requested_mode": requested_mode,
                        "effective_mode": effective_mode,
                    },
                )
            elif effective_mode != requested_mode:
                trace.add_step(
                    "execute_tasks",
                    "success",
                    "Execution mode adjusted",
                    output={
                        "requested_mode": requested_mode,
                        "effective_mode": effective_mode,
                    },
                )

            for result in run_results:
                task_output = summarize_task_output(result)
                elapsed_ms = result.get("elapsed_ms")
                if elapsed_ms is not None:
                    task_output["elapsed_ms"] = elapsed_ms

                payload = result.get("payload")
                if isinstance(payload, dict):
                    payload_warnings = payload.get("warnings")
                    if isinstance(payload_warnings, list):
                        extend_unique_warnings(warnings, payload_warnings)
                        if payload_warnings:
                            task_output["warnings"] = payload_warnings

                trace.add_step(
                    result["task"],
                    "success" if result["returncode"] == 0 else "failure",
                    f"Task {result['task']} completed",
                    error=result.get("stderr") or None,
                    rc=result["returncode"],
                    output=task_output,
                )

            result_map = {item["task"]: item for item in results}
            raw_ok = result_map.get("publish_raw", {"returncode": 1})["returncode"] == 0
            maps_ok = (
                result_map.get("publish_maps", {"returncode": 0})["returncode"] == 0
            )
            ts_keys = [
                key for key in result_map if key.startswith("publish_timeseries_")
            ]
            ts_ok = (
                all(result_map[key]["returncode"] == 0 for key in ts_keys)
                if ts_keys
                else True
            )

            final_ok = True
            degraded = False
            reason = "ok"

            if not raw_ok:
                final_ok = False
                reason = "raw_publish_failed"
            elif (
                not maps_ok and not ts_ok and ("publish_maps" in result_map or ts_keys)
            ):
                final_ok = False
                reason = "maps_and_timeseries_failed"
            elif not maps_ok or not ts_ok:
                degraded = True
                reason = "partial_success"

            try:
                if final_ok:
                    if run_class == "new" and has_assim and maps_ok:
                        clear_ready_markers(maps_model_dir)
                        write_ready_marker(maps_model_dir, run_date)
                        marker_actions.append("baseline_ready_written")

                    if run_class == "current" and has_assim and maps_ok:
                        remove_geoserver_marker(maps_model_dir, run_date)
                        marker_actions.append("caseB_geoserver_marker_removed")
            except Exception as exc:  # noqa: BLE001
                trace.add_step(
                    "finalize_markers",
                    "failure",
                    "Marker management failed",
                    error=str(exc),
                )
                exit_code = EXIT_MARKER_FAILED
                reason = "marker_management_failed"
                final_status = "failure"
                return exit_code

            if marker_actions:
                trace.add_step(
                    "finalize_markers",
                    "success",
                    "Markers finalized",
                    output={"actions": marker_actions},
                )
            else:
                trace.add_step(
                    "finalize_markers",
                    "success",
                    "No marker changes required",
                    output={"run_class": run_class},
                )

            final_status = "success" if final_ok else "failure"
            exit_code = (
                EXIT_OK
                if final_ok
                else (EXIT_RAW_FAILED if not raw_ok else EXIT_PROCESSING_FAILED)
            )
            return exit_code
    except Exception as exc:  # noqa: BLE001
        trace.add_step(
            "unexpected_exception", "failure", "Unhandled exception", error=str(exc)
        )
        final_status = "failure"
        exit_code = EXIT_PROCESSING_FAILED
        reason = "unexpected_exception"
    finally:
        summary = trace.build_summary(
            status=final_status,
            exit_code=exit_code,
            reason=reason,
            degraded=degraded,
            warnings=warnings,
            duration_ms=int((time.monotonic() - started) * 1000),
            run_class=run_class,
            latest_run=latest_run,
            outputs=collect_outputs(results),
            marker_actions=marker_actions,
        )
        print(json.dumps(summary), flush=True)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
