import os
import shutil
import subprocess
import sys
import tempfile

# Exit codes
SUCCESS = 0
GDAL_ERROR = 201
IO_ERROR = 202
TMP_ERROR = 203


def main():
    try:
        # Create temp files
        try:
            input_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tif")
            output_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tif")
            input_tmp.close()
            output_tmp.close()
        except Exception:
            return TMP_ERROR

        # Read binary TIFF from stdin
        try:
            with open(input_tmp.name, "wb") as f:
                shutil.copyfileobj(sys.stdin.buffer, f)
        except Exception:
            cleanup(input_tmp.name, output_tmp.name)
            return IO_ERROR

        # Run gdalwarp
        gdal_command = [
            "gdalwarp",
            "-s_srs",
            "+proj=tmerc +lat_0=42 +lon_0=12.5 +ellps=WGS84 +k=1 +x_0=0 +y_0=0",
            "-t_srs",
            "EPSG:4326",
            "-r",
            "bilinear",
            "-dstnodata",
            "-9999",
            "-co",
            "COMPRESS=LZW",
            "-co",
            "PREDICTOR=2",
            "-co",
            "ZLEVEL=9",
            "-co",
            "TILED=YES",
            "-co",
            "BLOCKXSIZE=256",
            "-co",
            "BLOCKYSIZE=256",
            input_tmp.name,
            output_tmp.name,
        ]

        try:
            proc = subprocess.run(gdal_command, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                cleanup(input_tmp.name, output_tmp.name)
                return GDAL_ERROR
        except Exception:
            cleanup(input_tmp.name, output_tmp.name)
            return GDAL_ERROR

        # Stream the output back to NiFi via STDOUT
        try:
            with open(output_tmp.name, "rb") as f:
                shutil.copyfileobj(f, sys.stdout.buffer)
        except Exception:
            cleanup(input_tmp.name, output_tmp.name)
            return IO_ERROR

        cleanup(input_tmp.name, output_tmp.name)
        return SUCCESS

    except Exception:
        return 99  # unexpected failure


def cleanup(*files):
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
