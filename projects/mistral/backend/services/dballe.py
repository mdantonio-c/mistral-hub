import itertools
import os
import subprocess
import tempfile
from datetime import datetime, time, timedelta
from functools import lru_cache

import arkimet as arki
import dateutil
import dballe
from mistral.services.arkimet import BeArkimet as arki_service
from restapi.utilities.logs import log

user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")


# DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,host=host, port=port))


class BeDballe:
    MAPS_NETWORK_FILTER = ["multim-forecast"]
    explorer = None
    LASTDAYS = os.environ.get(
        "LASTDAYS"
    )  # number of days after which data pass in Arkimet

    # path to json file where metadata of observed data in arkimet are stored
    ARKI_JSON_SUMMARY_PATH = "/arkimet/config/arkimet_summary.json"
    ARKI_JSON_SUMMARY_PATH_FILTERED = "/arkimet/config/arkimet_summary_filtered.json"
    DBALLE_JSON_SUMMARY_PATH = "/arkimet/config/dballe_summary.json"
    DBALLE_JSON_SUMMARY_PATH_FILTERED = "/arkimet/config/dballe_summary_filtered.json"

    @staticmethod
    def get_db_type(date_min, date_max):
        date_min_compar = datetime.utcnow() - date_min
        if date_min_compar.days > int(BeDballe.LASTDAYS):
            date_max_compar = datetime.utcnow() - date_max
            if date_max_compar.days > int(BeDballe.LASTDAYS):
                db_type = "arkimet"
            else:
                db_type = "mixed"
        else:
            db_type = "dballe"
        return db_type

    @staticmethod
    def split_reftimes(date_min, date_max):
        refmax_dballe = date_max
        refmin_dballe = datetime.utcnow() - timedelta(days=int(BeDballe.LASTDAYS))
        # refmax_arki_dt = refmin_dballe - timedelta(minutes=1)
        # refmax_arki = refmax_arki_dt.strftime("%Y-%m-%d %H:%M")
        # refmin_arki = date_min.strftime("%Y-%m-%d %H:%M")
        refmax_arki = refmin_dballe - timedelta(minutes=1)
        refmin_arki = date_min

        return refmax_dballe, refmin_dballe, refmax_arki, refmin_arki

    @staticmethod
    def build_arkimet_query(
        datemin=None,
        datemax=None,
        network=None,
        bounding_box=None,
        dballe_query=None,
        all_dballe_queries=None,
        fields=None,
    ):
        if isinstance(datemin, datetime):
            datemin_str = datemin.strftime("%Y-%m-%d %H:%M:%S")
            datemin = datemin_str

        if isinstance(datemax, datetime):
            datemax_str = datemax.strftime("%Y-%m-%d %H:%M:%S")
            datemax = datemax_str

        arkimet_query = ""
        if datemin:
            arkimet_query = "reftime: >={datemin},<={datemax};".format(
                datemin=datemin, datemax=datemax
            )
        if network:
            arkimet_query += "product: BUFR:t = {}".format(network[0])
            if len(network) > 1:
                for i in network[1:]:
                    arkimet_query += f" or  BUFR:t = {i}"
            arkimet_query += ";"

        if dballe_query or all_dballe_queries:
            # improve the query adding stations
            explorer = BeDballe.build_explorer("arkimet")
            # create a list of station details
            station_list = []
            # populate the station list.
            # If there is all_dballe_queries do an iteration to populate the list
            if dballe_query:
                for cur in explorer.query_summary_all(dballe_query):
                    el = {}
                    el["lat"] = cur["lat"]
                    el["lon"] = cur["lon"]
                    station_list.append(el)
            elif all_dballe_queries:
                for q in all_dballe_queries:
                    dballe_query = {}
                    for k, v in zip(fields, q):
                        dballe_query[k] = v
                    for cur in explorer.query_summary_all(dballe_query):
                        el = {}
                        el["lat"] = cur["lat"]
                        el["lon"] = cur["lon"]
                        station_list.append(el)
            if station_list:
                arkimet_query += "area: GRIB:lat={}, lon={}".format(
                    str(station_list[0]["lat"]).replace(".", ""),
                    str(station_list[0]["lon"]).replace(".", ""),
                )
                if len(station_list) > 1:
                    for e in station_list[1:]:
                        query_to_add = " or GRIB:lat={}, lon={}".format(
                            str(e["lat"]).replace(".", ""),
                            str(e["lon"]).replace(".", ""),
                        )
                        if query_to_add not in arkimet_query:
                            arkimet_query += query_to_add
            else:
                # if there is no station list it means there are no data for this query
                return None
        if bounding_box:
            if arkimet_query:
                if "area:" not in arkimet_query:
                    arkimet_query += "area: "
                else:
                    arkimet_query += " or "
            else:
                arkimet_query = "area: "
            arkimet_query += "bbox intersects POLYGON(({lonmin} {latmin},{lonmin} {latmax},{lonmax} {latmax}, {lonmax} {latmin}, {lonmin} {latmin}))".format(
                lonmin=bounding_box["lonmin"],
                latmin=bounding_box["latmin"],
                lonmax=bounding_box["lonmax"],
                latmax=bounding_box["latmax"],
            )
        return arkimet_query

    @staticmethod
    def build_explorer(db_type, network_list=None):
        need_filtered = True
        if network_list:
            match_nets = next(
                (net for net in network_list if net in BeDballe.MAPS_NETWORK_FILTER),
                None,
            )
            if match_nets:
                need_filtered = False
        # log.debug("filtered {}", need_filtered)
        explorer = dballe.DBExplorer()
        with explorer.update() as updater:
            if db_type == "dballe" or db_type == "mixed":
                if need_filtered:
                    json_summary_file = BeDballe.DBALLE_JSON_SUMMARY_PATH_FILTERED
                else:
                    json_summary_file = BeDballe.DBALLE_JSON_SUMMARY_PATH
                # log.debug("dballe summary file{}", json_summary_file)
                if os.path.exists(json_summary_file):
                    with open(json_summary_file) as fd:
                        updater.add_json(fd.read())
            if db_type == "arkimet" or db_type == "mixed":
                if need_filtered:
                    json_summary_file = BeDballe.ARKI_JSON_SUMMARY_PATH_FILTERED
                else:
                    json_summary_file = BeDballe.ARKI_JSON_SUMMARY_PATH
                if os.path.exists(json_summary_file):
                    with open(json_summary_file) as fd:
                        updater.add_json(fd.read())
        return explorer

    @staticmethod
    def get_summary(params, explorer, query=None):
        if params and "network" not in query:
            query["network"] = params
        fields, queries = BeDballe.from_query_to_lists(query)
        log.debug("Counting messages: fields: {}, queries: {}", fields, queries)

        # get all the possible combinations of queries to count the messages
        all_queries = list(itertools.product(*queries))
        message_count = 0
        min_date = None
        max_date = None
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            dballe_query["query"] = "details"
            explorer.set_filter(dballe_query)
            # count the items for each query
            log.debug("counting query: {}", dballe_query)
            for cur in explorer.query_summary(dballe_query):
                # count the items for each query
                message_count += cur["count"]

                datetimemin = datetime(
                    cur["yearmin"],
                    cur["monthmin"],
                    cur["daymin"],
                    cur["hourmin"],
                    cur["minumin"],
                    cur["secmin"],
                )
                datetimemax = datetime(
                    cur["yearmax"],
                    cur["monthmax"],
                    cur["daymax"],
                    cur["hourmax"],
                    cur["minumax"],
                    cur["secmax"],
                )
                # log.debug(datetimemax)
                # log.debug(datetimemin)
                # these notations still cause segfault
                # datetimemin = cur["datetimemin"]
                # datetimemin = cur["datetimemax"]
                if min_date:
                    if datetimemin < min_date:
                        min_date = datetimemin
                else:
                    min_date = datetimemin
                if max_date:
                    if datetimemax > max_date:
                        max_date = datetimemax
                else:
                    max_date = datetimemax
        # create the summary
        summary = {}
        summary["c"] = message_count
        if fields and "datetimemin" in fields:
            q_dtmin_index = fields.index("datetimemin")
            q_dtmin = queries[q_dtmin_index][0]
            if min_date > q_dtmin:
                summary["b"] = BeDballe.from_datetime_to_list(min_date)
            else:
                summary["b"] = BeDballe.from_datetime_to_list(q_dtmin)
        else:
            summary["b"] = BeDballe.from_datetime_to_list(min_date)

        if fields and "datetimemax" in fields:
            q_dtmax_index = fields.index("datetimemax")
            q_dtmax = queries[q_dtmax_index][0]
            if max_date < q_dtmax:
                summary["e"] = BeDballe.from_datetime_to_list(max_date)
            else:
                summary["e"] = BeDballe.from_datetime_to_list(q_dtmax)
        else:
            summary["e"] = BeDballe.from_datetime_to_list(max_date)

        return summary

    @staticmethod
    def load_filters(params, summary_stats, all_products, db_type, query_dic=None):
        query = {}
        if query_dic:
            query = {**query_dic}

        log.info("Loading filters dataset: {}, query: {}", params, query)

        # check if requested networks are in that dataset
        query_networks_list = []
        if params:
            if "network" in query:
                if not all(elem in params for elem in query["network"]):
                    return None, None
                else:
                    query_networks_list = query["network"]
            else:
                # if there aren't requested network, data will be filtered only by dataset
                query_networks_list = params
        else:
            if "network" in query:
                query_networks_list = query["network"]
        log.debug(f"Loading filters: query networks list : {query_networks_list}")

        bbox = {}
        bbox_keys = ["latmin", "lonmin", "latmax", "lonmax"]
        for key, value in query.items():
            if key in bbox_keys:
                bbox[key] = value

        # create and update the explorer object
        explorer = BeDballe.build_explorer(db_type, query_networks_list)

        # perform the queries in database to get the list of possible filters
        fields = {}
        network_products = []
        networks_list = []
        variables = []
        levels = []
        tranges = []
        filters_for_explorer = {}
        if bbox:
            for key, value in bbox.items():
                filters_for_explorer[key] = value
        if "datetimemin" in query:
            filters_for_explorer["datetimemin"] = query["datetimemin"]
            filters_for_explorer["datetimemax"] = query["datetimemax"]

        if not query_networks_list:
            # if there isn't a query network list, it's observed maps case (the data extraction is always managed using datasets)
            explorer.set_filter(filters_for_explorer)
            # list of the variables of the query without level and timerange costraints (used in "all available products" case)
            network_products = explorer.varcodes
            # add all values of the query to the filter for explorer (N.B. i can do that only beacuse i am in the maps case and i am sure that queries are all single param)
            if query:
                parsed_query = BeDballe.parse_query_for_maps(query)
                for key, value in parsed_query.items():
                    filters_for_explorer[key] = value
            explorer.set_filter(filters_for_explorer)

            ######### VARIABLES FIELDS
            # get the list of the variables coming from the query
            variables = explorer.varcodes

            ######### LEVELS FIELDS
            level_fields = explorer.levels
            if level_fields:
                for el in level_fields:
                    levels.append(BeDballe.from_level_object_to_string(el))
            ######### TIMERANGES FIELDS
            trange_fields = explorer.tranges
            if trange_fields:
                for el in trange_fields:
                    tranges.append(BeDballe.from_trange_object_to_string(el))
            ######### NETWORKS FIELDS
            networks_list = explorer.reports

        else:
            # get the fields network by network for the requested networks
            for n in query_networks_list:
                # filter the dballe database by network
                filters_for_explorer["report"] = n

                explorer.set_filter(filters_for_explorer)

                # list of the variables of this network
                net_variables = []

                ######### VARIABLES FIELDS
                # get the list of all the variables of the network
                varlist = explorer.varcodes
                # append all the products available for that network (not filtered by the query)
                if varlist:
                    network_products.extend(
                        x for x in varlist if x not in network_products
                    )

                #### PRODUCT is in the query filters
                if "product" in query:
                    # check if the requested variables are in the network
                    for e in query["product"]:
                        if e in varlist:
                            # if there is append it to the temporary list of matching variables
                            net_variables.append(e)
                    if not net_variables:
                        # if at the end of the cycle the temporary list of matching variables is still empty go to the next network
                        continue
                else:
                    # if product is not in the query filter append all the variable of the network o the final list of the fields
                    net_variables = varlist

                ######### LEVELS FIELDS
                level_fields, net_variables_temp = BeDballe.get_fields(
                    explorer, filters_for_explorer, net_variables, query, param="level"
                )
                if not level_fields:
                    continue
                # check if the temporary list of variable is not more little of the general one. If it is, replace the general list
                if not all(elem in net_variables_temp for elem in net_variables):
                    net_variables = net_variables_temp

                ######### TIMERANGES FIELDS
                (
                    trange_fields,
                    net_variables_temp,
                    level_fields_temp,
                ) = BeDballe.get_fields(
                    explorer,
                    filters_for_explorer,
                    net_variables,
                    query,
                    param="timerange",
                )
                if not trange_fields:
                    continue
                # check if the temporary list of variable is not more little of the general one. If it is, replace the general list
                if not all(elem in net_variables_temp for elem in net_variables):
                    net_variables = net_variables_temp

                # check if the temporary list of levels is not more little of the general one. If it is, replace the general list
                if not all(elem in level_fields_temp for elem in level_fields):
                    level_fields = level_fields_temp

                # append in the final list the timeranges retrieved
                tranges.extend(x for x in trange_fields if x not in tranges)

                # append in the final list the levels retrieved
                levels.extend(x for x in level_fields if x not in levels)

                # append all the network variables in the final field list
                variables.extend(x for x in net_variables if x not in variables)

                # if there are results, this network can be in the final fields
                networks_list.append(n)

        # if matching fields were found network list can't be empty
        if networks_list:
            # create the final dictionary
            fields["network"] = BeDballe.from_list_of_params_to_list_of_dic(
                networks_list, type="network"
            )
            fields["product"] = BeDballe.from_list_of_params_to_list_of_dic(
                variables, type="product"
            )
            fields["level"] = BeDballe.from_list_of_params_to_list_of_dic(
                levels, type="level"
            )
            fields["timerange"] = BeDballe.from_list_of_params_to_list_of_dic(
                tranges, type="timerange"
            )
            if all_products:
                fields[
                    "available_products"
                ] = BeDballe.from_list_of_params_to_list_of_dic(
                    network_products, type="product"
                )

            # create summary
            # if summary is required
            summary = {}
            if summary_stats:
                summary = BeDballe.get_summary(params, explorer, query)
            return fields, summary
        else:
            return None, None

    @staticmethod
    def get_fields(explorer, filters_for_explorer, variables, query, param):
        # filter the dballe database by list of variables (level and timerange depend on variable)
        filters_w_varlist = {**filters_for_explorer, "varlist": variables}
        explorer.set_filter(filters_w_varlist)

        level_list = []
        # get the list of all the fields for requested param according to the variables
        if param == "level":
            param_list = explorer.levels
        elif param == "timerange":
            param_list = explorer.tranges
            # if the param is timerange, 3 values packed are needed
            level_list = explorer.levels

        # parse the dballe object
        param_list_parsed = []
        for e in param_list:
            if e is not None:
                if param == "level":
                    p = BeDballe.from_level_object_to_string(e)
                elif param == "timerange":
                    p = BeDballe.from_trange_object_to_string(e)
                param_list_parsed.append(p)
        if level_list:
            level_list_parsed = []
            # parse the level list
            for lev in level_list:
                if lev is not None:
                    level = BeDballe.from_level_object_to_string(lev)
                    level_list_parsed.append(level)

        #### the param is in the query filters
        if param in query:
            temp_fields = []
            # check if the requested params matches the one required for the given variables
            for e in query[param]:
                if e in param_list_parsed:
                    # if there is append it to the temporary list of matching fields
                    temp_fields.append(e)
            if not temp_fields:
                # if at the end of the cycle the temporary list of matching variables is still empty go to the next network
                if param == "level":
                    return None, None
                elif param == "timerange":
                    return None, None, None
            else:
                # if only the param is in query and not product, discard from the network variable list all products not matching the param
                if "product" not in query:
                    variables_by_param = []
                    levels_by_trange = []
                    for qp in query[param]:
                        # for each variable i check if the param matches
                        for v in variables:
                            filters_w_var = {**filters_for_explorer, "var": v}
                            # discard from the query the query params i don't need
                            filters_w_var.pop("report", None)
                            explorer.set_filter(filters_w_var)

                            if param == "level":
                                param_list = explorer.levels
                            elif param == "timerange":
                                param_list = explorer.tranges
                            # parse the dballe object
                            param_list_parsed = []
                            for e in param_list:
                                if param == "level":
                                    p = BeDballe.from_level_object_to_string(e)
                                elif param == "timerange":
                                    p = BeDballe.from_trange_object_to_string(e)
                                param_list_parsed.append(p)
                            # if the param matches append the variable in a temporary list
                            if qp in param_list_parsed:
                                variables_by_param.append(v)
                    # the temporary list of variables matching the requested param become the list of the variable of the network
                    variables = variables_by_param
                    # if the list of variables has been modified, we are filtering by timeranges and level is not in
                    # query, i have to check if the level fields still matches the new variable list
                    if param == "timerange" and "level" not in query:
                        # for each variable check if the level matches
                        for level in level_list_parsed:
                            # discard from the query the query params i don't need
                            filters_w_varlist.pop("report", None)
                            explorer.set_filter(filters_w_varlist)

                            var_level = explorer.levels
                            var_level_parsed = []
                            # parse the dballe.Level object
                            for e in var_level:
                                lev = BeDballe.from_level_object_to_string(e)
                                var_level_parsed.append(lev)
                            # if the level matches append the level in a temporary list
                            if level in var_level_parsed:
                                levels_by_trange.append(level)
                        # the temporary list of levels matching the resulted variables become the list of levels to return
                        level_list_parsed = levels_by_trange
                if param == "level":
                    return temp_fields, variables
                elif param == "timerange":
                    return temp_fields, variables, level_list_parsed
        else:
            # if param is not in the query filter append return all the fields
            if param == "level":
                return param_list_parsed, variables
            elif param == "timerange":
                return param_list_parsed, variables, level_list_parsed

    @staticmethod
    def data_qc(attrs):
        attrs_dict = {v.code: v.get() for v in attrs}
        # Data already checked and checked as invalid by QC filter
        if attrs_dict.get("B33007", 100) == 0:
            return 0
        else:
            return 1

    @staticmethod
    @lru_cache(maxsize=128)
    def get_obs_data(
        cache_time,
        datetimemin=None,
        datetimemax=None,
        db_type=None,
        product=None,
        level=None,
        timerange=None,
        license=None,
        rep_memo=None,
        query=None,
        lonmin=None,
        lonmax=None,
        latmin=None,
        latmax=None,
    ):
        params = locals()
        query_data = {}
        for k, v in params.items():
            if v:
                # restore the list params
                if k == "product" or k == "level" or k == "timerange":
                    query_data[k] = [v]
                else:
                    query_data[k] = v
        return BeDballe.get_maps_response(query_data=query_data, db_type=db_type)

    @staticmethod
    def get_maps_response_for_mixed(
        query_data=None,
        only_stations=False,
        query_station_data=None,
    ):
        # get data from the dballe database
        log.debug("mixed dbs: get data from dballe")
        query_for_dballe = {}
        if query_station_data:
            query_for_dballe = {**query_station_data}
        elif query_data:
            query_for_dballe = {**query_data}

        refmin_arki = None
        if "datetimemin" in query_for_dballe:
            (
                refmax_dballe,
                refmin_dballe,
                refmax_arki,
                refmin_arki,
            ) = BeDballe.split_reftimes(
                query_for_dballe["datetimemin"], query_for_dballe["datetimemax"]
            )
            # set up query for dballe with the correct reftimes
            query_for_dballe["datetimemin"] = refmin_dballe
        else:
            # if there is no reftime i'll get the data of the last hour
            # TODO last hour or last day as default?
            # for production
            instant_now = datetime.now()
            # for local tests
            # today = date(2015, 12, 31)
            # time_now = datetime.now().time()
            # instant_now = datetime.combine(today, time_now)

            query_for_dballe["datetimemax"] = instant_now
            query_for_dballe["datetimemin"] = datetime.combine(
                instant_now, time(instant_now.hour, 0, 0)
            )

        if query_station_data:
            dballe_maps_data = BeDballe.get_maps_response(
                query_station_data=query_for_dballe,
                only_stations=only_stations,
                db_type="dballe",
            )
        else:
            dballe_maps_data = BeDballe.get_maps_response(
                query_data=query_for_dballe,
                only_stations=only_stations,
                db_type="dballe",
            )

        if query_for_dballe:
            if "datetimemin" not in query_for_dballe:
                return dballe_maps_data
            else:
                # get data from the arkimet database
                log.debug("mixed dbs: get data from arkimet")
                query_for_arki = {}
                if query_station_data:
                    query_for_arki = {**query_station_data}
                elif query_data:
                    query_for_arki = {**query_data}

                # set up query for arkimet with the correct reftimes
                if refmin_arki:
                    query_for_arki["datetimemin"] = refmin_arki
                    query_for_arki["datetimemax"] = refmax_arki

                if query_station_data:
                    arki_maps_data = BeDballe.get_maps_response(
                        query_station_data=query_for_arki,
                        only_stations=only_stations,
                        db_type="arkimet",
                        previous_res=dballe_maps_data,
                    )
                else:
                    arki_maps_data = BeDballe.get_maps_response(
                        query_data=query_for_arki,
                        only_stations=only_stations,
                        db_type="arkimet",
                        previous_res=dballe_maps_data,
                    )

                if not dballe_maps_data and not arki_maps_data:
                    response = []
                    return response

                if arki_maps_data:
                    return arki_maps_data

        return dballe_maps_data

    @staticmethod
    def get_maps_response(
        query_data=None,
        only_stations=False,
        db_type=None,
        query_station_data=None,
        download=None,
        previous_res=None,
    ):
        DB = dballe.DB.connect(f"{engine}://{user}:{pw}@{host}:{port}/DBALLE")

        # TODO va fatto un check licenze compatibili qui all'inizio (by dataset)? oppure a seconda della licenza lo si manda su un dballe o un altro?

        if previous_res:
            # integrate the already existent response
            response = previous_res
        else:
            response = {}
        # choose the right query for the right situation(station details response or default one)
        query = {}
        if query_station_data:
            parsed_query = BeDballe.parse_query_for_maps(query_station_data)
        elif query_data:
            parsed_query = BeDballe.parse_query_for_maps(query_data)

        query = {**parsed_query}

        # managing db_type
        if db_type == "arkimet":
            # manage bounding box for queries by station id
            bbox_for_arki = {}
            if query_data and "latmin" in query_data:
                bbox_for_arki["latmin"] = query_data["latmin"]
                bbox_for_arki["lonmin"] = query_data["lonmin"]
                bbox_for_arki["latmax"] = query_data["latmax"]
                bbox_for_arki["lonmax"] = query_data["lonmax"]
            # manage reftime for queries in arkimet
            datemin = None
            datemax = None
            if query_data:
                datemin = query_data["datetimemin"]
                datemax = query_data["datetimemax"]
            # for now we consider network as a single parameters.
            # TODO choose if the network will be a single or multiple param
            # transform network param in a list to be managed better for arkimet queries
            networks_as_list = None
            if query_data and "rep_memo" in query_data:
                networks_as_list = [query_data["rep_memo"]]
            query_for_arkimet = BeDballe.build_arkimet_query(
                datemin=datemin,
                datemax=datemax,
                network=networks_as_list,
                bounding_box=bbox_for_arki,
                dballe_query=query,
            )
            if query and not query_for_arkimet:
                # means that there aren't data in arkimet for this dballe query
                if download:
                    return None, {}, {}
                return []
            # check if there is a queried license
            license = None
            if query_data:
                if "license" in query_data.keys():
                    license = query_data["license"]
            # get the correct arkimet dataset
            datasets = arki_service.get_obs_datasets(query_for_arkimet, license)

            if not datasets:
                if download:
                    return None, {}, {}
                return []

            # check datasets license,
            # TODO se non passa il check il frontend lancerà un messaggio del tipo: 'dati con licenze diverse, prego sceglierne una'
            # check_license = arki_service.get_unique_license(
            #     datasets
            # )  # the exception raised by this function is enough?
            log.debug("datasets: {}", datasets)

        # managing different dbs
        if db_type == "arkimet":
            memdb = BeDballe.fill_db_from_arkimet(datasets, query_for_arkimet)

        if db_type == "arkimet":
            db = memdb
        else:
            db = DB

        # if download param, return the db and the query to download the data
        if download:
            return db, query_data, query_station_data

        log.debug("start retrieving data: query data for maps {}", query)
        with db.transaction() as tr:
            # check if query gives back a result
            count_data = tr.query_data(query).remaining
            # log.debug('count {}',count_data)
            if count_data == 0:
                return []
            # check if an extended response is requested:
            extend_res = False
            if query:
                if "level" and "trange" not in query:
                    extend_res = True

            for rec in tr.query_data(query):
                # discard data from excluded networks
                if rec["rep_memo"] in BeDballe.MAPS_NETWORK_FILTER:
                    if "rep_memo" not in query:
                        continue
                    else:
                        if rec["rep_memo"] not in query["rep_memo"]:
                            continue
                query_for_details = {}
                if rec["ident"]:
                    station_tuple = (rec["ident"], rec["rep_memo"])
                    query_for_details["ident"] = rec["ident"]
                else:
                    station_tuple = (
                        float(rec["lat"]),
                        float(rec["lon"]),
                        rec["rep_memo"],
                    )
                    query_for_details["lat"] = float(rec["lat"])
                    query_for_details["lon"] = float(rec["lon"])
                query_for_details["rep_memo"] = rec["rep_memo"]

                if station_tuple not in response.keys():
                    response[station_tuple] = {}
                    details = []
                    if not query_station_data:
                        # append the variable of station name to the query for details
                        query_for_details["var"] = "B01019"
                    # add station details
                    for el in tr.query_station_data(query_for_details):
                        detail_el = {}
                        var = el["variable"]
                        code = var.code
                        detail_el["var"] = code
                        detail_el["val"] = var.get()
                        details.append(detail_el)

                    response[station_tuple]["details"] = details

                # get data values
                if not only_stations:
                    if (
                        not query_station_data
                        and not extend_res
                        and not rec["var"] in response[station_tuple].keys()
                    ):
                        response[station_tuple][rec["var"]] = []
                    product_val = {}
                    product_val["val"] = rec[rec["var"]].get()
                    reftime = datetime(
                        rec["year"],
                        rec["month"],
                        rec["day"],
                        rec["hour"],
                        rec["min"],
                        rec["sec"],
                    )
                    product_val["ref"] = reftime.isoformat()

                    if query:
                        if "query" in query:
                            # add reliable flag
                            variable = rec["variable"]
                            attrs = variable.get_attrs()
                            is_reliable = BeDballe.data_qc(attrs)
                            product_val["rel"] = is_reliable

                    if query_station_data or extend_res:
                        level = BeDballe.from_level_object_to_string(rec["level"])
                        timerange = BeDballe.from_trange_object_to_string(rec["trange"])
                        product_tuple = (rec["var"], level, timerange)
                        if product_tuple not in response[station_tuple].keys():
                            response[station_tuple][product_tuple] = []
                        response[station_tuple][product_tuple].append(product_val)
                    else:
                        # append the value
                        response[station_tuple][rec["var"]].append(product_val)

        return response

    @staticmethod
    def parse_obs_maps_response(raw_res):
        log.debug("start parsing response for maps")
        response = {}
        response_data = []
        descriptions_dic = {}
        if raw_res:
            product_varcodes = []
            station_varcodes = []
            levels = []
            timeranges = []
            for key, value in raw_res.items():
                res_el = {}
                station_el = {}
                products_list = []
                if len(key) == 2:
                    station_el["ident"] = key[0]
                    station_el["net"] = key[1]
                else:
                    station_el["lat"] = key[0]
                    station_el["lon"] = key[1]
                    station_el["net"] = key[2]
                for prod_key, prod_value in value.items():
                    if prod_key != "details":
                        product_el = {}
                        if type(prod_key) != tuple:
                            product_el["var"] = prod_key
                            product_el["val"] = prod_value
                            if prod_key not in product_varcodes:
                                product_varcodes.append(prod_key)
                        else:
                            product_el["var"] = prod_key[0]
                            product_el["lev"] = prod_key[1]
                            product_el["trange"] = prod_key[2]
                            product_el["val"] = prod_value
                            if product_el["var"] not in product_varcodes:
                                product_varcodes.append(product_el["var"])
                            if product_el["lev"] not in levels:
                                levels.append(product_el["lev"])
                            if product_el["trange"] not in timeranges:
                                timeranges.append(product_el["trange"])
                        products_list.append(product_el)
                    else:
                        station_el["details"] = prod_value
                        for i in prod_value:
                            if i["var"] not in station_varcodes:
                                station_varcodes.append(i["var"])
                res_el["stat"] = station_el
                res_el["prod"] = products_list
                response_data.append(res_el)

            for el in product_varcodes:
                descr_el = {}
                var_info = dballe.varinfo(el)
                descr_el["descr"] = var_info.desc
                descr_el["unit"] = var_info.unit
                descriptions_dic[el] = descr_el
            for el in station_varcodes:
                descr_el = {}
                var_info = dballe.varinfo(el)
                descr_el["descr"] = var_info.desc
                descriptions_dic[el] = descr_el
            for el in levels:
                descr_el = {}
                descr_el["descr"] = BeDballe.get_description(el, "level")
                descriptions_dic[el] = descr_el
            for el in timeranges:
                descr_el = {}
                descr_el["descr"] = BeDballe.get_description(el, "timerange")
                descriptions_dic[el] = descr_el
        response["descr"] = descriptions_dic
        response["data"] = response_data

        return response

    @staticmethod
    def merge_db_for_download(
        dballe_db,
        dballe_query_data,
        arki_db=None,
        arki_query_data=None,
    ):
        # merge the dbs
        query_data = BeDballe.parse_query_for_maps(dballe_query_data)
        if arki_db:
            log.debug("Filling temp db with data from dballe. query: {}", query_data)
            with dballe_db.transaction() as tr:
                with arki_db.transaction() as temptr:
                    for cur in tr.query_messages(query_data):
                        temptr.import_messages(cur.message)
        # merge the queries for data
        if arki_query_data:
            if "datetimemin" in arki_query_data:
                query_data["datetimemin"] = arki_query_data["datetimemin"]
        # return the arki_db (the temp one) filled also with data from dballe
        if arki_db:
            return arki_db, query_data
        else:
            return dballe_db, query_data

    @staticmethod
    def download_data_from_map(db, output_format, query_data, query_station_data=None):
        download_query = {}
        if query_station_data:
            parsed_query = BeDballe.parse_query_for_maps(query_station_data)
        elif query_data:
            parsed_query = BeDballe.parse_query_for_maps(query_data)
        download_query = {**parsed_query}

        with db.transaction() as tr:
            exporter = dballe.Exporter(output_format)
            log.debug("download query: {}", download_query)
            for row in tr.query_messages(download_query):
                yield exporter.to_binary(row.message)

    @staticmethod
    def from_query_to_dic(q):
        # example of query string: string= "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;level:1,0,0,0 or 103,2000,0,0;product:B11001 or B13011;timerange:0,0,3600 or 1,0,900;network:fidupo or agrmet"
        params_list = ["reftime", "network", "product", "level", "timerange", "license"]
        query_list = q.split(";")
        query_dic = {}
        for e in query_list:
            for p in params_list:
                if e.startswith(p):
                    val = e.split(p + ":")[1]
                    # ex. from 'level:1,0,0,0 or 103,2000,0,0' to '1,0,0,0 or 103,2000,0,0'

                    # reftime param has to be parsed differently
                    if p == "reftime":
                        reftimes = [x.strip() for x in val.split(",")]
                        # ex. from ' >=2020-02-01 01:00,<=2020-02-04 15:13' to ['>=2020-02-01 01:00', '<=2020-02-04 15:13']
                        for r in reftimes:
                            if r.startswith(">"):
                                date_min = r.strip(">=")
                                query_dic["datetimemin"] = dateutil.parser.parse(
                                    date_min
                                )
                            if r.startswith("<"):
                                date_max = r.strip("<=")
                                query_dic["datetimemax"] = dateutil.parser.parse(
                                    date_max
                                )
                            if r.startswith("="):
                                date = r.strip("=")
                                query_dic["datetimemin"] = query_dic[
                                    "datetimemax"
                                ] = dateutil.parser.parse(date)

                    # parsing all other parameters
                    else:
                        val_list = [x.strip() for x in val.split(" or ")]
                        query_dic[p] = val_list
        return query_dic

    @staticmethod
    def from_level_object_to_string(level):
        level_list = []

        if level.ltype1:
            ltype1 = str(level.ltype1)
        else:
            ltype1 = "0"
        level_list.append(ltype1)

        if level.l1:
            l1 = str(level.l1)
        else:
            l1 = "0"
        level_list.append(l1)

        if level.ltype2:
            ltype2 = str(level.ltype2)
        else:
            ltype2 = "0"
        level_list.append(ltype2)

        if level.l2:
            l2 = str(level.l2)
        else:
            l2 = "0"
        level_list.append(l2)

        level_parsed = ",".join(level_list)
        return level_parsed

    @staticmethod
    def from_trange_object_to_string(trange):
        trange_list = []

        pind = str(trange.pind)
        trange_list.append(pind)

        p1 = str(trange.p1)
        trange_list.append(p1)

        p2 = str(trange.p2)
        trange_list.append(p2)

        trange_parsed = ",".join(trange_list)
        return trange_parsed

    @staticmethod
    def from_list_of_params_to_list_of_dic(param_list, type):
        list_dic = []
        for p in param_list:
            item = {}
            item["code"] = p
            item["desc"] = BeDballe.get_description(p, type)
            list_dic.append(item)
        return list_dic

    @staticmethod
    def get_description(value, type):
        if type == "network":
            description = value
        elif type == "product":
            var_code = value
            var_infos = dballe.varinfo(var_code)
            description = var_infos.desc
        elif type == "timerange" or type == "level":
            list = []
            for v in value.split(","):
                if type == "level" and v == "0":
                    val = None
                    list.append(val)
                else:
                    list.append(int(v))
            if type == "timerange":
                tr = dballe.Trange(list[0], list[1], list[2])
                description = tr.describe()
            else:
                lev = dballe.Level(list[0], list[1], list[2], list[3])
                description = lev.describe()

        return description

    @staticmethod
    def parse_query_for_maps(query):
        query_data = {}
        # TODO: now query does not support multiple values for a single param
        # adapt the query to the dballe syntax and add the params to the general query
        to_parse = [
            "level",
            "network",
            "product",
            "timerange",
            "datetimemin",
            "datetimemax",
        ]
        dballe_keys = [
            "level",
            "rep_memo",
            "var",
            "trange",
            "datetimemin",
            "datetimemax",
        ]
        allowed_keys = [
            "lonmin",
            "lonmax",
            "latmin",
            "latmax",
            "query",
            "lat",
            "lon",
            "ident",
            "rep_memo",
        ]

        for key, value in query.items():
            if key in to_parse:
                key_index = to_parse.index(key)
                if (
                    key == "timerange"
                    or key == "level"
                    and not isinstance(value, tuple)
                ):
                    tuple_list = []
                    for v in value[0].split(","):
                        if key == "level" and v == "0":
                            val = None
                            tuple_list.append(val)
                        else:
                            tuple_list.append(int(v))
                    query_data[dballe_keys[key_index]] = tuple(tuple_list)
                else:
                    if not isinstance(value, list):
                        query_data[dballe_keys[key_index]] = value
                    else:
                        query_data[dballe_keys[key_index]] = value[0]
            elif key in allowed_keys or key in dballe_keys:
                query_data[key] = value
        return query_data

    @staticmethod
    def from_filters_to_lists(filters):
        fields = []
        queries = []
        allowed_keys = ["level", "network", "product", "timerange"]
        dballe_keys = ["level", "rep_memo", "var", "trange"]

        for key, value in filters.items():
            if key in allowed_keys:
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])

                field_queries = []
                for e in value:
                    if key == "timerange" or key == "level":
                        # transform the timerange or level value in a tuple (required for dballe query)
                        tuple_list = []
                        for v in e["code"].split(","):
                            if key == "level" and v == "0":
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(v))
                        field_queries.append(tuple(tuple_list))
                    else:
                        field_queries.append(e["code"])
                queries.append(field_queries)
            else:
                continue

        return fields, queries

    @staticmethod
    def from_query_to_lists(query):
        fields = []
        queries = []
        allowed_keys = [
            "level",
            "network",
            "product",
            "timerange",
            "datetimemin",
            "datetimemax",
            "ana_id",
            "latmin",
            "lonmin",
            "latmax",
            "lonmax",
        ]
        dballe_keys = [
            "level",
            "rep_memo",
            "var",
            "trange",
            "datetimemin",
            "datetimemax",
            "ana_id",
            "latmin",
            "lonmin",
            "latmax",
            "lonmax",
        ]

        for key, value in query.items():
            if key in allowed_keys:
                # log.debug('{}: {}',key,value)
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])
                if key == "timerange" or key == "level":
                    # transform the timerange or level value in a tuple (required for dballe query)
                    query_list = []
                    for v in value:
                        split_list = v.split(",")
                        tuple_list = []
                        for s in split_list:
                            if key == "level" and s == "0":
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(s))
                        query_list.append(tuple(tuple_list))
                    queries.append(query_list)
                elif key == "datetimemin" or key == "datetimemax":
                    query_list = []
                    query_list.append(value)
                    queries.append(query_list)
                else:
                    if isinstance(value, list):
                        queries.append(value)
                    else:
                        queries.append([value])
            else:
                continue
        return fields, queries

    @staticmethod
    def parse_data_extraction_reftime(from_str, to_str):
        from_dt = dateutil.parser.parse(from_str)
        to_dt = dateutil.parser.parse(to_str)

        # to prevent problems with timezones
        from_naive = from_dt.replace(tzinfo=None)
        to_naive = to_dt.replace(tzinfo=None)

        return from_naive, to_naive

    @staticmethod
    def from_datetime_to_list(dt):
        str = dt.strftime("%Y,%m,%d,%H,%M,%S")
        str_list = str.split(",")
        list = []
        for s in str_list:
            list.append(int(s))
        return list

    @staticmethod
    def fill_db_from_arkimet(datasets, query):
        log.debug("filling dballe with data from arkimet")
        db = dballe.DB.connect("mem:")
        cfg = arki.cfg.Sections.parse(arki_service.arkimet_conf)
        importer = dballe.Importer("BUFR")
        with tempfile.SpooledTemporaryFile(mode="a+b", max_size=10000000) as tmpf:
            for d in datasets:
                dt_part = cfg.section(d)
                source = arki.dataset.Reader(dt_part)
                bin_data = source.query_bytes(query, with_data=True)
                tmpf.write(bin_data)
            tmpf.seek(0)
            with dballe.File(tmpf, "BUFR") as f:
                for binmsg in f:
                    msgs = importer.from_binary(binmsg)
                    with db.transaction() as tr:
                        tr.import_messages(msgs)
        return db

    @staticmethod
    def parse_query_for_data_extraction(datasets, filters=None, reftime=None):
        # get network list from requested datasets
        dataset_nets = []
        for ds in datasets:
            nets = arki_service.get_observed_dataset_params(ds)
            for n in nets:
                dataset_nets.append(n)

        fields = []
        queries = []
        # create a "base" query using the filters
        if filters:
            fields, queries = BeDballe.from_filters_to_lists(filters)
            # check if requested networks are in that dataset
            if "rep_memo" in fields:
                key_index = fields.index("rep_memo")
                nets_in_query = queries[key_index]
                if not all(elem in dataset_nets for elem in nets_in_query):
                    raise Exception(
                        "Failure in data extraction: Invalid set of filters"
                    )

        # parsing reftime and add it to the query
        if reftime:
            date_min, date_max = BeDballe.parse_data_extraction_reftime(
                reftime["from"], reftime["to"]
            )
            fields.append("datetimemin")
            queries.append([date_min])
            fields.append("datetimemax")
            queries.append([date_max])

        # if there aren't filters, data are filtered only by dataset's networks
        if "rep_memo" not in fields:
            fields.append("rep_memo")
            queries.append(dataset_nets)

        return fields, queries

    @staticmethod
    def extract_data_for_mixed(datasets, fields, queries, outfile):
        # extract data from the dballe database
        log.debug("mixed dbs: extract data from dballe")
        dballe_queries = []
        for q in queries:
            dballe_queries.append(q)
        if "datetimemin" in fields:
            (
                refmax_dballe,
                refmin_dballe,
                refmax_arki,
                refmin_arki,
            ) = BeDballe.split_reftimes(
                queries[fields.index("datetimemin")][0],
                queries[fields.index("datetimemax")][0],
            )
            # set up query for dballe with the correct reftimes
            dballe_queries[fields.index("datetimemin")][0] = refmin_dballe

        # set the filename for the partial extraction
        if outfile.endswith(".tmp"):
            outfile_split = outfile[:-4]
            filebase, fileext = os.path.splitext(outfile_split)
        else:
            filebase, fileext = os.path.splitext(outfile)

        dballe_outfile = filebase + "_dballe_part" + fileext + ".tmp"

        # extract
        BeDballe.extract_data(
            datasets, fields, dballe_queries, dballe_outfile, db_type="dballe"
        )

        # extract data from the arkimet database
        log.debug("mixed dbs: extract data from arkimet")
        arki_queries = []
        for q in queries:
            arki_queries.append(q)
        if "datetimemin" in fields:
            # set up query for arkimet with the correct reftimes
            arki_queries[fields.index("datetimemin")][0] = refmin_arki
            arki_queries[fields.index("datetimemax")][0] = refmax_arki

        arki_outfile = filebase + "_arki_part" + fileext + ".tmp"

        # extract
        BeDballe.extract_data(
            datasets, fields, arki_queries, arki_outfile, db_type="arkimet"
        )

        cat_cmd = ["cat"]
        if os.path.exists(dballe_outfile):
            cat_cmd.append(dballe_outfile)
        if os.path.exists(arki_outfile):
            cat_cmd.append(arki_outfile)

        # check if the extractions were done
        if len(cat_cmd) == 1:
            # any extraction file exists
            raise Exception("Failure in data extraction")

        # join the dballe extraction with the arki one
        with open(outfile, mode="w") as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise Exception("Failure in data extraction")

    @staticmethod
    def extract_data(datasets, fields, queries, outfile, db_type):
        # choose the db
        arkimet_query = None
        if db_type == "arkimet":
            # create arkimet query
            network = None
            if "rep_memo" in fields:
                network = queries[fields.index("rep_memo")]

            datemin = None
            datemax = None
            if "datetimemin" in fields:
                datemin = queries[fields.index("datetimemin")][0].strftime(
                    "%Y-%m-%d %H:%M"
                )
                datemax = queries[fields.index("datetimemax")][0].strftime(
                    "%Y-%m-%d %H:%M"
                )

            # get all the possible combinations of queries
            all_queries = list(itertools.product(*queries))
            arkimet_query = BeDballe.build_arkimet_query(
                datemin=datemin,
                datemax=datemax,
                network=network,
                all_dballe_queries=all_queries,
                fields=fields,
            )

        if arkimet_query:
            # fill the temp db and choose it as the db for extraction
            DB = BeDballe.fill_db_from_arkimet(datasets, arkimet_query)
        else:
            DB = dballe.DB.connect(
                "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                    engine=engine, user=user, pw=pw, host=host, port=port
                )
            )

        # get all the possible combinations of queries
        all_queries = list(itertools.product(*queries))
        counter = 1
        cat_cmd = ["cat"]
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            # set the filename for the partial extraction
            if outfile.endswith(".tmp"):
                outfile_split = outfile[:-4]
                filebase, fileext = os.path.splitext(outfile_split)
            else:
                filebase, fileext = os.path.splitext(outfile)
            part_outfile = filebase + "_part" + str(counter) + fileext + ".tmp"

            with DB.transaction() as tr:
                # check if the query gives a result
                count = tr.query_data(dballe_query).remaining
                # log.debug('counter= {} dballe query: {} count:{}'.format(str(counter), dballe_query, count))
                if count == 0:
                    continue
                log.debug("Extract data from dballe. query: {}", dballe_query)
                exporter = dballe.Exporter("BUFR")
                with open(part_outfile, "wb") as out:
                    for row in tr.query_messages(dballe_query):
                        out.write(exporter.to_binary(row.message))

            cat_cmd.append(part_outfile)
            # update counter
            counter += 1

        if db_type == "arkimet":
            # clear the temporary db
            DB.remove_all()

        if counter == 1:
            # any query has given a result
            raise Exception(
                "Failure in data extraction: the query does not give any result"
            )

        # join all the partial extractions
        with open(outfile, mode="w") as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise Exception("Failure in data extraction")
