"""Request-body builders for schedule-related integration tests.

Schedule scenarios in this suite mostly differ in business intent, not in JSON
syntax. These helpers build the payloads for on-data-ready, crontab, and periodic
schedules so the test modules can describe the scenario they want without being
cluttered by request-body boilerplate.
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
    """Build the JSON body for a schedule triggered by data-ready events.

    The helper fills the standard reftime and dataset sections and marks the
    schedule as ``on-data-ready`` so tests can focus on the rule under scrutiny.
    """
    # Componiamo il payload in un solo punto, cosi i test possono concentrarsi sulla
    # regola di business invece che sulla forma JSON.
    body: dict[str, Any] = {
        "request_name": request_name,
        "reftime": {"from": date_from, "to": date_to},
        "dataset_names": dataset_names,
        "filters": {"run": run_filter} if run_filter else {},
        "on-data-ready": True,
        "opendata": opendata,
    }
    # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
    # verifica riguarda la logica e non dettagli casuali di input.
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
    """Build the JSON body for a schedule driven by crontab-style fields.

    Only the time components explicitly provided by the caller are added to the
    payload. This keeps tests concise while still allowing them to build partial
    or fully specified crontab expressions.
    """
    # Componiamo il payload in un solo punto, cosi i test possono concentrarsi sulla
    # regola di business invece che sulla forma JSON.
    crontab: dict[str, int] = {}
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if hour is not None:
        crontab["hour"] = hour
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if minute is not None:
        crontab["minute"] = minute
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if day_of_week is not None:
        crontab["day_of_week"] = day_of_week
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if day_of_month is not None:
        crontab["day_of_month"] = day_of_month
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
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
    # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
    # verifica riguarda la logica e non dettagli casuali di input.
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
    """Build the JSON body for a schedule that repeats every fixed period.

    This helper is mainly used by periodic data-ready tests that need to express
    rules such as "every 2 days" without rewriting the schedule payload shape in
    each scenario.
    """
    # Componiamo il payload in un solo punto, cosi i test possono concentrarsi sulla
    # regola di business invece che sulla forma JSON.
    body: dict[str, Any] = {
        "request_name": request_name,
        "reftime": {"from": date_from, "to": date_to},
        "dataset_names": dataset_names,
        "filters": {"run": run_filter} if run_filter else {},
        "period-settings": {"every": every, "period": period},
        "on-data-ready": on_data_ready,
        "opendata": opendata,
    }
    # Costruiamo il payload esattamente nel formato atteso dall'endpoint, cosi la
    # verifica riguarda la logica e non dettagli casuali di input.
    return json.dumps(body)