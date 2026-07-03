#!/usr/bin/env python3
# Mini-flow giornaliero: elimina le cartelle di lavoro delle run MER piu'
# vecchie di <keep_days> giorni, lasciando quindi lo zip di backup solo per un
# breve periodo.
#
# Struttura attesa: <raw_files_root>/<MODEL>/<YYYYMMDD>/...
#
# Uso:
#   mer_daily_cleanup.py <raw_files_root> <keep_days>
#
# Esempio:
#   mer_daily_cleanup.py /opt/nifi/MER/work_dir/raw_files 3
#
# Exit code:
#   0  ok
#   2  argomenti errati
#   90 root fuori dal path atteso

from __future__ import annotations

import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

EXIT_BAD_ARGS = 2
EXIT_UNSAFE_ROOT = 90

EXPECTED_ROOT = Path("/opt/nifi/MER/work_dir/raw_files")
RUN_DATE_RE = re.compile(r"^\d{8}$")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def parse_run_date(name: str) -> date | None:
    if not RUN_DATE_RE.match(name):
        return None
    try:
        return datetime.strptime(name, "%Y%m%d").date()
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        eprint(f"Usage: {Path(sys.argv[0]).name} <raw_files_root> <keep_days>")
        return EXIT_BAD_ARGS

    root = Path(argv[0])
    try:
        keep_days = int(argv[1])
    except ValueError:
        eprint(f"keep_days must be an integer: {argv[1]}")
        return EXIT_BAD_ARGS

    if keep_days < 0 or root.resolve() != EXPECTED_ROOT.resolve():
        eprint(f"Refusing cleanup: root={root} keep_days={keep_days}")
        return EXIT_UNSAFE_ROOT

    if not root.is_dir():
        print(f"Nothing to clean, root does not exist: {root}")
        return 0

    cutoff = date.today() - timedelta(days=keep_days)
    removed = 0

    for model_dir in root.iterdir():
        if not model_dir.is_dir():
            continue
        for run_dir in model_dir.iterdir():
            if not run_dir.is_dir():
                continue
            run_date = parse_run_date(run_dir.name)
            if run_date is None:
                continue
            if run_date < cutoff:
                shutil.rmtree(run_dir, ignore_errors=True)
                removed += 1
                print(f"Removed old run dir: {run_dir}")

    print(f"Cleanup done: removed {removed} run dir(s) older than {keep_days} day(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
