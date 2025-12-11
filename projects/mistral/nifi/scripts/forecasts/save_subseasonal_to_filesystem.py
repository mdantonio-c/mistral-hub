import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

EXIT_INVALID_INPUT = 20
EXIT_INVALID_TREE = 30

expected_tree = {
    "t2m",
    "t2m/quintile_1",
    "t2m/quintile_5",
    "t2m/terzile_1",
    "t2m/terzile_2",
    "t2m/terzile_3",
    "tp",
    "tp/quintile_1",
    "tp/quintile_5",
    "tp/terzile_1",
    "tp/terzile_2",
    "tp/terzile_3",
}

DEST_DIR = Path("/opt/nifi/nfs/subseasonal")

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

    # for subseasonal this is the expected path of the zip <date>/<product>/<value>/yyyy-MM-dd.tif
    unzipped_data_dir = [p for p in extract_dir.iterdir() if p.is_dir()][0]
    # get the run date to use for .ready name
    file_date = unzipped_data_dir.name

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

    # clean the destination output
    if DEST_DIR.exists():
        for item in DEST_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        DEST_DIR.mkdir(parents=True)

    # copy new content

    for p in unzipped_data_dir.iterdir():
        target = Path(DEST_DIR, p.name)
        if p.is_dir():
            shutil.copytree(p, target)
        else:
            shutil.copy2(p, target)

# Success
# give to stdout the date to be set as flowfile attribute
print(file_date)
sys.exit(0)
