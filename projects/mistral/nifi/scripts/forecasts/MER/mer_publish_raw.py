#!/usr/bin/env python3
# Pubblica i NetCDF grezzi nella cartella di distribuzione esposta a nginx,
# in modo TRANSAZIONALE con backup/swap:
#   1. i file di destinazione gia' presenti (corrispondenti ai nuovi) vengono
#      spostati in una cartella di backup non esposta;
#   2. i nuovi file vengono copiati (atomico: .tmp + replace);
#   3. se tutto va a buon fine il backup viene eliminato;
#   4. in caso di errore i file originali vengono ripristinati dal backup.
#
# Uso:
#   mer_publish_raw.py <src_dir> <dest_dir> <bkp_dir> <file1> [<file2> ...]
#
# Esempio (solo i file effettivamente presenti vanno passati):
#   mer_publish_raw.py \
#     /opt/nifi/MER/work_dir/raw_files/BOLAM/20230409 \
#     /opt/nifi/MER/netcdf_extraction/20230409/BOLAM \
#     /opt/nifi/MER/temp_bkp/netcdf_extraction/20230409/BOLAM \
#     BOLAM_20230409_assim.nc BOLAM_20230409_noassim.nc
#
# Exit code:
#   0  ok
#   2  argomenti errati
#   72 errore di pubblicazione (ripristino tentato dal backup)
#   73 destinazione/backup fuori dai path attesi

from __future__ import annotations

import shutil
import sys
from pathlib import Path

EXIT_BAD_ARGS = 2
EXIT_PUBLISH_ERROR = 72
EXIT_UNSAFE_PATH = 73

DEST_ROOT = Path("/opt/nifi/MER/netcdf_extraction")
BKP_ROOT = Path("/opt/nifi/MER/temp_bkp")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        eprint(f"Usage: {Path(sys.argv[0]).name} <src_dir> <dest_dir> <bkp_dir> <file1> [<file2> ...]")
        return EXIT_BAD_ARGS

    src_dir = Path(argv[0])
    dest_dir = Path(argv[1])
    bkp_dir = Path(argv[2])
    names = argv[3:]

    if not is_under(dest_dir, DEST_ROOT) or not is_under(bkp_dir, BKP_ROOT):
        eprint(f"Unsafe dest/bkp path: dest={dest_dir} bkp={bkp_dir}")
        return EXIT_UNSAFE_PATH

    dest_dir.mkdir(parents=True, exist_ok=True)

    moved_to_bkp: list[tuple[Path, Path]] = []
    copied: list[Path] = []

    try:
        for name in names:
            src_file = src_dir / name
            if not src_file.is_file():
                # I file assenti non sono un errore: pubblichiamo solo i presenti.
                continue

            dest_file = dest_dir / name
            if dest_file.exists():
                bkp_dir.mkdir(parents=True, exist_ok=True)
                bkp_file = bkp_dir / name
                shutil.move(str(dest_file), str(bkp_file))
                moved_to_bkp.append((dest_file, bkp_file))

            tmp_file = dest_dir / f".{name}.tmp"
            shutil.copyfile(src_file, tmp_file)
            tmp_file.replace(dest_file)
            copied.append(dest_file)
    except Exception as exc:  # noqa: BLE001 - rollback e exit code pulito per NiFi
        eprint(f"Publish failed, rolling back: {exc}")
        for dest_file in copied:
            dest_file.unlink(missing_ok=True)
        for dest_file, bkp_file in moved_to_bkp:
            shutil.move(str(bkp_file), str(dest_file))
        return EXIT_PUBLISH_ERROR

    # Successo: rimuovi il backup.
    if bkp_dir.exists():
        shutil.rmtree(bkp_dir, ignore_errors=True)

    print(f"Published {len(copied)} raw file(s) into {dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
