#!/usr/bin/env python3
# Finalizza una run MER: gestisce i marker READY nella cartella esposta e
# rilascia il lock della run. NON elimina piu' la work dir: la pulizia e'
# demandata al mini-flow giornaliero (mer_daily_cleanup.py), cosi' lo zip
# resta come backup.
#
# Modalita':
#   baseline  run nuova piu' recente: rimuove i marker *.READY / *.geoserver.READY
#             della run precedente e scrive <run>.READY. Rilascia il lock.
#   caseB     re-send della run corrente: elimina <run>.geoserver.READY per
#             forzare la re-ingestion di GeoServer (mantiene <run>.READY).
#             Rilascia il lock.
#   caseA     re-send di una run passata: rilascia solo il lock.
#   noassim   pubblicato solo noassim (nessuna mappa): nessun READY, rilascia
#             solo il lock.
#
# Uso:
#   mer_finalize.py --mode {baseline,caseB,caseA,noassim} \
#       --run <YYYYMMDD> --lock-dir <model_dir> --lock-key <model> \
#       [--exposed <exposed_model_dir>]
#
# Il lock e' per-modello: viene rilasciato <lock-dir>/<lock-key>.lock.
#
# Exit code:
#   0  ok
#   2  argomenti errati
#   80 path esposto/lock fuori dai path attesi

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_BAD_ARGS = 2
EXIT_UNSAFE_PATH = 80

EXPOSED_ROOT = Path("/opt/nifi/nfs/SHYFEM")
LOCK_ROOT = Path("/opt/nifi/MER/work_dir/raw_files")

READY_RE = re.compile(r"^\d{8}\.READY$")
GEOSERVER_READY_RE = re.compile(r"^\d{8}\.geoserver\.READY$")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def write_ready(exposed_dir: Path, run: str) -> None:
    exposed_dir.mkdir(parents=True, exist_ok=True)
    ready_file = exposed_dir / f"{run}.READY"
    tmp = exposed_dir / f"{run}.READY.tmp"
    tmp.write_text("", encoding="utf-8")
    tmp.replace(ready_file)
    print(f"Wrote ready file: {ready_file}")


def clear_previous_ready_markers(exposed_dir: Path) -> None:
    if not exposed_dir.is_dir():
        return
    for entry in exposed_dir.iterdir():
        if entry.is_file() and (READY_RE.match(entry.name) or GEOSERVER_READY_RE.match(entry.name)):
            entry.unlink(missing_ok=True)
            print(f"Removed previous marker: {entry}")


def delete_geoserver_ready(exposed_dir: Path, run: str) -> None:
    marker = exposed_dir / f"{run}.geoserver.READY"
    if marker.exists():
        marker.unlink(missing_ok=True)
        print(f"Removed geoserver ready to trigger re-ingestion: {marker}")


def release_lock(lock_dir: Path, lock_key: str) -> None:
    lock_file = lock_dir / f"{lock_key}.lock"
    if lock_file.exists():
        lock_file.unlink(missing_ok=True)
        print(f"Released lock: {lock_file}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["baseline", "caseB", "caseA", "noassim"])
    parser.add_argument("--run", required=True)
    parser.add_argument("--lock-dir", required=True, type=Path)
    parser.add_argument("--lock-key", default=None)
    parser.add_argument("--exposed", type=Path, default=None)
    args = parser.parse_args(argv)

    if len(args.run) != 8 or not args.run.isdigit():
        eprint(f"Invalid run, expected YYYYMMDD: {args.run}")
        return EXIT_BAD_ARGS

    if not is_under(args.lock_dir, LOCK_ROOT):
        eprint(f"Unsafe lock dir: {args.lock_dir}")
        return EXIT_UNSAFE_PATH

    if args.mode in ("baseline", "caseB"):
        if args.exposed is None:
            eprint(f"--exposed is required for mode {args.mode}")
            return EXIT_BAD_ARGS
        if not is_under(args.exposed, EXPOSED_ROOT):
            eprint(f"Unsafe exposed dir: {args.exposed}")
            return EXIT_UNSAFE_PATH

    if args.mode == "baseline":
        clear_previous_ready_markers(args.exposed)
        write_ready(args.exposed, args.run)
    elif args.mode == "caseB":
        delete_geoserver_ready(args.exposed, args.run)

    # Il lock si rilascia sempre alla fine, in ogni modalita'.
    release_lock(args.lock_dir, args.lock_key or args.run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
