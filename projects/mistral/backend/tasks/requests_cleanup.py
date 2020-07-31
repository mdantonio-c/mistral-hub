from restapi.connectors.celery import CeleryExt
from restapi.utilities.logs import log

celery_app = CeleryExt.celery_app


@celery_app.task(bind=True)
def automatic_cleanup(self):
    with celery_app.app.app_context():

        # db = celery_app.get_service("sqlalchemy")

        # 1. get all requests
        # 2. retrieve user from request
        # 3. if user.requests_expiration_days == 0: continue
        # 4. if now - request.created < requests_expiration_days: continue
        # 5. delete request
        log.info("Task started!")

        return "Task executed!"
