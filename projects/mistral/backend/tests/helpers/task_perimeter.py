"""Confina i task reali che scorrono tabelle globali ai soli dati di un test.

Alcuni task Celery sono globali per costruzione: ``automatic_cleanup`` visita
ogni utente, richiesta e directory di download, mentre
``launch_all_on_data_ready_extractions`` visita ogni schedule. Eseguirli senza
modifiche da un test puo cambiare righe e file che il test non ha creato.

Questi helper mantengono il codice reale del task e le vere scritture ORM, ma
sostituiscono il connettore del database visto dal modulo del task con una
facade ristretta che espone solo le righe registrate dal test. Le facade sono
fail-closed: un tipo di accesso non supportato esplicitamente solleva un errore
invece di leggere un'intera tabella.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable

import pytest
from restapi.connectors import sqlalchemy
from sqlalchemy import false

import mistral.tasks.on_data_ready_extractions as on_data_ready_task
import mistral.tasks.requests_cleanup as requests_cleanup_task


class OutsideTestPerimeterError(AssertionError):
    """Sollevata quando un task confinato cerca dati fuori dal perimetro del test."""


def _as_ids(values: Iterable[int | str]) -> set[int]:
    """Converte gli id ricevuti (interi o stringhe) in un insieme di interi."""
    return {int(value) for value in values}


def _restrict(query: Any, column: Any, allowed_ids: set[int]) -> Any:
    """Filtra ``query`` alle sole righe con ``column`` tra gli id ammessi."""
    # Un perimetro vuoto deve produrre zero righe, non l'intera tabella.
    if not allowed_ids:
        return query.filter(false())
    return query.filter(column.in_(sorted(allowed_ids)))


class _ForwardOnly:
    """Proxy che inoltra solo gli attributi consentiti esplicitamente al task."""

    def __init__(self, target: Any, allowed: frozenset[str], label: str) -> None:
        self._target = target
        self._allowed = allowed
        self._label = label

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._allowed:
            raise OutsideTestPerimeterError(
                f"{self._label}.{name} non previsto dal perimetro del test"
            )
        return getattr(self._target, name)


class _ScopedModel:
    """Proxy di modello la cui ``query`` restituisce solo righe degli id registrati."""

    def __init__(
        self, model: Any, column: Any, allowed_ids: Callable[[], set[int]]
    ) -> None:
        self._model = model
        self._column = column
        self._allowed_ids = allowed_ids

    @property
    def query(self) -> Any:
        return _restrict(self._model.query, self._column, self._allowed_ids())

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        # Le colonne servono ai filtri e agli ordinamenti costruiti dal task.
        return getattr(self._model, name)


class _LookupByRegisteredId:
    """Sostituto della query che permette solo ``get()`` sugli id registrati."""

    def __init__(
        self, query: Any, allowed_ids: Callable[[], set[int]], label: str
    ) -> None:
        self._query = query
        self._allowed_ids = allowed_ids
        self._label = label

    def get(self, ident: Any) -> Any:
        if int(ident) not in self._allowed_ids():
            raise OutsideTestPerimeterError(
                f"{self._label} {ident} non registrata dal test"
            )
        return self._query.get(ident)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        raise OutsideTestPerimeterError(
            f"{self._label}.query.{name} non previsto dal perimetro del test"
        )


class _RequestLookupModel:
    """Proxy di Request: colonne usabili, query limitate agli id registrati."""

    def __init__(self, model: Any, allowed_ids: Callable[[], set[int]]) -> None:
        self._model = model
        self._allowed_ids = allowed_ids

    @property
    def query(self) -> _LookupByRegisteredId:
        return _LookupByRegisteredId(self._model.query, self._allowed_ids, "Request")

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._model, name)


class _CleanupSession(_ForwardOnly):
    """Proxy di sessione per le query su Request eseguite dal task di cleanup."""

    def __init__(
        self,
        session: Any,
        request_model: Any,
        request_proxy: _RequestLookupModel,
        allowed_ids: Callable[[], set[int]],
    ) -> None:
        super().__init__(session, frozenset({"commit", "delete"}), "session")
        self._request_model = request_model
        self._request_proxy = request_proxy
        self._request_ids = allowed_ids

    def query(self, *entities: Any) -> Any:
        if len(entities) == 1 and entities[0] is self._request_model.id:
            return _restrict(
                self._target.query(self._request_model.id),
                self._request_model.id,
                self._request_ids(),
            )
        if len(entities) == 1 and entities[0] is self._request_proxy:
            return _LookupByRegisteredId(
                self._target.query(self._request_model), self._request_ids, "Request"
            )
        raise OutsideTestPerimeterError(
            f"session.query{entities} non previsto dal perimetro del test"
        )


@dataclass
class RequestsCleanupPerimeter:
    """Utenti, richieste e root di download visibili ad ``automatic_cleanup``."""

    download_root: Path
    user_ids: set[int] = field(default_factory=set)
    request_ids: set[int] = field(default_factory=set)

    def allow(
        self,
        *,
        user_ids: Iterable[int | str] = (),
        request_ids: Iterable[int | str] = (),
    ) -> None:
        """Registra le righe create dal test che il task puo elaborare."""
        self.user_ids.update(_as_ids(user_ids))
        self.request_ids.update(_as_ids(request_ids))

    def registered_user_ids(self) -> set[int]:
        return set(self.user_ids)

    def registered_request_ids(self) -> set[int]:
        return set(self.request_ids)


class _RequestsCleanupDatabase(_ForwardOnly):
    """Facade del database vista da ``automatic_cleanup`` dentro un test."""

    def __init__(self, db: Any, perimeter: RequestsCleanupPerimeter) -> None:
        super().__init__(db, frozenset(), "db")
        request_ids = perimeter.registered_request_ids
        self.User = _ScopedModel(db.User, db.User.id, perimeter.registered_user_ids)
        self.Request = _RequestLookupModel(db.Request, request_ids)
        self.FileOutput = _ScopedModel(
            db.FileOutput, db.FileOutput.request_id, request_ids
        )
        self.session = _CleanupSession(db.session, db.Request, self.Request, request_ids)


def confine_requests_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    download_root: Path,
) -> RequestsCleanupPerimeter:
    """Fa vedere ad ``automatic_cleanup`` solo le righe registrate e ``download_root``.

    La scansione dei file orfani viene rediretta su ``download_root``. Gli output
    delle richieste registrate vengono comunque rimossi dal vero helper del
    repository; si trovano nelle directory degli utenti temporanei creati dal test.
    """
    download_root.mkdir(parents=True, exist_ok=True)
    perimeter = RequestsCleanupPerimeter(download_root=download_root)

    def confined_database(*args: Any, **kwargs: Any) -> _RequestsCleanupDatabase:
        return _RequestsCleanupDatabase(
            sqlalchemy.get_instance(*args, **kwargs), perimeter
        )

    monkeypatch.setattr(
        requests_cleanup_task,
        "sqlalchemy",
        SimpleNamespace(get_instance=confined_database),
    )
    monkeypatch.setattr(requests_cleanup_task, "DOWNLOAD_DIR", download_root)
    return perimeter


class _DataReadyDatabase(_ForwardOnly):
    """Facade del database vista da ``launch_all_on_data_ready_extractions``."""

    def __init__(self, db: Any, schedule_ids: Callable[[], set[int]]) -> None:
        super().__init__(db, frozenset(), "db")
        self.Schedule = _ScopedModel(db.Schedule, db.Schedule.id, schedule_ids)
        self.Request = _ScopedModel(db.Request, db.Request.schedule_id, schedule_ids)
        self.session = _ForwardOnly(db.session, frozenset({"merge"}), "session")


def confine_data_ready_schedules(
    monkeypatch: pytest.MonkeyPatch,
    schedule_ids: Iterable[int | str],
) -> None:
    """Fa considerare al launcher data-ready solo le schedule del test."""
    allowed = _as_ids(schedule_ids)

    def registered_schedule_ids() -> set[int]:
        return set(allowed)

    def confined_database(*args: Any, **kwargs: Any) -> _DataReadyDatabase:
        return _DataReadyDatabase(
            sqlalchemy.get_instance(*args, **kwargs), registered_schedule_ids
        )

    monkeypatch.setattr(
        on_data_ready_task,
        "sqlalchemy",
        SimpleNamespace(get_instance=confined_database),
    )
