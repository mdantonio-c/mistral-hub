from restapi.utilities.logs import log
import dballe
import os
import itertools
import subprocess
import dateutil
import tempfile
import shlex
from datetime import datetime, timedelta, date, time
from decimal import Decimal

from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
from mistral.exceptions import AccessToDatasetDenied

user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")



# DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,host=host, port=port))


class BeDballe():
    explorer = None
    LASTDAYS = os.environ.get("LASTDAYS")  # number of days after which data pass in Arkimet

    @staticmethod
    def get_db_type(date_min, date_max):
        date_min_compar = datetime.utcnow() - date_min
        if date_min_compar.days > int(BeDballe.LASTDAYS):
            date_max_compar = datetime.utcnow() - date_max
            if date_max_compar.days > int(BeDballe.LASTDAYS):
                db_type = 'arkimet'
            else:
                db_type = 'mixed'
        else:
            db_type = 'dballe'
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
    def build_arkimet_query(datemin=None, datemax=None, network=None, bounding_box=None):
        if isinstance(datemin, datetime):
            datemin_str = datemin.strftime("%Y-%m-%d %H:%M:%S")
            datemin = datemin_str

        if isinstance(datemax, datetime):
            datemax_str = datemax.strftime("%Y-%m-%d %H:%M:%S")
            datemax = datemax_str

        arkimet_query = ''
        if datemin:
            arkimet_query = "reftime: >={datemin},<={datemax};".format(
                datemin=datemin,
                datemax=datemax)
        if bounding_box:
            arkimet_query += 'area: bbox intersects POLYGON(({lonmin} {latmin},{lonmin} {latmax},{lonmax} {latmax}, {lonmax} {latmin}, {lonmin} {latmin}));'.format(
                lonmin=bounding_box['lonmin'], latmin=bounding_box['latmin'], lonmax=bounding_box['lonmax'],
                latmax=bounding_box['latmax'])
        if network:
            arkimet_query += 'product: BUFR:t = {}'.format(network[0])
            if len(network) > 1:
                for i in network[1:]:
                    arkimet_query += ' or  BUFR:t = {}'.format(i)
        return arkimet_query

    @staticmethod
    def build_explorer(memdb=None):
        if memdb:
            DB = memdb
        else:
            DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,
                                                                                        host=host, port=port))
        explorer = dballe.DBExplorer()
        with explorer.rebuild() as update:
            with DB.transaction() as tr:
                update.add_db(tr)
        return explorer

    @staticmethod
    def count_messages(params, query=None, memdb=None):
        if params and 'network' not in query:
            query['network'] = params
        fields, queries = BeDballe.from_query_to_lists(query)
        log.debug('Counting messages: fields: {}, queries: {}', fields, queries)

        if memdb:
            DB = memdb
        else:
            DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,
                                                                                        host=host, port=port))
        # get all the possible combinations of queries to count the messages
        all_queries = list(itertools.product(*queries))
        message_count = 0
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            # count the items for each query
            with DB.transaction() as tr:
                message_count += tr.query_data(dballe_query).remaining
        return message_count

    @staticmethod
    def load_filter_for_mixed(datasets, params, summary_stats, query=None):
        # TODO get all dataset filter can be optimized? (for now all the data in arkimet dataset are transfered in a temp dballe)
        # get fields for the dballe database
        log.debug('mixed dbs: get fields from dballe')
        query_for_dballe = {}
        if query:
            query_for_dballe = {**query}
        if 'datetimemin' in query:
            refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = BeDballe.split_reftimes(query['datetimemin'],
                                                                                             query['datetimemax'])
            # set up query for dballe with the correct reftimes
            query_for_dballe['datetimemin'] = refmin_dballe

        dballe_fields, dballe_summary = BeDballe.load_filters(datasets, params, summary_stats, db_type='dballe',
                                                              query_dic=query_for_dballe)

        # get fields for the arkimet database
        log.debug('mixed dbs: get fields from arkimet')
        query_for_arki = {}
        if query:
            query_for_arki = {**query}
        if 'datetimemin' in query:
            # set up query for arkimet with the correct reftimes
            query_for_arki['datetimemin'] = refmin_arki
            query_for_arki['datetimemax'] = refmax_arki
        else:
            # get retime min and max for arkimet datasets
            arki_summary = arki.load_summary(datasets)
            query_for_arki['datetimemin'] = datetime(*arki_summary['items']['summarystats']['b'])
            query_for_arki['datetimemax'] = datetime(*arki_summary['items']['summarystats']['e'])

        arki_fields, arki_summary = BeDballe.load_filters(datasets, params, summary_stats, db_type='arkimet',
                                                          query_dic=query_for_arki)

        if not dballe_fields and not arki_fields:
            return None, None
        # integrate the dballe dic with the arki one
        if arki_fields:
            for key in arki_fields:
                if not dballe_fields:
                    dballe_fields = {}
                    dballe_fields[key] = arki_fields[key]
                elif key not in dballe_fields:
                    dballe_fields[key] = arki_fields[key]
                else:
                    # merge the two lists
                    dballe_fields[key].extend(x for x in arki_fields[key] if x not in dballe_fields[key])

            # update summary
            if dballe_summary or arki_summary:
                if not dballe_summary:
                    dballe_summary = arki_summary
                else:
                    dballe_summary['b'] = arki_summary['b']
                    dballe_summary['c'] += arki_summary['c']
        return dballe_fields, dballe_summary

    @staticmethod
    def load_filters(datasets, params, summary_stats, db_type, query_dic=None):

        query = {}
        if query_dic:
            query = {**query_dic}

        # if not BeDballe.explorer:
        # BeDballe.explorer = BeDballe.build_explorer()
        # explorer = BeDballe.explorer

        log.info('Loading filters dataset: {}, query: {}', params, query)

        # check if requested networks are in that dataset
        query_networks_list = []
        if params:
            if 'network' in query:
                if not all(elem in params for elem in query['network']):
                    return None, None
                else:
                    query_networks_list = query['network']
            else:
                # if there aren't requested network, data will be filtered only by dataset
                query_networks_list = params
        else:
            if 'network' in query:
                query_networks_list = query['network']
        log.debug('Loading filters: query networks list : {}'.format(query_networks_list))

        bbox = {}
        bbox_keys = ['latmin', 'lonmin', 'latmax', 'lonmax']
        for key, value in query.items():
            if key in bbox_keys:
                bbox[key] = value

        memdb = None
        arkimet_query = None

        if db_type == 'arkimet':
            # redirect the query to arkimet to check if the data exists
            network = None
            if 'network' in query:
                network = query['network']
            datemin = query['datetimemin'].strftime("%Y-%m-%d %H:%M")
            datemax = query['datetimemax'].strftime("%Y-%m-%d %H:%M")
            arkimet_query = BeDballe.build_arkimet_query(datemin=datemin, datemax=datemax, network=network,
                                                         bounding_box=bbox)
            if not datasets:
                license = None
                if query:
                    if 'license' in query.keys():
                        license = query['license']
                datasets = arki.get_obs_datasets(arkimet_query, license)
                if not datasets:
                    # any dataset matches the query
                    return None, None
                # TODO managing check for unique license: it will be substituted by a dsn management?

            datasize = arki.estimate_data_size(datasets, arkimet_query)
            if datasize == 0:
                return None, None
            else:
                memdb = BeDballe.fill_db_from_arkimet(datasets, arkimet_query)

        # create and update the explorer object
        explorer = BeDballe.build_explorer(memdb)

        # perform the queries in database to get the list of possible filters
        fields = {}
        networks_list = []
        variables = []
        levels = []
        tranges = []
        if not query_networks_list:
            query_networks_list = explorer.all_reports
            log.debug('all networks: {}', query_networks_list)
        for n in query_networks_list:
            # filter the dballe database by network
            filters_for_explorer = {'report': n}
            if bbox:
                for key, value in bbox.items():
                    filters_for_explorer[key] = value
            if 'datetimemin' in query:
                filters_for_explorer['datetimemin'] = query['datetimemin']
                filters_for_explorer['datetimemax'] = query['datetimemax']

            explorer.set_filter(filters_for_explorer)

            # list of the variables of this network
            net_variables = []

            ######### VARIABLES FIELDS
            # get the list of all the variables of the network
            varlist = explorer.varcodes

            #### PRODUCT is in the query filters
            if 'product' in query:
                # check if the requested variables are in the network
                for e in query['product']:
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
            level_fields, net_variables_temp = BeDballe.get_fields(explorer, filters_for_explorer, net_variables, query,
                                                                   param='level')
            if not level_fields:
                continue
            # check if the temporary list of variable is not more little of the general one. If it is, replace the general list
            if not all(elem in net_variables_temp for elem in net_variables):
                net_variables = net_variables_temp

            ######### TIMERANGES FIELDS
            trange_fields, net_variables_temp, level_fields_temp = BeDballe.get_fields(explorer, filters_for_explorer,
                                                                                       net_variables,
                                                                                       query, param='timerange')
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
            fields['network'] = BeDballe.from_list_of_params_to_list_of_dic(networks_list, type='network')
            fields['product'] = BeDballe.from_list_of_params_to_list_of_dic(variables, type='product')
            fields['level'] = BeDballe.from_list_of_params_to_list_of_dic(levels, type='level')
            fields['timerange'] = BeDballe.from_list_of_params_to_list_of_dic(tranges, type='timerange')

            # create summary
            summary = {}
            # if summary is required
            if summary_stats:
                summary['c'] = BeDballe.count_messages(params, query, memdb)
                if arkimet_query:
                    arki_summary = arki.load_summary(datasets, arkimet_query)
                    summary['b'] = arki_summary['items']['summarystats']['b']
                    summary['e'] = arki_summary['items']['summarystats']['e']
                else:
                    if 'datetimemin' in query:
                        summary['b'] = BeDballe.from_datetime_to_list(query['datetimemin'])
                        summary['e'] = BeDballe.from_datetime_to_list(query['datetimemax'])
                    else:  # case of query of all dataset
                        datemin_dballe = datetime.utcnow() - timedelta(days=int(BeDballe.LASTDAYS))
                        summary['b'] = BeDballe.from_datetime_to_list(datemin_dballe)
                        summary['e'] = BeDballe.from_datetime_to_list(datetime.utcnow())
            return fields, summary
        else:
            return None, None

    @staticmethod
    def get_fields(explorer, filters_for_explorer, variables, query, param):
        # filter the dballe database by list of variables (level and timerange depend on variable)
        filters_w_varlist = {**filters_for_explorer, 'varlist': variables}
        explorer.set_filter(filters_w_varlist)

        level_list = []
        # get the list of all the fields for requested param according to the variables
        if param == 'level':
            param_list = explorer.levels
        elif param == 'timerange':
            param_list = explorer.tranges
            # if the param is timerange, 3 values packed are needed
            level_list = explorer.levels

        # parse the dballe object
        param_list_parsed = []
        for e in param_list:
            if param == 'level':
                p = BeDballe.from_level_object_to_string(e)
            elif param == 'timerange':
                p = BeDballe.from_trange_object_to_string(e)
            param_list_parsed.append(p)

        if level_list:
            level_list_parsed = []
            # parse the level list
            for l in level_list:
                level = BeDballe.from_level_object_to_string(l)
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
                if param == 'level':
                    return None, None
                elif param == 'timerange':
                    return None, None, None
            else:
                # if only the param is in query and not product, discard from the network variable list all products not matching the param
                if 'product' not in query:
                    variables_by_param = []
                    levels_by_trange = []
                    for qp in query[param]:
                        # for each variable i check if the param matches
                        for v in variables:
                            filters_w_var = {**filters_for_explorer, 'var': v}
                            # discard from the query the query params i don't need
                            filters_w_var.pop('report', None)
                            explorer.set_filter(filters_w_var)

                            if param == 'level':
                                param_list = explorer.levels
                            elif param == 'timerange':
                                param_list = explorer.tranges
                            # parse the dballe object
                            param_list_parsed = []
                            for e in param_list:
                                if param == 'level':
                                    p = BeDballe.from_level_object_to_string(e)
                                elif param == 'timerange':
                                    p = BeDballe.from_trange_object_to_string(e)
                                param_list_parsed.append(p)
                            # if the param matches append the variable in a temporary list
                            if qp in param_list_parsed:
                                variables_by_param.append(v)
                    # the temporary list of variables matching the requested param become the list of the variable of the network
                    variables = variables_by_param
                    # if the list of variables has been modified, we are filtering by timeranges and level is not in
                    # query, i have to check if the level fields still matches the new variable list
                    if param == 'timerange' and 'level' not in query:
                        # for each variable check if the level matches
                        for level in level_list_parsed:
                            for v in variables:
                                filters_w_var = {**filters_for_explorer, 'var': v}
                                # discard from the query the query params i don't need
                                filters_w_var.pop('report', None)
                                explorer.set_filter(filters_w_var)

                                var_level = explorer.levels
                                var_level_parsed = []
                                # parse the dballe.Level object
                                for e in var_level:
                                    l = BeDballe.from_level_object_to_string(e)
                                    var_level_parsed.append(l)
                                # if the level matches append the level in a temporary list
                                if level in var_level_parsed:
                                    levels_by_trange.append(level)
                        # the temporary list of levels matching the resulted variables become the list of levels to return
                        level_list_parsed = levels_by_trange
                if param == 'level':
                    return temp_fields, variables
                elif param == 'timerange':
                    return temp_fields, variables, level_list_parsed
        else:
            # if param is not in the query filter append return all the fields
            if param == 'level':
                return param_list_parsed, variables
            elif param == 'timerange':
                return param_list_parsed, variables, level_list_parsed

    @staticmethod
    def get_maps_response_for_mixed(networks, bounding_box, query, only_stations, station_id=None):
        # get data from the dballe database
        log.debug('mixed dbs: get data from dballe')
        query_for_dballe = {}
        if query:
            query_for_dballe = {**query}

        if 'datetimemin' in query_for_dballe:
            refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = BeDballe.split_reftimes(query['datetimemin'],
                                                                                             query['datetimemax'])
            # set up query for dballe with the correct reftimes
            query_for_dballe['datetimemin'] = refmin_dballe
        else:
            # if there is no reftime i'll get the data of the last hour
            # TODO last hour or last day as default?
            # for production
            instant_now = datetime.now()
            # for local tests
            # today = date(2015, 12, 31)
            # time_now = datetime.now().time()
            # instant_now = datetime.combine(today, time_now)

            query_for_dballe['datetimemax'] = instant_now
            query_for_dballe['datetimemin'] = datetime.combine(instant_now, time(instant_now.hour, 0, 0))

        dballe_maps_data = BeDballe.get_maps_response(networks, bounding_box, query_for_dballe, only_stations,
                                                      db_type='dballe', station_id=station_id)

        if query:
            if 'datetimemin' not in query:
                return dballe_maps_data
            else:
                # get data from the arkimet database
                log.debug('mixed dbs: get data from arkimet')
                query_for_arki = {}
                if query:
                    query_for_arki = {**query}
                # set up query for arkimet with the correct reftimes
                query_for_arki['datetimemin'] = refmin_arki
                query_for_arki['datetimemax'] = refmax_arki
                arki_maps_data = BeDballe.get_maps_response(networks, bounding_box, query_for_arki, only_stations,
                                                            db_type='arkimet', station_id=station_id)

                if not dballe_maps_data and not arki_maps_data:
                    response = []
                    return response

                if arki_maps_data:
                    if not station_id:
                        for i in arki_maps_data:
                            if dballe_maps_data:
                                if any(d['station']['id'] == i['station']['id'] for d in dballe_maps_data):
                                    # get the element index
                                    for e in dballe_maps_data:
                                        if e['station']['id'] == i['station']['id']:
                                            el_index = dballe_maps_data.index(e)
                                            break
                                    # append values to the variable
                                    if not only_stations:
                                        for e in i['products']:
                                            varcode = e['varcode']
                                            existent_product = False
                                            for el in dballe_maps_data[el_index]['products']:
                                                if el['varcode'] == varcode:
                                                    existent_product = True
                                                    for v in e['values']:
                                                        el['values'].append(v)
                                            if not existent_product:
                                                dballe_maps_data[el_index]['products'].append(e)
                                else:
                                    dballe_maps_data.append(i)
                            else:
                                dballe_maps_data.append(i)
                    else:
                        # only one station in the response: add arkimet values to dballe response
                        if dballe_maps_data:
                            for e in arki_maps_data['products']:
                                varcode = e['varcode']
                                existent_product = False
                                for el in dballe_maps_data['products']:
                                    if el['varcode'] == varcode:
                                        existent_product = True
                                        for v in e['values']:
                                            el['values'].append(v)
                                if not existent_product:
                                    dballe_maps_data['products'].append(e)
                        else:
                            dballe_maps_data = arki_maps_data

        return dballe_maps_data

    @staticmethod
    def get_maps_response(networks, bounding_box, query, only_stations, db_type=None, station_id=None):

        DB = dballe.DB.connect(
            "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw, host=host, port=port))

        # TODO va fatto un check licenze compatibili qui all'inizio (by dataset)? oppure a seconda della licenza lo si manda su un dballe o un altro?

        response = []

        # prepare the query for stations
        query_station_data = {}
        if bounding_box:
            query_station_data = {**bounding_box}
        if networks:
            # for now we consider only single parameters.
            # TODO choose if the network will be a single or multiple param
            query_station_data['rep_memo'] = networks
        ###############################
        # append to the query the station id if there is one
        if station_id:
            query_station_data['ana_id'] = int(station_id)

        # managing db_type
        if db_type == 'arkimet':
            station_lat = None
            station_lon = None
            if station_id:
                # get station network
                with DB.transaction() as tr:
                    count_data = tr.query_stations(query_station_data).remaining
                    # log.debug('count {}',count_data)
                    if count_data == 0:
                        return response
                    for rec in tr.query_stations(query_station_data):
                        networks = rec['rep_memo']
                        station_lat = rec['lat']
                        station_lon = rec['lon']
            # manage bounding box for queries by station id
            if not bounding_box and station_lat and station_lon:
                lat_decimals = Decimal(station_lat).as_tuple()[-1] * -1
                lon_decimals = Decimal(station_lon).as_tuple()[-1] * -1
                lat_add = Decimal(1) / Decimal(10 ** lat_decimals)
                lon_add = Decimal(1) / Decimal(10 ** lon_decimals)
                bounding_box['latmin'] = float(station_lat - lat_add)
                bounding_box['lonmin'] = float(station_lon - lon_add)
                bounding_box['latmax'] = float(station_lat + lat_add)
                bounding_box['lonmax'] = float(station_lon + lon_add)
                # log.debug('bounding box for station {} : {}',station_id, bounding_box)

            # manage reftime for queries in arkimet
            datemin = None
            datemax = None
            if query:
                datemin = query['datetimemin']
                datemax = query['datetimemax']
            # for now we consider network as a single parameters.
            # TODO choose if the network will be a single or multiple param
            # transform network param in a list to be managed better for arkimet queries
            networks_as_list = None
            if networks:
                networks_as_list = [networks]
            query_for_arkimet = BeDballe.build_arkimet_query(datemin=datemin, datemax=datemax, network=networks_as_list,
                                                             bounding_box=bounding_box)
            # check if there is a queried license
            license = None
            if query:
                if 'license' in query.keys():
                    license = query['license']
            # get the correct arkimet dataset
            datasets = arki.get_obs_datasets(query_for_arkimet, license)

            if not datasets:
                return response

            # check datasets license,
            # TODO se non passa il check il frontend lancerà un messaggio del tipo: 'dati con licenze diverse, prego sceglierne una'
            check_license = arki.get_unique_license(datasets)  # the exception raised by this function is enough?
            log.debug('datasets: {}', datasets)

        # build query for data starting from the one for stations
        query_data = {}
        if query_station_data:
            query_data = {**query_station_data}
        if query:
            # TODO: now query does not support multiple values for a single param
            # adapt the query to the dballe syntax and add the params to the general query
            allowed_keys = ['level', 'network', 'product', 'timerange', 'datetimemin', 'datetimemax']
            dballe_keys = ['level', 'rep_memo', 'var', 'trange', 'datetimemin', 'datetimemax']
            for key, value in query.items():
                if key in allowed_keys:
                    key_index = allowed_keys.index(key)
                    if key == 'timerange' or key == 'level':
                        tuple_list = []
                        for v in value[0].split(','):
                            if key == 'level' and v == '0':
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

        # managing different dbs
        if db_type == 'arkimet':
            memdb = BeDballe.fill_db_from_arkimet(datasets, query_for_arkimet)

        # if not station_id:
        if not station_id:
            if db_type == 'arkimet':
                # get data
                response = BeDballe.get_data_for_maps(memdb, query_data, only_stations, original_db=DB)
                # remove data from temp db
                memdb.remove_all()
            else:
                response = BeDballe.get_data_for_maps(DB, query_data, only_stations)
        else:
            if db_type == 'arkimet':
                response = BeDballe.get_station_data_for_maps(memdb, station_id, query_station_data, query_data,
                                                              original_db=DB)
                # remove data from temp db
                memdb.remove_all()
            else:
                response = BeDballe.get_station_data_for_maps(DB, station_id, query_station_data, query_data)
        return response

    @staticmethod
    def get_data_for_maps(db, query, only_stations, original_db=None):
        response = []
        log.debug('query data for maps {}', query)
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
                station_data["lat"] = float(rec["lat"])
                station_data["lon"] = float(rec["lon"])
                station_data['network'] = rec['rep_memo']
                station_data["ident"] = "" if rec["ident"] is None else rec["ident"]
                if not original_db:
                    # it means we are using the actual station ids
                    station_data['id'] = rec['ana_id']

                # get data values
                if not only_stations:
                    product_data = {}
                    product_data['varcode'] = rec['var']
                    var_info = dballe.varinfo(rec['var'])
                    product_data['description'] = var_info.desc
                    product_data['unit'] = var_info.unit
                    product_data['scale'] = var_info.scale
                    product_val = {}
                    product_val['value'] = rec[rec['var']].get()
                    product_val['reftime'] = datetime(rec["year"], rec["month"], rec["day"], rec["hour"], rec["min"],
                                                      rec["sec"])
                    product_val['level'] = BeDballe.from_level_object_to_string(rec['level'])
                    product_val['timerange'] = BeDballe.from_trange_object_to_string(rec['trange'])

                # determine where append the values
                existent_station = False
                for i in response:
                    # check if station is already on the response
                    if float(rec["lat"]) == i['station']['lat'] and float(rec["lon"]) == i['station']['lon'] and rec[
                        'rep_memo'] == i['station']['network']:
                        existent_station = True
                        if not only_stations:
                            # check if the element has already the given product
                            existent_product = False
                            for e in i['products']:
                                if e['varcode'] == rec['var']:
                                    existent_product = True
                                    e['values'].append(product_val)
                            if not existent_product:
                                product_data['values'] = []
                                product_data['values'].append(product_val)
                                i['products'].append(product_data)
                if not existent_station:
                    # create a new record
                    res_element['station'] = station_data
                    if not only_stations:
                        res_element['products'] = []
                        product_data['values'] = []
                        product_data['values'].append(product_val)
                        res_element['products'].append(product_data)
                    response.append(res_element)

        if original_db:
            # get the correct station id from the original dballe
            with original_db.transaction() as tr:
                for el in response:
                    station_query = {}
                    station_query['lat'] = el['station']['lat']
                    station_query['lon'] = el['station']['lon']
                    station_query['ident'] = None if el['station']['ident'] == "" else el['station']['ident']
                    station_query['rep_memo'] = el['station']['network']
                    for cur in tr.query_stations(station_query):
                        el['station']['id'] = cur['ana_id']
        return response

    @staticmethod
    def get_station_data_for_maps(db, station_id, query_station_data, query_data, original_db=None):
        if original_db:
            # substitute ana_id in query with lat lon params of that station
            id_query = {'ana_id': int(station_id)}
            with original_db.transaction() as tr:
                for cur in tr.query_stations(id_query):
                    query_station_data['lat'] = float(cur['lat'])
                    query_station_data['lon'] = float(cur['lon'])
                    query_station_data['ident'] = cur['ident']
                    query_station_data['rep_memo'] = cur['rep_memo']
            query_station_data.pop('ana_id', None)
        log.debug('query station data: {}', query_station_data)
        # get station data
        with db.transaction() as tr:
            count_data = tr.query_stations(query_station_data).remaining
            # log.debug('count {}',count_data)
            if count_data == 0:
                return None
            # get station data
            res_element = {}
            station_data = {}
            for rec in tr.query_station_data(query_station_data):
                var = rec['variable']
                code = var.code
                var_info = dballe.varinfo(code)
                desc = var_info.desc
                station_data[desc] = var.get()
                res_element['station'] = station_data

            # add params related to data to the station query
            # TODO da capire se abbiamo bisogno di level e timerange: in quel caso usiamo query_data e giusto ci aggiungiamo il reftime se non c'è
            if 'datetimemin' in query_data.keys():
                query_station_data['datetimemax'] = query_data['datetimemax']
                query_station_data['datetimemin'] = query_data['datetimemin']
            else:
                # use the standard one (today)
                # for prod
                today = date.today()
                query_station_data['datetimemax'] = datetime.now()
                query_station_data['datetimemin'] = datetime.combine(today, time(0, 0, 0))
                # for local tests
                # today = date(2015, 12, 31)
                # time_now = datetime.now().time()
                # query_station_data['datetimemax'] = datetime.combine(today, time_now)
                # query_station_data['datetimemin'] = datetime.combine(today, time(0, 0, 0))
            if 'rep_memo' in query_data:
                query_station_data['rep_memo'] = query_data['rep_memo']

            log.debug('query for timeseries {}', query_station_data)
            # get values for timeseries
            products = []
            res_element['products'] = []
            for row in tr.query_data(query_station_data):
                product_data = {}
                product_data['varcode'] = row['var']
                var_info = dballe.varinfo(row['var'])
                product_data['description'] = var_info.desc
                product_data['unit'] = var_info.unit
                product_data['scale'] = var_info.scale
                product_val = {}
                product_val['value'] = row[row['var']].get()
                product_val['reftime'] = datetime(row["year"], row["month"], row["day"], row["hour"], row["min"],
                                                  row["sec"])
                product_val['level'] = BeDballe.from_level_object_to_string(row['level'])
                product_val['timerange'] = BeDballe.from_trange_object_to_string(row['trange'])

                # check if the product is already in the list
                existent_product = False
                for e in res_element['products']:
                    if e['varcode'] == row['var']:
                        existent_product = True
                        e['values'].append(product_val)
                if not existent_product:
                    product_data['values'] = []
                    product_data['values'].append(product_val)
                    res_element['products'].append(product_data)
                    prod_available = {'varcode': row['var'], 'description': var_info.desc}
                    products.append(prod_available)

        res_element['station']['products available'] = products
        return res_element

    @staticmethod
    def from_query_to_dic(q):
        # example of query string: string= "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;level:1,0,0,0 or 103,2000,0,0;product:B11001 or B13011;timerange:0,0,3600 or 1,0,900;network:fidupo or agrmet"
        params_list = ['reftime', 'network', 'product', 'level', 'timerange', 'license']
        query_list = q.split(';')
        query_dic = {}
        for e in query_list:
            for p in params_list:
                if e.startswith(p):
                    val = e.split(p + ':')[1]
                    # ex. from 'level:1,0,0,0 or 103,2000,0,0' to '1,0,0,0 or 103,2000,0,0'

                    # reftime param has to be parsed differently
                    if p == 'reftime':
                        reftimes = [x.strip() for x in val.split(',')]
                        # ex. from ' >=2020-02-01 01:00,<=2020-02-04 15:13' to ['>=2020-02-01 01:00', '<=2020-02-04 15:13']
                        for r in reftimes:
                            if r.startswith('>'):
                                date_min = r.strip('>=')
                                query_dic['datetimemin'] = dateutil.parser.parse(date_min)
                            if r.startswith('<'):
                                date_max = r.strip('<=')
                                query_dic['datetimemax'] = dateutil.parser.parse(date_max)
                            if r.startswith('='):
                                date = r.strip('=')
                                query_dic['datetimemin'] = query_dic['datetimemax'] = dateutil.parser.parse(date)

                    # parsing all other parameters
                    else:
                        val_list = [x.strip() for x in val.split('or')]
                        query_dic[p] = val_list
        return query_dic

    @staticmethod
    def from_level_object_to_string(level):
        level_list = []

        if level.ltype1:
            ltype1 = str(level.ltype1)
        else:
            ltype1 = '0'
        level_list.append(ltype1)

        if level.l1:
            l1 = str(level.l1)
        else:
            l1 = '0'
        level_list.append(l1)

        if level.ltype2:
            ltype2 = str(level.ltype2)
        else:
            ltype2 = '0'
        level_list.append(ltype2)

        if level.l2:
            l2 = str(level.l2)
        else:
            l2 = '0'
        level_list.append(l2)

        level_parsed = ','.join(level_list)
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

        trange_parsed = ','.join(trange_list)
        return trange_parsed

    @staticmethod
    def from_list_of_params_to_list_of_dic(param_list, type):
        list_dic = []
        for p in param_list:
            item = {}
            item['dballe_p'] = p
            item['desc'] = BeDballe.get_description(p, type)
            list_dic.append(item)
        return list_dic

    @staticmethod
    def get_description(value, type):
        if type == 'network':
            description = value
        elif type == 'product':
            var_code = value
            var_infos = dballe.varinfo(var_code)
            description = var_infos.desc
        elif type == 'timerange' or type == 'level':
            list = []
            for v in value.split(','):
                if type == 'level' and v == '0':
                    val = None
                    list.append(val)
                else:
                    list.append(int(v))
            if type == 'timerange':
                tr = dballe.Trange(list[0], list[1], list[2])
                description = tr.describe()
            else:
                l = dballe.Level(list[0], list[1], list[2], list[3])
                description = l.describe()

        return description

    @staticmethod
    def from_filters_to_lists(filters):
        fields = []
        queries = []
        allowed_keys = ['level', 'network', 'product', 'timerange']
        dballe_keys = ['level', 'rep_memo', 'var', 'trange']

        for key, value in filters.items():
            if key in allowed_keys:
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])

                field_queries = []
                for e in value:
                    if key == 'timerange' or key == 'level':
                        # transform the timerange or level value in a tuple (required for dballe query)
                        tuple_list = []
                        for v in e['dballe_p'].split(','):
                            if key == 'level' and v == '0':
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(v))
                        field_queries.append(tuple(tuple_list))
                    else:
                        field_queries.append(e['dballe_p'])
                queries.append(field_queries)
            else:
                continue

        return fields, queries

    @staticmethod
    def from_query_to_lists(query):
        fields = []
        queries = []
        allowed_keys = ['level', 'network', 'product', 'timerange', 'datetimemin', 'datetimemax', 'ana_id', 'latmin',
                        'lonmin', 'latmax', 'lonmax']
        dballe_keys = ['level', 'rep_memo', 'var', 'trange', 'datetimemin', 'datetimemax', 'ana_id', 'latmin', 'lonmin',
                       'latmax', 'lonmax']

        for key, value in query.items():
            if key in allowed_keys:
                # log.debug('{}: {}',key,value)
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])
                if key == 'timerange' or key == 'level':
                    # transform the timerange or level value in a tuple (required for dballe query)
                    query_list = []
                    for v in value:
                        split_list = v.split(',')
                        tuple_list = []
                        for s in split_list:
                            if key == 'level' and s == '0':
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(s))
                        query_list.append(tuple(tuple_list))
                    queries.append(query_list)
                elif key == 'datetimemin' or key == 'datetimemax':
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
        str_list = str.split(',')
        list = []
        for s in str_list:
            list.append(int(s))
        return list

    @staticmethod
    def fill_db_from_arkimet(datasets, query):
        db = dballe.DB.connect("mem:")
        ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
        arki_query_cmd = shlex.split("arki-query --data '{}' {}".format(query, ds))
        log.debug('extracting obs data from arkimet: {}', arki_query_cmd)
        proc = subprocess.Popen(arki_query_cmd, stdout=subprocess.PIPE)
        if proc.returncode:
            raise AccessToDatasetDenied('Access to dataset denied')
        # write the result of the extraction on a temporary file
        with tempfile.SpooledTemporaryFile(max_size=10000000) as tmpf:
            tmpf.write(proc.stdout.read())
            tmpf.seek(0)
            with db.transaction() as tr:
                tr.load(tmpf, "BUFR")
        return db

    @staticmethod
    def parse_query_for_data_extraction(datasets, filters=None, reftime=None):

        # get network list from requested datasets
        dataset_nets = []
        for ds in datasets:
            nets = arki.get_observed_dataset_params(ds)
            for n in nets:
                dataset_nets.append(n)

        fields = []
        queries = []
        # create a "base" query using the filters
        if filters:
            fields, queries = BeDballe.from_filters_to_lists(filters)
            # check if requested networks are in that dataset
            if 'rep_memo' in fields:
                key_index = fields.index('rep_memo')
                nets_in_query = queries[key_index]
                if not all(elem in dataset_nets for elem in nets_in_query):
                    raise Exception('Failure in data extraction: Invalid set of filters')

        # parsing reftime and add it to the query
        if reftime:
            date_min, date_max = BeDballe.parse_data_extraction_reftime(reftime['from'], reftime['to'])
            fields.append('datetimemin')
            queries.append([date_min])
            fields.append('datetimemax')
            queries.append([date_max])

        # if there aren't filters, data are filtered only by dataset's networks
        if 'rep_memo' not in fields:
            fields.append('rep_memo')
            queries.append(dataset_nets)

        return fields, queries

    @staticmethod
    def extract_data_for_mixed(datasets, fields, queries, outfile):

        # extract data from the dballe database
        log.debug('mixed dbs: extract data from dballe')
        dballe_queries = []
        for q in queries:
            dballe_queries.append(q)
        if 'datetimemin' in fields:
            refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = BeDballe.split_reftimes(
                queries[fields.index('datetimemin')][0],
                queries[fields.index('datetimemax')][0])
            # set up query for dballe with the correct reftimes
            dballe_queries[fields.index('datetimemin')][0] = refmin_dballe

        # set the filename for the partial extraction
        if outfile.endswith('.tmp'):
            outfile_split = outfile[:-4]
            filebase, fileext = os.path.splitext(outfile_split)
        else:
            filebase, fileext = os.path.splitext(outfile)

        dballe_outfile = filebase + '_dballe_part' + fileext + '.tmp'

        # extract
        BeDballe.extract_data(datasets, fields, dballe_queries, dballe_outfile, db_type='dballe')

        # extract data from the arkimet database
        log.debug('mixed dbs: extract data from arkimet')
        arki_queries = []
        for q in queries:
            arki_queries.append(q)
        if 'datetimemin' in fields:
            # set up query for arkimet with the correct reftimes
            arki_queries[fields.index('datetimemin')][0] = refmin_arki
            arki_queries[fields.index('datetimemax')][0] = refmax_arki

        arki_outfile = filebase + '_arki_part' + fileext + '.tmp'

        # extract
        BeDballe.extract_data(datasets, fields, arki_queries, arki_outfile, db_type='arkimet')

        cat_cmd = ['cat']
        if os.path.exists(dballe_outfile):
            cat_cmd.append(dballe_outfile)
        if os.path.exists(arki_outfile):
            cat_cmd.append(arki_outfile)

        # check if the extractions were done
        if len(cat_cmd) == 1:
            # any extraction file exists
            raise Exception('Failure in data extraction')

        # join the dballe extraction with the arki one
        with open(outfile, mode='w') as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise Exception('Failure in data extraction')

    @staticmethod
    def extract_data(datasets, fields, queries, outfile, db_type):

        # choose the db
        if db_type == 'arkimet':
            # create arkimet query
            network = None
            if 'rep_memo' in fields:
                network = queries[fields.index('rep_memo')]

            datemin = None
            datemax = None
            if 'datetimemin' in fields:
                datemin = queries[fields.index('datetimemin')][0].strftime("%Y-%m-%d %H:%M")
                datemax = queries[fields.index('datetimemax')][0].strftime("%Y-%m-%d %H:%M")

            arkimet_query = BeDballe.build_arkimet_query(datemin=datemin, datemax=datemax, network=network)

            # fill the temp db and choose it as the db for extraction
            DB = BeDballe.fill_db_from_arkimet(datasets, arkimet_query)
        else:
            DB = dballe.DB.connect(
                "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw, host=host,
                                                                     port=port))

        # get all the possible combinations of queries
        all_queries = list(itertools.product(*queries))
        counter = 1
        cat_cmd = ['cat']
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            # set the filename for the partial extraction
            if outfile.endswith('.tmp'):
                outfile_split = outfile[:-4]
                filebase, fileext = os.path.splitext(outfile_split)
            else:
                filebase, fileext = os.path.splitext(outfile)
            part_outfile = filebase + '_part' + str(counter) + fileext + '.tmp'

            with DB.transaction() as tr:
                # check if the query gives a result
                count = tr.query_data(dballe_query).remaining
                # log.debug('counter= {} dballe query: {} count:{}'.format(str(counter), dballe_query, count))
                if count == 0:
                    continue
                log.debug('Extract data from dballe. query: {}', dballe_query)
                exporter = dballe.Exporter("BUFR")
                with open(part_outfile, "wb") as out:
                    for row in tr.query_messages(dballe_query):
                        out.write(exporter.to_binary(row.message))

            cat_cmd.append(part_outfile)
            # update counter
            counter += 1

        if db_type == 'arkimet':
            # clear the temporary db
            DB.remove_all()

        if counter == 1:
            # any query has given a result
            raise Exception('Failure in data extraction: the query does not give any result')

        # join all the partial extractions
        with open(outfile, mode='w') as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise Exception('Failure in data extraction')
