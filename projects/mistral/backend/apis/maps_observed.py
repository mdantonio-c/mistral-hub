# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi import decorators
from restapi.utilities.htmlcodes import hcodes
from mistral.services.dballe import BeDballe as dballe
from restapi.utilities.logs import log
from mistral.exceptions import AccessToDatasetDenied


class MapsObservations(EndpointResource):
    # schema_expose = True
    labels = ['maps-observations']
    GET = {
        '/observations': {
            'summary': 'Get values of observed parameters',
            'parameters': [
                # uncomment if we decide that networks can be multiple
                # {
                #     'name': 'networks',
                #     'in': 'query',
                #     'type': 'array',
                #     'uniqueItems': True,
                #     'items': {'type': 'string'},
                # },
                {'name': 'networks', 'in': 'query', 'type': 'string'},
                {'name': 'q', 'in': 'query', 'type': 'string', 'default': ''},
                {'name': 'bounding-box', 'in': 'query', 'type': 'string',
                 'description': 'coordinates of a bounding box'},
                {'name': 'lat', 'in': 'query', 'type': 'string'},
                {'name': 'lon', 'in': 'query', 'type': 'string'},
                {'name': 'ident', 'in': 'query', 'type': 'string'},

                {
                    'name': 'onlyStations',
                    'in': 'query',
                    'type': 'boolean',
                    'default': False,
                    'allowEmptyValue': True,
                },
                {
                    'name': 'stationDetails',
                    'in': 'query',
                    'type': 'boolean',
                    'default': False,
                    'allowEmptyValue': True,
                },

            ],
            'responses': {
                '200': {
                    'description': 'List of values successfully retrieved',
                    'schema': {'$ref': '#/definitions/MapStations'},
                },
                '404': {
                    'description': 'the query does not give result',
                }
            },
        },
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self):
        params = self.get_input()
        # ids = params.get('stations')
        # nt = params.get('networks')
        # stations = ids.split(',') if ids is not None else []
        # networks = nt.split(',') if nt is not None else []
        networks = params.get('networks')
        # log.debug(networks)
        bbox = params.get('bounding-box')
        bbox_list = bbox.split(',') if bbox is not None else []
        q = params.get('q')
        lat = params.get('lat')
        lon = params.get('lon')
        ident = params.get('ident')

        bounding_box = {}
        if bbox_list:
            log.debug(bbox_list)
            for i in bbox_list:
                split = i.split(':')
                bounding_box[split[0]] = split[1]

        # check if only stations are requested
        only_stations = params.get('onlyStations')
        if isinstance(only_stations, str) and (
                only_stations == '' or only_stations.lower() == 'true'
        ):
            only_stations = True
        elif type(only_stations) == bool:
            # do nothing
            pass
        else:
            only_stations = False

        # check if station details are requested
        station_details = params.get('stationDetails')
        if isinstance(station_details, str) and (
                station_details == '' or station_details.lower() == 'false'
        ):
            station_details = False
        elif type(station_details) == bool:
            # do nothing
            pass
        else:
            station_details = True
        station_details_q = {}
        if station_details:
            # check params for station
            if not networks:
                raise RestApiException(
                    'Parameter networks is missing',
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            if not ident:
                if not lat or not lon:
                    raise RestApiException(
                        'Parameters to get station details are missing',
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )
                else:
                    station_details_q['lat'] = float(lat)
                    station_details_q['lon'] = float(lon)
            else:
                station_details_q['ident'] = ident
        query = None
        db_type = None
        if q:
            # parse the query
            query = dballe.from_query_to_dic(q)

            # get db type
            if 'datetimemin' in query:
                db_type = dballe.get_db_type(query['datetimemin'], query['datetimemax'])
            else:
                db_type = 'mixed'
        else:
            db_type = 'mixed'
        log.debug('type of database: {}', db_type)
        try:
            if db_type == 'mixed':
                res = dballe.get_maps_response_for_mixed(networks, bounding_box, query, only_stations,
                                                         station_details_q=station_details_q)
            else:
                res = dballe.get_maps_response(networks, bounding_box, query, only_stations, db_type=db_type,
                                               station_details_q=station_details_q)
        except AccessToDatasetDenied:
            raise RestApiException(
                'Access to dataset denied',
                status_code=hcodes.HTTP_SERVER_ERROR,
            )

        if not res and station_details_q:
            raise RestApiException(
                "Station data not found",
                status_code=hcodes.HTTP_BAD_NOTFOUND,
            )

        return self.response(res)
