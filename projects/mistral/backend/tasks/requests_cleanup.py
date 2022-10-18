from datetime import datetime, timedelta

from celery import states
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from restapi.connectors import sqlalchemy
from restapi.connectors.celery import CeleryExt, Task
from restapi.utilities.logs import log

# period after that the pending requests and files are considered as ended in error
GRACE_PERIOD = timedelta(days=2)


@CeleryExt.task(idempotent=False)
def automatic_cleanup(self: Task[[], str]) -> str:
    log.info("Auto-cleaning task started!")

    db = sqlalchemy.get_instance()
    users_settings = {}
    users = {}
    for u in db.User.query.all():
        if exp := u.requests_expiration_days:
            users_settings[u.id] = timedelta(days=exp)
            users[u.id] = u

    now = datetime.now()
    requests = db.Request.query.all()
    for r in requests:
        if not (exp := users_settings.get(r.user_id)):
            log.debug("{}: user {} disabled requests auto-cleaning", r.id, r.user_id)
            continue

        if not r.end_date:
            log.info("{} not completed yet?", r.id)
            # check if the grace period has passed
            if r.status == "STARTED" and now - GRACE_PERIOD > r.submission_date:
                # mark the request as error
                log.info("{} submitted on {} marked as error ", r.id, r.submission_date)
                r.end_date = now
                r.status = states.FAILURE
                r.error_message = f"request in 'STARTED' status for more than {GRACE_PERIOD.days} days"
                db.session.commit()
            continue

        if r.archived:
            log.debug("{} already archived", r.id)
            continue

        if r.end_date > now - exp:
            # log.info("{} {}: {}", r.id, r.user_id, r.end_date.isoformat())
            continue

        user = users.get(r.user_id)
        repo.delete_request_record(db, user, r.id)
        # check if the request has to be deleted or archived
        operation = None
        if user and user.requests_expiration_delete:
            db.session.delete(r)
            operation = "deleted"
        else:
            # set the request as archived
            r.archived = True
            operation = "archived"
        db.session.commit()

        log.warning(
            "Request {} (completed on {}) {}", r.id, r.end_date.isoformat(), operation
        )

    # check for orphan files
    for dir in DOWNLOAD_DIR.iterdir():
        if dir.is_dir():
            user_dir = dir.joinpath("outputs")
            if user_dir.exists():
                for f in user_dir.iterdir():
                    if f.is_file():
                        # check if is a tmp file and has passed the grace period
                        if (
                            f.suffix == ".tmp"
                            and now - GRACE_PERIOD
                            > datetime.fromtimestamp(f.stat().st_mtime)
                        ):
                            log.info(
                                "temp file {} created on {} has passed the grace period and has been deleted",
                                f,
                                datetime.fromtimestamp(f.stat().st_mtime),
                            )
                            f.unlink()
                            continue
                        # check if it is an orphan file
                        file_object = db.FileOutput.query.filter_by(
                            filename=f.name
                        ).first()
                        if not file_object:
                            # check if has passed the grace period
                            if now - GRACE_PERIOD > datetime.fromtimestamp(
                                f.stat().st_mtime
                            ):
                                log.info(
                                    "output file {} without a db entry and created on {} has passed the grace period and has been deleted",
                                    f,
                                    datetime.fromtimestamp(f.stat().st_mtime),
                                )
                                f.unlink()
                                continue

    log.info("Auto-cleaning task completed")
    return "Auto-cleaning task completed"
