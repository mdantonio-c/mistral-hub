#!/usr/bin/env python3
"""Cleanup MER published outputs for NiFi.

Scope:
- /opt/nifi/nfs/MER/<MODEL>/json
- /opt/nifi/nfs/MER/<MODEL>/wl
- MER crash log file

Retention policy:
- Consistent mtime-based retention for JSON and WL managed files.
- JSON files for current READY run are always protected.
- WL aggressive cleanup of canonical managed files is enabled only when
  <run_date>.READY and <run_date>.GEOSERVER.READY both exist for the same run.
  Otherwise WL cleanup is conservative and removes only stale temp artifacts.

Output:
- Single-line JSON summary on stdout (NiFi-friendly).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mer_workflow_manager import CRASH_LOG_ENV
from mer_workflow_manager import DEFAULT_CRASH_LOG as WORKFLOW_DEFAULT_CRASH_LOG
from mer_workflow_manager import MAPS_MAX_TIMESTEP, MAPS_ROOT

EXIT_OK = 0
EXIT_BAD_ARGS = 2
EXIT_RUNTIME_ERROR = 1
EXIT_UNSAFE_ROOT = 90

EXPECTED_MAPS_ROOT = MAPS_ROOT
DEFAULT_CRASH_LOG = Path(WORKFLOW_DEFAULT_CRASH_LOG)
DEFAULT_MAX_TIMESTEP_HOURS = MAPS_MAX_TIMESTEP
MAX_TIMESTEP_HOURS_ENV = "MER_MAPS_MAX_TIMESTEP_HOURS"

READY_RE = re.compile(r"^(\d{8})\.READY$")
GEOSERVER_READY_RE = re.compile(r"^(\d{8})\.GEOSERVER\.READY$")
RUN_DATE_RE = re.compile(r"^\d{8}$")
JSON_FILE_RE = re.compile(
    r"^[A-Za-z]+_(\d{8})_[A-Za-z0-9_-]+_station_timeseries\.json$"
)
WL_TIF_RE = re.compile(r"^(\d{8})T(\d{6})\.tif$")
WL_TMP_FILE_RE = re.compile(r"^\..+\.tmp$")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def parse_args(argv: list[str]) -> tuple[int, bool] | None:
    if len(argv) not in (1, 2):
        return None

    try:
        retention_days = int(argv[0])
    except ValueError:
        return None

    if retention_days < 0:
        return None

    dry_run = False
    if len(argv) == 2:
        if argv[1] != "--dry-run":
            return None
        dry_run = True

    return retention_days, dry_run


def parse_run_date(name: str) -> datetime | None:
    if not RUN_DATE_RE.match(name):
        return None
    try:
        return datetime.strptime(name, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_wl_timestamp(name: str) -> datetime | None:
    match = WL_TIF_RE.match(name)
    if not match:
        return None
    try:
        return datetime.strptime(
            match.group(1) + match.group(2), "%Y%m%d%H%M%S"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_old(path: Path, cutoff_epoch: float) -> bool:
    return path.stat().st_mtime < cutoff_epoch


def delete_file(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.unlink(missing_ok=True)


def delete_tree(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    shutil.rmtree(path, ignore_errors=True)


def find_current_run(model_dir: Path) -> str | None:
    run_dates: list[str] = []
    for entry in model_dir.iterdir():
        if not entry.is_file():
            continue
        match = READY_RE.match(entry.name)
        if match:
            run_dates.append(match.group(1))
    return max(run_dates) if run_dates else None


def has_matching_geoserver_ready(model_dir: Path, run_date: str | None) -> bool:
    if run_date is None:
        return False
    marker = model_dir / f"{run_date}.GEOSERVER.READY"
    if marker.is_file():
        return True

    # Fallback scan protects against odd symlink/fs behavior.
    for entry in model_dir.iterdir():
        if not entry.is_file():
            continue
        match = GEOSERVER_READY_RE.match(entry.name)
        if match and match.group(1) == run_date:
            return True
    return False


def parse_max_timestep_hours(value: str | None) -> int:
    if value is None:
        return DEFAULT_MAX_TIMESTEP_HOURS
    try:
        parsed = int(value)
    except ValueError:
        return DEFAULT_MAX_TIMESTEP_HOURS
    return max(1, parsed)


def new_bucket() -> dict[str, int]:
    return {
        "scanned": 0,
        "deleted": 0,
        "kept_recent": 0,
        "kept_protected": 0,
        "kept_non_managed": 0,
        "errors": 0,
    }


def cleanup_json_dir(
    json_dir: Path,
    cutoff_epoch: float,
    current_run: str | None,
    dry_run: bool,
    errors: list[str],
) -> dict[str, int]:
    bucket = new_bucket()

    if not json_dir.is_dir():
        return bucket

    for entry in json_dir.iterdir():
        if not entry.is_file():
            bucket["kept_non_managed"] += 1
            continue

        match = JSON_FILE_RE.match(entry.name)
        if not match:
            bucket["kept_non_managed"] += 1
            continue

        bucket["scanned"] += 1

        belongs_current = current_run is not None and match.group(1) == current_run
        if belongs_current:
            bucket["kept_protected"] += 1
            continue

        try:
            if is_old(entry, cutoff_epoch):
                delete_file(entry, dry_run=dry_run)
                bucket["deleted"] += 1
            else:
                bucket["kept_recent"] += 1
        except Exception as exc:  # noqa: BLE001
            bucket["errors"] += 1
            errors.append(f"json_cleanup_failed:{entry}:{exc}")

    return bucket


def cleanup_wl_temp_artifacts(
    wl_dir: Path, cutoff_epoch: float, dry_run: bool, errors: list[str]
) -> dict[str, int]:
    bucket = new_bucket()

    if not wl_dir.is_dir():
        return bucket

    for entry in wl_dir.iterdir():
        is_tmp_file = entry.is_file() and WL_TMP_FILE_RE.match(entry.name)
        is_backup_dir = entry.is_dir() and entry.name == ".maps_publish_bak"
        if not (is_tmp_file or is_backup_dir):
            continue

        bucket["scanned"] += 1
        try:
            if is_old(entry, cutoff_epoch):
                if entry.is_dir():
                    delete_tree(entry, dry_run=dry_run)
                else:
                    delete_file(entry, dry_run=dry_run)
                bucket["deleted"] += 1
            else:
                bucket["kept_recent"] += 1
        except Exception as exc:  # noqa: BLE001
            bucket["errors"] += 1
            errors.append(f"wl_temp_cleanup_failed:{entry}:{exc}")

    return bucket


def is_current_run_wl_file(
    file_name: str,
    current_run_start: datetime | None,
    current_run_end: datetime | None,
) -> bool:
    if current_run_start is None or current_run_end is None:
        return False

    file_ts = parse_wl_timestamp(file_name)
    if file_ts is None:
        return False

    return current_run_start <= file_ts <= current_run_end


def cleanup_wl_canonical(
    wl_dir: Path,
    cutoff_epoch: float,
    current_run_start: datetime | None,
    current_run_end: datetime | None,
    aggressive_mode: bool,
    dry_run: bool,
    errors: list[str],
) -> dict[str, int]:
    bucket = new_bucket()

    if not wl_dir.is_dir():
        return bucket

    for entry in wl_dir.iterdir():
        if not entry.is_file():
            bucket["kept_non_managed"] += 1
            continue

        is_canonical = entry.name == "timeregex.properties" or WL_TIF_RE.match(
            entry.name
        )
        if not is_canonical:
            bucket["kept_non_managed"] += 1
            continue

        bucket["scanned"] += 1

        if is_current_run_wl_file(entry.name, current_run_start, current_run_end):
            bucket["kept_protected"] += 1
            continue

        try:
            if not is_old(entry, cutoff_epoch):
                bucket["kept_recent"] += 1
                continue

            if not aggressive_mode:
                bucket["kept_recent"] += 1
                continue

            delete_file(entry, dry_run=dry_run)
            bucket["deleted"] += 1
        except Exception as exc:  # noqa: BLE001
            bucket["errors"] += 1
            errors.append(f"wl_canonical_cleanup_failed:{entry}:{exc}")

    return bucket


def cleanup_crash_log(
    cutoff_epoch: float, dry_run: bool, errors: list[str]
) -> dict[str, Any]:
    crash_log = Path(os.getenv(CRASH_LOG_ENV, str(DEFAULT_CRASH_LOG)))
    result: dict[str, Any] = {
        "path": str(crash_log),
        "exists": crash_log.exists(),
        "deleted": False,
        "kept_recent": False,
        "error": None,
    }

    if not crash_log.exists():
        return result

    if not crash_log.is_file():
        result["error"] = "crash_log_path_not_file"
        errors.append(f"crash_log_not_file:{crash_log}")
        return result

    try:
        if is_old(crash_log, cutoff_epoch):
            delete_file(crash_log, dry_run=dry_run)
            result["deleted"] = True
        else:
            result["kept_recent"] = True
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        errors.append(f"crash_log_cleanup_failed:{crash_log}:{exc}")

    return result


def build_totals(models_summary: dict[str, Any]) -> dict[str, int]:
    totals = {
        "json_deleted": 0,
        "wl_canonical_deleted": 0,
        "wl_temp_deleted": 0,
        "errors": 0,
    }
    for model_data in models_summary.values():
        totals["json_deleted"] += model_data["json"]["deleted"]
        totals["wl_canonical_deleted"] += model_data["wl_canonical"]["deleted"]
        totals["wl_temp_deleted"] += model_data["wl_temp"]["deleted"]
        totals["errors"] += (
            model_data["json"]["errors"]
            + model_data["wl_canonical"]["errors"]
            + model_data["wl_temp"]["errors"]
        )
    return totals


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args is None:
        eprint("Usage: " f"{Path(sys.argv[0]).name} <retention_days> [--dry-run]")
        return EXIT_BAD_ARGS

    retention_days, dry_run = args
    root = EXPECTED_MAPS_ROOT

    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_epoch = cutoff_dt.timestamp()

    errors: list[str] = []
    max_timestep_hours = parse_max_timestep_hours(os.getenv(MAX_TIMESTEP_HOURS_ENV))

    summary: dict[str, Any] = {
        "event_type": "mer_daily_cleanup_summary",
        "timestamp": now_utc_iso(),
        "root": str(root),
        "retention_days": retention_days,
        "dry_run": dry_run,
        "cutoff": cutoff_dt.isoformat(timespec="seconds"),
        "models": {},
        "crash_log": {},
        "totals": {},
        "status": "success",
        "errors": errors,
    }

    if not root.is_dir():
        summary["status"] = "no_root"
        summary["crash_log"] = cleanup_crash_log(cutoff_epoch, dry_run, errors)
        summary["totals"] = {
            "json_deleted": 0,
            "wl_canonical_deleted": 0,
            "wl_temp_deleted": 0,
            "errors": len(errors),
        }
        print(json.dumps(summary), flush=True)
        return EXIT_OK if not errors else EXIT_RUNTIME_ERROR

    for model_dir in sorted(root.iterdir()):
        if not model_dir.is_dir():
            continue

        current_run = find_current_run(model_dir)
        geoserver_ready = has_matching_geoserver_ready(model_dir, current_run)
        aggressive_wl = current_run is not None and geoserver_ready

        current_run_start = parse_run_date(current_run) if current_run else None
        current_run_end = (
            current_run_start + timedelta(hours=max_timestep_hours)
            if current_run_start is not None
            else None
        )

        json_dir = model_dir / "json"
        wl_dir = model_dir / "wl"

        json_bucket = cleanup_json_dir(
            json_dir=json_dir,
            cutoff_epoch=cutoff_epoch,
            current_run=current_run,
            dry_run=dry_run,
            errors=errors,
        )
        wl_temp_bucket = cleanup_wl_temp_artifacts(
            wl_dir=wl_dir,
            cutoff_epoch=cutoff_epoch,
            dry_run=dry_run,
            errors=errors,
        )
        wl_canonical_bucket = cleanup_wl_canonical(
            wl_dir=wl_dir,
            cutoff_epoch=cutoff_epoch,
            current_run_start=current_run_start,
            current_run_end=current_run_end,
            aggressive_mode=aggressive_wl,
            dry_run=dry_run,
            errors=errors,
        )

        summary["models"][model_dir.name] = {
            "current_run": current_run,
            "geoserver_ready_for_current": geoserver_ready,
            "wl_mode": "aggressive" if aggressive_wl else "conservative",
            "json": json_bucket,
            "wl_temp": wl_temp_bucket,
            "wl_canonical": wl_canonical_bucket,
        }

    summary["crash_log"] = cleanup_crash_log(cutoff_epoch, dry_run, errors)
    summary["totals"] = build_totals(summary["models"])
    if summary["crash_log"].get("error"):
        summary["totals"]["errors"] += 1

    if errors:
        summary["status"] = "partial_failure"

    print(json.dumps(summary), flush=True)
    return EXIT_OK if not errors else EXIT_RUNTIME_ERROR


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
