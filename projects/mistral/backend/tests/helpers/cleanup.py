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


class CleanupError(Exception):
    """Riassume piu errori avvenuti durante lo stesso teardown."""

    def __init__(self, errors: list[Exception]) -> None:
        self.errors = errors
        details = "; ".join(f"{type(e).__name__}: {e}" for e in errors)
        super().__init__(f"{len(errors)} cleanup actions failed: {details}")


class CleanupRegistry:
    """Raccoglie le azioni di cleanup e le esegue in ordine LIFO (dall'ultima).

    Il teardown LIFO conta perche i test creano spesso risorse dipendenti tra loro:
    per esempio i file vanno cancellati prima della directory che li contiene, e
    le richieste devono sparire prima che venga rimosso l'utente proprietario.
    Usato dalla fixture ``cleanup_registry`` (tests/conftest.py).
    """

    def __init__(self) -> None:
        """Parte con uno stack di cleanup vuoto per il test corrente."""
        self._actions: list[tuple[Callable[[], None], bool]] = []

    def add(self, fn: Callable[[], None], *, barrier: bool = False) -> None:
        """Aggiunge al registro una callback di teardown per il test corrente.

        I test usano questo metodo per i passi di cleanup che non si riducono a un
        semplice percorso su filesystem, come cancellare risorse via API o
        ripristinare un'impostazione globale modificata con monkeypatch.

        Con ``barrier=True`` le azioni registrate prima (quindi eseguite dopo)
        dipendono da questa: se fallisce non vengono eseguite e restano nel registro
        insieme alla barriera, per esempio i dati di un utente finche i worker non
        confermano di aver fermato i suoi task.
        """
        self._actions.append((fn, barrier))

    def add_path(self, path: str | Path) -> None:
        """Registra un percorso su filesystem da rimuovere ricorsivamente.

        I test creano spesso directory di output degli utenti o template estratti.
        Questo helper incapsula quei percorsi in una callback di cleanup, cosi i
        chiamanti non devono ripetere lo stesso schema con ``shutil.rmtree``. Se il
        percorso resta su disco il cleanup fallisce, invece di riuscire in silenzio.
        """
        p = Path(path)

        def remove_path() -> None:
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
            if p.exists():
                raise RuntimeError(f"Cleanup was not able to remove {p}")

        self.add(remove_path)

    def run(self) -> None:
        """Esegue le azioni di cleanup registrate in ordine inverso.

        Ogni azione viene tolta dal registro dopo l'esecuzione, riuscita o no, cosi
        un nuovo ``run`` non la ripete. Un errore non ferma le azioni indipendenti
        successive; solo il fallimento di una barriera (vedi ``add``) ferma il
        teardown, lasciando nel registro la barriera e le azioni che ne dipendono.

        Qui il registro volutamente non ingoia le eccezioni: se il teardown e rotto,
        il fallimento deve essere visibile, cosi la suite viene corretta invece di
        accumulare in silenzio stato sporco. Un solo errore viene rilanciato cosi
        com'e, piu errori insieme con ``CleanupError``.
        """
        errors: list[Exception] = []
        while self._actions:
            action, barrier = self._actions[-1]
            try:
                action()
            except Exception as exc:
                errors.append(exc)
                if barrier:
                    break
            self._actions.pop()
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise CleanupError(errors) from errors[0]
