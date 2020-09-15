import itertools
import os
import subprocess
import tempfile
from datetime import datetime, time, timedelta
from decimal import Decimal

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
    explorer = None
    LASTDAYS = os.environ.get(
        "LASTDAYS"
    )  # number of days after which data pass in Arkimet

    # path to json file where metadata of observed data in arkimet are stored
    JSON_SUMMARY_PATH = "/arkimet/config/arkimet_summary.json"

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
            # create a list of station datails
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
                arkimet_query += "area:GRIB:lat={}, lon={}".format(
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
            if "area: " not in arkimet_query:
                arkimet_query += "area: "
            else:
                arkimet_query += " or "

            arkimet_query += "bbox intersects POLYGON(({lonmin} {latmin},{lonmin} {latmax},{lonmax} {latmax}, {lonmax} {latmin}, {lonmin} {latmin}))".format(
                lonmin=bounding_box["lonmin"],
                latmin=bounding_box["latmin"],
                lonmax=bounding_box["lonmax"],
                latmax=bounding_box["latmax"],
            )
        return arkimet_query

    @staticmethod
    def build_explorer(db_type):

        DB = dballe.DB.connect(
            "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                engine=engine, user=user, pw=pw, host=host, port=port
            )
        )

        explorer = dballe.DBExplorer()
        with explorer.update() as updater:
            if db_type == "dballe" or db_type == "mixed":
                with DB.transaction() as tr:
                    updater.add_db(tr)
            if db_type == "arkimet" or db_type == "mixed":
                if os.path.exists(BeDballe.JSON_SUMMARY_PATH):
                    with open(BeDballe.JSON_SUMMARY_PATH) as fd:
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
            # count the items for each query

            for cur in explorer.query_summary(dballe_query):
                # commented out since causes segfault
                # count the items for each query
                # message_count += cur["count"]

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

            # bug fixing while the correct one raises the segfault
            message_count += explorer.query_summary(dballe_query).remaining
            # log.debug(
            #     "query: {}, count: {},min date: {}, max date: {}",
            #     dballe_query,
            #     explorer.query_summary(dballe_query).remaining,
            #     min_date,
            #     max_date,
            # )
        # log.debug("min date: {}, max date: {}",min_date,max_date)
        # create the summary
        summary = {}
        summary["c"] = message_count
        if "datetimemin" in fields:
            dtmin_index = fields.index("datetimemin")
            dtmin_for_summary = queries[dtmin_index][0]
        else:
            dtmin_for_summary = min_date
        summary["b"] = [
            dtmin_for_summary.year,
            dtmin_for_summary.month,
            dtmin_for_summary.day,
            dtmin_for_summary.hour,
            dtmin_for_summary.minute,
            dtmin_for_summary.second,
        ]
        if "datetimemax" in fields:
            dtmax_index = fields.index("datetimemax")
            dtmax_for_summary = queries[dtmax_index][0]
        else:
            dtmax_for_summary = max_date
        summary["e"] = [
            dtmax_for_summary.year,
            dtmax_for_summary.month,
            dtmax_for_summary.day,
            dtmax_for_summary.hour,
            dtmax_for_summary.minute,
            dtmax_for_summary.second,
        ]

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
        explorer = BeDballe.build_explorer(db_type)

        # perform the queries in database to get the list of possible filters
        fields = {}
        network_products = []
        networks_list = []
        variables = []
        levels = []
        tranges = []
        if not query_networks_list:
            query_networks_list = explorer.all_reports
            log.debug("all networks: {}", query_networks_list)
        for n in query_networks_list:
            # filter the dballe database by network
            filters_for_explorer = {"report": n}
            if bbox:
                for key, value in bbox.items():
                    filters_for_explorer[key] = value
            if "datetimemin" in query:
                filters_for_explorer["datetimemin"] = query["datetimemin"]
                filters_for_explorer["datetimemax"] = query["datetimemax"]

            explorer.set_filter(filters_for_explorer)

            # list of the variables of this network
            net_variables = []

            ######### VARIABLES FIELDS
            # get the list of all the variables of the network
            varlist = explorer.varcodes
            # append all the products available for that network (not filtered by the query)
            if varlist:
                network_products.extend(x for x in varlist if x not in network_products)

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
            trange_fields, net_variables_temp, level_fields_temp = BeDballe.get_fields(
                explorer, filters_for_explorer, net_variables, query, param="timerange"
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
                            for v in variables:
                                filters_w_var = {**filters_for_explorer, "var": v}
                                # discard from the query the query params i don't need
                                filters_w_var.pop("report", None)
                                explorer.set_filter(filters_w_var)

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
            return False
        else:
            return True

    @staticmethod
    def get_maps_response_for_mixed(
        query_data=None, only_stations=False, query_station_data=None,
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
                    )
                else:
                    arki_maps_data = BeDballe.get_maps_response(
                        query_data=query_for_arki,
                        only_stations=only_stations,
                        db_type="arkimet",
                    )

                if not dballe_maps_data and not arki_maps_data:
                    response = []
                    return response

                if arki_maps_data:
                    if not query_station_data:
                        for i in arki_maps_data:
                            if dballe_maps_data:
                                # if any(d['station']['id'] == i['station']['id'] for d in dballe_maps_data):
                                if any(
                                    d["station"]["lat"] == i["station"]["lat"]
                                    and d["station"]["lon"] == i["station"]["lon"]
                                    and d["station"]["network"]
                                    == i["station"]["network"]
                                    for d in dballe_maps_data
                                ):
                                    # get the element index
                                    for e in dballe_maps_data:
                                        if (
                                            e["station"]["lat"] == i["station"]["lat"]
                                            and e["station"]["lon"]
                                            == i["station"]["lon"]
                                            and e["station"]["network"]
                                            == i["station"]["network"]
                                        ):
                                            el_index = dballe_maps_data.index(e)
                                            break
                                    # append values to the variable
                                    if not only_stations:
                                        for e in i["products"]:
                                            varcode = e["varcode"]
                                            existent_product = False
                                            for el in dballe_maps_data[el_index][
                                                "products"
                                            ]:
                                                if el["varcode"] == varcode:
                                                    existent_product = True
                                                    for v in e["values"]:
                                                        el["values"].append(v)
                                            if not existent_product:
                                                dballe_maps_data[el_index][
                                                    "products"
                                                ].append(e)
                                else:
                                    dballe_maps_data.append(i)
                            else:
                                dballe_maps_data.append(i)
                    else:
                        # only one station in the response: add arkimet values to dballe response
                        if dballe_maps_data:
                            for e in arki_maps_data["products"]:
                                varcode = e["varcode"]
                                existent_product = False
                                for el in dballe_maps_data["products"]:
                                    if el["varcode"] == varcode:
                                        existent_product = True
                                        for v in e["values"]:
                                            el["values"].append(v)
                                if not existent_product:
                                    dballe_maps_data["products"].append(e)
                        else:
                            dballe_maps_data = arki_maps_data

        return dballe_maps_data

    @staticmethod
    def get_maps_response(
        query_data=None,
        only_stations=False,
        db_type=None,
        query_station_data=None,
        download=None,
    ):
        DB = dballe.DB.connect(f"{engine}://{user}:{pw}@{host}:{port}/DBALLE")

        # TODO va fatto un check licenze compatibili qui all'inizio (by dataset)? oppure a seconda della licenza lo si manda su un dballe o un altro?

        response = []
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
                return response
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
                return response

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

        log.debug("query data for maps {}", query)
        with db.transaction() as tr:
            # check if query gives back a result
            count_data = tr.query_data(query).remaining
            # log.debug('count {}',count_data)
            if count_data == 0:
                return response
            for rec in tr.query_data(query):
                res_element = {}
                # get data about the station
                station_data = {}
                query_for_details = {}
                station_data["lat"] = float(rec["lat"])
                query_for_details["lat"] = float(rec["lat"])
                station_data["lon"] = float(rec["lon"])
                query_for_details["lon"] = float(rec["lon"])
                station_data["network"] = rec["rep_memo"]
                query_for_details["rep_memo"] = rec["rep_memo"]
                station_data["ident"] = "" if rec["ident"] is None else rec["ident"]
                if station_data["ident"]:
                    query_for_details["ident"] = station_data["ident"]
                details = []
                # add station details
                for el in tr.query_station_data(query_for_details):
                    detail_el = {}
                    var = el["variable"]
                    code = var.code
                    var_info = dballe.varinfo(code)
                    desc = var_info.desc
                    detail_el["code"] = code
                    detail_el["value"] = var.get()
                    detail_el["description"] = desc
                    details.append(detail_el)
                station_data["details"] = details

                # get data values
                if not only_stations:
                    product_data = {}
                    product_data["varcode"] = rec["var"]
                    var_info = dballe.varinfo(rec["var"])
                    product_data["description"] = var_info.desc
                    product_data["unit"] = var_info.unit
                    # product_data['scale'] = var_info.scale
                    product_val = {}
                    product_val["value"] = rec[rec["var"]].get()
                    reftime = datetime(
                        rec["year"],
                        rec["month"],
                        rec["day"],
                        rec["hour"],
                        rec["min"],
                        rec["sec"],
                    )
                    product_val["reftime"] = reftime.isoformat()
                    product_val["level"] = BeDballe.from_level_object_to_string(
                        rec["level"]
                    )
                    product_val["level_desc"] = BeDballe.get_description(
                        product_val["level"], "level"
                    )
                    product_val["timerange"] = BeDballe.from_trange_object_to_string(
                        rec["trange"]
                    )
                    product_val["timerange_desc"] = BeDballe.get_description(
                        product_val["timerange"], "timerange"
                    )

                    if query:
                        if "query" in query:
                            # add reliable flag
                            variable = rec["variable"]
                            attrs = variable.get_attrs()
                            is_reliable = BeDballe.data_qc(attrs)
                            product_val["is_reliable"] = is_reliable

                # determine where append the values
                existent_station = False
                for i in response:
                    # check if station is already on the response
                    if (
                        float(rec["lat"]) == i["station"]["lat"]
                        and float(rec["lon"]) == i["station"]["lon"]
                        and rec["rep_memo"] == i["station"]["network"]
                    ):
                        existent_station = True
                        if not only_stations:
                            # check if the element has already the given product
                            existent_product = False
                            for e in i["products"]:
                                if e["varcode"] == rec["var"]:
                                    existent_product = True
                                    e["values"].append(product_val)
                            if not existent_product:
                                product_data["values"] = []
                                product_data["values"].append(product_val)
                                i["products"].append(product_data)
                if not existent_station:
                    # create a new record
                    res_element["station"] = station_data
                    if not only_stations:
                        res_element["products"] = []
                        product_data["values"] = []
                        product_data["values"].append(product_val)
                        res_element["products"].append(product_data)
                    response.append(res_element)

        return response

    @staticmethod
    def merge_db_for_download(
        dballe_db, dballe_query_data, arki_db=None, arki_query_data=None,
    ):
        # merge the dbs
        if arki_db:
            log.debug(
                "Filling temp db with data from dballe. query: {}", dballe_query_data
            )
            with dballe_db.transaction() as tr:
                with arki_db.transaction() as temptr:
                    for cur in tr.query_messages(dballe_query_data):
                        temptr.import_messages(cur.message)
        # merge the queries for data
        query_data = {**dballe_query_data}
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
                        val_list = [x.strip() for x in val.split("or")]
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
                if key == "timerange" or key == "level":
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
