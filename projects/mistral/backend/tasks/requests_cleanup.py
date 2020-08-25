from datetime import datetime, timedelta

from restapi.connectors.celery import CeleryExt
from restapi.utilities.logs import log

celery_app = CeleryExt.celery_app


@celery_app.task(bind=True)
def automatic_cleanup(self):
    with celery_app.app.app_context():

        log.info("Autocleaning task started!")

        db = celery_app.get_service("sqlalchemy")
        users_settings = {}
        for u in db.User.query.all():
            users_settings[u.uuid] = u.requests_expiration_days

        now = datetime.now()
        requests = db.Request.query.all()
        for r in requests:
            log.info("{} {}: {}", r.id, r.user_id, r.end_date.isoformat())
            exp = users_settings.get(r.user_id, 0)
            if not exp:
                log.info("User {} disabled requests autocleaning", r.user_id)
                continue

            exp = timedelta(days=exp)

            if r.end_date < now - exp:
                log.warning(
                    "Request {} (completed on {}) should be deleted",
                    r.id,
                    r.end_date.isoformat(),
                )
                # repo.delete_request_record(db, user, request_id, DOWNLOAD_DIR)

        return "Autocleaning task executed!"
