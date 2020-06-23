from flask_apispec import MethodResource, use_kwargs
from marshmallow import fields, validate
from mistral.exceptions import AccessToDatasetDenied
from mistral.services.dballe import BeDballe as dballe
from restapi import decorators
from restapi.exceptions import RestApiException
from restapi.models import InputSchema
from restapi.rest.definition import EndpointResource
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class ObservationsQuery(InputSchema):
    networks = fields.Str(required=False)
    q = fields.Str(required=False)
    bounding_box = fields.Str(required=False)
    lat = fields.Str(required=False)
    lon = fields.Str(required=False)
    ident = fields.Str(required=False)
    onlyStations = fields.Bool(required=False)
    stationDetails = fields.Bool(required=False)
    reliabilityCheck = fields.Bool(required=False)


class MapsObservations(EndpointResource):
    # schema_expose = True
    labels = ["maps-observations"]
    GET = {
        "/observations": {
            "summary": "Get values of observed parameters",
            "responses": {
                "200": {
                    "description": "List of values successfully retrieved",
                    "schema": {"$ref": "#/definitions/MapStations"},
                },
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
        bounding_box=None,
        lat=None,
        lon=None,
        ident=None,
        onlyStations=False,
        stationDetails=False,
        reliabilityCheck=False,
    ):
        bbox_list = bounding_box.split(",") if bounding_box is not None else []

        bounding_box = {}
        if bbox_list:
            log.debug(bbox_list)
            for i in bbox_list:
                split = i.split(":")
                bounding_box[split[0]] = split[1]

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
                    station_details_q["lat"] = float(lat)
                    station_details_q["lon"] = float(lon)
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
