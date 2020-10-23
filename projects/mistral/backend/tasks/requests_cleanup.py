from datetime import datetime, timedelta

from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from restapi.connectors.celery import CeleryExt
from restapi.utilities.logs import log

celery_app = CeleryExt.celery_app


@celery_app.task(bind=True)
def automatic_cleanup(self):
    with celery_app.app.app_context():

        log.info("Autocleaning task started!")

        db = celery_app.get_service("sqlalchemy")
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
                log.verbose(
                    "{}: user {} disabled requests autocleaning", r.id, r.user_id
                )
                continue

            if not r.end_date:
                log.info("{} not completed yet?", r.id)
                continue

            if r.end_date > now - exp:
                # log.info("{} {}: {}", r.id, r.user_id, r.end_date.isoformat())
                continue

            user = users.get(r.user_id)
            repo.delete_request_record(db, user, r.id, DOWNLOAD_DIR)
            log.warning(
                "Request {} (completed on {}) deleted",
                r.id,
                r.end_date.isoformat(),
            )

        log.info("Autocleaning task completed")
        return "Autocleaning task completed"
