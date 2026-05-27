"""Local helpers for dataset integration tests.

This module keeps small utility functions close to the dataset integration
tests. The logic is intentionally simple and aims to answer a practical testing
question: "which public dataset can I safely use in this runtime right now?"
"""

from __future__ import annotations

from typing import Any

import pytest


def first_public_dataset_id(datasets: list[dict[str, Any]]) -> str:
    """Return the identifier of a public dataset from the current catalog payload.

    Dataset integration tests sometimes need to follow a catalog listing with a
    ``GET /datasets/<id>`` request. This helper picks the first dataset that is
    already marked as public by the API response. If the runtime exposes no
    public dataset, the scenario is skipped because there is no valid target for
    that contract.
    """
    # Entriamo nel blocco operativo dell'helper catalogo dataset, mantenendo esplicito
    # quale stato viene letto o prodotto.
    for dataset in datasets:
        dataset_id = dataset.get("id")
        if dataset.get("is_public") is True and dataset_id:
            # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
            # direttamente nelle asserzioni.
            return str(dataset_id)
    # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
    # contratto non sarebbe verificabile in modo significativo.
    pytest.skip("No public dataset is available in this environment")