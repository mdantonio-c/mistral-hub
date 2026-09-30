import re

from arkimet.formatter import Formatter

# Auto-generated GRIB2 formatter for dataset BOLAM.
# Mapping layout: discipline -> category -> number -> description.
prodtab = {
    0: {
        # Mappings found in DWD local tables (edzw). Not present for centre 80 (cnmc).
        2: {
            208: "U-component of vertical wind shear vector",
            209: "V-component of vertical wind shear vector",
        },
        4: {
            8: "Upward short-wave radiation flux",
            198: "Surface down solar direct radiation",
            199: "Surface down solar diffuse radiation",
        },
        7: {193: "supercell detection index 2 (only rot. up drafts)"},
        1: {
            61: "Snow density",
            64: "Total column integrated water vapour",
            204: "Height of snow fall limit",
            205: "Massflux at convective cloud base",
        },
        15: {17: "Precipitation rate from radar"},
        # Mappings found at https://codes.ecmwf.int/grib/param-db/260689. Not present for centre 80 (cnmc).
        17: {
            192: "Lightning Potential Index (J/kg)",
        },
    }
}

# Deterministic local level mappings from ecCodes local table sources.
levtab = {
    # Mappings from ECMWF (ecmf) / DWD (edzw) local tables.
    192: "Mean layer",  # CNMC/DWD local concepts
    200: "Atmosphere single layer",  # ECMWF
    214: "Low cloud layer",  # DWD
    224: "Middle cloud layer",  # DWD
    234: "High cloud layer",
}


def format_product_grib2(v):
    if v.get("style") != "GRIB2":
        return None

    discipline = v.get("discipline")
    category = v.get("category")
    number = v.get("number")

    if discipline is None or category is None or number is None:
        return None

    return prodtab.get(discipline, {}).get(category, {}).get(number)


def format_level_grib2(v):
    style = v.get("style")
    if style not in {"GRIB2S", "GRIB2D", "GRIB2"}:
        return None

    level_type = (
        v.get("level_type") or v.get("ltype") or v.get("typeOfFirstFixedSurface")
    )

    if level_type is None and v.get("type") != "level":
        level_type = v.get("type")

    if level_type is None:
        val = v.get("val")
        if isinstance(val, dict):
            level_type = (
                val.get("level_type")
                or val.get("ltype")
                or val.get("typeOfFirstFixedSurface")
            )

            if level_type is None and val.get("type") != "level":
                level_type = val.get("type")

    if level_type is None:
        # Some payloads expose only encoded strings like GRIB2S(234,...)
        # and may nest them in dict/list structures.
        def _iter_scalars(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    yield from _iter_scalars(value)
            elif isinstance(obj, (list, tuple, set)):
                for item in obj:
                    yield from _iter_scalars(item)
            else:
                yield obj

        candidates = [
            v.get("raw"),
            v.get("value"),
            v.get("repr"),
            v.get("description"),
            v.get("id"),
            v.get("val"),
            v,
        ]

        for candidate in candidates:
            if candidate is None:
                continue
            for scalar in _iter_scalars(candidate):
                match = re.search(r"GRIB2S\(\s*(\d+)\s*,", str(scalar))
                if match:
                    level_type = match.group(1)
                    break
            if level_type is not None:
                break

    try:
        level_type = int(level_type)
    except Exception:
        return None

    return levtab.get(level_type)


Formatter.register("product", format_product_grib2)
Formatter.register("level", format_level_grib2)
