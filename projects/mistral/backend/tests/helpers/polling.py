"""Piccolo helper di polling per asserzioni su stati che si aggiornano in ritardo.

La suite evita quando possibile le chiamate ``sleep()`` alla cieca. Questo helper
riprova un predicato finche non restituisce un valore truthy o scade il timeout,
il che rende i test piu chiari e meno fragili delle attese fisse.
"""

from __future__ import annotations

import time
from typing import Any, Callable


def wait_until(
    predicate: Callable[[], Any],
    timeout: float = 60,
    interval: float = 2,
    message: str = "Condition not met within timeout",
) -> Any:
    """Interroga ``predicate`` finche restituisce un valore truthy o scade il timeout.

    Restituisce il primo valore truthy prodotto dal predicato, cosi il chiamante
    puo riusare subito l'oggetto trovato. Se prima si raggiunge la scadenza,
    solleva ``AssertionError`` con il messaggio indicato.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError(message)
