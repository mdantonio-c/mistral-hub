# -*- coding: utf-8 -*-
import os
import subprocess

from restapi.rest.definition import EndpointResource

from restapi import decorators
from restapi.utilities.htmlcodes import hcodes
# from restapi.utilities.logs import log

# from sqlalchemy.orm import load_only

DOWNLOAD_DIR = '/data'


class Usage(EndpointResource):

    labels = ['usage']
    GET = {
        '/usage': {
            'summary': 'Get user disk usage.',
            'responses': {
                '200': {
                    'description': 'Disk usage information',
                    'schema': {'$ref': '#/definitions/StorageUsage'},
                },
                '401': {'description': 'Authentication required'},
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self):
        """
        Get actual user disk quota and current usage
        :return:
        """
        user = self.get_current_user()

        # get user disk quota
        # db = self.get_service_instance('sqlalchemy')
        # disk_quota = db.session.query(db.User.disk_quota).filter_by(id=user.id).scalar()
        # log.debug(disk_quota)

        # get current usage
        used_quota = 0
        user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
        if os.path.isdir(user_dir):
            used_quota = int(
                subprocess.check_output(['du', '-sb', user_dir]).split()[0]
            )

        data = {'quota': user.disk_quota, 'used': used_quota}
        return self.response(data, code=hcodes.HTTP_OK_BASIC)
