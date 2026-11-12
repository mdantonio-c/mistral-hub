"""Builder dei body delle richieste per i test di integrazione sulle schedule.

Gli scenari sulle schedule di questa suite differiscono soprattutto per l'intento
di business, non per la sintassi JSON. Questi helper costruiscono i payload per
schedule on-data-ready, crontab e periodiche (inviati a ``POST /api/schedules``),
cosi i moduli di test descrivono lo scenario voluto senza essere appesantiti dal
boilerplate del body.
"""

from __future__ import annotations

import json
from typing import Any


def build_on_data_ready_schedule(
    *,
    request_name: str,
    date_from: str,
    date_to: str,
    dataset_names: list[str],
    run_filter: list[dict[str, Any]] | None = None,
    opendata: bool = True,
) -> str:
    """Costruisce il body JSON di una schedule avviata dagli eventi data-ready.

    L'helper riempie le sezioni standard di reftime e dataset e marca la schedule
    come ``on-data-ready``, cosi i test si concentrano sulla regola sotto esame.
    """
    body: dict[str, Any] = {
        "request_name": request_name,
        "reftime": {"from": date_from, "to": date_to},
        "dataset_names": dataset_names,
        "filters": {"run": run_filter} if run_filter else {},
        "on-data-ready": True,
        "opendata": opendata,
    }
    return json.dumps(body)


def build_crontab_schedule(
    *,
    request_name: str,
    date_from: str,
    date_to: str,
    dataset_names: list[str],
    run_filter: list[dict[str, Any]] | None = None,
    hour: int | None = None,
    minute: int | None = None,
    day_of_week: int | None = None,
    day_of_month: int | None = None,
    month_of_year: int | None = None,
    on_data_ready: bool = False,
    opendata: bool = True,
) -> str:
    """Costruisce il body JSON di una schedule guidata da campi in stile crontab.

    Nel payload vengono aggiunti solo i campi temporali passati esplicitamente dal
    chiamante. Cosi i test restano concisi, ma possono comunque costruire
    espressioni crontab parziali o complete.
    """
    crontab: dict[str, int] = {}
    if hour is not None:
        crontab["hour"] = hour
    if minute is not None:
        crontab["minute"] = minute
    if day_of_week is not None:
        crontab["day_of_week"] = day_of_week
    if day_of_month is not None:
        crontab["day_of_month"] = day_of_month
    if month_of_year is not None:
        crontab["month_of_year"] = month_of_year

    body: dict[str, Any] = {
        "request_name": request_name,
        "reftime": {"from": date_from, "to": date_to},
        "dataset_names": dataset_names,
        "filters": {"run": run_filter} if run_filter else {},
        "crontab-settings": crontab,
        "on-data-ready": on_data_ready,
        "opendata": opendata,
    }
    return json.dumps(body)


def build_periodic_schedule(
    *,
    request_name: str,
    date_from: str,
    date_to: str,
    dataset_names: list[str],
    run_filter: list[dict[str, Any]] | None = None,
    every: int = 1,
    period: str = "days",
    on_data_ready: bool = True,
    opendata: bool = True,
) -> str:
    """Costruisce il body JSON di una schedule che si ripete a intervallo fisso.

    Usato soprattutto dai test data-ready periodici che devono esprimere regole
    come "ogni 2 giorni" senza riscrivere in ogni scenario la forma del payload.
    """
    body: dict[str, Any] = {
        "request_name": request_name,
        "reftime": {"from": date_from, "to": date_to},
        "dataset_names": dataset_names,
        "filters": {"run": run_filter} if run_filter else {},
        "period-settings": {"every": every, "period": period},
        "on-data-ready": on_data_ready,
        "opendata": opendata,
    }
    return json.dumps(body)