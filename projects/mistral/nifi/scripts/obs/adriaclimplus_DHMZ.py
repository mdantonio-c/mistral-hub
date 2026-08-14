"""Build DBAllE-ready staging rows from a DHMZ CIP measurements payload.

The DHMZ CIP endpoint ``/mjerenja/numericka`` is called once per batch with a
hardcoded ``mmeId`` list and a time window, so a single GET response carries
every station and every requested product. The observed response shape (see
``adriaclimplus/DHMZ/DHMZ_API_Spec.md``) is::

    [
      {
        "postajaNaziv": "BATINA - CMP",
        "postajaId": 17,
        "termini": [
          {
            "termin": "2024-11-15 12:00:00.0",
            "mjerenja": [
              {"mmeId": 30, "vrijednost": 6.3, "mjernaJedinica": "\N{DEGREE SIGN}C",
               "status": "...", "komentar": "..."}
            ]
          }
        ]
      }
    ]

For every measurement the script maps ``mmeId`` to one canonical product,
converts the value using the unit reported in ``mjernaJedinica``, drops null
measurements, and emits one JSON record per (station, product, timestamp).

Station coordinates are intentionally NOT added here: NiFi joins ``dhmz_anag``
on ``station_id`` when it reads the batch back, so only stations present in the
anagrafica are imported into DBAllE and the transformer stays database-free.

NiFi invocation (one call, all stations)::

    python3 obs/adriaclimplus_DHMZ.py [BATCHID] [STATION_IDS]

STATION_IDS is an optional comma-separated list of postajaId values.
When provided, only stations in this list are emitted.

The GET response is read from STDIN and a JSON array of rows is written to
STDOUT. The script performs no dedupe, retry or HTTP/DB access.

Exit codes (non zero => NiFi error-handling path):
    0  success (records printed, possibly the empty array ``[]``)
    2  invalid batch argument
    3  missing / unparsable / unsupported API payload
    5  unexpected error
"""

import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

NETWORK = "dhmz"
IDENT = None

TIMERANGE = 254
P1 = 0
P2 = 0

# mmeId -> canonical product.
#
# These numbers MUST match the mmeId values hardcoded in the NiFi InvokeHTTP URL
# (``?mmeId=...``). All five confirmed by DHMZ (August 2026).
MME_TO_PRODUCT = {
    5: "atmospheric_pressure",
    30: "air_temperature",
    31: "wind_speed",
    32: "wind_direction",
    33: "relative_humidity",
}

# Minimum number of samples in a 10-min frame for data to be usable (85% of 600).
MIN_SAMPLES = 510

# Status values known to be valid. The filter is applied at SQL level (step 15),
# not here; the script emits all records but logs a warning for unknown statuses.
ACCEPTED_STATUSES = {"Neslužbeni", "Službeni"}

# DHMZ uses CET (UTC+1) year-round, no DST.
CET_OFFSET = timedelta(hours=1)

# Accepted formats for the "termin" field. ``strptime`` "%f" accepts 1..6
# fractional digits, so the sample ".0" is handled. Timestamps are in CET (UTC+1)
# and converted to UTC for DBAllE output.
TERMIN_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
)


def log(message):
    """Minimal stderr logging, so STDOUT stays a clean JSON array for NiFi."""
    print("[adriaclimplus_DHMZ] " + message, file=sys.stderr)


def _norm_unit(value):
    """Normalize a unit string: NFKC, casefold, drop whitespace."""
    if value is None:
        return None
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)).casefold())


def _pressure_to_pa(value, unit):
    """hPa/mbar -> Pa, rounded to the nearest 10 (template: round(misura*100, -1))."""
    if _norm_unit(unit) not in ("hpa", "mbar"):
        raise ValueError(f"unsupported pressure unit {unit!r}")
    return round(float(value) * 100.0, -1)


def _humidity_percent(value, unit):
    """% -> %, rounded to integer (template IGRO: round(misura, 0))."""
    if _norm_unit(unit) not in ("%", "percent", "postotak"):
        raise ValueError(f"unsupported humidity unit {unit!r}")
    return round(float(value), 0)


def _temperature_to_kelvin(value, unit):
    """degC -> K, rounded to 2 decimals (template: round(misura + 273.15, 2))."""
    if _norm_unit(unit) not in ("c", "degc", "\N{DEGREE SIGN}c", "celsius"):
        raise ValueError(f"unsupported temperature unit {unit!r}")
    return round(float(value) + 273.15, 2)


def _wind_speed(value, unit):
    """m/s identity, or km/h -> m/s (template: round(misura/3.6, 1))."""
    unit_key = _norm_unit(unit)
    if unit_key in ("m/s", "ms", "ms-1", "m*s-1"):
        return round(float(value), 1)
    if unit_key in ("km/h", "kmh", "kmh-1"):
        return round(float(value) / 3.6, 1)
    raise ValueError(f"unsupported wind-speed unit {unit!r}")


def _wind_direction(value, unit):
    """degrees true, rounded to integer and range-checked to 0..360."""
    if _norm_unit(unit) not in (
        "\N{DEGREE SIGN}",
        "deg",
        "degree",
        "degrees",
        "\N{DEGREE SIGN}t",
        "degt",
        "stupanj",
        "stupnjeva",
    ):
        raise ValueError(f"unsupported wind-direction unit {unit!r}")
    direction = round(float(value), 0)
    if not 0.0 <= direction <= 360.0:
        raise ValueError(f"wind direction out of range: {direction}")
    return direction


# Per-product configuration.
#   varcode        = BUFR/DBAllE B-code
#   level1/l1/...  = DBAllE level (from ObsFromDPCNtoDBAlle.xml conventions)
#   convert        = (value, unit) -> DBAllE-unit value, unit taken from the API
PRODUCTS = {
    "atmospheric_pressure": {
        "varcode": "B10004",
        "level1": 1,
        "l1": None,
        "level2": None,
        "l2": None,
        "convert": _pressure_to_pa,
    },
    "relative_humidity": {
        "varcode": "B13003",
        "level1": 103,
        "l1": 2000,
        "level2": None,
        "l2": None,
        "convert": _humidity_percent,
    },
    "air_temperature": {
        "varcode": "B12101",
        "level1": 103,
        "l1": 2000,
        "level2": None,
        "l2": None,
        "convert": _temperature_to_kelvin,
    },
    "wind_speed": {
        "varcode": "B11002",
        "level1": 103,
        "l1": 10000,
        "level2": None,
        "l2": None,
        "convert": _wind_speed,
    },
    "wind_direction": {
        "varcode": "B11001",
        "level1": 103,
        "l1": 10000,
        "level2": None,
        "l2": None,
        "convert": _wind_direction,
    },
}


def _parse_args(args):
    """Return (batchid, whitelist_set)."""
    if len(args) > 2:
        raise ValueError("expected: [batchid] [station_ids]")
    batchid = None
    whitelist = None
    if len(args) >= 1:
        try:
            batchid = int(args[0])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"batchid is not an integer: {args[0]!r}") from exc
        if batchid <= 0:
            raise ValueError("batchid must be a positive integer")
    if len(args) >= 2 and args[1].strip():
        whitelist = {s.strip() for s in args[1].split(",") if s.strip()}
        if not whitelist:
            whitelist = None
    return batchid, whitelist


def _parse_termin(value):
    """Parse the ``termin`` string (CET) to ``YYYY-MM-DDTHH:MM:SSZ`` (UTC), or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text[-1] in ("Z", "z"):
        text = text[:-1].strip()
    for fmt in TERMIN_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        # CET (UTC+1 fixed) -> UTC
        utc_dt = parsed.replace(tzinfo=timezone.utc) - CET_OFFSET
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def _check_completeness(komentar):
    """Return True if the measurement passes the completeness check.

    Returns False only when komentar contains broj_uzoraka < MIN_SAMPLES.
    Returns True if komentar is null, empty, or unparsable.
    """
    if komentar is None:
        return True
    try:
        items = json.loads(komentar)
    except (TypeError, ValueError):
        return True
    if isinstance(items, list) and items and isinstance(items[0], dict):
        samples = items[0].get("broj_uzoraka")
        if samples is not None and int(samples) < MIN_SAMPLES:
            return False
    return True


def _stations(payload):
    """Return the list of station objects from the DHMZ payload."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "termini" in payload or "postajaId" in payload:
            return [payload]
        for key in ("data", "postaje", "results", "content", "items"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
        if not payload:
            return []
    raise ValueError("payload is not a DHMZ station array")


def build_records(payload, batchid=None, whitelist=None):
    """Flatten the nested DHMZ response into DBAllE staging rows.

    Rules:
      1. null ``vrijednost`` measurements are excluded;
      2. measurements whose ``mmeId`` is not in ``MME_TO_PRODUCT`` are ignored;
      3. a measurement with an unparsable timestamp or unsupported unit is
         skipped (logged), never aborting the whole batch;
      4. the first reading of a logical key (station_id, varcode, date) wins;
      5. measurements with ``broj_uzoraka < 510`` in ``komentar`` are excluded;
      6. if ``whitelist`` is set, stations not in it are skipped.

    ``status`` is not used as a quality filter (\"Neslužbeni\" = usable data).
    """
    stations = _stations(payload)
    if not isinstance(stations, list):
        raise ValueError("payload station container is not a list")

    records = []
    seen = set()

    for station in stations:
        if not isinstance(station, dict):
            raise ValueError("station entry is not an object")

        raw_id = station.get("postajaId")
        if raw_id is None:
            log("skipping station without postajaId")
            continue
        station_id = str(raw_id).strip()
        if not station_id:
            log("skipping station with empty postajaId")
            continue

        if whitelist is not None and station_id not in whitelist:
            continue

        station_name = station.get("postajaNaziv")
        if station_name is not None:
            station_name = str(station_name).strip() or None

        termini = station.get("termini") or []
        if not isinstance(termini, list):
            raise ValueError(f"'termini' for station {station_id} is not a list")

        for termin in termini:
            if not isinstance(termin, dict):
                raise ValueError("termin entry is not an object")

            date = _parse_termin(termin.get("termin"))
            if date is None:
                log(f"skipping unparsable termin {termin.get('termin')!r}")
                continue

            mjerenja = termin.get("mjerenja") or []
            if not isinstance(mjerenja, list):
                raise ValueError("'mjerenja' is not a list")

            for mjerenje in mjerenja:
                if not isinstance(mjerenje, dict):
                    raise ValueError("mjerenje entry is not an object")

                value = mjerenje.get("vrijednost")
                if value is None:
                    continue  # rule 1: exclude null measurements

                if not _check_completeness(mjerenje.get("komentar")):
                    log(f"skipping incomplete measurement for station {station_id}")
                    continue  # rule 5: insufficient samples

                try:
                    mme_id = int(mjerenje.get("mmeId"))
                except (TypeError, ValueError):
                    log(f"skipping non-numeric mmeId {mjerenje.get('mmeId')!r}")
                    continue
                product = MME_TO_PRODUCT.get(mme_id)
                if product is None:
                    continue  # rule 2: not one of the requested products

                cfg = PRODUCTS[product]
                try:
                    converted = cfg["convert"](value, mjerenje.get("mjernaJedinica"))
                except (TypeError, ValueError) as exc:
                    log(f"skipping {product} for station {station_id}: {exc}")
                    continue  # rule 3: robust to a bad unit/value

                key = (station_id, cfg["varcode"], date)
                if key in seen:
                    continue  # rule 4: first reading wins
                seen.add(key)

                mjerenje_status = mjerenje.get("status")
                if mjerenje_status and mjerenje_status not in ACCEPTED_STATUSES:
                    log(f"unknown status {mjerenje_status!r} for station {station_id}")

                record = {
                    "station_id": station_id,
                    "station_name": station_name,
                    "ident": IDENT,
                    "network": NETWORK,
                    "date": date,
                    "timerange": TIMERANGE,
                    "p1": P1,
                    "p2": P2,
                    "varcode": cfg["varcode"],
                    "value": converted,
                    "level1": cfg["level1"],
                    "l1": cfg["l1"],
                    "level2": cfg["level2"],
                    "l2": cfg["l2"],
                    "status": mjerenje_status,
                }
                if batchid is not None:
                    record["batchid"] = batchid
                records.append(record)

    return records


def _as_int(value):
    return None if value is None else int(round(float(value)))


def _normalize_emit(record):
    """Return a copy with integer-typed codes/levels, as DBAllE/dballe expect."""
    out = dict(record)
    for key in ("timerange", "p1", "p2", "level1", "l1", "level2", "l2"):
        out[key] = _as_int(out.get(key))
    return out


def _emit(records):
    """Print the JSON array expected by the NiFi record pipeline."""
    json.dump([_normalize_emit(r) for r in records], sys.stdout)
    sys.stdout.write("\n")


def main(args=None):
    """Read one GET payload from STDIN and emit its valid records."""
    try:
        batchid, whitelist = _parse_args(sys.argv[1:] if args is None else args)
    except ValueError as exc:
        log(f"invalid arguments: {exc}")
        return 2

    if whitelist:
        log(f"station whitelist: {len(whitelist)} station(s)")

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
        records = build_records(payload, batchid, whitelist)
    except ValueError as exc:
        log(f"invalid API payload: {exc}")
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
