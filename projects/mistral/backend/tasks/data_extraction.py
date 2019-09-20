# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import datetime
from celery.schedules import crontab
from restapi.flask_ext.flask_celery import CeleryExt
from celery import states
from celery.exceptions import Ignore
from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
from restapi.flask_ext.flask_celery import send_errors_by_email
from mistral.services.requests_manager import RequestManager

from utilities.logs import get_logger

celery_app = CeleryExt.celery_app

log = get_logger(__name__)
DOWNLOAD_DIR = '/data'
# MAX_USER_QUOTA = 1570000000
MAX_USER_QUOTA = 1073741824  # 1 GB


@celery_app.task(bind=True)
def add(self, a, b):
    c = a + b
    log.critical("%s + %s = %s", a, b, c)
    return c


@celery_app.task(bind=True)
@send_errors_by_email
def data_extract(self, user_id, datasets, filters=None, postprocessors=[], request_id=None, schedule_id=None):
    with celery_app.app.app_context():
        log.info("Start task [{}:{}]".format(self.request.id, self.name))
        try:
            db = celery_app.get_service('sqlalchemy')

            query = ''  # default to no matchers
            if filters is not None:
                query = arki.parse_matchers(filters)
                log.debug('Arkimet query: {}'.format(query))

            if schedule_id is not None:
                # if the request is a scheduled one, create an entry in request db linked to the scheduled request entry
                product_name = RequestManager.get_schedule_name(db, schedule_id)
                request = RequestManager.create_request_record(db, user_id, product_name, {
                    'datasets': datasets,
                    'filters': filters,
                    'postprocessors': postprocessors
                }, schedule_id=schedule_id)
                # update the entry with celery task id
                # RequestManager.update_task_id(db, request_id, self.request.id)
                request.task_id = self.request.id
                request_id = request.id
                db.session.commit()
                log.debug('Schedule at: {}, Request <ID:{}>'.format(schedule_id, request.id))
            else:
                # load request by id
                request = db.Request.query.get(request_id)
                if request is None:
                    raise ReferenceError("Cannot find request reference for task %s" % self.request.id)

            # I should check the user quota before...
            # check the output size
            data_size = arki.estimate_data_size(datasets, query)
            log.debug('Resulting output size: {} ({})'.format(data_size, human_size(data_size)))

            # create download user dir if it doesn't exist
            uuid = RequestManager.get_uuid(db, user_id)
            user_dir = os.path.join(DOWNLOAD_DIR, uuid)
            os.makedirs(user_dir, exist_ok=True)

            # check for current used space
            used_quota = int(subprocess.check_output(['du', '-sb', user_dir]).split()[0])
            log.info('Current used space: {} ({})'.format(used_quota, human_size(used_quota)))

            # check for exceeding quota
            if used_quota + data_size > MAX_USER_QUOTA:
                free_space = MAX_USER_QUOTA - used_quota
                # save error message in db
                message = 'Disk quota exceeded: required size {}; remaining space {}'.format(
                    human_size(data_size), human_size(free_space))
                raise DiskQuotaException(message)

            '''
             $ arki-query [OPZIONI] QUERY DATASET...
            '''
            ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
            arki_query_cmd = shlex.split("arki-query --data '{}' {}".format(query, ds))
            log.debug(arki_query_cmd)

            # output filename in the user space
            # max filename len = 64
            out_filename = 'data-{utc_now}-{id}.grib'.format(
                utc_now=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                id=self.request.id)

            if postprocessors:
                # at the moment ONLY 'additional_variables' post-processing is allowed
                p = postprocessors[0]
                log.debug(p)
                pp_type = p.get('type')
                if pp_type != 'additional_variables':
                    raise ValueError("Unknown post-processor: {}".format(pp_type))
                log.debug('Data extraction with post-processing <{}>'.format(pp_type))
                # temporarily save the data extraction output
                tmp_outfile = os.path.join(user_dir, out_filename + '.tmp')
                # call data extraction
                with open(tmp_outfile, mode='w') as query_outfile:
                    subprocess.Popen(arki_query_cmd, stdout=query_outfile)
                try:
                    post_proc_cmd = shlex.split("vg6d_transform --output-variable-list={} {} {}".format(
                        ",".join(p.get('variables')),
                        tmp_outfile,
                        os.path.join(user_dir, out_filename)
                    ))
                    proc = subprocess.run(post_proc_cmd, stdout=subprocess.PIPE)
                    proc.check_returncode()
                except Exception:
                    log.error('Runtime error in post-processing')
                    raise
                finally:
                    # always remove tmp file
                    os.remove(tmp_outfile)
            else:
                with open(os.path.join(user_dir, out_filename), mode='w') as outfile:
                    subprocess.Popen(arki_query_cmd, stdout=outfile)

            # create fileoutput record in db
            RequestManager.create_fileoutput_record(db, user_id, request_id, out_filename, data_size)
            # update request status
            request.status = states.SUCCESS
            request.end_date = datetime.datetime.utcnow()
            db.session.commit()
        except Exception as e:
            message = 'Failed to extract data'
            log.error('{}: {}'.format(message, str(e)))
            # RequestManager.save_message_error(db, request_id, message)
            request.status = states.FAILURE
            request.error_message = 'Failed to extract data'
            request.end_date = datetime.datetime.utcnow()
            db.session.commit()
            # manually update the task state too
            self.update_state(
                state=states.FAILURE,
                meta=message
            )
            log.info('Terminate task {} with state {}'.format(self.request.id, states.FAILURE))
            if isinstance(e, DiskQuotaException):
                raise Ignore()
            else:
                raise e

        log.info("Task [{}] completed successfully".format(self.request.id))
        return 1


def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """ Returns a human readable string reprentation of bytes
    :rtype: string
    """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


class DiskQuotaException(Exception): pass
