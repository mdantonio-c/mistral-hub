from utilities.logs import get_logger
import json
import os

from restapi.flask_ext.flask_celery import CeleryExt
from datetime import datetime

celery_app = CeleryExt.celery_app

log = get_logger(__name__)

class RequestManager ():

    @staticmethod
    def check_fileoutput(db, uuid, filename,download_dir):
        fileoutput = db.FileOutput
        # query for the requested file in database
        f_to_download = fileoutput.query.filter(fileoutput.filename == filename).first()
        # check if the requested file is in the database
        if f_to_download is not None:
            # check if the user owns the file
            if RequestManager.check_owner(db,uuid,file_id=f_to_download.id):
                # check if the requested file is in the user folder
                path = os.path.join(download_dir, uuid, f_to_download.filename)
                if os.path.exists(path):
                    return True
                else:
                    log.info('file path: {} does not exists'.format(path))
            else:
                log.info('user is not the file owner')
        else:
            log.info('file: {} is not in database'.format(filename))

    @staticmethod
    def check_owner(db, uuid, scheduled_request_id=None, single_request_id=None, file_id=None):

        # check a single request
        if single_request_id is not None:
            item = db.Request
            item_id = single_request_id
        # check a scheduled request
        if scheduled_request_id is not None:
            item = db.ScheduledRequest
            item_id = scheduled_request_id
        # check a file
        if file_id is not None:
            item = db.FileOutput
            item_id = file_id

        item_to_check = item.query.filter(item.id == item_id).first()
        if item_to_check.user_uuid == uuid:
            return True




    @staticmethod
    def create_request_record(db,user,filters, scheduled_id=None):
        request = db.Request
        args = json.dumps(filters)
        #r = request(user_uuid=user, args=args, task_id=task_id)
        r = request(user_uuid=user, args=args)
        if scheduled_id is not None:
            #scheduled_request = db.ScheduledRequest
            r.scheduled_request_id = scheduled_id
        db.session.add(r)
        db.session.commit()
        request_id = r.id

        return request_id

    @staticmethod
    def create_scheduled_request_record(db, user, filters, every=None, period=None, crontab_settings=None):
        scheduled_request = db.ScheduledRequest
        args = json.dumps(filters)
        crontab_args = json.dumps(crontab_settings)
        # check if the request is periodic
        if (every or period) is not None:
            r = scheduled_request(user_uuid=user.uuid, args=args, periodic_task=True, crontab_task=False, every=every, period=period )
        # check if the request is a crontab type
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
    def delete_fileoutput(db, filename):
        fileoutput = db.FileOutput
        f_to_delete = fileoutput.query.filter(fileoutput.filename == filename).first()
        db.session.delete(f_to_delete)
        db.session.commit()

    @staticmethod
    def delete_scheduled_request_record(db, request_id):
        scheduled_request = db.ScheduledRequest
        r_to_delete = scheduled_request.query.filter(scheduled_request.id == request_id).first()
        db.session.delete(r_to_delete)
        db.session.commit()

    @staticmethod
    # retrieve requests related to a scheduled task
    def get_scheduled_requests(db, scheduled_request_id, sort_by=None, sort_order=None):

        scheduled_request = db.ScheduledRequest
        r = scheduled_request.query.filter(scheduled_request.id == scheduled_request_id).first()
        requests_list = r.submitted_request

        # update celery status for the requests coming from the database query
        for row in requests_list:
            RequestManager.update_task_status(db, row.task_id)

        # create the response schema
        submitted_request_list = []
        for row in requests_list:
            submitted_request = {}
            submitted_request['request_id'] = row.id
            submitted_request['submission_date'] = row.creation_date.isoformat()
            submitted_request['args'] = json.loads(row.args)
            # submitted_request['user_name'] = user_name
            submitted_request['status'] = row.status

            current_fileoutput = row.fileoutput
            if current_fileoutput is not None:
                fileoutput_name = current_fileoutput.filename
            else:
                fileoutput_name = 'no file available'
            submitted_request['fileoutput'] = fileoutput_name

            submitted_request_list.append(submitted_request)

        # sorting the list if there are sorting parameters
        if sort_by == "date":
            if sort_order == "asc":
                sorted_list = sorted(submitted_request_list, key=lambda date: date['submission_date'])
                return sorted_list
            if sort_order == "desc":
                sorted_list = sorted(submitted_request_list, key=lambda date: date['submission_date'], reverse=True)
                return sorted_list
        else:
            return submitted_request_list

    @staticmethod
    def get_user_requests (db, uuid, sort_by=None, sort_order=None, filter=None):

        user = db.User
        current_user = user.query.filter(user.uuid == uuid).first()
        user_name = current_user.name
        requests_list = current_user.requests
        scheduled_list = current_user.scheduledrequests

        # update celery status for the requests coming from the database query
        for row in requests_list:
            RequestManager.update_task_status(db, row.task_id)

        # create the response schema for not scheduled requests
        user_list = []
        if filter != "scheduled": # check if the user doesn't have filtered the request to ask for scheduled requests only
            for row in requests_list:
                user_request = {}
                if row.scheduled_request_id is not None:
                    continue
                user_request['request_id'] = row.id
                user_request['submission_date'] = row.creation_date.isoformat()
                user_request['args'] = json.loads(row.args)
                user_request['user_name'] = user_name
                user_request['status'] = row.status

                current_fileoutput = row.fileoutput
                if current_fileoutput is not None:
                    fileoutput_name = current_fileoutput.filename
                else:
                    fileoutput_name = 'no file available'
                user_request['fileoutput'] =fileoutput_name

                user_list.append(user_request)

        # create the response schema for scheduled requests
        if filter != "no-scheduled": # check if the user doesn't have filtered the request to ask for single requests only
            for row in scheduled_list:
                user_request = {}
                user_request['request_id'] = row.id
                user_request['submission_date'] = row.creation_date.isoformat()
                user_request['args'] = json.loads(row.args)
                user_request['user_name'] = user_name
                if row.periodic_task==True:
                    user_request['periodic'] = row.periodic_task
                    periodic_settings= ('every',str(row.every),row.period.name)
                    user_request['periodic_settings'] = ' '.join(periodic_settings)
                else:
                    user_request['crontab'] = row.crontab_task
                    user_request['crontab_settings'] = json.loads(row.crontab_settings)
                user_list.append(user_request)

        if sort_by == "date":
            if sort_order == "asc":
                sorted_list = sorted(user_list, key=lambda date: date['submission_date'])
                return sorted_list
            if sort_order == "desc":
                sorted_list = sorted(user_list, key=lambda date: date['submission_date'], reverse=True)
                return sorted_list
        else:
            return user_list

    @staticmethod
    def count_user_requests(db, user_uuid):
        log.debug('get total requests for user UUID {}'.format(user_uuid))
        return db.Request.query.filter_by(user_uuid=user_uuid).count()

    @staticmethod
    def update_task_id (db,request_id,task_id):
        request = db.Request
        r_to_update = request.query.filter(request.id == request_id).first()

        r_to_update.task_id = task_id
        db.session.commit()

    @staticmethod
    def update_task_status(db, task_id):
        # log.info('updating status for: {}'.format(task_id))
        request = db.Request
        r_to_update = request.query.filter(request.task_id == task_id).first()

        # ask celery the status of the given request
        result = CeleryExt.data_extract.AsyncResult(task_id)
        # log.info('status:{}'.format(result.status))

        r_to_update.status = result.status
        db.session.commit()


