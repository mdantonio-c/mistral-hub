# -*- coding: utf-8 -*-

import shlex, subprocess
import os
import datetime
from restapi.flask_ext.flask_celery import CeleryExt
from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
# from restapi.flask_ext.flask_celery import send_errors_by_email

from utilities.logs import get_logger

celery_app = CeleryExt.celery_app

log = get_logger(__name__)
DOWNLOAD_DIR = '/data'
MAX_USER_QUOTA = 1073741824 # 1 GB


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(self, user_uuid, datasets, filters=None):
    with celery_app.app.app_context():
        log.info("Start task [{}:{}]".format(self.request.id, self.name))

        query = ''    # default to no matchers
        if filters is not None:
            query = arki.parse_matchers(filters)

        # I should check the user quota before...
        # check the output size
        data_size = arki.estimate_data_size(query, datasets)
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
            raise IOError('User quota exceeds: required size {} ({}); '
                          'remaining space {} ({})'.format(
                data_size, human_size(data_size), free_space, human_size(free_space)))

        '''
         $ arki-query [OPZIONI] QUERY DATASET...
        '''
        ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
        arki_query_cmd = "arki-query --data '{}' {}".format(query, ds)
        log.debug(arki_query_cmd)

        # save results into user space
        args = shlex.split(arki_query_cmd)
        with open(os.path.join(user_dir, 'output-'+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")), mode='w') as outfile:
            subprocess.Popen(args, stdout=outfile)

        log.info("Task [{}] completed successfully".format(self.request.id))
        return 1


def human_size(bytes, units=[' bytes','KB','MB','GB','TB', 'PB', 'EB']):
    """ Returns a human readable string reprentation of bytes
    :rtype: string
    """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes>>10, units[1:])
