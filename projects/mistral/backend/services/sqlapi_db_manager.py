import datetime
import json
from pathlib import Path
from typing import Any, Optional

from celery.result import AsyncResult
from celery.states import READY_STATES
from mistral.endpoints import DOWNLOAD_DIR, OPENDATA_DIR
from restapi.connectors import sqlalchemy
from restapi.exceptions import NotFound, Unauthorized
from restapi.services.authentication import User
from restapi.utilities.logs import log


class SqlApiDbManager:
    @staticmethod
    def check_fileoutput(user: User, filename: str) -> Path:

        db = sqlalchemy.get_instance()
        fileoutput = db.FileOutput
        # query for the requested file in database
        f_to_download = fileoutput.query.filter(fileoutput.filename == filename).first()
        # check if the requested file is in the database
        if f_to_download is None:
            raise NotFound(f"file: {filename} is not in database")

        # check if the user owns the file
        if not SqlApiDbManager.check_owner(db, user.id, file_id=f_to_download.id):
            raise NotFound("User is not the file owner")

        # check if the file is an opendata or not
        if f_to_download.request.opendata:
            file_dir = OPENDATA_DIR
        else:
            file_dir = DOWNLOAD_DIR.joinpath(user.uuid, "outputs")

        # check if the requested file is in the user folder
        path = file_dir.joinpath(f_to_download.filename)
        if not path.exists():
            log.error("File path: {} does not exists", path)
            raise NotFound(f"File path for {f_to_download.filename} does not exists")

        return file_dir

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
            log.debug("look for request with ID {}", request_id)
            res = db.Request.query.get(int(request_id))
        elif schedule_id is not None:
            log.debug("look for schedule with ID {}", schedule_id)
            res = db.Schedule.query.get(int(schedule_id))
        return True if res is not None else False

    @staticmethod
    def check_request_is_pending(db, request_id=None):
        res = None
        if request_id is not None:
            log.debug("look for request with ID {}", request_id)
            res = db.Request.query.get(int(request_id))

        return True if res.status not in READY_STATES else False

    @staticmethod
    def count_user_requests(db, user_id, archived):
        log.debug("get total requests for user UUID {}", user_id)
        return db.Request.query.filter_by(user_id=user_id, archived=archived).count()

    @staticmethod
    def count_user_schedules(db, user_id):
        log.debug("get total schedules for user UUID {}", user_id)
        return db.Schedule.query.filter_by(user_id=user_id).count()

    @staticmethod
    def count_schedule_requests(db, schedule_id):
        log.debug("get total requests for schedule {}", schedule_id)
        return db.Request.query.filter_by(schedule_id=schedule_id).count()

    @staticmethod
    def create_request_record(
        db, user_id, product_name, filters, schedule_id=None, opendata=False
    ):
        args = filters
        r = db.Request(
            user_id=user_id,
            name=product_name,
            args=args,
            status="CREATED",
            opendata=opendata,
        )
        if schedule_id is not None:
            # scheduled_request = db.Schedule
            r.schedule_id = schedule_id
        db.session.add(r)
        db.session.commit()

        return r

    @staticmethod
    def create_schedule_record(db, user, product_name, args, **schedule_settings):
        # load schedule settings
        every = schedule_settings["every"] if "every" in schedule_settings else None
        period = schedule_settings["period"] if "period" in schedule_settings else None
        crontab_settings = (
            schedule_settings["crontab_settings"]
            if "crontab_settings" in schedule_settings
            else None
        )
        on_data_ready = schedule_settings["on_data_ready"] if "on_data_ready" else False

        s = db.Schedule(user_id=user.id, name=product_name, args=args, is_crontab=False)
        # check if the request is periodic
        if (every or period) is not None:
            s.every = every
            s.period = period
        # check if the request is a crontab type
        if crontab_settings is not None:
            s.is_crontab = True
            s.crontab_settings = json.dumps(crontab_settings)
        s.is_enabled = True
        s.on_data_ready = on_data_ready
        s.opendata = schedule_settings["opendata"]
        s.time_delta = schedule_settings["time_delta"]

        db.session.add(s)
        db.session.commit()
        log.info("schedule created: ID <{}>", s.id)

        return s.id

    @staticmethod
    def create_fileoutput_record(db, user_id, request_id, filename, data_size):
        f = db.FileOutput(
            user_id=user_id, request_id=request_id, filename=filename, size=data_size
        )
        db.session.add(f)
        db.session.commit()
        log.info("fileoutput for request ID <{}>", request_id)

    @staticmethod
    def delete_request_record(db, user, request_id):
        request = db.Request.query.get(request_id)
        out_file = request.fileoutput
        if out_file is not None:
            if out_file.request.opendata:
                file_dir = OPENDATA_DIR
            else:
                file_dir = DOWNLOAD_DIR.joinpath(user.uuid, "outputs")
            # delete the file output
            try:
                filepath = file_dir.joinpath(out_file.filename)
                filepath.unlink()
                db.session.delete(out_file)
            except FileNotFoundError as error:
                # silently pass when file is not found
                log.warning(error)
        # db.session.delete(request)
        db.session.commit()

    @staticmethod
    def delete_schedule(db, schedule_id):
        schedule = db.Schedule.query.get(schedule_id)
        name = schedule.name
        db.session.delete(schedule)
        db.session.commit()
        log.debug("Schedule <{}, {}> deleted", schedule_id, name)

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
        r = (
            db.Request.query.filter_by(schedule_id=schedule_id, status="SUCCESS")
            .order_by(db.Request.submission_date.desc())
            .first()
        )
        return SqlApiDbManager._get_request_response(r) if r else None

    @staticmethod
    def get_schedule_by_id(db, schedule_id):
        schedule = db.Schedule.query.get(schedule_id)
        return SqlApiDbManager._get_schedule_response(schedule)

    @staticmethod
    def get_schedule_name(db, schedule_id):
        schedule = db.Schedule.query.filter(db.Schedule.id == schedule_id).first()
        return schedule.name

    @staticmethod
    def get_schedule_requests(
        db, schedule_id, sort_by="submission_date", sort_order="desc"
    ):
        """
        Retrieve all the scheduled requests for a given schedule.
        :param db:
        :param schedule_id:
        :param sort_by:
        :param sort_order:
        :return:
        """
        scheduled_requests = []
        requests_list = db.Request.query.filter_by(schedule_id=schedule_id).order_by(
            db.Request.submission_date.desc()
        )
        for row in requests_list:
            scheduled_requests.append(SqlApiDbManager._get_request_response(row))
        return scheduled_requests

    @staticmethod
    def _get_request_response(db_request):
        """
        Create the response schema
        :param db_request:
        :return:
        """
        r = {
            "id": db_request.id,
            "name": db_request.name,
            "request_id": db_request.id,
            "task_id": db_request.task_id,
            "submission_date": db_request.submission_date.isoformat(),
            "end_date": None,
            "status": db_request.status,
        }
        if db_request.end_date is not None:
            r["end_date"] = db_request.end_date.isoformat()

        if db_request.error_message is not None:
            r["error message"] = db_request.error_message

        current_fileoutput = db_request.fileoutput
        if current_fileoutput is not None:
            fileoutput_name = current_fileoutput.filename
        else:
            fileoutput_name = "no file available"
        r["fileoutput"] = fileoutput_name
        r["filesize"] = (
            current_fileoutput.size if current_fileoutput is not None else None
        )
        return r

    @staticmethod
    def _get_license_group_response(db_lgroup):
        r = {
            "id": db_lgroup.id,
            "name": db_lgroup.name,
            "descr": db_lgroup.descr,
            "is_public": db_lgroup.is_public,
            "dballe_dsn": db_lgroup.dballe_dsn,
        }
        return r

    @staticmethod
    def _get_license_response(db_license):
        r = {
            "id": db_license.id,
            "name": db_license.name,
            "descr": db_license.descr,
            "url": db_license.url,
        }
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
        # user_name = current_user.name
        requests_list = current_user.requests

        # update celery status for the requests coming from the database query
        # for row in requests_list:
        #    if row.task_id is not None:
        #        SqlApiDbManager.update_task_status(db, row.task_id)
        #    # handle the case rabbit was down when the request was posted and the request has not a task id
        #    else:
        #        message = "Service was temporarily unavailable when data extraction request was posted"
        #        SqlApiDbManager.save_message_error(db, row.id, message)

        # create the response schema for not scheduled requests
        user_list = []

        for row in requests_list:
            user_request = {}
            if row.schedule_id is not None:
                continue
            user_request["id"] = row.id
            user_request["name"] = row.name
            user_request["submission_date"] = row.submission_date.isoformat()
            user_request["end_date"] = row.end_date.isoformat()
            user_request["args"] = json.loads(row.args)
            user_request["user_name"] = user.name
            user_request["status"] = row.status
            user_request["task_id"] = row.task_id

            if row.error_message is not None:
                user_request["error message"] = row.error_message

            current_fileoutput = row.fileoutput
            if current_fileoutput is not None:
                fileoutput_name = current_fileoutput.filename
            else:
                fileoutput_name = "no file available"
            user_request["fileoutput"] = fileoutput_name
            user_request["filesize"] = (
                current_fileoutput.size if current_fileoutput is not None else None
            )

            user_list.append(user_request)

        if sort_by == "date":
            if sort_order == "asc":
                sorted_list = sorted(
                    user_list, key=lambda date: date["submission_date"]  # type: ignore
                )
                return sorted_list
            if sort_order == "desc":
                sorted_list = sorted(
                    user_list,
                    key=lambda date: date["submission_date"],  # type: ignore
                    reverse=True,
                )
                return sorted_list
        else:
            return user_list

    @staticmethod
    def get_user_request_by_id(db, request_id):
        return db.Request.query.get(request_id)

    @staticmethod
    def get_user_schedules(db, user_id, sort_by=None, sort_order=None):

        # default value if sort_by and sort_order are None
        if sort_by is None:
            sort_by = "date"
        if sort_order is None:
            sort_order = "desc"

        user = db.User
        current_user = user.query.filter(user.id == user_id).first()
        # user_name = current_user.name
        schedules_list = current_user.schedules

        user_list = []

        # create the response schema
        for schedule in schedules_list:
            user_schedules = SqlApiDbManager._get_schedule_response(schedule)
            user_list.append(user_schedules)

        if sort_by == "date":
            if sort_order == "asc":
                sorted_list = sorted(
                    user_list, key=lambda date: date["creation_date"]  # type: ignore
                )
                return sorted_list
            if sort_order == "desc":
                sorted_list = sorted(
                    user_list,
                    key=lambda date: date["creation_date"],  # type: ignore
                    reverse=True,
                )
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
        # log.info('updating status for: {}', task_id)
        request = db.Request
        r_to_update = request.query.filter(request.task_id == task_id).first()

        # ask celery the status of the given request
        result: AsyncResult[Any] = AsyncResult(task_id)
        # log.info('status:{}', result.status)

        r_to_update.status = result.status
        db.session.commit()

    @staticmethod
    def _get_schedule_response(schedule):
        resp = {
            "id": schedule.id,
            "user_id": schedule.user_id,
            "name": schedule.name,
            "creation_date": schedule.submission_date.isoformat(),
            "args": schedule.args,
            "requests_count": schedule.submitted_request.count(),
            "enabled": schedule.is_enabled,
            "on_data_ready": schedule.on_data_ready,
            "period": schedule.period,
            "every": schedule.every,
            "crontab_set": schedule.crontab_settings,
            "opendata": schedule.opendata,
        }
        if schedule.is_crontab:
            resp["crontab"] = True
            resp["crontab_settings"] = json.loads(schedule.crontab_settings)
        elif schedule.period and schedule.every:
            resp["periodic"] = True
            periodic_settings = ("every", str(schedule.every), schedule.period.name)
            resp["periodic_settings"] = " ".join(periodic_settings)
            resp["every"] = schedule.every
            resp["period"] = schedule.period.name
        return resp

    @staticmethod
    def get_datasets(db, user, category=None, licenceSpecs=False, group_license=None):
        # get all datasets
        ds_objects = db.Datasets.query.filter_by().all()
        datasets = []
        for ds in ds_objects:
            dataset_el = {}
            if category:
                if ds.category.name != category:
                    continue
            # get license
            license = db.License.query.filter_by(id=ds.license_id).first()
            # get license group
            group_license_obj = db.GroupLicense.query.filter_by(
                id=license.group_license_id
            ).first()
            if group_license:
                if group_license_obj.name != group_license:
                    continue
            if user:
                # get user authorized datasets
                user_datasets_auth = [ds.name for ds in user.datasets]
                open_dataset = user.open_dataset
                # check the authorization
                if not group_license_obj.is_public:
                    # looking for exception: check the authorized datasets
                    if ds.name not in user_datasets_auth:
                        continue
                # check if the user want to see also open dataset
                else:
                    if not open_dataset:
                        continue

            dataset_el["id"] = ds.arkimet_id
            dataset_el["name"] = ds.name
            dataset_el["description"] = ds.description
            dataset_el["category"] = ds.category.name
            dataset_el["format"] = ds.fileformat
            dataset_el["bounding"] = ds.bounding
            dataset_el["is_public"] = group_license_obj.is_public

            if licenceSpecs:
                attribution = db.Attribution.query.filter_by(
                    id=ds.attribution_id
                ).first()
                dataset_el["license"] = license.name
                dataset_el["license_description"] = license.descr
                dataset_el["license_url"] = license.url
                dataset_el["group_license"] = group_license_obj.name
                dataset_el["group_license_description"] = group_license_obj.descr
                dataset_el["attribution"] = attribution.name
                dataset_el["attribution_description"] = attribution.descr
                dataset_el["attribution_url"] = attribution.url
            datasets.append(dataset_el)

        return datasets

    @staticmethod
    def get_license_group(db, datasets):
        license_group: Optional[Any] = None
        for d in datasets:
            ds = db.Datasets.query.filter_by(arkimet_id=d).first()
            license = db.License.query.filter_by(id=ds.license_id).first()
            group_license = db.GroupLicense.query.filter_by(
                id=license.group_license_id
            ).first()
            if not license_group:
                license_group = group_license
            elif license_group.id != group_license.id:
                # datasets belongs to different license groups
                return None
        return license_group

    @staticmethod
    def check_dataset_authorization(db, dataset_name, user):
        ds_object = db.Datasets.query.filter_by(arkimet_id=dataset_name).first()
        license = db.License.query.filter_by(id=ds_object.license_id).first()
        group_license = db.GroupLicense.query.filter_by(
            id=license.group_license_id
        ).first()
        if group_license.is_public:
            # open dataset
            return True
        else:
            if not user:
                # anonymous user and private dataset
                return False
            user_datasets_auth = [ds.name for ds in user.datasets]
            if dataset_name in user_datasets_auth:
                return True
            else:
                return False

    @staticmethod
    def retrieve_dataset_by_dsn(db, dsn_name):
        license_groups = db.GroupLicense.query.filter_by(dballe_dsn=dsn_name).all()
        datasets_names = []
        for lg in license_groups:
            # get all licenses
            licenses = lg.license.all()
            for lic in licenses:
                datasets = lic.datasets.all()
                for d in datasets:
                    if d.category.name == "OBS":
                        datasets_names.append(d.arkimet_id)
        return datasets_names

    @staticmethod
    def retrieve_dataset_by_license_group(db, group_license_name):
        # function used for observed data
        license_group = db.GroupLicense.query.filter_by(name=group_license_name).first()
        datasets_names = []
        # get all licenses
        licenses = license_group.license.all()
        for lic in licenses:
            datasets = lic.datasets.all()
            for d in datasets:
                if d.category.name == "OBS":
                    datasets_names.append(d.arkimet_id)
        return datasets_names

    @staticmethod
    def get_all_user_authorized_license_groups(db, user):
        auth_license_groups = []
        all_license_groups = db.GroupLicense.query.filter_by().all()
        for lg in all_license_groups:
            if lg.is_public:
                # check if user want to see also opendata datasets
                if user and not user.open_dataset:
                    continue
                else:
                    auth_license_groups.append(lg.name)
            else:
                if not user:
                    # to see private dataset the user has to be logged
                    continue
                else:
                    # get all authorized datasets
                    user_datasets_auth = [ds.name for ds in user.datasets]
                    # get all license group datasets
                    lg_dataset_list = SqlApiDbManager.retrieve_dataset_by_license_group(
                        db, lg.name
                    )
                    if any(item in user_datasets_auth for item in lg_dataset_list):
                        auth_license_groups.append(lg.name)
        return auth_license_groups

    @staticmethod
    def check_user_request_limit(db, user):
        max_request_hour = SqlApiDbManager.get_user_permissions(
            user, param="request_par_hour"
        )
        if max_request_hour:
            now = datetime.datetime.utcnow()
            last_hour = now.replace(minute=0, second=0, microsecond=0)
            request_count = (
                db.session.query(db.Request)
                .filter(db.Request.user_id == user.id)
                .filter(db.Request.submission_date > last_hour)
                .filter(db.Request.submission_date < now)
                .count()
            )
            if request_count >= max_request_hour:
                next_hour = last_hour + datetime.timedelta(hours=1)
                raise Unauthorized(
                    f"The max number of requests par hour has been reached: New requests can be submitted after {next_hour.hour}:00"
                )

    @staticmethod
    def get_user_permissions(user, param):
        if param == "templates":
            return user.max_templates
        elif param == "output_size":
            return user.max_output_size
        elif param == "request_par_hour":
            return user.request_par_hour
        elif param == "allowed_postprocessing":
            return user.allowed_postprocessing
        elif param == "allowed_schedule":
            return user.allowed_schedule
        elif param and param == "allowed_obs_archive":
            return user.allowed_obs_archive
        return None
