from flask import Response, stream_with_context
from flask_apispec import use_kwargs
from marshmallow import fields, validate
from mistral.exceptions import AccessToDatasetDenied
from mistral.services.dballe import BeDballe as dballe
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.models import InputSchema
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

FILEFORMATS = ["BUFR", "JSON"]


class ObservationsQuery(InputSchema):
    networks = fields.Str(required=False)
    q = fields.Str(required=False)
    lonmin = fields.Float(required=False)
    latmin = fields.Float(required=False)
    lonmax = fields.Float(required=False)
    latmax = fields.Float(required=False)
    lat = fields.Float(required=False)
    lon = fields.Float(required=False)
    ident = fields.Str(required=False)
    onlyStations = fields.Bool(required=False)
    stationDetails = fields.Bool(required=False)
    reliabilityCheck = fields.Bool(required=False)


class ObservationsDownloader(InputSchema):
    output_format = fields.Str(validate=validate.OneOf(FILEFORMATS), required=True)
    networks = fields.Str(required=False)
    q = fields.Str(required=False)
    lonmin = fields.Float(required=False)
    latmin = fields.Float(required=False)
    lonmax = fields.Float(required=False)
    latmax = fields.Float(required=False)
    lat = fields.Float(required=False)
    lon = fields.Float(required=False)
    ident = fields.Str(required=False)
    singleStation = fields.Bool(required=False)
    reliabilityCheck = fields.Bool(required=False)


class MapsObservations(EndpointResource):
    # schema_expose = True
    labels = ["maps-observations"]
    _GET = {
        "/observations": {
            "summary": "Get values of observed parameters",
            "responses": {
                "200": {
                    "description": "List of values successfully retrieved",
                    "schema": {"$ref": "#/definitions/MapStations"},
                },
                "400": {"description": "missing params"},
                "404": {"description": "the query does not give result"},
            },
        },
    }
    _POST = {
        "/observations": {
            "summary": "Download the observed data displayed on the map",
            "responses": {
                "200": {
                    "description": "File of observed data",
                    "schema": {"$ref": "#/definitions/Fileoutput"},
                },
                "400": {"description": "missing params"},
                "404": {"description": "the query does not give result"},
            },
        },
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    @use_kwargs(ObservationsQuery)
    def get(
        self,
        networks=None,
        q="",
        lonmin=None,
        latmin=None,
        lonmax=None,
        latmax=None,
        lat=None,
        lon=None,
        ident=None,
        onlyStations=False,
        stationDetails=False,
        reliabilityCheck=False,
    ):
        bounding_box = {}
        if lonmin or latmin or lonmax or latmax:
            if not lonmin or not lonmax or not latmin or not latmax:
                raise RestApiException(
                    "Coordinates for bounding box are missing",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            else:
                bounding_box["lonmin"] = lonmin
                bounding_box["lonmax"] = lonmax
                bounding_box["latmin"] = latmin
                bounding_box["latmax"] = latmax

        station_details_q = {}
        if stationDetails:
            # check params for station
            if not networks:
                raise RestApiException(
                    "Parameter networks is missing",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            if not ident:
                if not lat or not lon:
                    raise RestApiException(
                        "Parameters to get station details are missing",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )
                else:
                    station_details_q["lat"] = lat
                    station_details_q["lon"] = lon
            else:
                station_details_q["ident"] = ident
        query = None
        db_type = None
        if q:
            # parse the query
            query = dballe.from_query_to_dic(q)

            # get db type
            if "datetimemin" in query:
                db_type = dballe.get_db_type(query["datetimemin"], query["datetimemax"])
            else:
                db_type = "mixed"
        else:
            db_type = "mixed"
        log.debug("type of database: {}", db_type)
        try:
            if db_type == "mixed":
                res = dballe.get_maps_response_for_mixed(
                    networks,
                    bounding_box,
                    query,
                    onlyStations,
                    station_details_q=station_details_q,
                    quality_check=reliabilityCheck,
                )
            else:
                res = dballe.get_maps_response(
                    networks,
                    bounding_box,
                    query,
                    onlyStations,
                    db_type=db_type,
                    station_details_q=station_details_q,
                    quality_check=reliabilityCheck,
                )
        except AccessToDatasetDenied:
            raise RestApiException(
                "Access to dataset denied", status_code=hcodes.HTTP_SERVER_ERROR,
            )

        if not res and station_details_q:
            raise RestApiException(
                "Station data not found", status_code=hcodes.HTTP_BAD_NOTFOUND,
            )

        return self.response(res)

    @decorators.catch_errors()
    @decorators.auth.required()
    @use_kwargs(ObservationsDownloader)
    def post(
        self,
        output_format,
        networks=None,
        q="",
        lonmin=None,
        latmin=None,
        lonmax=None,
        latmax=None,
        lat=None,
        lon=None,
        ident=None,
        singleStation=False,
        reliabilityCheck=False,
    ):
        bounding_box = {}
        if lonmin or latmin or lonmax or latmax:
            if not lonmin or not lonmax or not latmin or not latmax:
                raise RestApiException(
                    "Coordinates for bounding box are missing",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            else:
                bounding_box["lonmin"] = lonmin
                bounding_box["lonmax"] = lonmax
                bounding_box["latmin"] = latmin
                bounding_box["latmax"] = latmax

        station_details_q = {}
        if singleStation:
            # check params for station
            if not networks:
                raise RestApiException(
                    "Parameter networks is missing",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            if not ident:
                if not lat or not lon:
                    raise RestApiException(
                        "Parameters to get station details are missing",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )
                else:
                    station_details_q["lat"] = lat
                    station_details_q["lon"] = lon
            else:
                station_details_q["ident"] = ident
        query = None
        db_type = None
        if q:
            # parse the query
            query = dballe.from_query_to_dic(q)

            # get db type
            if "datetimemin" in query:
                db_type = dballe.get_db_type(query["datetimemin"], query["datetimemax"])
            else:
                db_type = "mixed"
        else:
            db_type = "mixed"
        log.debug("type of database: {}", db_type)
        try:
            if db_type == "mixed":
                query_for_dballe = {}
                query_for_arki = {}
                # get reftimes for arkimet and dballe
                if query:
                    # setup query for dballe
                    query_for_dballe = {**query}
                    query_for_arki = {**query}
                    if "datetimemin" in query and "datetimemax" in query:
                        (
                            refmax_dballe,
                            refmin_dballe,
                            refmax_arki,
                            refmin_arki,
                        ) = dballe.split_reftimes(
                            query["datetimemin"], query["datetimemax"]
                        )
                        # set up queries with the correct reftimes
                        query_for_dballe["datetimemin"] = refmin_dballe
                        query_for_dballe["datetimemin"] = refmin_dballe
                        query_for_arki["datetimemin"] = refmin_arki
                        query_for_arki["datetimemax"] = refmax_arki

                # get queries and db for dballe extraction (taking advantage of the method already implemented to get data values for maps)
                log.debug("getting queries and db for dballe")
                (
                    dballe_db,
                    dballe_query_data,
                    dballe_query_station_data,
                ) = dballe.get_maps_response(
                    networks,
                    bounding_box,
                    query_for_dballe,
                    False,
                    db_type="dballe",
                    station_details_q=station_details_q,
                    quality_check=reliabilityCheck,
                    download=True,
                )
                # get queries and db for arkimet extraction
                log.debug("getting queries and db for arkimet")
                (
                    arki_db,
                    arki_query_data,
                    arki_query_station_data,
                ) = dballe.get_maps_response(
                    networks,
                    bounding_box,
                    query_for_arki,
                    False,
                    db_type="arkimet",
                    station_details_q=station_details_q,
                    quality_check=reliabilityCheck,
                    download=True,
                )

                # merge the queries and the db
                log.debug("merge queries and db for mixed extraction")
                (db_for_extraction, query_data,) = dballe.merge_db_for_download(
                    dballe_db, dballe_query_data, arki_db, arki_query_data,
                )
                # query station data has no reftime, so the arki_ and the dballe_ ones are exactly the same
                query_station_data = arki_query_station_data
            else:
                # take advantage of the method already implemented to get data values for maps in order to get the query and the db to extract the data
                (
                    db_for_extraction,
                    query_data,
                    query_station_data,
                ) = dballe.get_maps_response(
                    networks,
                    bounding_box,
                    query,
                    False,
                    db_type=db_type,
                    station_details_q=station_details_q,
                    quality_check=reliabilityCheck,
                    download=True,
                )

            mime = None
            if output_format == "JSON":
                mime = "application/json"
            else:
                mime = "application/octet-stream"

            # stream data
            return Response(
                stream_with_context(
                    dballe.download_data_from_map(
                        db_for_extraction,
                        singleStation,
                        output_format,
                        query_data,
                        query_station_data,
                    )
                ),
                mimetype=mime,
            )
        except AccessToDatasetDenied:
            raise RestApiException(
                "Access to dataset denied", status_code=hcodes.HTTP_SERVER_ERROR,
            )
