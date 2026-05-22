"""Small Celery stand-ins used by integration tests that must stay fully local.

These helpers are intentionally simple. They let a test call the real Flask
endpoint or the real task function while replacing only the Celery transport
layer that would normally talk to the broker and to external workers.

In practice they are useful when a test wants to prove:

- the application accepts a task submission,
- the scheduling logic decides whether a task should be submitted,
- a request row is created with the expected content,

without also depending on RabbitMQ, worker timing, or heavy extraction code.
"""

from __future__ import annotations

from typing import Any

from celery import states

import mistral.tasks.data_extraction as data_extraction_task
from mistral.services.sqlapi_db_manager import SqlApiDbManager


class AcceptTasksWithoutRunningCelery:
    """Record Celery submissions but never forward them to the real broker.

    Tests use this fake when they want the surrounding application code to
    behave as if a task submission succeeded, while keeping the execution fully
    in-process. The fake stores every submission in ``sent_tasks`` so a test can
    inspect what would have been sent to Celery.
    """

    def __init__(self, *accepted_task_names: str) -> None:
        self.sent_tasks: list[dict[str, Any]] = []
        self.celery_app = _AcceptingCeleryApp(
            accepted_task_names=set(accepted_task_names),
            sent_tasks=self.sent_tasks,
        )

    def delete_periodic_task(self, *args: Any, **kwargs: Any) -> bool:
        """Mimic successful cleanup of a periodic Celery entry.

        Some code paths expect the Celery wrapper to expose this method. The
        fake always returns ``True`` because there is no real periodic task to
        remove during the test.
        """
        return True


class _AcceptingCeleryApp:
    """Minimal ``celery_app`` replacement used by ``AcceptTasksWithoutRunningCelery``."""

    def __init__(
        self,
        *,
        accepted_task_names: set[str],
        sent_tasks: list[dict[str, Any]],
    ) -> None:
        self.accepted_task_names = accepted_task_names
        self.sent_tasks = sent_tasks

    def send_task(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Store one task submission instead of sending it to Celery.

        When ``accepted_task_names`` is not empty, the fake also checks that the
        code under test is submitting only the task names expected by the test.
        """
        if self.accepted_task_names:
            assert name in self.accepted_task_names
        self.sent_tasks.append({"name": name, "args": args, "kwargs": kwargs})
        return None


class InlineDataReadyExtractionCelery:
    """Replace ``data_extract`` worker execution with a direct database effect.

    The periodic data-ready tests want to verify the scheduler decision itself:
    should a new extraction request be generated or not? They do not need to run
    the real extraction worker. This fake translates the Celery submission into
    the same request row that the rest of the test expects to observe in the DB.
    """

    def __init__(self, db: Any) -> None:
        self.celery_app = _InlineDataReadyExtractionApp(db)

    def delete_periodic_task(self, *args: Any, **kwargs: Any) -> bool:
        """Pretend that periodic-task cleanup succeeded.

        The data-ready code path may call this method on the Celery wrapper. For
        this fake there is nothing to clean up, so the method simply reports
        success.
        """
        return True


class InlineDataExtractCelery:
    """Execute ``data_extract`` immediately in-process.

    Some integration tests need the real extraction side effects, such as file
    creation and opendata publication, but they still want to avoid depending on
    RabbitMQ and external Celery workers. This fake keeps the task transport
    local by calling ``data_extract.run(...)`` directly.
    """

    def __init__(self) -> None:
        self.celery_app = _InlineDataExtractApp()

    def delete_periodic_task(self, *args: Any, **kwargs: Any) -> bool:
        """Report success for periodic-task cleanup even though nothing is scheduled.

        The inline fake never registers real periodic tasks with Celery, but the
        production-facing wrapper still expects this method to exist. Returning
        ``True`` keeps those code paths satisfied without introducing extra test
        setup.
        """
        return True


class _InlineDataReadyExtractionApp:
    """Minimal ``celery_app`` facade that emulates ``data_extract`` side effects."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def send_task(
        self,
        name: str,
        args: tuple[Any, ...] | None = None,
        **kwargs: Any,
    ) -> None:
        """Convert a ``data_extract`` submission into a synthetic request row.

        The method validates that the code under test is really trying to submit
        ``data_extract`` in ``data_ready`` mode. It then either skips duplicate
        submissions for the same reftime or inserts a new successful request row
        so the caller can assert on the resulting schedule state.
        """
        assert name == "data_extract"
        assert args is not None
        (
            user_id,
            datasets,
            reftime,
            filters,
            postprocessors,
            output_format,
            _request_id,
            _only_reliable,
            _pushing_queue,
            schedule_id,
            data_ready,
            opendata,
        ) = args
        assert data_ready is True

        last_request = (
            self.db.Request.query.filter_by(
                schedule_id=schedule_id,
                status=states.SUCCESS,
            )
            .order_by(self.db.Request.submission_date.desc())
            .first()
        )
        if last_request and last_request.args.get("reftime") == reftime:
            return None

        request_name = SqlApiDbManager.get_schedule_name(self.db, schedule_id)
        request = SqlApiDbManager.create_request_record(
            self.db,
            user_id,
            request_name,
            {
                "datasets": datasets,
                "reftime": reftime,
                "filters": filters,
                "postprocessors": postprocessors,
                "output_format": output_format,
            },
            schedule_id=schedule_id,
            opendata=opendata,
        )
        request.status = states.SUCCESS
        self.db.session.add(request)
        self.db.session.commit()
        return None


class _InlineDataExtractApp:
    """Minimal ``celery_app`` facade that runs ``data_extract`` inline."""

    def send_task(
        self,
        name: str,
        args: tuple[Any, ...] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Execute the real extraction task instead of enqueuing it."""
        assert name == "data_extract"
        assert args is not None
        data_extraction_task.data_extract.run(*args)
        return None