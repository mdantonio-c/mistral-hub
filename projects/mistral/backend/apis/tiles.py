# -*- coding: utf-8 -*-
import os
import copy
from flask import send_file

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi import decorators
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

MEDIA_ROOT = '/meteo/'

RUNS = ['00', '12']
RESOLUTIONS = ['lm2.2', 'lm5']

class TilesEndpoint(EndpointResource):
    labels = ['tiled map ready']
    GET = {
        '/tiles': {
            'summary': 'Get the last available tiled map set as a reference time.',
            'parameters': [
                {'name': 'run', 'in': 'query', 'required': True, 'type': 'string', 'enum': RUNS, 'description': 'Execution of the forecast model'},
                {'name': 'res', 'in': 'query', 'required': True, 'type': 'string', 'enum': RESOLUTIONS, 'description': 'Resolution of the forecast model'}
            ],
            'responses': {
                '200': {'description': 'Tiled map successfully retrieved'},
                '400': {'description': 'Invalid parameters'},
                '404': {'description': 'Tiled map does not exists'},
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.base_path = None;

    @decorators.catch_errors()
    def get(self):
        params = self.get_input()
        # TODO validate params
        # e.g. Tiles-00-lm2.2.web
        run = params['run'] if 'run' in params else '00'
        self.base_path = os.path.join(
            MEDIA_ROOT,
            'GALILEO',
            'PROD', "Tiles-{}-{}.web".format(run, params['res']))
        area = 'Italia' if params['res'] == 'lm2.2' else 'Area_Mediterranea'
        ready_file = self._get_ready_file(area)

        data = {
            'reftime': ready_file[:10],
            'platform': 'GALILEO'
        }
        return self.response(data)

    def _get_ready_file(self, area):
        ready_path = os.path.join(self.base_path, area)
        log.debug("ready_path: {}".format(ready_path))

        ready_files = []
        if os.path.exists(ready_path):
            ready_files = [f for f in os.listdir(ready_path) if os.path.isfile(
                os.path.join(ready_path, f)) and ".READY" in f]

        # Check if .READY file exists (if not, images are not ready yet)
        log.debug("Looking for .READY files in: {}".format(ready_path))
        if len(ready_files) > 0:
            log.debug(".READY files found: {}".format(ready_files))
        else:
            raise RestApiException('no .READY files found', status_code=hcodes.HTTP_BAD_NOTFOUND)
        return ready_files[0]
