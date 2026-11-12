"""Helper di runtime a livello di sessione per stato riusabile condiviso tra i test."""

from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Any


class TestRuntime:
    """Singleton di sessione che tiene in cache risorse di test riusabili.

    Evita di ripetere ricerche costose, come la risoluzione degli id dei dataset,
    e offre anche un context manager sicuro per sovrascrivere temporaneamente
    attributi di moduli o classi durante un test. Usato dalla fixture
    ``test_runtime``.
    """

    _instance: TestRuntime | None = None
    _lock = RLock()

    def __new__(cls) -> TestRuntime:
        """Crea il singleton una sola volta e lo riusa per tutta la sessione."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._dataset_cache = {}
        return cls._instance

    def dataset_id(self, db: Any, name: str) -> int:
        """Risolve una sola volta l'id di un dataset e lo mette in cache.

        I test hanno spesso bisogno dell'id numerico nel database di un dataset a
        cui si riferiscono per nome o per ``arkimet_id``. Questo helper converte
        quel nome simbolico nell'id numerico (tabella ``Datasets``) e salva il
        risultato nella cache di runtime.
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
        """Sovrascrive temporaneamente un attributo e poi ripristina l'originale.

        Diversi domini di test lo usano per modificare attributi di classe che
        dipendono dall'ambiente, per la durata di una fixture o di uno scenario,
        senza che la modifica resti attiva nei test successivi.
        """
        with self._lock:
            old_value = getattr(target, attr)
            setattr(target, attr, value)
        try:
            yield
        finally:
            with self._lock:
                setattr(target, attr, old_value)

