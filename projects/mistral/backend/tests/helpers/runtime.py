"""Session-wide runtime helpers for reusable state shared across tests."""

from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Any


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
                # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
                # succedere quando lo stato non e quello ideale.
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._dataset_cache = {}
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return cls._instance

    def dataset_id(self, db: Any, name: str) -> int:
        """Resolve one dataset identifier once and cache it for future lookups.

        Tests often need the numeric database id for a dataset that they refer to
        symbolically by name or ``arkimet_id``. This helper turns that symbolic
        name into the numeric id and stores the result in the runtime cache.
        """
        if name not in self._dataset_cache:
            # Leggiamo lo stato dal database di test per collegare la risposta API agli
            # effetti persistiti dal backend.
            ds = db.Datasets.query.filter(
                (db.Datasets.name == name) | (db.Datasets.arkimet_id == name)
            ).first()
            # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
            # succedere quando lo stato non e quello ideale.
            if ds is None:
                raise LookupError(f"Dataset '{name}' not found")
            self._dataset_cache[name] = ds.id
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return self._dataset_cache[name]

    @contextmanager
    def override_attr(self, target: Any, attr: str, value: Any):
        """Temporarily override an attribute and restore the original afterwards.

        This is used by several test domains to patch environment-dependent class
        attributes for the duration of a fixture or scenario without leaking the
        override to later tests.
        """
        # Entriamo nel blocco operativo dell'helper condiviso, mantenendo
        # esplicito quale stato viene letto o prodotto.
        with self._lock:
            old_value = getattr(target, attr)
            setattr(target, attr, value)
        try:
            # Cediamo la fixture al test; quando il test termina, il codice sotto il
            # yield eseguira il teardown.
            yield
        finally:
            with self._lock:
                setattr(target, attr, old_value)

