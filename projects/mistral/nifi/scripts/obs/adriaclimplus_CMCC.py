"""Build DBAllE-ready JSON records from a CMCC station API payload.

The station name and coordinates are supplied by NiFi from ``cmcc_anag``. The
payload comes from the corresponding Interbox REST API station endpoint.

It is meant to be run by a NiFi ``ExecuteStreamCommand`` processor, exactly like
the sibling ``obs/*.py`` scripts, with the API payload piped on STDIN and the
station metadata passed as positional arguments::

    python3 obs/adriaclimplus_CMCC.py "Ofanto" 41.268 16.0568 [BATCHID]

The script only validates, filters, converts and enriches the API data. It has no
database dependency and does not perform dedupe or retry. When NiFi supplies the
optional ``batchid``, it is included in every output record for staging.

The emitted JSON array matches the record shape expected by
``obs/json2jsonl_nifi.py`` (keys: ``station_name``, ``station_hmsl``, ``ident``,
``network``, ``lon``, ``lat``, ``date``, ``timerange``, ``p1``, ``p2``,
``varcode``, ``value``, ``level1``, ``l1``, ``level2``, ``l2``, plus
``batchid`` when supplied).

Exit codes (non zero => NiFi error-handling path):
    0  success (records printed, possibly the empty array ``[]``)
    2  missing or invalid station/batch arguments
    3  invalid / unparsable API payload
    5  unexpected error
"""

import json
import math
import sys
from datetime import datetime

STATION_HMSL = None
IDENT = None
NETWORK = "ofa-01-cmcc"

TIMERANGE = 254
P1 = 0
P2 = 0

# Only clean 10-minute marks are accepted (minutes 00/10/20/30/40/50, seconds 00).
CLEAN_MINUTES = frozenset((0, 10, 20, 30, 40, 50))

# The CMCC payload timestamps are treated as already UTC. We therefore preserve
# the wall-clock value and only normalize the format to the DBAllE/BUFR style
# ``YYYY-MM-DDTHH:MM:SSZ``.


def _celsius_to_kelvin(value):
    """°C -> K, rounded to 2 decimals (template: ``round(misura + 273.15, 2)``)."""
    return round(float(value) + 273.15, 2)


def _mbar_to_pa(value):
    """mbar (= hPa) -> Pa, rounded to the nearest 10 (template: ``round(misura * 100, -1)``)."""
    return round(float(value) * 100.0, -1)


def _percent_identity(value):
    """% -> %, rounded to integer (template IGRO: ``round(misura, 0)``)."""
    return round(float(value), 0)


def _meters_identity(value):
    """m -> m, rounded to 3 decimals (template length convention: ``round(., 3)``)."""
    return round(float(value), 3)


def _parse_coordinate(value, name, minimum, maximum):
    """Parse and range-check one station coordinate supplied by NiFi."""
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not numeric: {value!r}") from exc

    if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
        raise ValueError(
            f"{name} must be a finite value between {minimum} and {maximum}"
        )
    return coordinate


def _parse_station_args(args):
    """Return validated station metadata and an optional NiFi batch ID."""
    if len(args) not in (3, 4):
        raise ValueError(
            "expected arguments: station_name latitude longitude [batchid]"
        )

    station_name = args[0].strip()
    if not station_name:
        raise ValueError("station_name must not be empty")

    latitude = _parse_coordinate(args[1], "latitude", -90.0, 90.0)
    longitude = _parse_coordinate(args[2], "longitude", -180.0, 180.0)
    batchid = None
    if len(args) == 4:
        try:
            batchid = int(args[3])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"batchid is not an integer: {args[3]!r}") from exc
        if batchid <= 0:
            raise ValueError("batchid must be a positive integer")

    return station_name, latitude, longitude, batchid


def _coordinate_to_dballe(value):
    """Encode decimal degrees as the integer degrees * 1e5 expected by DBAllE."""
    return int(round(round(value, 5) * 1e5))


# Per-product configuration.
#   key            = product key in the API payload (and its ``<key>_suspect`` twin)
#   varcode        = BUFR/DBAllE B-code requested by the prompt
#   level1/l1/...  = DBAllE level, requested by the prompt
#   convert        = source-unit -> DBAllE-unit conversion derived from the template
PRODUCTS = {
    "temperature": {
        "varcode": "B12101",
        "level1": 103,
        "l1": 2000,
        "level2": None,
        "l2": None,
        "convert": _celsius_to_kelvin,
    },
    "sea_level": {
        "varcode": "B22037",
        "level1": 101,
        "l1": None,
        "level2": None,
        "l2": None,
        "convert": _meters_identity,
    },
    "pressure": {
        "varcode": "B10004",
        "level1": 1,
        "l1": None,
        "level2": None,
        "l2": None,
        "convert": _mbar_to_pa,
    },
    "humidity": {
        "varcode": "B13003",
        "level1": 103,
        "l1": 2000,
        "level2": None,
        "l2": None,
        "convert": _percent_identity,
    },
}


def log(message):
    """Minimal stderr logging, so STDOUT stays a clean JSON array for NiFi."""
    print("[adriaclimplus_CMCC] " + message, file=sys.stderr)


def _timestamp_to_utc_iso(dt_value):
    """Format an already-UTC timestamp as ``YYYY-MM-DDTHH:MM:SSZ``."""
    return dt_value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_clean_timestamp(dt_value):
    """True only for minutes 00/10/20/30/40/50 and seconds 00."""
    return dt_value.minute in CLEAN_MINUTES and dt_value.second == 0


def _get_array(payload, key, length):
    """Return ``payload[key]`` as a list padded/validated against ``length``.

    A missing array is treated as all-null. A present array of a different
    length is a payload-shape error.
    """
    value = payload.get(key)
    if value is None:
        return [None] * length
    if not isinstance(value, list):
        raise ValueError(f"field '{key}' is not a list")
    if len(value) != length:
        raise ValueError(
            f"field '{key}' has length {len(value)}, expected {length} (timestamps)"
        )
    return value


def build_records(payload, station_name, latitude, longitude, batchid=None):
    """Apply the CMCC filtering rules and build the enriched records.

    Filtering rules implemented (in order, per index and per product):
      1. ``*_suspect`` arrays are never ingested as values.
      2. null product values are ignored.
      3. discard when the product value AND its ``*_suspect`` twin are both set.
      4. discard when the product value is set but the timestamp is null.
      5. keep only "clean" timestamps (minutes 00/10/20/30/40/50, seconds 00).

    Returns a list of record dictionaries using the documented output keys.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload is not a JSON object")

    timestamps = payload.get("timestamps")
    if not isinstance(timestamps, list):
        raise ValueError("missing or invalid 'timestamps' array")

    length = len(timestamps)
    lat = _coordinate_to_dballe(latitude)
    lon = _coordinate_to_dballe(longitude)
    records = []

    for product, cfg in PRODUCTS.items():
        values = _get_array(payload, product, length)
        suspects = _get_array(payload, product + "_suspect", length)

        for i in range(length):
            value = values[i]
            if value is None:
                continue  # rule 2: ignore null values

            if suspects[i] is not None:
                continue  # rule 3: value present but also flagged as suspect

            raw_ts = timestamps[i]
            if raw_ts is None:
                continue  # rule 4: value present but timestamp missing

            try:
                dt_value = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                log(f"skipping unparsable timestamp {raw_ts!r} for {product}")
                continue

            if not _is_clean_timestamp(dt_value):
                continue  # rule 5: keep only clean 10-minute marks

            record = {
                "station_name": station_name,
                "station_hmsl": STATION_HMSL,
                "ident": IDENT,
                "network": NETWORK,
                "lon": lon,
                "lat": lat,
                "date": _timestamp_to_utc_iso(dt_value),
                "timerange": TIMERANGE,
                "p1": P1,
                "p2": P2,
                "varcode": cfg["varcode"],
                "value": cfg["convert"](value),
                "level1": cfg["level1"],
                "l1": cfg["l1"],
                "level2": cfg["level2"],
                "l2": cfg["l2"],
            }
            if batchid is not None:
                record["batchid"] = batchid
            records.append(record)

    return records


def _as_int(value):
    return None if value is None else int(round(float(value)))


def _normalize_emit(record):
    """Return a copy with integer-typed codes/coords, as DBAllE/dballe expect."""
    out = dict(record)
    for key in ("lon", "lat", "timerange", "p1", "p2", "level1", "l1", "level2", "l2"):
        out[key] = _as_int(out.get(key))
    return out


def _emit(records):
    """Print the JSON array expected by the NiFi record pipeline."""
    json.dump([_normalize_emit(r) for r in records], sys.stdout)
    sys.stdout.write("\n")


def main(args=None):
    """Read one API payload from STDIN and emit its valid enriched records."""
    try:
        station_name, latitude, longitude, batchid = _parse_station_args(
            sys.argv[1:] if args is None else args
        )
    except ValueError as exc:
        log(f"invalid station arguments: {exc}")
        return 2

    raw = sys.stdin.buffer.read()
    if not raw or not raw.strip():
        log("empty STDIN payload")
        return 3
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        log(f"cannot parse API payload as JSON: {exc}")
        return 3

    try:
        records = build_records(payload, station_name, latitude, longitude, batchid)
    except ValueError as exc:
        log(f"invalid API payload shape: {exc}")
        return 3

    log(f"{len(records)} valid record(s) generated after filtering")
    _emit(records)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - last-resort guard for NiFi
        log(f"unexpected error: {exc}")
        sys.exit(5)
