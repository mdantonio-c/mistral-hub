"""
Centralized validation of extraction filters for /data and /schedules endpoints.

Filters come in two formats depending on the dataset type:
- Forecast/GRIB (arkimet-style): each filter item is a dict with a "style" key
  and style-specific attributes.
- Observed/BUFR (dballe-style): each filter item is a dict with a "code" key
  containing a comma-separated string of values.

This module validates the deep structure of filter items so that malformed
requests are rejected early (HTTP 400) instead of failing inside Celery tasks.
"""

import re
from typing import Any, Dict, List, Optional

# All allowed top-level filter keys (same as BeArkimet.allowed_filters)
ALLOWED_FILTER_KEYS = {
    "area",
    "level",
    "origin",
    "proddef",
    "product",
    "quantity",
    "run",
    "task",
    "timerange",
    "network",
}

# --- GRIB / forecast (arkimet-style) validation rules ---

# Valid styles for each filter key (based on arkimet.py decode functions)
GRIB_AREA_STYLES = {"GRIB", "ODIMH5", "VM2"}
GRIB_LEVEL_STYLES = {"GRIB1", "GRIB2S", "GRIB2D", "ODIMH5"}
GRIB_ORIGIN_STYLES = {"GRIB1", "GRIB2", "BUFR", "ODIMH5"}
GRIB_PRODDEF_STYLES = {"GRIB"}
GRIB_PRODUCT_STYLES = {"GRIB1", "GRIB2", "BUFR", "ODIMH5", "VM2"}
GRIB_QUANTITY_STYLES: set = set()  # quantity uses "value" list, no style check
GRIB_RUN_STYLES = {"MINUTE"}
GRIB_TASK_STYLES: set = set()  # task uses "value", no style check
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

# B-table variable code pattern (e.g. "B12101", "B13011")
_BTABLE_RE = re.compile(r"^B\d{5}$")


def validate_filters(
    filters: Optional[Dict[str, Any]],
    dataset_format: str,
) -> Optional[str]:
    """
    Validate the deep structure of extraction filters.

    :param filters: The filters dict as received from the request body.
    :param dataset_format: "grib" or "bufr" (from arki.get_datasets_format).
    :return: An error message string if validation fails, or None if valid.
    """
    if not filters:
        return None

    errors: List[str] = []

    for key, items in filters.items():
        if key not in ALLOWED_FILTER_KEYS:
            # Unknown keys are silently dropped elsewhere; skip here.
            continue

        if not isinstance(items, list):
            errors.append(f"Filter '{key}': expected a list of items, got {type(items).__name__}.")
            continue

        if len(items) == 0:
            errors.append(f"Filter '{key}': list must not be empty.")
            continue

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(
                    f"Filter '{key}' item [{idx}]: expected a dict, got {type(item).__name__} ({item!r})."
                )
                continue

            if not item:
                errors.append(f"Filter '{key}' item [{idx}]: dict must not be empty.")
                continue

            if dataset_format == "grib":
                err = _validate_grib_filter_item(key, idx, item)
            else:
                # bufr / observed
                err = _validate_bufr_filter_item(key, idx, item)

            if err:
                errors.append(err)

    if errors:
        return "Invalid filters: " + "; ".join(errors)

    return None


# --------------- GRIB / forecast helpers ---------------


def _validate_grib_filter_item(key: str, idx: int, item: dict) -> Optional[str]:
    """Validate a single filter item in arkimet/GRIB notation."""
    prefix = f"Filter '{key}' item [{idx}]"

    # quantity and task don't use style; they just need a "value" key
    if key == "quantity":
        if "value" not in item and "va" not in item:
            return f"{prefix}: missing 'value' key."
        val = item.get("value", item.get("va"))
        if not isinstance(val, list):
            return f"{prefix}: 'value' must be a list."
        return None

    if key == "task":
        if "value" not in item and "va" not in item:
            return f"{prefix}: missing 'value' key."
        return None

    if key == "network":
        # In GRIB mode the network filter is not typically used, but if present
        # each item should have at least some identifying key.
        return None

    # All other filter types require a "style" (or old-notation "s") key
    style = item.get("style") or item.get("s")
    if not style:
        return f"{prefix}: missing 'style' key."

    valid_styles = GRIB_STYLES_MAP.get(key)
    if valid_styles and style not in valid_styles:
        return f"{prefix}: invalid style '{style}'. Allowed: {sorted(valid_styles)}."

    # Style-specific required attributes
    err = _validate_grib_style_attrs(key, style, idx, item)
    return err


def _validate_grib_style_attrs(key: str, style: str, idx: int, item: dict) -> Optional[str]:
    """Check that required attributes for a given style are present and reasonable."""
    prefix = f"Filter '{key}' item [{idx}]"

    if key == "area":
        if style in ("GRIB", "ODIMH5"):
            val = item.get("value", item.get("va"))
            if val is not None and not isinstance(val, dict):
                return f"{prefix}: 'value' must be a dict for style '{style}'."
        return None

    if key == "level":
        if style in ("GRIB1", "GRIB2S"):
            if "level_type" not in item and "lt" not in item:
                return f"{prefix}: missing 'level_type' for style '{style}'."
        if style == "GRIB2D":
            for required in ("l1", "l2"):
                if required not in item:
                    return f"{prefix}: missing '{required}' for style 'GRIB2D'."
        if style == "ODIMH5":
            if "mi" not in item and "ma" not in item:
                return f"{prefix}: missing 'mi'/'ma' for style 'ODIMH5'."
        return None

    if key == "origin":
        if style in ("GRIB1",):
            for required in ("centre", "subcentre"):
                if required not in item and (required[:2] not in item):
                    return f"{prefix}: missing '{required}' for style '{style}'."
        if style == "GRIB2":
            if "centre" not in item and "ce" not in item:
                return f"{prefix}: missing 'centre' for style 'GRIB2'."
        return None

    if key == "proddef":
        if style == "GRIB":
            val = item.get("value", item.get("va"))
            if val is not None and not isinstance(val, dict):
                return f"{prefix}: 'value' must be a dict for style 'GRIB'."
        return None

    if key == "product":
        if style == "GRIB1":
            for required in ("origin", "table", "product"):
                if required not in item and ("or" not in item and "ta" not in item and "pr" not in item):
                    return f"{prefix}: missing '{required}' for style 'GRIB1'."
                break  # just need to check at least one notation exists
        if style == "GRIB2":
            if "centre" not in item and "ce" not in item:
                return f"{prefix}: missing 'centre' for style 'GRIB2'."
        return None

    if key == "run":
        if style == "MINUTE":
            val = item.get("value", item.get("va"))
            if val is None:
                return f"{prefix}: missing 'value' for style 'MINUTE'."
            if not isinstance(val, (int, float)):
                return f"{prefix}: 'value' must be a number for run filter."
        return None

    if key == "timerange":
        if style in ("GRIB1", "GRIB2"):
            for required in ("trange_type", "p1", "p2", "unit"):
                old_key = {"trange_type": "ty", "p1": "p1", "p2": "p2", "unit": "un"}.get(required)
                if required not in item and old_key not in item:
                    return f"{prefix}: missing '{required}' for style '{style}'."
        if style == "Timedef":
            if "step_len" not in item and "sl" not in item:
                return f"{prefix}: missing 'step_len' for style 'Timedef'."
            if "step_unit" not in item and "su" not in item:
                return f"{prefix}: missing 'step_unit' for style 'Timedef'."
        return None

    return None


# --------------- BUFR / observed helpers ---------------


def _validate_bufr_filter_item(key: str, idx: int, item: dict) -> Optional[str]:
    """Validate a single filter item in dballe/observed notation."""
    prefix = f"Filter '{key}' item [{idx}]"

    # Only level, product, timerange, and network are used by from_filters_to_lists.
    # Other keys (area, origin, proddef, run, task, quantity) may appear but are
    # not consumed by the observed extraction.  Still validate structurally.

    if key in ("level", "product", "timerange", "network"):
        code = item.get("code")
        if code is None:
            return f"{prefix}: missing required 'code' key."
        if not isinstance(code, str):
            return f"{prefix}: 'code' must be a string, got {type(code).__name__}."
        if not code.strip():
            return f"{prefix}: 'code' must not be empty."

        # Format-specific validation of the code value
        return _validate_bufr_code(key, idx, code)

    # For other keys allow through if they are non-empty dicts (they are passthrough)
    return None


def _validate_bufr_code(key: str, idx: int, code: str) -> Optional[str]:
    """Validate the format of a 'code' value for observed/BUFR filters."""
    prefix = f"Filter '{key}' item [{idx}]"

    if key == "product":
        # Product code should be a B-table variable code like "B13011"
        if not _BTABLE_RE.match(code):
            return f"{prefix}: invalid product code '{code}'. Expected format: 'BXXXXX' (e.g. 'B13011')."
        return None

    if key == "level":
        # Level code is comma-separated integers, e.g. "1,0,0,0" or "103,2000,0,0"
        parts = code.split(",")
        if len(parts) not in (3, 4):
            return (
                f"{prefix}: invalid level code '{code}'. "
                f"Expected 3 or 4 comma-separated values (e.g. '1,0,0,0')."
            )
        for i, part in enumerate(parts):
            part = part.strip()
            try:
                int(part)
            except (ValueError, TypeError):
                return (
                    f"{prefix}: invalid level code '{code}'. "
                    f"Part [{i}] ('{part}') is not a valid integer."
                )
        return None

    if key == "timerange":
        # Timerange code is 3 comma-separated integers, e.g. "1,0,60" or "254,0,0"
        parts = code.split(",")
        if len(parts) != 3:
            return (
                f"{prefix}: invalid timerange code '{code}'. "
                f"Expected 3 comma-separated values (e.g. '254,0,0')."
            )
        for i, part in enumerate(parts):
            part = part.strip()
            try:
                int(part)
            except (ValueError, TypeError):
                return (
                    f"{prefix}: invalid timerange code '{code}'. "
                    f"Part [{i}] ('{part}') is not a valid integer."
                )
        return None

    if key == "network":
        # Network code is a string identifier (rep_memo). Just check it's not empty.
        # Already checked above; no further format constraint.
        return None

    return None
