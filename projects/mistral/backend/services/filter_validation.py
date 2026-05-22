"""
Centralized validation of extraction filters for /data and /schedules endpoints.

Filters come in two formats depending on the dataset type:
- Forecast/GRIB (arkimet-style): each filter item is a dict with a "style" key
  and style-specific attributes.
- Observed/BUFR (dballe-style): each filter item is a dict with a "code" key
  containing a comma-separated string of values.

This module performs shallow structural validation of filter items so that
clearly malformed requests are rejected early (HTTP 400) instead of failing
inside Celery tasks. Deep attribute-level checks are intentionally omitted
to avoid blocking future additions of new styles or codes.
"""

from typing import Any, Dict, List, Optional, Tuple

MAX_REPORTED_ERRORS = 3

# Keys that are valid for GRIB / forecast datasets
GRIB_ALLOWED_KEYS = {
        "area",
        "level",
        "origin",
        "proddef",
        "product",
        "quantity",
        "run",
        "task",
        "timerange"
}

# Keys that are valid for BUFR / observed datasets
BUFR_ALLOWED_KEYS = {"product", "level", "timerange", "network"}

# --- GRIB / forecast (arkimet-style) validation rules ---

# Valid styles for each filter key (based on arkimet.py decode functions)
GRIB_AREA_STYLES = {"GRIB", "ODIMH5", "VM2"}
GRIB_LEVEL_STYLES = {"GRIB1", "GRIB2S", "GRIB2D", "ODIMH5"}
GRIB_ORIGIN_STYLES = {"GRIB1", "GRIB2", "BUFR", "ODIMH5"}
GRIB_PRODDEF_STYLES = {"GRIB"}
GRIB_PRODUCT_STYLES = {"GRIB1", "GRIB2", "BUFR", "ODIMH5", "VM2"}
GRIB_RUN_STYLES = {"MINUTE"}
GRIB_TIMERANGE_STYLES = {"GRIB1", "GRIB2", "Timedef", "BUFR"}

GRIB_STYLES_MAP = {
    "area": GRIB_AREA_STYLES,
    "level": GRIB_LEVEL_STYLES,
    "origin": GRIB_ORIGIN_STYLES,
    "proddef": GRIB_PRODDEF_STYLES,
    "product": GRIB_PRODUCT_STYLES,
    "run": GRIB_RUN_STYLES,
    "timerange": GRIB_TIMERANGE_STYLES,
}


def validate_filters(
    filters: Optional[Dict[str, Any]],
    dataset_format: str,
) -> Tuple[Optional[str], Optional[List[str]]]:
    """
    Validate the structural correctness of extraction filters (shallow).

    :param filters: The filters dict as received from the request body.
    :param dataset_format: "grib" or "bufr" (from arki.get_datasets_format).
    :return: A tuple (error_message, warnings) where error_message is a string
             if validation fails or None if valid, and warnings is a list of
             warning strings (e.g. unrecognised styles that don't block execution)
             or None if there are no warnings.
    """
    if not filters:
        return None, None

    errors: List[str] = []
    warnings: List[str] = []

    for key, items in filters.items():
        # --- key-level check: reject keys not valid for this format ---
        allowed_keys = GRIB_ALLOWED_KEYS if dataset_format == "grib" else BUFR_ALLOWED_KEYS
        if key not in allowed_keys:
            errors.append(
                f"Filter '{key}' is not valid for {dataset_format.upper()} datasets. "
                f"Allowed: {sorted(allowed_keys)}."
            )
            continue

        # --- structural checks common to both formats ---
        if len(items) == 0:
            errors.append(f"Filter '{key}': list must not be empty.")
            continue

        for idx, item in enumerate(items):
            if not item:
                errors.append(f"Filter '{key}' item [{idx}]: dict must not be empty.")
                continue

            # --- format-specific validation ---
            if dataset_format == "grib":
                err, warn = _validate_grib_filter_item(key, idx, item)
            else:
                err, warn = _validate_bufr_filter_item(key, idx, item)

            if err:
                errors.append(err)
            if warn:
                warnings.append(warn)

    if errors:
        reported = errors[:MAX_REPORTED_ERRORS]
        omitted = len(errors) - len(reported)
        msg = "Invalid filters: " + "; ".join(reported)
        if omitted:
            msg += f" (and {omitted} more error{'s' if omitted > 1 else ''})"
        return msg, warnings or None

    return None, warnings or None


# --------------- GRIB / forecast helpers ---------------


def _validate_grib_filter_item(key: str, idx: int, item: dict) -> Tuple[Optional[str], Optional[str]]:
    """Shallow validation of a single GRIB filter item.

    - ``quantity`` and ``task`` don't use ``style``, skip style check.
    - All other keys must have a ``style`` (or alias ``s``).
      If the style is not in the known set, a warning is returned but
      execution continues (no error).
    
    :return: A tuple (error, warning).  At most one will be non-None.
    """
    # quantity and task don't use style
    if key in ("quantity", "task"):
        return None, None

    prefix = f"Filter '{key}' item [{idx}]"

    style = item.get("style") or item.get("s")
    if not style:
        return f"{prefix}: missing 'style' key.", None

    valid_styles = GRIB_STYLES_MAP.get(key)
    if valid_styles and style not in valid_styles:
        warn = (
            f"{prefix}: unrecognised style '{style}' (known: {sorted(valid_styles)}). "
            "Proceeding anyway, the style may have been added recently."
        )
        return None, warn

    return None, None


# --------------- BUFR / observed helpers ---------------


def _validate_bufr_filter_item(key: str, idx: int, item: dict) -> Tuple[Optional[str], Optional[str]]:
    """Shallow validation of a single BUFR filter item.

    Each item must contain a non-empty string ``code`` field.

    :return: A tuple (error, warning).  Currently warnings are never emitted
             for BUFR items.
    """
    prefix = f"Filter '{key}' item [{idx}]"

    code = item.get("code")
    if code is None:
        return f"{prefix}: missing required 'code' key.", None
    if not isinstance(code, str):
        return f"{prefix}: 'code' must be a string, got {type(code).__name__}.", None
    if not code.strip():
        return f"{prefix}: 'code' must not be empty.", None

    return None, None
