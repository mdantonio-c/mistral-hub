# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import datetime
from celery.schedules import crontab
from restapi.flask_ext.flask_celery import CeleryExt
from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
# from restapi.flask_ext.flask_celery import send_errors_by_email
from mistral.services.requests_manager import RequestManager

from utilities.logs import get_logger

celery_app = CeleryExt.celery_app

log = get_logger(__name__)
DOWNLOAD_DIR = '/data'
MAX_USER_QUOTA = 1073741824  # 1 GB
#MAX_USER_QUOTA = 1570000000

@celery_app.task(bind=True)
def add(self, a, b):
    c = a + b
    log.critical("%s + %s = %s", a, b, c)
    return c


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(self, user_uuid, datasets, filters=None, request_id=None, scheduled_id=None):
    with celery_app.app.app_context():
        log.info("Start task [{}:{}]".format(self.request.id, self.name))

        db = celery_app.get_service('sqlalchemy')

        query = ''    # default to no matchers
        if filters is not None:
            query = arki.parse_matchers(filters)
            log.debug('Arkimet query: {}'.format(query))

        if scheduled_id is not None:
            # if the request is a scheduled one, create an entry in request db linked to the scheduled request entry
            request_id = RequestManager.create_request_record(db, user_uuid, filters,scheduled_id=scheduled_id)
            # update the entry with celery task id
            RequestManager.update_task_id(db, request_id, self.request.id)
            log.debug('request is scheduled at: {}, Request id: {}'.format(scheduled_id,request_id))

        # I should check the user quota before...
        # check the output size
        data_size = arki.estimate_data_size(datasets, query)
        log.debug('Resulting output size: {} ({})'.format(data_size, human_size(data_size)))

        # create download user dir if it doesn't exist
        user_dir = os.path.join(DOWNLOAD_DIR, user_uuid)
        os.makedirs(user_dir, exist_ok=True)

        # check for current used space
        used_quota = int(subprocess.check_output(['du', '-sb', user_dir]).split()[0])
        log.info('Current used space: {} ({})'.format(used_quota, human_size(used_quota)))

        # check for exceeding quota
        if used_quota + data_size > MAX_USER_QUOTA:
            free_space = MAX_USER_QUOTA - used_quota
            # save error message in db
            message = 'User quota exceeds: required size {} ({}); ' 'remaining space {} ({})'.format(data_size, human_size(data_size), free_space, human_size(free_space))
            RequestManager.save_message_error(db, request_id, message)

            # raise IOError('User quota exceeds: required size {} ({}); '
            #               'remaining space {} ({})'.format(
            #     data_size, human_size(data_size), free_space, human_size(free_space)))

            raise IOError(message)

        '''
         $ arki-query [OPZIONI] QUERY DATASET...
        '''
        ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
        arki_query_cmd = "arki-query --data '{}' {}".format(query, ds)
        log.debug(arki_query_cmd)

        # save results into user space
        args = shlex.split(arki_query_cmd)
        filename = 'output-'+datetime.datetime.now().strftime("%Y%m%d%H%M%S")+'-'+self.request.id
        with open(os.path.join(user_dir, filename), mode='w') as outfile:
            subprocess.Popen(args, stdout=outfile)
        if request_id is not None:
            #create fileoutput record in db
            RequestManager.create_fileoutput_record(db, user_uuid, request_id, filename, data_size )

        log.info("Task [{}] completed successfully".format(self.request.id))
        return 1


def human_size(bytes, units=[' bytes','KB','MB','GB','TB', 'PB', 'EB']):
    """ Returns a human readable string reprentation of bytes
    :rtype: string
    """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes>>10, units[1:])
