#!/usr/bin/env python3
# Determina l'ultima run disponibile a frontend per un modello, come massimo
# <run_date>.READY presente nella cartella esposta (esclusi i .geoserver.READY).
#
# Uso:
#   mer_latest_run.py <exposed_model_dir>
#
# Stampa su stdout:
#   {"latest_run": "YYYYMMDD"} oppure {"latest_run": null}
#
# Exit code:
#   0  ok
#   2  argomenti errati

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXIT_BAD_ARGS = 2

READY_RE = re.compile(r"^(\d{8})\.READY$")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        eprint(f"Usage: {Path(sys.argv[0]).name} <exposed_model_dir>")
        return EXIT_BAD_ARGS

    exposed_dir = Path(argv[0])

    latest: str | None = None
    if exposed_dir.is_dir():
        run_dates = []
        for entry in exposed_dir.iterdir():
            if not entry.is_file():
                continue
            match = READY_RE.match(entry.name)
            if match:
                run_dates.append(match.group(1))
        if run_dates:
            latest = max(run_dates)

    print(json.dumps({"latest_run": latest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
