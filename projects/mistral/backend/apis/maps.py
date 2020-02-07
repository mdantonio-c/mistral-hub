# -*- coding: utf-8 -*-
import os
import datetime
from flask import send_file

from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

MEDIA_ROOT = '/meteo/'

RUNS = ['00', '12']
RESOLUTIONS = ['lm2.2', 'lm5']
FIELDS = ['prec3', 'prec6', 't2m', 'wind', 'cloud', 'cloud_hml', 'humidity', 'snow3', 'snow6']
AREAS = ['Italia', 'Nord_Italia', 'Centro_Italia', 'Sud_Italia', 'Area_Mediterranea']
PLATFORMS = ['GALILEO', 'MEUCCI']
ENVS = ['PROD', 'DEV']


def validate_meteo_params(params):
    if 'run' not in params or params['run'] not in RUNS:
        raise RestApiException(
            "Please specify a valid run. Expected one of {}".format(RUNS),
            status_code=hcodes.HTTP_BAD_REQUEST)
    # TODO validate parameters


class MapEndpoint:

    __meteo_params__ = [
        {'name': 'run', 'in': 'query', 'required': True, 'type': 'string', 'enum': RUNS,
         'description': 'Execution of the forecast model'},
        {'name': 'res', 'in': 'query', 'required': True, 'type': 'string', 'enum': RESOLUTIONS,
         'description': 'Resolution of the forecast model'},
        {'name': 'field', 'in': 'query', 'required': True, 'type': 'string', 'enum': FIELDS,
         'description': 'Forecast parameter (e.g. temperature, humidity etc.)'},
        {'name': 'area', 'in': 'query', 'required': True, 'type': 'string', 'enum': AREAS,
         'description': 'Forecast area'},
        {'name': 'platform', 'in': 'query', 'default': 'GALILEO', 'type': 'string', 'enum': PLATFORMS,
         'description': 'HPC cluster'},
        {'name': 'env', 'in': 'query', 'default': 'PROD', 'type': 'string', 'enum': ENVS,
         'description': 'Execution environment'}
    ]

    def __init__(self):
        self.base_path = None

    def set_base_path(self, params):
        self.base_path = os.path.join(
            MEDIA_ROOT,
            params['platform'],
            params['env'], "Magics-{}-{}.web".format(params['run'], params['res']))

    def get_ready_file(self, area):
        ready_path = os.path.join(self.base_path, area)
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


class MapImage(EndpointResource, MapEndpoint):
    labels = ['map image']
    GET = {
        '/maps/<map_offset>': {
            'summary': 'Get a forecast map for a specific run.',
            'parameters': MapEndpoint.__meteo_params__,
            'responses': {
                '200': {'description': 'Map successfully retrieved'},
                '400': {'description': 'Invalid parameters'},
                '404': {'description': 'Map does not exists'},
            }
        }
    }

    @catch_error()
    @authentication.required()
    def get(self, map_offset):
        """Get a forecast map for a specific run."""
        params = self.get_input()
        # validate_meteo_params(params)
        log.debug('Retrieve map image by offset <{}>'.format(map_offset))

        self.set_base_path(params)

        # Check if the images are ready: 2017112900.READY
        ready_file = self.get_ready_file(params['area'])
        reftime = ready_file[:10]

        # get map image
        map_image_file = os.path.join(
            self.base_path,
            params['area'],
            params['field'],
            '{field}.{reftime}.{offset}.png'.format(
                field=params['field'], reftime=reftime, offset=map_offset
            ))
        if not os.path.isfile(map_image_file):
            raise RestApiException('Map image not found for offset {}'.format(map_offset), hcodes.HTTP_BAD_NOTFOUND)
        return send_file(map_image_file, mimetype='image/png')


class MapSet(EndpointResource, MapEndpoint):
    labels = ['map set']
    GET = {
        '/maps/ready': {
            'summary': 'Get the last available map set for a specific run returning the reference time as well.',
            'parameters': MapEndpoint.__meteo_params__,
            'responses': {
                '200': {'description': 'Map set successfully retrieved', 'schema': {'$ref': '#/definitions/Mapset'}},
                '400': {'description': 'Invalid parameters'},
                '404': {'description': 'Map set does not exists'},
            }
        }
    }

    @catch_error()
    @authentication.required()
    def get(self):
        """Get the last available map set for a specific run returning the reference time as well."""
        params = self.get_input()
        # validate_meteo_params(params)
        log.debug('Retrieve map set for last run <{}>'.format(params['run']))

        self.set_base_path(params)

        # Check if the images are ready: 2017112900.READY
        ready_file = self.get_ready_file(params['area'])
        reftime = ready_file[:10]

        data = {
            'reftime': reftime,
            'offsets': []
        }

        # load image offsets
        images_path = os.path.join(
            self.base_path,
            params['area'],
            params['field'])
        list_file = sorted(os.listdir(images_path))
        data['offsets'] = [f.split('.')[-2] for f in list_file if os.path.isfile(
            os.path.join(images_path, f))]
        return self.force_response(data)


class MapLegend(EndpointResource, MapEndpoint):
    labels = ['legend']
    GET = {
        '/maps/legend': {
            'summary': 'Get a specific forecast map legend.',
            'parameters': MapEndpoint.__meteo_params__,
            'responses': {
                '200': {'description': 'Legend successfully retrieved'},
                '400': {'description': 'Invalid parameters'},
                '404': {'description': 'Legend does not exists'},
            }
        }
    }

    @catch_error()
    @authentication.required()
    def get(self):
        """Get a forecast legend for a specific run."""
        params = self.get_input()
        # validate_meteo_params(params)
        # NOTE: 'area' param is not strictly necessary here although present among the parameters of the request
        log.debug('Retrieve legend for run <{run}, {res}, {field}>'.format(
            run=params['run'], res=params['res'], field=params['field']))

        self.set_base_path(params)

        # Get legend image
        legend_path = os.path.join(self.base_path, "legends")
        map_legend_file = os.path.join(
            legend_path, params['field'] + ".png")
        log.debug(map_legend_file)
        if not os.path.isfile(map_legend_file):
            raise RestApiException(
                'Map legend not found for field <{}>'.format(params['field']), hcodes.HTTP_BAD_NOTFOUND)
        return send_file(map_legend_file, mimetype='image/png')
