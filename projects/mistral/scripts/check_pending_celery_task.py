from datetime import datetime,timedelta
from restapi.connectors import sqlalchemy
from celery import states
from celery.result import AsyncResult
from restapi.connectors import celery

db = sqlalchemy.get_instance()
c = celery.get_instance()

pending_list = db.Request.query.filter_by(status="PENDING")
now = datetime.now()
for p in pending_list:
    task_id = p.task_id
    res = AsyncResult(task_id,app=c.celery_app)
    if res.state:
        if res.state == 'FAILURE' or res.state == 'REVOKED':
            p.end_date = now
            p.error_message = f"extraction task has the following state:{res.state}"
            p.status = states.FAILURE
            db.session.commit()
        else:
            GRACE_PERIOD = timedelta(days=2)
            if now - GRACE_PERIOD > p.submission_date:
                p.end_date = now
                p.status = states.FAILURE
                p.error_message = f"request in 'PENDING' status for more than {GRACE_PERIOD.days} days"
                db.session.commit()
