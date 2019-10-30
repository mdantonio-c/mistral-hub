# -*- coding: utf-8 -*-
import os
import subprocess

from restapi.rest.definition import EndpointResource
# from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
# from sqlalchemy.orm import load_only

logger = get_logger(__name__)
DOWNLOAD_DIR = '/data'


class Usage(EndpointResource):

    # schema_expose = True
    labels = ['usage']
    GET = {'/usage': {'summary': 'Get user disk usage.', 'custom': {}, 'responses': {'200': {'description': 'Disk usage information', 'schema': {'$ref': '#/definitions/StorageUsage'}}, '401': {'description': 'Authentication required'}}}}

    @catch_error()
    @authentication.required()
    def get(self):
        """
        Get actual user disk quota and current usage
        :return:
        """
        user = self.get_current_user()

        # get user disk quota
        # db = self.get_service_instance('sqlalchemy')
        # disk_quota = db.session.query(db.User.disk_quota).filter_by(id=user.id).scalar()
        # logger.debug(disk_quota)

        # get current usage
        used_quota = 0
        user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
        if os.path.isdir(user_dir):
            used_quota = int(subprocess.check_output(['du', '-sb', user_dir]).split()[0])

        data = {
            'quota': user.disk_quota,
            'used': used_quota
        }
        return self.force_response(
            data, code=hcodes.HTTP_OK_BASIC)
