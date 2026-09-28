# EXTENSION TRACEABILITY: added by coverage extension prompt 04
# EXTENSION SCOPE: integrates the refactored suite without modifying legacy baseline
# EXTENSION DATA WINDOW: no real runtime data required; uses DB-seeded rows and fake Celery
# EXTENSION RUNTIME: deterministic fake schedule rows and fake Celery send; no async dependencies
# EXTENSION CLEANUP: schedule rows cleaned via cleanup_registry
#
# This module extends the tasks integration area with tests for:
# - launch_all_on_data_ready_extractions skips schedule with zero datasets
# - launch_all_on_data_ready_extractions skips schedule with multiple datasets
# - launch_all_on_data_ready_extractions skips schedule with invalid run filter decode
# - launch_all_on_data_ready_extractions raises SystemError on Celery send failure
#
# The baseline test_schedule_opendata_bridge.py already covers the happy path data-ready
# flow inline. This extension focuses on the edge cases inside the task function that
# skip or fail schedules without sending an extraction request.

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
import restapi.connectors.celery as celery_connector
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

from mistral.tasks.on_data_ready_extractions import (
    launch_all_on_data_ready_extractions,
)
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


# =============================================================================
# Local helper: seed schedule rows with controlled args for edge cases
# =============================================================================


def seed_schedule_for_data_ready(
    db: Any,
    faker: Faker,
    user_id: int,
    *,
    enabled: bool = True,
    on_data_ready: bool = True,
    datasets: list[str],
    run_filter: list[dict[str, Any]] | None = None,
) -> int:
    """Seed one schedule row configured for data-ready task edge cases."""
    # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
    # quando l'endpoint POST richiederebbe troppo contesto esterno.
    schedule_row = db.Schedule(
        user_id=user_id,
        name=faker.pystr(),
        args={
            "datasets": datasets,
            "reftime": None,
            "filters": {"run": run_filter} if run_filter else None,
            "postprocessors": None,
            "output_format": None,
            "only_reliable": False,
            "pushing_queue": None,
        },
        is_enabled=enabled,
        on_data_ready=on_data_ready,
        opendata=False,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(schedule_row)
    db.session.commit()
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return schedule_row.id


def delete_schedule_row(db: Any, schedule_id: int) -> None:
    """Delete one seeded schedule row from the database if still present."""
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    schedule = db.Schedule.query.get(schedule_id)
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if schedule is not None:
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.delete(schedule)
        db.session.commit()


@pytest.fixture
def data_ready_task_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Create a temporary user used as schedule owner by task-edge scenarios."""
    # Prepariamo un utente reale del DB di test invece di dipendere da account seedati:
    # il task legge `user_id` dalla schedule e non richiede privilegi speciali qui.
    base = BaseTests()
    user = create_authenticated_test_user(base, client, {"allowed_schedule": True})
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    return user


# =============================================================================
# Tests: launch_all_on_data_ready_extractions edge cases
# =============================================================================


class TestOnDataReadyTaskEdges:
    """Verify the data-ready task skips or fails schedules with invalid configurations."""

    def test_skip_schedule_with_zero_datasets(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """launch_all_on_data_ready_extractions must skip schedules with empty dataset list."""
        # arrange - seed schedule with zero datasets
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=[],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - run task with model matching the empty dataset schedule
        # Eseguiamo l'helper direttamente per verificare che gestisca correttamente il
        # caso limite.
        launch_all_on_data_ready_extractions.run(
            "lm5",
            datetime(2021, 10, 19, 0, 0, 0),
        )

        # assert - Celery send_task was never called
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert fake_celery.celery_app.send_task.call_count == 0

    def test_skip_schedule_with_multiple_datasets(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """launch_all_on_data_ready_extractions must skip schedules with multiple datasets."""
        # arrange - seed schedule with multiple datasets
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=["lm5", "lm2.2"],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - run task with model matching the multi-dataset schedule
        # Eseguiamo l'helper direttamente per verificare che gestisca correttamente il
        # caso limite.
        launch_all_on_data_ready_extractions.run(
            "lm5",
            datetime(2021, 10, 19, 0, 0, 0),
        )

        # assert - Celery send_task was never called
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert fake_celery.celery_app.send_task.call_count == 0

    def test_skip_schedule_with_invalid_run_filter_decode(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """launch_all_on_data_ready_extractions must skip schedules with malformed run filter."""
        # arrange - seed schedule with invalid run filter
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=["lm5"],
            run_filter=[{"invalid_arkimet_run": "broken"}],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        # act - run task with model matching the schedule with broken run filter
        # Eseguiamo l'helper direttamente per verificare che gestisca correttamente il
        # caso limite.
        launch_all_on_data_ready_extractions.run(
            "lm5",
            datetime(2021, 10, 19, 0, 0, 0),
        )

        # assert - Celery send_task was never called
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        assert fake_celery.celery_app.send_task.call_count == 0

    def test_celery_send_failure_raises_system_error(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """launch_all_on_data_ready_extractions must raise SystemError when Celery send fails."""
        # arrange - seed valid schedule
        # Costruiamo lo stato controllato richiesto dal test, usando un DB seed diretto
        # quando l'endpoint POST richiederebbe troppo contesto esterno.
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=["lm5"],
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
        # test resta deterministico.
        fake_celery = MagicMock()
        fake_celery.celery_app.send_task.side_effect = Exception("Celery broker unreachable")
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)

        def raise_original_task_error_EXT(*args: Any, exception: Exception, **kwargs: Any):
            """Expose the task error without sending Celery failure events.

            Directly calling a decorated Celery task in a deterministic test still
            goes through the restapi failure hook. The production hook emits a
            Celery event through the broker; here that would test broker reachability
            instead of the on-data-ready branch. Re-raising the original exception
            keeps the assertion on the backend contract requested by this module.
            """
            # Manteniamo il fake confinato al test: il monkeypatch verra ripristinato
            # da pytest e non nasconde altri failure hook della suite.
            raise exception

        monkeypatch.setattr(
            celery_connector,
            "mark_task_as_failed",
            raise_original_task_error_EXT,
        )

        # act & assert - task raises SystemError on Celery send failure
        # Controlliamo il contratto specifico dello scenario, non soltanto che il
        # codice sia arrivato fin qui senza eccezioni.
        with pytest.raises(SystemError, match="Unable to submit the data ready request extraction"):
            launch_all_on_data_ready_extractions.run(
                "lm5",
                datetime(2021, 10, 19, 0, 0, 0),
            )
