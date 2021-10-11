import datetime
from typing import Optional

from flask import Response, stream_with_context
from mistral.exceptions import (
    AccessToDatasetDenied,
    NetworkNotInLicenseGroup,
    UnAuthorizedUser,
    UnexistingLicenseGroup,
    WrongDbConfiguration,
)
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import BadRequest, Conflict, NotFound, ServerError, Unauthorized
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource
from restapi.services.authentication import User
from restapi.utilities.logs import log

FILEFORMATS = ["BUFR", "JSON"]


class ObservationsQuery(Schema):
    networks = fields.Str(required=False)
    q = fields.Str(required=False)
    interval = fields.Int(required=False)
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


class ObservationsDownloader(Schema):
    output_format = fields.Str(validate=validate.OneOf(FILEFORMATS), required=True)
    networks = fields.Str(required=False)
    q = fields.Str(required=True)
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

    @decorators.auth.optional()
    @decorators.use_kwargs(ObservationsQuery, location="query")
    @decorators.endpoint(
        path="/observations",
        summary="Get values of observed parameters",
        responses={
            200: "List of values successfully retrieved",
            400: "Missing params",
            404: "The query does not give result",
            409: "The requested interval is greater than the requested timerange",
        },
    )
    @decorators.cache(timeout=600)
    # 200: {'schema': {'$ref': '#/definitions/MapStations'}}
    def get(
        self,
        user: Optional[User],
        q="",
        networks=None,
        interval=None,
        lonmin=None,
        latmin=None,
        lonmax=None,
        latmax=None,
        lat=None,
        lon=None,
        ident=None,
        onlyStations: bool = False,
        stationDetails: bool = False,
        reliabilityCheck: bool = False,
    ) -> Response:
        alchemy_db = sqlalchemy.get_instance()
        query = {}
        if lonmin or latmin or lonmax or latmax:
            if not lonmin or not lonmax or not latmin or not latmax:
                raise BadRequest("Coordinates for bounding box are missing")
            else:
                # append bounding box params to the query
                query["lonmin"] = lonmin
                query["lonmax"] = lonmax
                query["latmin"] = latmin
                query["latmax"] = latmax

        dataset_name = None
        if networks:
            # check user authorization for the requested network
            dataset_name = arki.from_network_to_dataset(networks)
            if not dataset_name:
                raise NotFound("The requested network does not exists")
            check_auth = SqlApiDbManager.check_dataset_authorization(
                alchemy_db, dataset_name, user
            )
            if not check_auth:
                raise Unauthorized(
                    "user is not authorized to access the selected network"
                )
            query["rep_memo"] = networks
        if reliabilityCheck:
            query["query"] = "attrs"

        # parse the query
        if q:
            parsed_query = dballe.from_query_to_dic(q)
            for key, value in parsed_query.items():
                query[key] = value

        query_station_data = {}
        if stationDetails:
            # check params for station
            if not networks:
                raise BadRequest("Parameter networks is missing")
            if not ident:
                if not lat or not lon:
                    raise BadRequest("Parameters to get station details are missing")
                else:
                    query_station_data["lat"] = lat
                    query_station_data["lon"] = lon
            else:
                query_station_data["ident"] = ident

            query_station_data["rep_memo"] = networks
            query_station_data["license"] = query["license"]

            # get the license group
            station_dataset = arki.from_network_to_dataset(networks)
            l_group = SqlApiDbManager.get_license_group(alchemy_db, [station_dataset])
            query["license"] = l_group.name

            # since timerange and level are mandatory, add to the query for meteograms
            if query:
                if "timerange" in query:
                    query_station_data["timerange"] = query["timerange"]
                if "level" in query:
                    query_station_data["level"] = query["level"]

            if reliabilityCheck:
                query_station_data["query"] = "attrs"
            if query and "datetimemin" in query:
                query_station_data["datetimemin"] = query["datetimemin"]
                query_station_data["datetimemax"] = query["datetimemax"]

        # check consistency with license group
        if "license" not in query:
            if networks == "multim-forecast":
                # is the only case where the request come without a requested license group
                multim_group_license = SqlApiDbManager.get_license_group(
                    alchemy_db, [dataset_name]
                )
                query["license"] = multim_group_license.name
            else:
                raise BadRequest("License group parameter is mandatory")
        try:
            group_license, dsn_subset = dballe.check_access_authorization(
                user, query["license"], dataset_name
            )

        except UnexistingLicenseGroup:
            raise BadRequest("The selected group of license does not exists")
        except UnAuthorizedUser:
            raise Unauthorized("user is not authorized to access the datasets")
        except NetworkNotInLicenseGroup:
            raise BadRequest(
                "The selected network and the selected license group does not match"
            )

        # get db type
        if "datetimemin" in query:
            db_type = dballe.get_db_type(query["datetimemin"], query["datetimemax"])
            if db_type != "dballe":
                if not user:
                    raise Unauthorized(
                        "to access archived data the user has to be logged"
                    )
                else:
                    # check for user authorization to access archived observed data
                    is_allowed_obs_archive = SqlApiDbManager.get_user_permissions(
                        user, param="allowed_obs_archive"
                    )
                    if not is_allowed_obs_archive:
                        raise Unauthorized(
                            "user is not authorized to access archived data"
                        )
        else:
            if not user:
                raise Unauthorized("to access archived data the user has to be logged")
            else:
                # check for user authorization to access archived observed data
                is_allowed_obs_archive = SqlApiDbManager.get_user_permissions(
                    user, param="allowed_obs_archive"
                )
                if not is_allowed_obs_archive:
                    raise Unauthorized("user is not authorized to access archived data")
                db_type = "mixed"

        log.debug("type of database: {}", db_type)

        if interval:
            # check if there is a requested timerange and if its interval is lower of the requested one
            if "timerange" in query:
                splitted_timerange = query["timerange"][0].split(",")
                timerange_interval = int(splitted_timerange[1]) / 3600
                if timerange_interval > interval:
                    raise Conflict(
                        "the requested interval is greater than the requested timerange"
                    )
        try:
            if db_type == "mixed":
                raw_res = dballe.get_maps_response_for_mixed(
                    query,
                    onlyStations,
                    query_station_data=query_station_data,
                    dsn_subset=dsn_subset,
                )
            else:
                raw_res = dballe.get_maps_response(
                    query,
                    onlyStations,
                    interval=interval,
                    db_type=db_type,
                    query_station_data=query_station_data,
                    dsn_subset=dsn_subset,
                )
        except AccessToDatasetDenied:
            raise ServerError("Access to dataset denied")
        except WrongDbConfiguration:
            raise ServerError(
                "no dballe DSN configured for the requested license group"
            )
        # parse the response
        res = dballe.parse_obs_maps_response(raw_res)

        if not res and stationDetails:
            raise NotFound("Station data not found")

        return self.response(res)

    @decorators.auth.optional()
    @decorators.use_kwargs(ObservationsDownloader, location="query")
    @decorators.endpoint(
        path="/observations",
        summary="Download the observed data displayed on the map",
        responses={
            200: "File of observed data",
            400: "Missing params",
            404: "The query does not give result",
        },
    )
    # 200: {'schema': {'$ref': '#/definitions/Fileoutput'}}
    def post(
        self,
        q,
        output_format,
        user: Optional[User],
        networks=None,
        lonmin=None,
        latmin=None,
        lonmax=None,
        latmax=None,
        lat=None,
        lon=None,
        ident=None,
        singleStation: bool = False,
        reliabilityCheck: bool = False,
    ) -> Response:
        alchemy_db = sqlalchemy.get_instance()
        query_data = {}
        if lonmin or latmin or lonmax or latmax:
            if not lonmin or not lonmax or not latmin or not latmax:
                raise BadRequest("Coordinates for bounding box are missing")
            else:
                # append bounding box params to the query
                query_data["lonmin"] = lonmin
                query_data["lonmax"] = lonmax
                query_data["latmin"] = latmin
                query_data["latmax"] = latmax

        dataset_name = None
        if networks:
            # check user authorization for the requested network
            dataset_name = arki.from_network_to_dataset(networks)
            if not dataset_name:
                raise NotFound("The requested network does not exists")
            check_auth = SqlApiDbManager.check_dataset_authorization(
                alchemy_db, dataset_name, user
            )
            if not check_auth:
                raise Unauthorized(
                    "user is not authorized to access the selected network"
                )
            query_data["rep_memo"] = networks
        if reliabilityCheck:
            query_data["query"] = "attrs"

        # parse the query
        parsed_query = dballe.from_query_to_dic(q)
        for key, value in parsed_query.items():
            query_data[key] = value

        query_station_data = {}
        if singleStation:
            # check params for station
            if not networks:
                raise BadRequest("Parameter networks is missing")

            if not ident:
                if not lat or not lon:
                    raise BadRequest("Parameters to get station details are missing")
                else:
                    query_station_data["lat"] = lat
                    query_station_data["lon"] = lon
            else:
                query_station_data["ident"] = ident

            query_station_data["rep_memo"] = networks

            # get the license group
            station_dataset = arki.from_network_to_dataset(networks)
            l_group = SqlApiDbManager.get_license_group(alchemy_db, [station_dataset])
            query_data["license"] = l_group.name

            # since timerange and level are mandatory, add to the query for meteograms
            if query_data:
                if "timerange" in query_data:
                    query_station_data["timerange"] = query_data["timerange"]
                if "level" in query_data:
                    query_station_data["level"] = query_data["level"]

            if reliabilityCheck:
                query_station_data["query"] = "attrs"
            if query_data and "datetimemin" in query_data:
                query_station_data["datetimemin"] = query_data["datetimemin"]
                query_station_data["datetimemax"] = query_data["datetimemax"]

        # check consistency with license group
        if "license" not in query_data:
            raise BadRequest("License group parameter is mandatory")

        try:
            group_license, dsn_subset = dballe.check_access_authorization(
                user, query_data["license"], dataset_name
            )

        except UnexistingLicenseGroup:
            raise BadRequest("The selected group of license does not exists")
        except UnAuthorizedUser:
            raise Unauthorized("user is not authorized to access the datasets")
        except NetworkNotInLicenseGroup:
            raise BadRequest(
                "The selected network and the selected license group does not match"
            )

        # get db type
        if "datetimemin" in query_data:
            db_type = dballe.get_db_type(
                query_data["datetimemin"], query_data["datetimemax"]
            )
            if db_type != "dballe":
                if not user:
                    raise Unauthorized(
                        "to access archived data the user has to be logged"
                    )
                else:
                    # check for user authorization to access archived observed data
                    is_allowed_obs_archive = SqlApiDbManager.get_user_permissions(
                        user, param="allowed_obs_archive"
                    )
                    if not is_allowed_obs_archive:
                        raise Unauthorized(
                            "user is not authorized to access archived data"
                        )
        else:
            if not user:
                raise Unauthorized("to access archived data the user has to be logged")
            else:
                # check for user authorization to access archived observed data
                is_allowed_obs_archive = SqlApiDbManager.get_user_permissions(
                    user, param="allowed_obs_archive"
                )
                if not is_allowed_obs_archive:
                    raise Unauthorized("user is not authorized to access archived data")
                db_type = "mixed"

        log.debug("type of database: {}", db_type)

        try:
            if db_type == "mixed":
                query_data_for_dballe = {}
                query_data_for_arki = {}
                query_station_data_for_dballe = {}
                query_station_data_for_arki = {}
                if query_station_data:
                    query_station_data_for_dballe = {**query_station_data}
                    query_station_data_for_arki = {**query_station_data}
                if query_data:
                    query_data_for_dballe = {**query_data}
                    query_data_for_arki = {**query_data}

                # get reftimes for arkimet and dballe
                dballe_reftime_in_query = {}
                arki_reftime_in_query = {}
                if query_data:
                    if "datetimemin" in query_data and "datetimemax" in query_data:
                        (
                            refmax_dballe,
                            refmin_dballe,
                            refmax_arki,
                            refmin_arki,
                        ) = dballe.split_reftimes(
                            query_data["datetimemin"], query_data["datetimemax"]
                        )
                        # set up queries with the correct reftimes
                        dballe_reftime_in_query["datetimemin"] = refmin_dballe
                        dballe_reftime_in_query["datetimemax"] = refmax_dballe
                        arki_reftime_in_query["datetimemin"] = refmin_arki
                        arki_reftime_in_query["datetimemax"] = refmax_arki

                if not dballe_reftime_in_query:
                    # if there is no reftime i'll get the data of the last hour
                    # TODO last hour or last day as default?
                    # for production
                    instant_now = datetime.datetime.now()
                    # for local tests
                    # today = date(2015, 12, 31)
                    # time_now = datetime.datetime.now().time()
                    # instant_now = datetime.datetime.combine(today, time_now)

                    dballe_reftime_in_query["datetimemax"] = instant_now
                    dballe_reftime_in_query["datetimemin"] = datetime.datetime.combine(
                        instant_now, datetime.time(instant_now.hour, 0, 0)
                    )

                # get queries and db for dballe extraction (taking advantage of the method already implemented to get data values for maps)
                log.debug("getting queries and db for dballe")
                for key, value in dballe_reftime_in_query.items():
                    query_data_for_dballe[key] = value
                    if query_station_data_for_dballe:
                        query_station_data_for_dballe[key] = value
                (
                    dballe_db,
                    dballe_query_data,
                    dballe_query_station_data,
                    mobile_db,
                ) = dballe.get_maps_response(
                    query_data_for_dballe,
                    False,
                    db_type="dballe",
                    query_station_data=query_station_data_for_dballe,
                    download=True,
                )
                # get queries and db for arkimet extraction
                arki_db = None
                arki_query_data = {}
                arki_query_station_data = {}
                if arki_reftime_in_query:
                    for key, value in arki_reftime_in_query.items():
                        query_data_for_arki[key] = value
                        if query_station_data_for_arki:
                            query_station_data_for_arki[key] = value
                    log.debug("getting queries and db for arkimet")
                    (
                        arki_db,
                        arki_query_data,
                        arki_query_station_data,
                        arki_mobile_db,
                    ) = dballe.get_maps_response(
                        query_data_for_arki,
                        False,
                        db_type="arkimet",
                        query_station_data=query_station_data_for_arki,
                        download=True,
                        dsn_subset=dsn_subset,
                    )

                # merge the queries and the db
                log.debug("merge queries and db for mixed extraction")
                (
                    db_for_extraction,
                    download_query_data,
                ) = dballe.merge_db_for_download(
                    dballe_db,
                    dballe_query_data,
                    arki_db,
                    arki_query_data,
                    mobile_db=mobile_db,
                    dsn_subset=dsn_subset,
                )
                # if there is a temporary db we no more need the dsn subset list and the mobile db connection as we have already use them for fill the temp db
                if arki_db:
                    dsn_subset = []
                    mobile_db = None
                # if there is a query station data, merge the two queries
                download_query_station_data = {}
                if query_station_data:
                    download_query_station_data = dballe.parse_query_for_maps(
                        dballe_query_station_data
                    )
                    if arki_query_station_data:
                        if "datetimemin" in arki_query_station_data:
                            download_query_station_data[
                                "datetimemin"
                            ] = arki_query_station_data["datetimemin"]
            else:
                # take advantage of the method already implemented to get data values for maps in order to get the query and the db to extract the data
                (
                    db_for_extraction,
                    download_query_data,
                    download_query_station_data,
                    mobile_db,
                ) = dballe.get_maps_response(
                    query_data,
                    False,
                    db_type=db_type,
                    query_station_data=query_station_data,
                    download=True,
                    dsn_subset=dsn_subset,
                )

            mime = None
            if output_format == "JSON":
                mime = "application/json"
            else:
                mime = "application/octet-stream"

            # stream data
            if db_for_extraction:
                return Response(
                    stream_with_context(
                        dballe.download_data_from_map(
                            db_for_extraction,
                            output_format,
                            download_query_data,
                            download_query_station_data,
                            qc_filter=reliabilityCheck,
                            mobile_db=mobile_db,
                            dsn_subset=dsn_subset,
                        )
                    ),
                    mimetype=mime,
                )
            else:
                return []
        except AccessToDatasetDenied:
            raise ServerError("Access to dataset denied")
