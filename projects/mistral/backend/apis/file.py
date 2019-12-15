# -*- coding: utf-8 -*-

import os
from flask import send_from_directory
from mistral.services.requests_manager import RequestManager
from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

DOWNLOAD_DIR = '/data'


class FileDownload(EndpointResource):

    # schema_expose = True
    labels = ['file']
    GET = {
        '/data/<filename>': {
            'summary': 'Download output file',
            'parameters': [
                {
                    'in': 'path',
                    'name': 'file',
                    'type': 'string',
                    'required': True,
                    'description': 'file to download',
                }
            ],
            'responses': {
                '200': {
                    'description': 'found the file to download',
                    'schema': {'$ref': '#/definitions/Fileoutput'},
                },
                '404': {'description': 'file not found'},
            },
        }
    }

    @catch_error()
    @authentication.required()
    def get(self, filename):

        user = self.get_current_user()
        db = self.get_service_instance('sqlalchemy')
        # check if the file exists, the current user is the owner and if it is in its folder
        if RequestManager.check_fileoutput(db, user, filename, DOWNLOAD_DIR):
            user_dir = os.path.join(DOWNLOAD_DIR, user.uuid)
            log.info('directory: {}', user_dir)
            # download the file as a response attachment
            return send_from_directory(user_dir, filename, as_attachment=True)

        else:
            raise RestApiException(
                "File not found", status_code=hcodes.HTTP_BAD_NOTFOUND
            )
