import json
import os

from restapi.flask_ext.flask_celery import CeleryExt
from restapi.utilities.logs import get_logger

log = get_logger(__name__)
celery_app = CeleryExt.celery_app


class RequestManager():

    @staticmethod
    def check_fileoutput(db, user, filename, download_dir):
        fileoutput = db.FileOutput
        # query for the requested file in database
        f_to_download = fileoutput.query.filter(fileoutput.filename == filename).first()
        # check if the requested file is in the database
        if f_to_download is not None:
            # check if the user owns the file
            if RequestManager.check_owner(db, user.id, file_id=f_to_download.id):
                # check if the requested file is in the user folder
                path = os.path.join(download_dir, user.uuid, f_to_download.filename)
                if os.path.exists(path):
                    return True
                else:
                    log.info('file path: {} does not exists'.format(path))
            else:
                log.info('user is not the file owner')
        else:
            log.info('file: {} is not in database'.format(filename))

    @staticmethod
    def check_owner(db, user_id, schedule_id=None, request_id=None, file_id=None):
        if request_id is not None:
            # check a single request
            item = db.Request
            item_id = request_id
        elif schedule_id is not None:
            # check a scheduled request
            item = db.Schedule
            item_id = schedule_id
        # check a file
        elif file_id is not None:
            item = db.FileOutput
            item_id = file_id

        item_to_check = item.query.get(int(item_id))
        if item_to_check.user_id == user_id:
            return True

    @staticmethod
    def check_request(db, schedule_id=None, request_id=None):
        res = None
        if request_id is not None:
            log.debug('look for request with ID {}'.format(request_id))
            res = db.Request.query.get(int(request_id))
        elif schedule_id is not None:
            log.debug('look for schedule with ID {}'.format(schedule_id))
            res = db.Schedule.query.get(int(schedule_id))
        return True if res is not None else False

    @staticmethod
    def count_user_requests(db, user_id):
        log.debug('get total requests for user UUID {}'.format(user_id))
        return db.Request.query.filter_by(user_id=user_id).count()

    @staticmethod
    def count_user_schedules(db, user_id):
        log.debug('get total schedules for user UUID {}'.format(user_id))
        return db.Schedule.query.filter_by(user_id=user_id).count()

    @staticmethod
    def count_schedule_requests(db, schedule_id):
        log.debug('get total requests for schedule {}'.format(schedule_id))
        return db.Request.query.filter_by(schedule_id=schedule_id).count()

    @staticmethod
    def create_request_record(db, user_id, product_name, filters, schedule_id=None):
        args = json.dumps(filters)
        r = db.Request(user_id=user_id, name=product_name, args=args, status='CREATED')
        if schedule_id is not None:
            # scheduled_request = db.Schedule
            r.schedule_id = schedule_id
        db.session.add(r)
        db.session.commit()

        return r

    @staticmethod
    def create_schedule_record(db, user, product_name, args, every=None, period=None, crontab_settings=None):
        schedule = db.Schedule
        args = json.dumps(args)
        # check if the request is periodic
        if (every or period) is not None:
            s = schedule(user_id=user.id, name=product_name, args=args, is_crontab=False, every=every,
                         period=period)
        # check if the request is a crontab type
        if crontab_settings is not None:
            crontab_args = json.dumps(crontab_settings)
            s = schedule(user_id=user.id, name=product_name, args=args, is_crontab=True,
                         crontab_settings=crontab_args)
        s.is_enabled = True
        db.session.add(s)
        db.session.commit()
        schedule_id = s.id
        log.info('task record {}'.format(s.id))

        return schedule_id

    @staticmethod
    def create_fileoutput_record(db, user_id, request_id, filename, data_size):
        fileoutput = db.FileOutput
        f = fileoutput(user_id=user_id, request_id=request_id, filename=filename, size=data_size)
        db.session.add(f)
        db.session.commit()
        log.info('fileoutput for: {}'.format(request_id))

    @staticmethod
    def delete_fileoutput(uuid, download_dir, filename):
        try:
            filepath = os.path.join(download_dir, uuid, filename)
            os.remove(filepath)
        except FileNotFoundError as error:
            # silently pass when file is not found
            log.warn(error)

    @staticmethod
    def delete_request_record(db, user, request_id, download_dir):
        request = db.Request.query.get(request_id)
        out_file = request.fileoutput
        if out_file is not None:
            RequestManager.delete_fileoutput(user.uuid, download_dir, out_file.filename)
        db.session.delete(request)
        db.session.commit()

    def delete_schedule(db, schedule_id):
        schedule = db.Schedule.query.get(schedule_id)
        name = schedule.name
        db.session.delete(schedule)
        db.session.commit()
        log.debug('Schedule <{}, {}> deleted'.format(schedule_id, name))

    @staticmethod
    # used in a deprecated endpoint
    def disable_schedule_record(db, request_id):
        schedule = db.Schedule
        r_to_disable = db.Schedule.query.filter(schedule.id == request_id).first()
        r_to_disable.is_enabled = False
        db.session.commit()

    @staticmethod
    def get_last_scheduled_request(db, schedule_id):
        """
        Get the last scheduled request completed successfully for a given schedule.
        :param db:
        :param schedule_id: Schedule ID
        :return:
        """
        r = db.Request.query \
            .filter_by(schedule_id=schedule_id, status='SUCCESS') \
            .order_by(db.Request.submission_date.desc()) \
            .first()
        return RequestManager._get_request_response(r) if r else None

    @staticmethod
    def get_schedule_by_id(db, schedule_id):
        schedule = db.Schedule.query.get(schedule_id)
        return RequestManager._get_schedule_response(schedule)

    @staticmethod
    def get_schedule_name(db, schedule_id):
        schedule = db.Schedule.query.filter(db.Schedule.id == schedule_id).first()
        return schedule.name

    @staticmethod
    def get_schedule_requests(db, schedule_id, sort_by="submission_date", sort_order="desc"):
        """
        Retrieve all the scheduled requests for a given schedule.
        :param db:
        :param schedule_id:
        :param sort_by:
        :param sort_order:
        :return:
        """
        scheduled_requests = []
        requests_list = db.Request.query.filter_by(schedule_id=schedule_id)\
            .order_by(db.Request.submission_date.desc())
        for row in requests_list:
            scheduled_requests.append(RequestManager._get_request_response(row))
        return scheduled_requests

    @staticmethod
    def _get_request_response(db_request):
        """
        Create the response schema
        :param db_request:
        :return:
        """
        r = {
            'id': db_request.id,
            'name': db_request.name,
            'request_id': db_request.id,
            'task_id': db_request.task_id,
            'submission_date': db_request.submission_date.isoformat(),
            'end_date': None,
            'status': db_request.status
        }
        if db_request.end_date is not None:
            r['end_date'] = db_request.end_date.isoformat()

        if db_request.error_message is not None:
            r['error message'] = db_request.error_message

        current_fileoutput = db_request.fileoutput
        if current_fileoutput is not None:
            fileoutput_name = current_fileoutput.filename
        else:
            fileoutput_name = 'no file available'
        r['fileoutput'] = fileoutput_name
        r['filesize'] = current_fileoutput.size if current_fileoutput is not None else None
        return r

    @staticmethod
    def get_user_requests(db, user_id, sort_by=None, sort_order=None):

        # default value if sort_by and sort_order are None
        if sort_by is None:
            sort_by = "date"
        if sort_order is None:
            sort_order = "desc"

        user = db.User
        current_user = user.query.filter(user.id == user_id).first()
        user_name = current_user.name
        requests_list = current_user.requests

        # update celery status for the requests coming from the database query
        # for row in requests_list:
        #    if row.task_id is not None:
        #        RequestManager.update_task_status(db, row.task_id)
        #    # handle the case rabbit was down when the request was posted and the request has not a task id
        #    else:
        #        message = "Service was temporarily unavailable when data extraction request was posted"
        #        RequestManager.save_message_error(db, row.id, message)

        # create the response schema for not scheduled requests
        user_list = []

        for row in requests_list:
            user_request = {}
            if row.schedule_id is not None:
                continue
            user_request['id'] = row.id
            user_request['name'] = row.name
            user_request['submission_date'] = row.submission_date.isoformat()
            user_request['end_date'] = row.end_date.isoformat()
            user_request['args'] = json.loads(row.args)
            user_request['user_name'] = user.name
            user_request['status'] = row.status
            user_request['task_id'] = row.task_id

            if row.error_message is not None:
                user_request['error message'] = row.error_message

            current_fileoutput = row.fileoutput
            if current_fileoutput is not None:
                fileoutput_name = current_fileoutput.filename
            else:
                fileoutput_name = 'no file available'
            user_request['fileoutput'] = fileoutput_name
            user_request['filesize'] = current_fileoutput.size if current_fileoutput is not None else None

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
    def get_user_schedules(db, user_id, sort_by=None, sort_order=None):

        # default value if sort_by and sort_order are None
        if sort_by is None:
            sort_by = "date"
        if sort_order is None:
            sort_order = "desc"

        user = db.User
        current_user = user.query.filter(user.id == user_id).first()
        user_name = current_user.name
        schedules_list = current_user.schedules

        user_list = []

        # create the response schema
        for schedule in schedules_list:
            user_schedules = RequestManager._get_schedule_response(schedule)
            user_list.append(user_schedules)

        if sort_by == "date":
            if sort_order == "asc":
                sorted_list = sorted(user_list, key=lambda date: date['creation_date'])
                return sorted_list
            if sort_order == "desc":
                sorted_list = sorted(user_list, key=lambda date: date['creation_date'], reverse=True)
                return sorted_list
        else:
            return user_list

    @staticmethod
    def get_uuid(db, user_id):
        user = db.User
        u = user.query.filter(user.id == user_id).first()
        return u.uuid

    @staticmethod
    def save_message_error(db, request_id, message):
        request = db.Request.query.get(int(request_id))
        request.error_message = message
        db.session.commit()

    @staticmethod
    def update_schedule_status(db, schedule_id, is_active):
        schedule = db.Schedule.query.get(schedule_id)
        # update is_enabled field
        schedule.is_enabled = is_active
        db.session.commit()

    @staticmethod
    def update_task_id(db, request_id, task_id):
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

    @staticmethod
    def _get_schedule_response(schedule):
        resp = {
            'id': schedule.id,
            'name': schedule.name,
            'creation_date': schedule.submission_date.isoformat(),
            'args': json.loads(schedule.args),
            'requests_count': schedule.submitted_request.count(),
            'enabled': schedule.is_enabled
        }
        if not schedule.is_crontab:
            resp['periodic'] = True
            periodic_settings = ('every', str(schedule.every), schedule.period.name)
            resp['periodic_settings'] = ' '.join(periodic_settings)
            resp['every'] = schedule.every
            resp['period'] = schedule.period.name
        else:
            resp['crontab'] = True
            resp['crontab_settings'] = json.loads(schedule.crontab_settings)
        return resp
