"""Helper di teardown deterministico per le risorse create durante i test.

La suite crea utenti, schedule, richieste, file e directory temporanei. Questo
registro offre a ogni test un unico punto dove registrare le azioni di cleanup,
cosi il teardown avviene in ordine inverso anche quando un'asserzione fallisce a
meta test.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable


class CleanupRegistry:
    """Raccoglie le azioni di cleanup e le esegue in ordine LIFO (dall'ultima).

    Il teardown LIFO conta perche i test creano spesso risorse dipendenti tra loro:
    per esempio i file vanno cancellati prima della directory che li contiene, e
    le richieste devono sparire prima che venga rimosso l'utente proprietario.
    Usato dalla fixture ``cleanup_registry`` (tests/conftest.py).
    """

    def __init__(self) -> None:
        """Parte con uno stack di cleanup vuoto per il test corrente."""
        self._actions: list[Callable[[], None]] = []

    def add(self, fn: Callable[[], None]) -> None:
        """Aggiunge al registro una callback di teardown per il test corrente.

        I test usano questo metodo per i passi di cleanup che non si riducono a un
        semplice percorso su filesystem, come cancellare risorse via API o
        ripristinare un'impostazione globale modificata con monkeypatch.
        """
        self._actions.append(fn)

    def add_path(self, path: str | Path) -> None:
        """Registra un percorso su filesystem da rimuovere ricorsivamente (best-effort).

        I test creano spesso directory di output degli utenti o template estratti.
        Questo helper incapsula quei percorsi in una callback di cleanup, cosi i
        chiamanti non devono ripetere lo stesso schema con ``shutil.rmtree``.
        """
        p = Path(path)
        self.add(lambda: shutil.rmtree(p, ignore_errors=True) if p.exists() else None)

    def run(self) -> None:
        """Esegue tutte le azioni di cleanup registrate in ordine inverso e le svuota.

        Qui il registro volutamente non ingoia le eccezioni: se il teardown e rotto,
        il fallimento deve essere visibile, cosi la suite viene corretta invece di
        accumulare in silenzio stato sporco.
        """
        for action in reversed(self._actions):
            action()
        self._actions.clear()
