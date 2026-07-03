#!/usr/bin/env python3
# Estrae l'archivio della run MER (ZIP o TAR) e riporta su stdout quali file
# sono presenti, in modo che NiFi instradi il flusso di conseguenza.
#
# NON pubblica i dati raw: la pubblicazione (con backup/swap) e' delegata a
# mer_publish_raw.py, cosi' baseline e re-send condividono lo stesso primitivo.
#
# Uso:
#   mer_stage_raw.py <archive_path> <extract_dir> <nc_stem>
#
# Stampa su stdout un JSON:
#   {"has_assim":bool,"has_noassim":bool,"has_msl":bool,
#    "assim_path":str,"noassim_path":str,"msl_path":str}
#
# Exit code:
#   0  ok (leggere il JSON su stdout)
#   2  argomenti errati
#   20 archivio mancante
#   21 formato archivio non supportato
#   31 HARD ERROR: mancano entrambi i NetCDF (solo msl o niente)

from __future__ import annotations

import json
import sys
import tarfile
import zipfile
from pathlib import Path

EXIT_BAD_ARGS = 2
EXIT_ARCHIVE_NOT_FOUND = 20
EXIT_UNSUPPORTED_ARCHIVE = 21
EXIT_NO_NETCDF = 31


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def extract_archive(archive: Path, extract_dir: Path) -> int:
    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as handle:
            handle.extractall(extract_dir)
        return 0

    if name.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        with tarfile.open(archive, "r:*") as handle:
            handle.extractall(extract_dir)
        return 0

    eprint(f"Unsupported archive format: {archive}")
    return EXIT_UNSUPPORTED_ARCHIVE


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        eprint(f"Usage: {Path(sys.argv[0]).name} <archive_path> <extract_dir> <nc_stem>")
        return EXIT_BAD_ARGS

    archive = Path(argv[0])
    extract_dir = Path(argv[1])
    nc_stem = argv[2]

    if not archive.is_file():
        eprint(f"Archive not found: {archive}")
        return EXIT_ARCHIVE_NOT_FOUND

    extract_dir.mkdir(parents=True, exist_ok=True)
    rc = extract_archive(archive, extract_dir)
    if rc != 0:
        return rc

    assim = extract_dir / f"{nc_stem}_assim.nc"
    noassim = extract_dir / f"{nc_stem}_noassim.nc"
    msl = extract_dir / f"{nc_stem}_msl.dat"

    status = {
        "has_assim": assim.is_file(),
        "has_noassim": noassim.is_file(),
        "has_msl": msl.is_file(),
        "assim_path": str(assim),
        "noassim_path": str(noassim),
        "msl_path": str(msl),
    }
    print(json.dumps(status))

    if not status["has_assim"] and not status["has_noassim"]:
        eprint("Hard error: no NetCDF found in archive (only msl or empty).")
        return EXIT_NO_NETCDF

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
