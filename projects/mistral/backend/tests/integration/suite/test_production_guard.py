"""Test del blocco della suite negli stack di produzione (tests/conftest.py)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mistral.tests import conftest as suite_conftest

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_suite_does_not_start_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con APP_MODE=production la sessione termina prima di raccogliere i test."""
    # arrange
    monkeypatch.setenv("APP_MODE", "production")
    registered_markers: list[tuple] = []
    config = SimpleNamespace(
        addinivalue_line=lambda *args: registered_markers.append(args)
    )

    # act
    with pytest.raises(pytest.exit.Exception) as exc_info:
        suite_conftest.pytest_configure(config)

    # assert
    assert exc_info.value.returncode == pytest.ExitCode.USAGE_ERROR
    assert "production" in str(exc_info.value)
    assert registered_markers == []


def test_suite_starts_on_test_stacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fuori dalla produzione la configurazione registra i marker e prosegue."""
    # arrange
    monkeypatch.setenv("APP_MODE", "test")
    registered_markers: list[tuple] = []
    config = SimpleNamespace(
        addinivalue_line=lambda *args: registered_markers.append(args)
    )

    # act
    suite_conftest.pytest_configure(config)

    # assert
    assert registered_markers
