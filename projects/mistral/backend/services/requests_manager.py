from utilities.logs import get_logger
import json

from restapi.flask_ext.flask_celery import CeleryExt

celery_app = CeleryExt.celery_app

log = get_logger(__name__)

class RequestManager ():

    @staticmethod
    def create_request_table(db,user,filters,task_id):
        request = db.Request
        args = json.dumps(filters)
        r = request(user_uuid=user, args=args, task_id=task_id)
        db.session.add(r)
        db.session.commit()
        request_id = r.id

        return request_id

    @staticmethod
    def get_user_requests (db,uuid):
        request = db.Request
        query_list = request.query.filter(request.user_uuid == uuid)

        user = db.User
        current_user = user.query.filter(user.uuid == uuid).first()
        user_name = current_user.name

        for row in query_list:
            RequestManager.update_task_status(db,row.task_id)

        request_list = []
        for row in query_list:
            user_request = {}
            user_request['submission_date'] = row.submission_date
            user_request['args'] = json.loads(row.args)
            user_request['user_name'] = user_name
            user_request['status'] = row.status
            user_request['fileoutput'] = "file.file"
            request_list.append(user_request)

        return request_list

    @staticmethod
    def update_task_status (db,task_id):
        #log.info('updating status for: {}'.format(task_id))
        request = db.Request
        r_to_update = request.query.filter(request.task_id == task_id).first()

        result = CeleryExt.data_extract.AsyncResult(task_id)
        #log.info('status:{}'.format(result.status))

        r_to_update.status = result.status
        db.session.commit()


