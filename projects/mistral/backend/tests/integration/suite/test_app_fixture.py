"""Test della fixture ``app`` della suite (tests/conftest.py).

restapi avvolge ``Connection.execute`` e ``Connection._execute_context`` con
``catch_db_exceptions`` a ogni ``create_app`` e la suite crea un'app per test: senza
``unwrap_connection_methods`` la catena di wrapper crescerebbe di un livello per test
fino al ``RecursionError`` (oltre ~300 test nella stessa sessione).
"""

from __future__ import annotations

import pytest
from restapi.connectors.sqlalchemy import catch_db_exceptions
from sqlalchemy.engine import Connection

from mistral.tests.conftest import unwrap_connection_methods

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def _wrapping_depth(function) -> int:
    """Conta i livelli di wrapper (functools.wraps) attorno a ``function``."""
    depth = 0
    while hasattr(function, "__wrapped__"):
        function = function.__wrapped__
        depth += 1
    return depth


def test_wrappers_of_previous_apps_are_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I wrapper lasciati dalle app dei test precedenti vengono tolti tutti."""
    # arrange - simula tre app create in precedenza
    for name in ("execute", "_execute_context"):
        method = getattr(Connection, name)
        for _ in range(3):
            method = catch_db_exceptions(method)
        monkeypatch.setattr(Connection, name, method)

    # act
    unwrap_connection_methods()

    # assert
    assert _wrapping_depth(Connection.execute) == 0
    assert _wrapping_depth(Connection._execute_context) == 0
