#!/usr/bin/env python3
# Gestione del lock per-run (concorrenza) delle run MER.
#
# Convenzione consigliata: UN solo file di lock deterministico per cartella run,
# <run_date>.lock, con dentro il timestamp di acquisizione. Rende banale il
# controllo di esistenza ed evita race grazie all'acquisizione atomica (O_EXCL).
#
# Uso:
#   mer_lock.py acquire <run_dir> <run_date>
#   mer_lock.py release <run_dir> <run_date>
#   mer_lock.py check   <run_dir> <run_date>
#
# Semantica pensata per il routing NiFi (niente busy-wait nello script):
#   - acquire: exit 0 sempre (salvo errori); stampa {"acquired": true|false}.
#              false => il lock era già presente: NiFi mette in penalty e ritenta.
#   - release: idempotente; stampa {"released": true|false}.
#   - check:   stampa {"locked": bool, "age_seconds": <float|null>}.
#
# Exit code:
#   0  ok (leggere il JSON su stdout)
#   2  argomenti errati
#   70 errore di I/O

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

EXIT_BAD_ARGS = 2
EXIT_IO_ERROR = 70


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def lock_path(run_dir: Path, run_date: str) -> Path:
    return run_dir / f"{run_date}.lock"


def cmd_acquire(run_dir: Path, run_date: str) -> int:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = lock_path(run_dir, run_date)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        print(json.dumps({"acquired": False, "lock_file": str(path)}))
        return 0
    except OSError as exc:
        eprint(f"Cannot create lock {path}: {exc}")
        return EXIT_IO_ERROR

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"{time.time()}\n")
    print(json.dumps({"acquired": True, "lock_file": str(path)}))
    return 0


def cmd_release(run_dir: Path, run_date: str) -> int:
    path = lock_path(run_dir, run_date)
    try:
        path.unlink()
        released = True
    except FileNotFoundError:
        released = False
    except OSError as exc:
        eprint(f"Cannot remove lock {path}: {exc}")
        return EXIT_IO_ERROR
    print(json.dumps({"released": released, "lock_file": str(path)}))
    return 0


def cmd_check(run_dir: Path, run_date: str) -> int:
    path = lock_path(run_dir, run_date)
    if not path.exists():
        print(json.dumps({"locked": False, "age_seconds": None, "lock_file": str(path)}))
        return 0
    age = None
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        pass
    print(json.dumps({"locked": True, "age_seconds": age, "lock_file": str(path)}))
    return 0


COMMANDS = {"acquire": cmd_acquire, "release": cmd_release, "check": cmd_check}


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] not in COMMANDS:
        eprint(f"Usage: {Path(sys.argv[0]).name} <acquire|release|check> <run_dir> <run_date>")
        return EXIT_BAD_ARGS

    command, run_dir_raw, run_date = argv
    return COMMANDS[command](Path(run_dir_raw), run_date)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
