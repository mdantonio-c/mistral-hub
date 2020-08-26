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
            if exp := u.requests_expiration_days:
                users_settings[u.uuid] = timedelta(days=exp)

        now = datetime.now()
        requests = db.Request.query.all()
        for r in requests:
            if not (exp := users_settings.get(r.user_id)):
                log.info("{}: user {} disabled requests autocleaning", r.id, r.user_id)
                continue

            if not r.end_date:
                log.info("{} not completed yet?", r.id)
                continue

            if r.end_date > now - exp:
                log.info("{} {}: {}", r.id, r.user_id, r.end_date.isoformat())
                continue

            log.warning(
                "Request {} (completed on {}) should be deleted",
                r.id,
                r.end_date.isoformat(),
            )
            # repo.delete_request_record(db, user, request_id, DOWNLOAD_DIR)

        return "Autocleaning task executed!"
