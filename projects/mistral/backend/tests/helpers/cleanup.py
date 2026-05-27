"""Deterministic teardown helpers for resources created during tests.

The modularized suite creates temporary users, schedules, requests, files, and
directories. This registry gives every test a simple place to register cleanup
actions so teardown happens in reverse order even when assertions fail midway.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable


class CleanupRegistry:
    """Collect cleanup actions and execute them in last-in, first-out order.

    LIFO teardown matters because tests often create dependent resources. For
    example, files may need to be deleted before their parent directory, and
    requests may need to disappear before the owning user is removed.
    """

    def __init__(self) -> None:
        """Start with an empty cleanup stack for the current test."""
        # Memorizziamo nello stato dell'oggetto i valori che i metodi successivi
        # useranno durante il test.
        self._actions: list[Callable[[], None]] = []

    def add(self, fn: Callable[[], None]) -> None:
        """Append one teardown callback to the registry for the current test.

        Tests use this method for cleanup steps that cannot be expressed as a
        simple filesystem path, such as deleting API resources or restoring a
        monkeypatched global setting.
        """
        # Entriamo nel blocco operativo dell'helper condiviso, mantenendo
        # esplicito quale stato viene letto o prodotto.
        self._actions.append(fn)

    def add_path(self, path: str | Path) -> None:
        """Register a filesystem path for best-effort recursive removal.

        Tests often create user output directories or extracted templates. This
        helper wraps those paths into a cleanup callback so callers do not need to
        repeat the same ``shutil.rmtree`` pattern.
        """
        # Entriamo nel blocco operativo dell'helper condiviso, mantenendo
        # esplicito quale stato viene letto o prodotto.
        p = Path(path)
        self.add(lambda: shutil.rmtree(p, ignore_errors=True) if p.exists() else None)

    def run(self) -> None:
        """Execute all registered cleanup actions in reverse order and clear them.

        The registry deliberately does not swallow exceptions here: if teardown is
        broken, the failure should be visible so the suite can be fixed instead of
        silently accumulating dirty state.
        """
        # Entriamo nel blocco operativo dell'helper condiviso, mantenendo
        # esplicito quale stato viene letto o prodotto.
        for action in reversed(self._actions):
            action()
        self._actions.clear()
