# Finestra dati: nessun dato runtime reale; usa righe schedule inserite nel DB e un
# fake Celery.
# Runtime: righe schedule deterministiche e invio Celery fake; il task vede solo la
# schedule inserita da ciascun test (confine_data_ready_schedules).
# Cleanup: le righe schedule vengono rimosse tramite cleanup_registry.
#
# Il modulo verifica i casi limite del task launch_all_on_data_ready_extractions
# (tasks/on_data_ready_extractions.py):
# - salta la schedule con zero dataset
# - salta la schedule con piu dataset
# - salta la schedule con un filtro run non decodificabile (passando dal decoder reale)
#   e invia invece la schedule gemella con un run valido
# - solleva SystemError se l'invio del task a Celery fallisce
#
# test_schedule_opendata_bridge.py copre gia il caso di successo del flusso data-ready.
# Questo modulo si concentra sui casi limite interni al task, che saltano o fanno
# fallire le schedule senza inviare una richiesta di estrazione.

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
import restapi.connectors.celery as celery_connector
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

from mistral.services.arkimet import BeArkimet
from mistral.tasks.on_data_ready_extractions import (
    launch_all_on_data_ready_extractions,
)
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from mistral.tests.helpers.task_perimeter import confine_data_ready_schedules

pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


# =============================================================================
# Helper locali: righe schedule con args controllati per i casi limite
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
    """Inserisce nel DB una schedule data-ready con i dataset e il filtro run indicati.

    Il seed diretto evita l'endpoint di creazione schedule, che richiederebbe troppo
    contesto esterno. Restituisce l'id della schedule creata.
    """
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
    db.session.add(schedule_row)
    db.session.commit()
    return schedule_row.id


def delete_schedule_row(db: Any, schedule_id: int) -> None:
    """Rimuove dal DB una schedule inserita dal test, se esiste ancora (cleanup)."""
    schedule = db.Schedule.query.get(schedule_id)
    if schedule is not None:
        db.session.delete(schedule)
        db.session.commit()


@pytest.fixture
def data_ready_task_user(
    client: FlaskClient,
    cleanup_registry,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo proprietario delle schedule usate negli scenari.

    L'utente e creato tramite l'API admin di restapi e rimosso nel cleanup.
    """
    # Il task legge solo `user_id` dalla schedule: non servono privilegi speciali.
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
# Test: casi limite di launch_all_on_data_ready_extractions
# =============================================================================


class TestOnDataReadyTaskEdges:
    """Verifica che il task data-ready salti o fallisca le schedule non valide."""

    def test_skip_schedule_with_zero_datasets(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """Verifica che il task salti le schedule senza dataset.

        launch_all_on_data_ready_extractions viene eseguito con Celery sostituito da un
        MagicMock: nessun send_task deve essere invocato.
        """
        # arrange - schedule con zero dataset
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=[],
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        fake_celery = MagicMock()
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)
        # Il task legge tutte le schedule: il perimetro lascia visibile solo questa.
        confine_data_ready_schedules(monkeypatch, [schedule_id])

        # act - esegue il task per il modello lm5 con la schedule senza dataset
        launch_all_on_data_ready_extractions.run(
            "lm5",
            datetime(2021, 10, 19, 0, 0, 0),
        )

        # assert - send_task di Celery non viene mai chiamato
        assert fake_celery.celery_app.send_task.call_count == 0

    def test_skip_schedule_with_multiple_datasets(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """Verifica che il task salti le schedule con piu dataset.

        launch_all_on_data_ready_extractions viene eseguito con Celery sostituito da un
        MagicMock: nessun send_task deve essere invocato.
        """
        # arrange - schedule con piu dataset
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=["lm5", "lm2.2"],
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        fake_celery = MagicMock()
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)
        # Il task legge tutte le schedule: il perimetro lascia visibile solo questa.
        confine_data_ready_schedules(monkeypatch, [schedule_id])

        # act - esegue il task per il modello lm5, presente nella schedule multi-dataset
        launch_all_on_data_ready_extractions.run(
            "lm5",
            datetime(2021, 10, 19, 0, 0, 0),
        )

        # assert - send_task di Celery non viene mai chiamato
        assert fake_celery.celery_app.send_task.call_count == 0

    @pytest.mark.parametrize(
        ("run_filter", "expected_error", "expected_sends"),
        [
            ({"invalid_arkimet_run": "broken"}, ValueError, 0),
            ({"style": "MINUTE", "value": 0}, None, 1),
        ],
        ids=["invalid-run-is-skipped", "valid-run-is-sent"],
    )
    def test_run_filter_goes_through_the_real_decoder(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
        run_filter: dict[str, Any],
        expected_error: type[Exception] | None,
        expected_sends: int,
    ):
        """Verifica che il filtro run arrivi al vero ``BeArkimet.decode_run``.

        Uno spy delega al decoder reale e registra input ed eccezioni: il run
        malformato solleva ValueError e la sua schedule non viene inviata, mentre la
        schedule gemella con un run valido (00:00, come il rundate) viene inviata.
        """
        # arrange - schedule con il filtro run dello scenario
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=["lm5"],
            run_filter=[run_filter],
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        real_decode_run = BeArkimet.decode_run
        decoded: list[dict[str, Any]] = []
        errors: list[Exception] = []

        def decode_run_spy(run: dict[str, Any]) -> str:
            decoded.append(dict(run))
            try:
                return real_decode_run(run)
            except Exception as exc:
                errors.append(exc)
                raise

        monkeypatch.setattr(BeArkimet, "decode_run", staticmethod(decode_run_spy))
        fake_celery = MagicMock()
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)
        # Il task legge tutte le schedule: il perimetro lascia visibile solo questa.
        confine_data_ready_schedules(monkeypatch, [schedule_id])

        # act
        launch_all_on_data_ready_extractions.run(
            "lm5",
            datetime(2021, 10, 19, 0, 0, 0),
        )

        # assert
        assert decoded == [run_filter]
        if expected_error is None:
            assert errors == []
        else:
            assert [type(error) for error in errors] == [expected_error]
        send_task = fake_celery.celery_app.send_task
        assert send_task.call_count == expected_sends
        if expected_sends:
            # args[9] e l'id della schedule passato a data_extract
            assert send_task.call_args.kwargs["args"][9] == schedule_id

    def test_celery_send_failure_raises_system_error(
        self,
        faker: Faker,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
        data_ready_task_user: AuthenticatedTestUser,
    ):
        """Verifica che il task sollevi SystemError se l'invio a Celery fallisce.

        Il MagicMock di Celery fa fallire send_task e
        launch_all_on_data_ready_extractions deve trasformare l'errore in SystemError.
        """
        # arrange - schedule valida
        db = sqlalchemy.get_instance()
        schedule_id = seed_schedule_for_data_ready(
            db,
            faker,
            data_ready_task_user.user_id,
            datasets=["lm5"],
        )
        cleanup_registry.add(lambda: delete_schedule_row(db, schedule_id))

        fake_celery = MagicMock()
        fake_celery.celery_app.send_task.side_effect = Exception("Celery broker unreachable")
        from restapi.connectors import celery
        monkeypatch.setattr(celery, "get_instance", lambda: fake_celery)
        # Il task legge tutte le schedule: il perimetro lascia visibile solo questa.
        confine_data_ready_schedules(monkeypatch, [schedule_id])

        def raise_original_task_error(*args: Any, exception: Exception, **kwargs: Any):
            """Rilancia l'errore del task senza inviare eventi di failure a Celery.

            Anche chiamato direttamente in un test deterministico, un task Celery
            decorato passa dall'hook di failure di restapi. In produzione l'hook
            emette un evento Celery tramite il broker; qui finirebbe per verificare
            la raggiungibilita del broker invece del ramo on-data-ready. Rilanciare
            l'eccezione originale mantiene l'asserzione sul comportamento del backend.
            """
            # Manteniamo il fake confinato al test: il monkeypatch verra ripristinato
            # da pytest e non nasconde altri failure hook della suite.
            raise exception

        monkeypatch.setattr(
            celery_connector,
            "mark_task_as_failed",
            raise_original_task_error,
        )

        # act & assert - il task solleva SystemError se l'invio a Celery fallisce
        with pytest.raises(SystemError, match="Unable to submit the data ready request extraction"):
            launch_all_on_data_ready_extractions.run(
                "lm5",
                datetime(2021, 10, 19, 0, 0, 0),
            )
