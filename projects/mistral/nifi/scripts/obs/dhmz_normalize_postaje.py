"""Normalize DHMZ /postaje API response for dhmz_anag table.

Reads the JSON array from /postaje on STDIN and outputs a JSON array of
records ready for PutDatabaseRecord into public.dhmz_anag.

The /postaje response uses projected coordinates (HTRS96/Croatia TM,
EPSG:3765). This script converts them to WGS84 (EPSG:4326) for use with
Leaflet maps and DBAllE.

Requires: pyproj

Output fields per record:
    station_id, station_name, latitude, longitude, station_hmsl, enabled

Exit codes:
    0  success
    1  missing/invalid input
    2  pyproj not available
"""

import json
import sys

try:
    from pyproj import Transformer
except ImportError:
    print("pyproj is required: pip install pyproj", file=sys.stderr)
    sys.exit(2)

# Source CRS: HTRS96/Croatia TM (confirmed from /postaje coordinate ranges)
SOURCE_EPSG = 3765
TARGET_EPSG = 4326

transformer = Transformer.from_crs(
    f"EPSG:{SOURCE_EPSG}", f"EPSG:{TARGET_EPSG}", always_xy=True
)


def normalize_station(station):
    """Convert one /postaje station object to a dhmz_anag record."""
    station_id = station.get("id")
    if station_id is None:
        return None

    station_name = station.get("naziv")
    station_hmsl = station.get("nadmorskaVisina")

    geo = station.get("geolokacija")
    if not geo or not isinstance(geo, dict):
        return None
    coords = geo.get("coordinates")
    if not coords or len(coords) < 2:
        return None

    easting, northing = float(coords[0]), float(coords[1])
    lon, lat = transformer.transform(easting, northing)

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        print(
            f"[dhmz_normalize_postaje] invalid WGS84 for station {station_id}: "
            f"lat={lat}, lon={lon}",
            file=sys.stderr,
        )
        return None

    return {
        "station_id": str(station_id),
        "station_name": station_name,
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "station_hmsl": station_hmsl,
    }


def main():
    raw = sys.stdin.buffer.read()
    if not raw or not raw.strip():
        print("empty STDIN", file=sys.stderr)
        return 1

    try:
        stations = json.loads(raw)
    except (TypeError, ValueError) as exc:
        print(f"cannot parse JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(stations, list):
        print("expected JSON array", file=sys.stderr)
        return 1

    records = []
    for station in stations:
        rec = normalize_station(station)
        if rec is not None:
            records.append(rec)

    json.dump(records, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
