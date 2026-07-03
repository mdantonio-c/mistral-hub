#!/usr/bin/env python3
# Riorganizza la staging dir prodotta da water_level_processor.py e pubblica
# gli output (geotiff/ e json/) nella cartella esposta a frontend, in modo
# TRANSAZIONALE con backup/swap.
#
# Riorganizzazione staging:
#   - la cartella geotiff_<stem>_<label>/ viene rinominata in "geotiff"
#   - i file station_timeseries_*.json vengono spostati in "json/"
#
# Swap verso la cartella esposta (per ciascuna tra geotiff/ e json/ presente
# in staging):
#   1. l'eventuale versione vecchia in esposto viene spostata nel backup
#   2. la nuova versione viene spostata da staging a esposto
#   3. se tutto ok il backup viene eliminato, altrimenti si ripristina
#
# Uso:
#   mer_publish_outputs.py <staging_dir> <exposed_model_dir> <bkp_dir>
#
# Exit code:
#   0  ok
#   2  argomenti errati
#   74 errore di pubblicazione (ripristino tentato dal backup)
#   75 esposto/backup fuori dai path attesi
#   76 staging senza output pubblicabili

from __future__ import annotations

import shutil
import sys
from pathlib import Path

EXIT_BAD_ARGS = 2
EXIT_PUBLISH_ERROR = 74
EXIT_UNSAFE_PATH = 75
EXIT_NOTHING_TO_PUBLISH = 76

EXPOSED_ROOT = Path("/opt/nifi/nfs/SHYFEM")
BKP_ROOT = Path("/opt/nifi/MER/temp_bkp")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def reorganize_staging(staging_dir: Path) -> list[str]:
    """Normalizza staging in geotiff/ e json/. Ritorna i nomi pubblicabili."""
    publishable: list[str] = []

    geotiff_dirs = sorted(
        d for d in staging_dir.iterdir() if d.is_dir() and d.name.startswith("geotiff_")
    )
    target_geotiff = staging_dir / "geotiff"
    if geotiff_dirs and not target_geotiff.exists():
        # Un'unica risoluzione => una sola cartella geotiff_*.
        geotiff_dirs[0].rename(target_geotiff)
        for extra in geotiff_dirs[1:]:
            for item in extra.iterdir():
                shutil.move(str(item), str(target_geotiff / item.name))
            shutil.rmtree(extra, ignore_errors=True)
    if target_geotiff.is_dir():
        publishable.append("geotiff")

    json_files = sorted(staging_dir.glob("station_timeseries_*.json"))
    if json_files:
        json_dir = staging_dir / "json"
        json_dir.mkdir(exist_ok=True)
        for json_file in json_files:
            shutil.move(str(json_file), str(json_dir / json_file.name))
    if (staging_dir / "json").is_dir():
        publishable.append("json")

    return publishable


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        eprint(f"Usage: {Path(sys.argv[0]).name} <staging_dir> <exposed_model_dir> <bkp_dir>")
        return EXIT_BAD_ARGS

    staging_dir = Path(argv[0])
    exposed_dir = Path(argv[1])
    bkp_dir = Path(argv[2])

    if not is_under(exposed_dir, EXPOSED_ROOT) or not is_under(bkp_dir, BKP_ROOT):
        eprint(f"Unsafe exposed/bkp path: exposed={exposed_dir} bkp={bkp_dir}")
        return EXIT_UNSAFE_PATH

    if not staging_dir.is_dir():
        eprint(f"Staging dir not found: {staging_dir}")
        return EXIT_NOTHING_TO_PUBLISH

    names = reorganize_staging(staging_dir)
    if not names:
        eprint(f"No publishable outputs (geotiff/json) in staging: {staging_dir}")
        return EXIT_NOTHING_TO_PUBLISH

    exposed_dir.mkdir(parents=True, exist_ok=True)

    moved_to_bkp: list[tuple[Path, Path]] = []
    published: list[Path] = []

    try:
        for name in names:
            new_item = staging_dir / name
            exposed_item = exposed_dir / name

            if exposed_item.exists():
                bkp_dir.mkdir(parents=True, exist_ok=True)
                bkp_item = bkp_dir / name
                if bkp_item.exists():
                    shutil.rmtree(bkp_item, ignore_errors=True)
                shutil.move(str(exposed_item), str(bkp_item))
                moved_to_bkp.append((exposed_item, bkp_item))

            shutil.move(str(new_item), str(exposed_item))
            published.append(exposed_item)
    except Exception as exc:  # noqa: BLE001 - rollback e exit code pulito per NiFi
        eprint(f"Publish failed, rolling back: {exc}")
        for exposed_item in published:
            if exposed_item.is_dir():
                shutil.rmtree(exposed_item, ignore_errors=True)
            else:
                exposed_item.unlink(missing_ok=True)
        for exposed_item, bkp_item in moved_to_bkp:
            shutil.move(str(bkp_item), str(exposed_item))
        return EXIT_PUBLISH_ERROR

    if bkp_dir.exists():
        shutil.rmtree(bkp_dir, ignore_errors=True)

    print(f"Published outputs {names} into {exposed_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
