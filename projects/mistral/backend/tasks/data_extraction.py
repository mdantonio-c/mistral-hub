# -*- coding: utf-8 -*-
from restapi.flask_ext.flask_celery import CeleryExt
# from restapi.flask_ext.flask_celery import send_errors_by_email

from utilities.logs import get_logger

celery_app = CeleryExt.celery_app

log = get_logger(__name__)


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(self):
    with celery_app.app.app_context():
        log.info("I'm %s" % self.request.id)
        log.info("All (nothing) done!")
        return 1
