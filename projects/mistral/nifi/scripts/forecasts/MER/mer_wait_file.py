#!/usr/bin/env python3
# Probe NON bloccante dell'esistenza di un file: serve al pattern di attesa
# NiFi (penalty-loop). Lo script NON attende: fa solo un check istantaneo e
# lascia a NiFi il compito di ritentare con penalty.
#
# Uso:
#   mer_wait_file.py <path>
#
# Stampa su stdout:
#   {"exists": true|false, "path": "<path>"}
#
# Exit code:
#   0  ok
#   2  argomenti errati

from __future__ import annotations

import json
import sys
from pathlib import Path

EXIT_BAD_ARGS = 2


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        eprint(f"Usage: {Path(sys.argv[0]).name} <path>")
        return EXIT_BAD_ARGS

    target = Path(argv[0])
    print(json.dumps({"exists": target.exists(), "path": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
