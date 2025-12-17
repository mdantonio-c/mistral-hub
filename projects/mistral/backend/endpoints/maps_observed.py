import datetime
from typing import Any, Dict, List, Optional

from flask import Response as FlaskResponse
from flask import stream_with_context
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
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log

FILEFORMATS = ["BUFR", "JSON"]
MAX_REQ_DAYS = 3
MAX_REQ_DAYS_AUTHENTICATED = 10


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
    allStationProducts = fields.Bool(required=False)
    reliabilityCheck = fields.Bool(required=False)
    last = fields.Bool(required=False)


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
        q: str = "",
        networks: Optional[str] = None,
        interval: Optional[int] = None,
        lonmin: Optional[float] = None,
        latmin: Optional[float] = None,
        lonmax: Optional[float] = None,
        latmax: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        ident: Optional[str] = None,
        onlyStations: bool = False,
        stationDetails: bool = False,
        allStationProducts: bool = True,
        reliabilityCheck: bool = False,
        last: bool = False,
    ) -> Response:
        alchemy_db = sqlalchemy.get_instance()
        query: Dict[str, Any] = {}
        if lonmin or latmin or lonmax or latmax:
            if not lonmin or not lonmax or not latmin or not latmax:
                raise BadRequest("Coordinates for bounding box are missing")
            else:
                # append bounding box params to the query
                query["lonmin"] = lonmin
                query["lonmax"] = lonmax
                query["latmin"] = latmin
                query["latmax"] = latmax

        # parse the query
        if q:
            parsed_query = dballe.from_query_to_dic(q)
            log.debug(f"complete query: {parsed_query}")
            for key, value in parsed_query.items():
                query[key] = value

        networks_list = None
        if networks:
            networks_list = [x.strip() for x in networks.split(" or ")]
            for n in networks_list:
                # check user authorization for the requested network
                dataset_name = arki.from_network_to_dataset(n)
                if not dataset_name:
                    raise NotFound("The requested network does not exists")
                check_auth = SqlApiDbManager.check_dataset_authorization(
                    alchemy_db, dataset_name, user
                )
                if not check_auth:
                    raise Unauthorized(
                        "user is not authorized to access the selected network"
                    )
            query["network"] = networks_list

        if reliabilityCheck:
            query["query"] = "attrs"

        query_station_data: Dict[str, Any] = {}
        if stationDetails:
            # check params for station
            if not networks:
                raise BadRequest("Parameter networks is missing")
            if not len(networks_list) == 1:
                raise BadRequest(
                    "You can set a maximum of 1 network in parameter 'networks' if stationDetails is chosen"
                )
            if not ident:
                if not lat or not lon:
                    raise BadRequest("Parameters to get station details are missing")
                else:
                    query_station_data["lat"] = lat
                    query_station_data["lon"] = lon
            else:
                query_station_data["ident"] = ident

            query_station_data["network"] = networks

            query_station_data["license"] = query["license"]

            # get the license group
            station_dataset = arki.from_network_to_dataset(networks)

            l_group = SqlApiDbManager.get_license_group(alchemy_db, [station_dataset])
            query["license"] = l_group.name

            # since timerange and level are mandatory, add to the query for meteograms
            if query:
                if "datetimemin" in query:
                    query_station_data["datetimemin"] = query["datetimemin"]
                if "datetimemax" in query:
                    query_station_data["datetimemax"] = query["datetimemax"]

            if reliabilityCheck:
                query_station_data["query"] = "attrs"

        # check consistency with license group
        if "license" not in query:
            raise BadRequest("License group parameter is mandatory")
        try:
            all_dsn = set()
            if networks_list:
                for n in networks_list:
                    # get dataset name (note that dataset name corresponds to arkimet id)
                    dataset_name = arki.from_network_to_dataset(n)
                    if not dataset_name:
                        raise NotFound("The requested network does not exists")
                    group_license, dsn_subset = dballe.check_access_authorization(
                        user, query["license"], dataset_name
                    )
                    all_dsn.update(dsn_subset)
                dsn_subset = list(all_dsn)
            else:
                group_license, dsn_subset = dballe.check_access_authorization(
                    user, query["license"], None
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
        datetime_min = None
        datetime_max = None
        if "datetimemin" in query:
            datetime_min = query["datetimemin"]
            log.debug(f"min datetime: {datetime_min}")
        if "datetimemax" in query:
            datetime_max = query["datetimemax"]
            log.debug(f"max datetime: {datetime_max}")
        if not datetime_min or not datetime_max:
            log.debug(f"entering {not datetime_min or datetime_max}")
            raise BadRequest("Reftime is missing")

        # check the timedelta
        requested_days = (datetime_max - datetime_min).days
        if requested_days > MAX_REQ_DAYS:
            # check if the user is authenticated
            if user:
                if requested_days > MAX_REQ_DAYS_AUTHENTICATED:
                    raise Unauthorized(
                        f"maximum {MAX_REQ_DAYS_AUTHENTICATED} days can be requested"
                    )
            else:
                raise Unauthorized(f"maximum {MAX_REQ_DAYS} days can be requested")

        # get the db type
        db_type = dballe.get_db_type(date_min=datetime_min, date_max=datetime_max)
        if db_type != "dballe":
            if not user:
                raise Unauthorized("to access archived data the user has to be logged")
            else:
                # check for user authorization to access archived observed data
                is_allowed_obs_archive = SqlApiDbManager.get_user_permissions(
                    user, param="allowed_obs_archive"
                )
                if not is_allowed_obs_archive:
                    raise Unauthorized("user is not authorized to access archived data")

        if last and db_type == "mixed":
            # only the most recent data is needed. In case of mixed dbs for sure this data will be on dballe
            db_type = "dballe"
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
            query_and_dsn_list: Optional[List[Dict[str, Any]]] = []
            if query:
                query_and_dsn_list = dballe.get_queries_and_dsn_list_with_itertools(
                    query
                )
            else:
                # you need to iterate over query list to extract data, so add an empty element to the list
                query_and_dsn_list.append({"query": None, "aggregations_dsn": None})
            raw_res: Optional[Any] = None
            for query_and_dsn in query_and_dsn_list:
                q = query_and_dsn["query"]
                if q and query_station_data:
                    # add the params that can be multiple to the query for station details
                    if "timerange" in q:
                        query_station_data["timerange"] = q["timerange"]
                    if "level" in q:
                        query_station_data["level"] = q["level"]
                    if "product" in q and not allStationProducts:
                        query_station_data["product"] = q["product"]
                if db_type == "mixed":
                    raw_res = dballe.get_maps_response_for_mixed(
                        q,
                        onlyStations,
                        query_station_data=query_station_data,
                        dsn_subset=dsn_subset,
                        previous_res=raw_res,
                    )
                else:
                    raw_res = dballe.get_maps_response(
                        q,
                        onlyStations,
                        interval=interval,
                        db_type=db_type,
                        query_station_data=query_station_data,
                        dsn_subset=dsn_subset,
                        previous_res=raw_res,
                        aggregations_dsn=query_and_dsn["aggregations_dsn"],
                    )
        except AccessToDatasetDenied:
            raise ServerError("Access to dataset denied")
        except WrongDbConfiguration:
            raise ServerError(
                "no dballe DSN configured for the requested license group"
            )
        # parse the response
        res = dballe.parse_obs_maps_response(raw_res, last)

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
        q: str,
        output_format: str,
        user: Optional[User],
        networks: Optional[str] = None,
        lonmin: Optional[float] = None,
        latmin: Optional[float] = None,
        lonmax: Optional[float] = None,
        latmax: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        ident: Optional[str] = None,
        singleStation: bool = False,
        reliabilityCheck: bool = False,
    ) -> Response:
        alchemy_db = sqlalchemy.get_instance()
        query_data: Dict[str, Any] = {}
        if lonmin or latmin or lonmax or latmax:
            if not lonmin or not lonmax or not latmin or not latmax:
                raise BadRequest("Coordinates for bounding box are missing")
            else:
                # append bounding box params to the query
                query_data["lonmin"] = lonmin
                query_data["lonmax"] = lonmax
                query_data["latmin"] = latmin
                query_data["latmax"] = latmax

        parsed_query = dballe.from_query_to_dic(q)
        for key, value in parsed_query.items():
            query_data[key] = value

        networks_list = None
        if networks:
            networks_list = [x.strip() for x in networks.split(" or ")]
            for n in networks_list:
                # check user authorization for the requested network
                dataset_name = arki.from_network_to_dataset(n)
                if not dataset_name:
                    raise NotFound("The requested network does not exist")
                check_auth = SqlApiDbManager.check_dataset_authorization(
                    alchemy_db, dataset_name, user
                )
                if not check_auth:
                    raise Unauthorized(
                        "user is not authorized to access the selected network"
                    )

            query_data["network"] = networks_list

        if reliabilityCheck:
            query_data["query"] = "attrs"

        query_station_data: Dict[str, Any] = {}
        if singleStation:
            # check params for station
            if not networks:
                raise BadRequest("Parameter networks is missing")

            if not len(networks_list) == 1:
                raise BadRequest(
                    "You can set a maximum of 1 network in parameter 'networks' if singleStation is chosen"
                )

            if not ident:
                if not lat or not lon:
                    raise BadRequest("Parameters to get station details are missing")
                else:
                    query_station_data["lat"] = lat
                    query_station_data["lon"] = lon
            else:
                query_station_data["ident"] = ident

            query_station_data["network"] = networks_list[0]

            # get the license group
            station_dataset = arki.from_network_to_dataset(networks_list[0])

            l_group = SqlApiDbManager.get_license_group(alchemy_db, [station_dataset])
            query_data["license"] = l_group.name

            if reliabilityCheck:
                query_station_data["query"] = "attrs"

        # check consistency with license group
        if "license" not in query_data:
            raise BadRequest("License group parameter is mandatory")

        try:
            all_dsn = set()
            if networks_list:
                for d in networks_list:
                    group_license, dsn_subset = dballe.check_access_authorization(
                        user, query_data["license"], d
                    )
                    all_dsn.update(dsn_subset)
                dsn_subset = list(all_dsn)
            else:
                group_license, dsn_subset = dballe.check_access_authorization(
                    user, query_data["license"], None
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
        datetime_min = None
        datetime_max = None
        if "datetimemin" in query_data:
            datetime_min = query_data["datetimemin"]
        if "datetimemax" in query_data:
            datetime_max = query_data["datetimemax"]
        if not datetime_min or not datetime_max:
            raise BadRequest("Reftime is missing")

        # check the timedelta
        requested_days = (datetime_max - datetime_min).days
        if requested_days > MAX_REQ_DAYS:
            # check if the user is authenticated
            if user:
                if requested_days > MAX_REQ_DAYS_AUTHENTICATED:
                    raise Unauthorized(
                        f"maximum {MAX_REQ_DAYS_AUTHENTICATED} days can be requested"
                    )
            else:
                raise Unauthorized(f"maximum {MAX_REQ_DAYS} days can be requested")

        # get the db type
        db_type = dballe.get_db_type(date_min=datetime_min, date_max=datetime_max)
        if db_type != "dballe":
            if not user:
                raise Unauthorized("to access archived data the user has to be logged")
            else:
                # check for user authorization to access archived observed data
                is_allowed_obs_archive = SqlApiDbManager.get_user_permissions(
                    user, param="allowed_obs_archive"
                )
                if not is_allowed_obs_archive:
                    raise Unauthorized("user is not authorized to access archived data")
        log.debug("type of database: {}", db_type)
        try:
            queries_and_dsns: Optional[List[Dict[str, Any]]] = []
            download_queries: Optional[List[Dict[str, Any]]] = []

            if query_data:
                # if there are filters with multiple queries, we use the itertool to get multiple queries with single
                # filters. Basically, this is needed to get correct queries for dballe.
                queries_and_dsns = dballe.get_queries_and_dsn_list_with_itertools(
                    query_data
                )

            if db_type == "mixed":
                query_station_data_for_dballe = (
                    {**query_station_data} if query_station_data else {}
                )
                query_station_data_for_arki = (
                    {**query_station_data} if query_station_data else {}
                )
                query_data_for_arki = {**query_data} if query_data else {}

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

                # We will need the list of the dballe queries to get the list of the stations
                # in the arkimet extraction
                dballe_queries = []

                # get queries and db for dballe extraction
                for query_and_dsn in queries_and_dsns:
                    query_data_for_dballe = query_and_dsn["query"]
                    for key, value in dballe_reftime_in_query.items():
                        query_data_for_dballe[key] = value
                        if query_station_data_for_dballe:
                            query_station_data_for_dballe[key] = value

                    if query_station_data_for_dballe:
                        for key in ("level", "product", "timerange"):
                            if key in query_data_for_dballe:
                                query_station_data_for_dballe[
                                    key
                                ] = query_data_for_dballe[key]

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

                    dballe_queries.append(
                        dballe.parse_query_for_maps(dballe_query_data)
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

                    if query_station_data_for_arki and query_data_for_arki:
                        for key in ("level", "product", "timerange"):
                            if key in query_data_for_arki:
                                query_station_data_for_arki[key] = query_data_for_arki[
                                    key
                                ]

                    for q in dballe_queries:
                        # this is needed to get the list of stations and obtain a valid query_for_arkimet in the
                        # get_maps_response method
                        q["datetimemin"] = arki_reftime_in_query["datetimemin"]

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
                        all_dballe_queries=dballe_queries,
                    )

                    # merge the queries and the db
                    for q in dballe_queries:
                        (
                            db_for_extraction,
                            download_query_data,
                        ) = dballe.merge_db_for_download(
                            dballe_db,
                            q,
                            arki_db,
                            arki_query_data,
                            mobile_db=mobile_db,
                            dsn_subset=dsn_subset,
                        )

                    # if there is a temporary db we no more need the dsn subset list and the mobile db connection as we
                    # have already used them for fill the temp db
                    if arki_db:
                        dsn_subset = []
                        mobile_db = None

                    for qnd in queries_and_dsns:
                        download_query_data = {**qnd["query"]}
                        query_station_data_local = {**query_station_data}
                        if query_station_data_local:
                            for key in ("level", "product", "timerange"):
                                if key in download_query_data:
                                    query_station_data_local[key] = download_query_data[
                                        key
                                    ]
                            # if there is an arki query station data, merge the two reftimes
                            if arki_query_station_data:
                                if "datetimemin" in arki_query_station_data:
                                    query_station_data_local[
                                        "datetimemin"
                                    ] = arki_query_station_data["datetimemin"]
                        else:
                            if (
                                arki_reftime_in_query
                                and "datetimemin" in arki_reftime_in_query
                            ):
                                download_query_data[
                                    "datetimemin"
                                ] = query_data_for_arki["datetimemin"]
                            if (
                                dballe_reftime_in_query
                                and "datetimemax" in dballe_reftime_in_query
                            ):
                                download_query_data[
                                    "datetimemax"
                                ] = dballe_reftime_in_query["datetimemax"]

                        download_queries.append(
                            {
                                "download_query_data": download_query_data
                                if not query_station_data
                                else None,
                                "download_query_station_data": query_station_data_local
                                if query_station_data
                                else None,
                            }
                        )

            elif db_type == "arkimet":
                if query_station_data:
                    for key in (
                        "level",
                        "product",
                        "timerange",
                        "datetimemin",
                        "datetimemax",
                    ):
                        if key in query_data:
                            query_station_data[key] = query_data[key]
                    # TODO da controllare quando scarica il vento, se funziona o se ce'è da fare un itertoools?
                    # queries_and_dsns = dballe.get_queries_and_dsn_list_with_itertools(query_station_data)

                dballe_queries = []
                for qnd in queries_and_dsns:
                    db_query = dballe.parse_query_for_maps(qnd["query"])
                    dballe_queries.append(db_query)

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
                    all_dballe_queries=dballe_queries,
                )

                for qnd in queries_and_dsns:
                    download_query_data = {**qnd["query"]}
                    query_station_data_local = {**query_station_data}
                    if query_station_data_local:
                        for key in ("level", "product", "timerange"):
                            if key in download_query_data:
                                query_station_data_local[key] = download_query_data[key]

                    download_queries.append(
                        {
                            "download_query_data": download_query_data
                            if not query_station_data
                            else None,
                            "download_query_station_data": query_station_data_local
                            if query_station_data
                            else None,
                        }
                    )

            elif db_type == "dballe":
                for query_and_dsn in queries_and_dsns:
                    query_for_maps_response = {**query_and_dsn["query"]}
                    query_station_data_local = {**query_station_data}
                    if query_station_data_local:
                        for key in (
                            "level",
                            "product",
                            "timerange",
                            "datetimemin",
                            "datetimemax",
                        ):
                            if key in query_for_maps_response:
                                query_station_data_local[key] = query_for_maps_response[
                                    key
                                ]

                    # take advantage of the method already implemented to get data values for maps in order to get the query and the db to extract the data
                    (
                        db_for_extraction,
                        download_query_data,
                        download_query_station_data,
                        mobile_db,
                    ) = dballe.get_maps_response(
                        query_for_maps_response,
                        False,
                        db_type=db_type,
                        query_station_data=query_station_data_local,
                        download=True,
                        dsn_subset=dsn_subset,
                        aggregations_dsn=None
                        # aggregations_dsn=query_and_dsn["aggregations_dsn"]
                    )

                    download_queries.append(
                        {
                            "download_query_data": download_query_data
                            if not query_station_data
                            else None,
                            "download_query_station_data": download_query_station_data
                            if query_station_data
                            else None,
                        }
                    )

            mime = None
            if output_format == "JSON":
                mime = "application/json"
            else:
                mime = "application/octet-stream"

            # stream data
            if db_for_extraction:
                return FlaskResponse(
                    stream_with_context(
                        dballe.download_data_from_map(
                            db_for_extraction,
                            output_format,
                            download_queries,
                            qc_filter=reliabilityCheck,
                            mobile_db=mobile_db,
                            dsn_subset=dsn_subset,
                        )
                    ),
                    mimetype=mime,
                )
            else:
                return self.response([])
        except AccessToDatasetDenied:
            raise ServerError("Access to dataset denied")
