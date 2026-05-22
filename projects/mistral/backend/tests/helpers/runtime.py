"""Session-wide runtime helpers for resources that outlive a single test function.

The suite distinguishes between two kinds of state:

- heavy or reusable state that should live for the whole pytest session,
- mutable state that belongs only to one test and must be cleaned afterwards.

``TestRuntime`` handles the first category, while ``TestContext`` provides a
small cleanup-aware container for the second.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable


class TestContextCleanupError(RuntimeError):
    """Aggregate error raised when one or more context cleanup actions fail."""

    def __init__(self, errors: list[Exception]) -> None:
        """Store the collected cleanup errors and build a compact summary message."""
        self.errors = errors
        details = "; ".join(
            f"{type(err).__name__}: {err}" for err in errors[:3]
        )
        if len(errors) > 3:
            details += f"; ... ({len(errors) - 3} more)"
        super().__init__(
            f"TestContext cleanup failed with {len(errors)} error(s): {details}"
        )


@dataclass
class TestContext:
    """Per-test state holder that can accumulate teardown callbacks.

    The object is intentionally lightweight. Tests or fixtures can attach cleanup
    callbacks as they create mutable resources, and then ask the context to run
    them all at teardown time.
    """

    cleanup_actions: list[Callable[[], None]] = field(default_factory=list)
    created_users: list[str] = field(default_factory=list)
    created_request_ids: list[int] = field(default_factory=list)
    created_schedule_ids: list[str] = field(default_factory=list)
    created_paths: list[str] = field(default_factory=list)

    def add_cleanup(self, fn: Callable[[], None]) -> None:
        """Append one teardown callback to the current test's cleanup stack."""
        self.cleanup_actions.append(fn)

    def cleanup(self) -> None:
        """Run registered teardowns and aggregate any cleanup failures.

        Cleanup callbacks are executed in reverse order so resources are dismantled
        in a dependency-safe sequence. If one or more callbacks fail, the method
        raises a single aggregated exception with a compact summary.
        """
        errors: list[Exception] = []
        while self.cleanup_actions:
            fn = self.cleanup_actions.pop()
            try:
                fn()
            except Exception as exc:
                errors.append(exc)

        if errors:
            raise TestContextCleanupError(errors)


class TestRuntime:
    """Session-scoped singleton that caches reusable test resources.

    This object avoids repeating expensive lookups, such as resolving dataset ids,
    and also offers a safe context manager for temporarily overriding module or
    class attributes during a test.
    """

    _instance: TestRuntime | None = None
    _lock = RLock()

    def __new__(cls) -> TestRuntime:
        """Instantiate the singleton once and reuse it for the whole session."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._dataset_cache = {}
        return cls._instance

    def dataset_id(self, db: Any, name: str) -> int:
        """Resolve one dataset identifier once and cache it for future lookups.

        Tests often need the numeric database id for a dataset that they refer to
        symbolically by name or ``arkimet_id``. This helper turns that symbolic
        name into the numeric id and stores the result in the runtime cache.
        """
        if name not in self._dataset_cache:
            ds = db.Datasets.query.filter(
                (db.Datasets.name == name) | (db.Datasets.arkimet_id == name)
            ).first()
            if ds is None:
                raise LookupError(f"Dataset '{name}' not found")
            self._dataset_cache[name] = ds.id
        return self._dataset_cache[name]

    @contextmanager
    def override_attr(self, target: Any, attr: str, value: Any):
        """Temporarily override an attribute and restore the original afterwards.

        This is used by several test domains to patch environment-dependent class
        attributes for the duration of a fixture or scenario without leaking the
        override to later tests.
        """
        with self._lock:
            old_value = getattr(target, attr)
            setattr(target, attr, value)
        try:
            yield
        finally:
            with self._lock:
                setattr(target, attr, old_value)

    def new_context(self) -> TestContext:
        """Return a fresh per-test context ready to collect cleanup callbacks."""
        return TestContext()
