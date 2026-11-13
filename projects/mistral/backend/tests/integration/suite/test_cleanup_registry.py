"""Test del registro di cleanup della suite (tests/helpers/cleanup.py).

Usano solo callback locali e directory temporanee: nessun worker, DB o servizio.
"""

from __future__ import annotations

import pytest

import mistral.tests.helpers.cleanup as cleanup_module
from mistral.tests.helpers.cleanup import CleanupError, CleanupRegistry

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def _failing(message: str):
    def action() -> None:
        raise RuntimeError(message)

    return action


def test_cleanup_runs_the_actions_in_lifo_order() -> None:
    """Le azioni vengono eseguite dall'ultima registrata alla prima."""
    # arrange
    calls: list[str] = []
    registry = CleanupRegistry()
    for name in ("first", "second", "third"):
        registry.add(lambda name=name: calls.append(name))

    # act
    registry.run()

    # assert
    assert calls == ["third", "second", "first"]


def test_cleanup_error_does_not_stop_the_independent_actions() -> None:
    """Un errore viene rilanciato, ma le azioni indipendenti successive girano."""
    # arrange
    calls: list[str] = []
    registry = CleanupRegistry()
    registry.add(lambda: calls.append("first"))
    registry.add(_failing("second failed"))
    registry.add(lambda: calls.append("third"))

    # act
    with pytest.raises(RuntimeError, match="second failed"):
        registry.run()

    # assert
    assert calls == ["third", "first"]


def test_cleanup_reports_every_error() -> None:
    """Piu errori nello stesso teardown sono riportati tutti insieme."""
    # arrange
    registry = CleanupRegistry()
    registry.add(_failing("first failed"))
    registry.add(_failing("second failed"))

    # act
    with pytest.raises(CleanupError) as exc_info:
        registry.run()

    # assert
    assert [str(error) for error in exc_info.value.errors] == [
        "second failed",
        "first failed",
    ]


def test_cleanup_does_not_repeat_the_executed_actions() -> None:
    """Un nuovo run non riesegue le azioni gia eseguite, riuscite o fallite."""
    # arrange
    calls: list[str] = []
    registry = CleanupRegistry()
    registry.add(lambda: calls.append("done"))
    registry.add(_failing("failed once"))
    with pytest.raises(RuntimeError):
        registry.run()

    # act
    registry.run()

    # assert
    assert calls == ["done"]


def test_cleanup_barrier_failure_blocks_the_dependent_actions() -> None:
    """Se una barriera fallisce, le azioni che ne dipendono non vengono eseguite.

    E il caso dei worker reali: senza la conferma che i task dell'utente sono fermi,
    i dati dell'utente non vanno cancellati. Un run successivo riprova la barriera.
    """
    # arrange
    calls: list[str] = []
    attempts: list[int] = []

    def stop_workers() -> None:
        attempts.append(1)
        if len(attempts) == 1:
            raise AssertionError("workers did not confirm")
        calls.append("workers stopped")

    registry = CleanupRegistry()
    registry.add(lambda: calls.append("user data deleted"))
    registry.add(stop_workers, barrier=True)
    registry.add(lambda: calls.append("independent"))

    # act
    with pytest.raises(AssertionError, match="workers did not confirm"):
        registry.run()
    blocked_calls = list(calls)
    registry.run()

    # assert
    assert blocked_calls == ["independent"]
    assert calls == ["independent", "workers stopped", "user data deleted"]


def test_cleanup_add_path_removes_the_directory(tmp_path) -> None:
    """add_path rimuove ricorsivamente la directory registrata."""
    # arrange
    target = tmp_path / "user-dir"
    target.joinpath("outputs").mkdir(parents=True)
    target.joinpath("outputs", "file.txt").write_text("synthetic", encoding="utf-8")
    registry = CleanupRegistry()
    registry.add_path(target)

    # act
    registry.run()

    # assert
    assert not target.exists()


def test_cleanup_add_path_fails_when_the_path_is_left_on_disk(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un errore di rimozione non diventa un successo silenzioso."""
    # arrange
    target = tmp_path / "undeletable"
    target.mkdir()
    # rmtree con ignore_errors=True non segnala errori: qui non rimuove nulla.
    monkeypatch.setattr(cleanup_module.shutil, "rmtree", lambda *args, **kwargs: None)
    registry = CleanupRegistry()
    registry.add_path(target)

    # act / assert
    with pytest.raises(RuntimeError, match="not able to remove"):
        registry.run()
    assert target.exists()
