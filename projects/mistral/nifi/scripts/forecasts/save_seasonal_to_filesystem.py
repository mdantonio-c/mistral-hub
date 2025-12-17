import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

EXIT_INVALID_INPUT = 20
EXIT_INVALID_TREE = 30

expected_tree = {
    "grib",
    "json",
    "tiff",
    "tiff/ano_max_TM",
    "tiff/ano_min_Tm",
    "tiff/ano_P",
    "tiff/mean_Tm",
    "tiff/mean_TM",
    "tiff/sum_P",
}

TIFF_DEST_DIR = Path("/opt/nifi/nfs/seasonal")
# TODO JSON_DEST_DIR = Path("")
# TODO GRIB_DEST_DIR = Path("")

# read the content from stdin
zip_bytes = sys.stdin.buffer.read()
if not zip_bytes:
    print("Error in reading input received on stdin", file=sys.stderr)
    sys.exit(EXIT_INVALID_INPUT)

# unzip the file in a temporary location
with tempfile.TemporaryDirectory() as tmpdir_str:
    tmpdir = Path(tmpdir_str)
    zip_path = Path(tmpdir, "input.zip")
    extract_dir = Path(tmpdir, "unzipped")

    # Write FlowFile content to zip file
    zip_path.write_bytes(zip_bytes)

    # unzip
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
    except zipfile.BadZipFile:
        print("Invalid ZIP file", file=sys.stderr)
        sys.exit(EXIT_INVALID_INPUT)

    # check tree

    # Collect list of paths inside the unzipped directory (relative paths)
    actual_paths = set()

    # for seasonal this is the expected path of the zip <date>/<fileformat>/<product>/<product>_yyyyMMdd.tiff
    unzipped_data_dir = [p for p in extract_dir.iterdir() if p.is_dir()][0]
    # get the run date to use for .ready name
    monthly_file_date = unzipped_data_dir.name
    # since the run is only the YYYY_MM add the day as first day of the month and substitute _ with - to normalize the string with the same used by subseasonal
    file_date = f"{monthly_file_date}_01".replace("_", "-")

    for p in unzipped_data_dir.rglob("*"):
        # Normalize directories
        if p.is_dir():
            rel = p.relative_to(unzipped_data_dir).as_posix()
            actual_paths.add(rel)

    if actual_paths != expected_tree:
        print(
            f"ZIP structure does not match expected tree: tree found {actual_paths}",
            file=sys.stderr,
        )
        sys.exit(EXIT_INVALID_TREE)

    for p in unzipped_data_dir.rglob("*"):
        if p.is_dir() and p.name == "tiff":
            # move the tiff in the folder for the map visualization
            # clean the destination output
            if TIFF_DEST_DIR.exists():
                for item in TIFF_DEST_DIR.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            else:
                TIFF_DEST_DIR.mkdir(parents=True)

            for tiff_p in p.iterdir():
                target = Path(TIFF_DEST_DIR, tiff_p.name)
                if tiff_p.is_dir():
                    shutil.copytree(tiff_p, target)
                else:
                    shutil.copy2(tiff_p, target)

# Success
# give to stdout the date to be set as flowfile attribute
print(file_date)
sys.exit(0)
