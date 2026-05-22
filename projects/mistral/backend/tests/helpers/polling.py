"""Small polling helper used when test assertions depend on eventual consistency.

The suite avoids blind ``sleep()`` calls whenever possible. This helper retries a
predicate until it becomes truthy or a timeout expires, which makes tests both
clearer and less brittle than fixed waits.
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
    """Poll ``predicate`` until it returns a truthy value or the timeout expires.

    The helper returns the first truthy value produced by the predicate so callers
    can immediately reuse the discovered object. If the deadline is reached first,
    it raises ``AssertionError`` with the provided message.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError(message)
