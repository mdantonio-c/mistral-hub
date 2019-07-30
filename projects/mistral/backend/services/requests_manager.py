from utilities.logs import get_logger
import json

from restapi.flask_ext.flask_celery import CeleryExt

celery_app = CeleryExt.celery_app

log = get_logger(__name__)

class RequestManager ():

    @staticmethod
    def create_request_record(db,user,filters):
        request = db.Request
        args = json.dumps(filters)
        #r = request(user_uuid=user, args=args, task_id=task_id)
        r = request(user_uuid=user, args=args)
        db.session.add(r)
        db.session.commit()
        request_id = r.id

        return request_id

    @staticmethod
    def create_scheduled_request_record(db, user, filters, every=None, period=None, crontab_settings=None):
        scheduled_request = db.ScheduledRequest
        args = json.dumps(filters)
        crontab_args = json.dumps(crontab_settings)
        # r = request(user_uuid=user, args=args, task_id=task_id)
        if (every or period) is not None:
            r = scheduled_request(user_uuid=user.uuid, args=args, periodic_task=True, crontab_task=False, every=every, period=period )
            #log.info('task args {} {} {} {}'.format(user.uuid,args,every,period))
        if crontab_settings is not None:
            r = scheduled_request(user_uuid=user.uuid, args=args, periodic_task=False, crontab_task=True,crontab_settings= crontab_args)
        db.session.add(r)
        db.session.commit()
        request_id = r.id
        log.info('task record {}'.format(r.id))

        return request_id

    @staticmethod
    def create_fileoutput_record(db, user, request_id, filename, data_size):
        fileoutput = db.FileOutput
        f = fileoutput(user_uuid=user, request_id=request_id, filename=filename, size=data_size)
        db.session.add(f)
        db.session.commit()
        log.info('fileoutput for: {}'.format(request_id))

    @staticmethod
    def get_user_requests (db,uuid):

        user = db.User
        current_user = user.query.filter(user.uuid == uuid).first()
        user_name = current_user.name
        query_list = current_user.requests

        for row in query_list:
            RequestManager.update_task_status(db,row.task_id)

        request_list = []
        for row in query_list:
            user_request = {}
            user_request['submission_date'] = row.submission_date
            user_request['args'] = json.loads(row.args)
            user_request['user_name'] = user_name
            user_request['status'] = row.status

            current_fileoutput = row.fileoutput
            if current_fileoutput is not None:
                fileoutput_name = current_fileoutput.filename
            else:
                fileoutput_name = 'no file available'
            user_request['fileoutput'] =fileoutput_name

            request_list.append(user_request)

        return request_list

    @staticmethod
    def update_task_id (db,request_id,task_id):
        #log.info('updating status for: {}'.format(request_id))
        request = db.Request
        r_to_update = request.query.filter(request.id == request_id).first()

        r_to_update.task_id = task_id
        db.session.commit()

    @staticmethod
    def update_task_status(db, task_id):
        # log.info('updating status for: {}'.format(task_id))
        request = db.Request
        r_to_update = request.query.filter(request.task_id == task_id).first()

        result = CeleryExt.data_extract.AsyncResult(task_id)
        # log.info('status:{}'.format(result.status))

        r_to_update.status = result.status
        db.session.commit()


