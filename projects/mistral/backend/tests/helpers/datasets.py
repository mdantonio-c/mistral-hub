"""Small helpers that make dataset integration tests less environment-dependent.

The dataset catalog exposed by the running test environment can vary depending
on seed data and runtime configuration. These helpers avoid hard-coding more
than necessary when a test simply needs "one public dataset that really exists
right now".
"""

from __future__ import annotations

from typing import Any

import pytest


def first_public_dataset_id(datasets: list[dict[str, Any]]) -> str:
    """Return the identifier of a public dataset present in the current catalog.

    The ``/datasets`` endpoint returns dictionaries that already tell the test
    whether each dataset is public. This helper scans that payload and extracts a
    usable identifier for follow-up requests like ``GET /datasets/<id>``.

    If the environment exposes no public dataset at all, the test is skipped
    because there is nothing meaningful left to verify for that scenario.
    """
    for dataset in datasets:
        dataset_id = dataset.get("id")
        if dataset.get("is_public") is True and dataset_id:
            return str(dataset_id)
    pytest.skip("No public dataset is available in this environment")