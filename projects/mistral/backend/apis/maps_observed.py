# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from restapi.utilities.logs import log


class MapsObservations(EndpointResource):

    # schema_expose = True
    labels = ['maps-observations']
    GET = {
        '/maps/observations': {
            'summary': 'Get values of observed parameters',
            'parameters': [
                {
                    'name': 'networks',
                    'in': 'query',
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {'type': 'string'},
                },
                {'name': 'q', 'in': 'query', 'type': 'string', 'default': ''},
                {'name': 'bounding-box', 'in': 'query', 'type': 'string', 'description': 'coordinates of a bounding box'},

            ],
            'responses': {
                '200': {
                    'description': 'List of values successfully retrieved',
                    'schema': {'$ref': '#/definitions/MapStations'},
                }
            },
        },
        '/maps/observations/<station_id>': {
            'summary': 'Get station information by id',
            'parameters': [
                {
                    'name': 'networks',
                    'in': 'query',
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {'type': 'string'},
                },
                {'name': 'q', 'in': 'query', 'type': 'string', 'default': ''},
            ],
            'responses': {
                '200': {
                    'description': 'List of values successfully retrieved',
                    'schema': {'$ref': '#/definitions/MapStationData'},
                },
                '404': {
                   'description': 'station not found',
                }
            },
        }
    }

    @catch_error()
    @authentication.required()
    def get(self, station_id=None):
        params = self.get_input()
        # ids = params.get('stations')
        # nt = params.get('networks')
        # stations = ids.split(',') if ids is not None else []
        # networks = nt.split(',') if nt is not None else []
        log.debug('params: {}', params)
        networks = params.get('networks')
        bbox = params.get('bounding-box')
        bbox_list = bbox.split(',') if bbox is not None else []
        q = params.get('q')

        bounding_box = {}
        if bbox_list:
            log.debug(bbox_list)
            for i in bbox_list:
                split = i.split(':')
                bounding_box[split[0]] = split[1]

        query = None
        db_type = None
        if q:
            # parse the query
            query = dballe.from_query_to_dic(q)

            # get db type
            if 'datetimemin' in query:
                db_type = dballe.get_db_type(query['datetimemin'], query['datetimemax'])
                # log.debug('db type: {}', db_type)
                # if reftime is expressed and db_type is mixed, split the query for  arkimet and dballe
                if db_type == 'mixed':
                    refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = dballe.split_reftimes(
                        query['datetimemin'],
                        query['datetimemax'])
                    # set the datetimemin as limit to data in dballe
                    query['datetimemin'] = refmin_dballe
                    query['datetimemax_arki'] = refmax_arki
                    query['datetimemin_arki'] = refmin_arki
            else:
                db_type = 'mixed'

        res = dballe.get_maps_data(networks, bounding_box, query, db_type, station_id=station_id)

        if station_id and not res:
            raise RestApiException(
                "Station '{}' not found".format(station_id),
                status_code=hcodes.HTTP_BAD_NOTFOUND,
            )


        # # check if only stations are requested
        # only_stations = params.get('onlyStations')
        # if isinstance(only_stations, str) and (
        #         only_stations == '' or only_stations.lower() == 'true'
        # ):
        #     only_stations = True
        # elif type(only_stations) == bool:
        #     # do nothing
        #     pass
        # else:
        #     only_stations = False

        # per il reftime: se sono dati puntuali, non ha to from ma ha solo data e ora

        return self.force_response(res)
