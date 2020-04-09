from restapi.utilities.logs import log
import dballe
import os
import itertools
import subprocess
import dateutil
import tempfile
import shlex
from datetime import datetime, timedelta

from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki

user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")


LASTDAYS = os.environ.get("LASTDAYS")  # number of days after which data pass in Arkimet

#DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,host=host, port=port))


class BeDballe():
    explorer = None

    @staticmethod
    def get_db_type(date_min, date_max):
        date_min_compar = datetime.utcnow() - date_min
        if date_min_compar.days >int(LASTDAYS):
            date_max_compar = datetime.utcnow() - date_max
            if date_max_compar.days > int(LASTDAYS):
                db_type = 'arkimet'
            else:
                db_type = 'mixed'
        else:
            db_type = 'dballe'
        return db_type

    @staticmethod
    def split_reftimes(date_min, date_max):
        refmax_dballe = date_max
        refmin_dballe = datetime.utcnow() - timedelta(days=int(LASTDAYS))
        refmax_arki_dt = refmin_dballe - timedelta(minutes=1)
        refmax_arki = refmax_arki_dt.strftime("%Y-%m-%d %H:%M")
        refmin_arki = date_min.strftime("%Y-%m-%d %H:%M")
        return refmax_dballe, refmin_dballe, refmax_arki, refmin_arki

    @staticmethod
    def build_arkimet_query(datemin=None, datemax=None, network=None):
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
        if network:
            arkimet_query += 'product: BUFR:t = {}'.format(network[0])
            if len(network) > 1:
                for i in network[1:]:
                    arkimet_query += ' or  BUFR:t = {}'.format(i)
        return arkimet_query

    @staticmethod
    def build_explorer():
        DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,
                                                                            host=host, port=port))
        explorer = dballe.Explorer()
        with explorer.rebuild() as update:
            with DB.transaction() as tr:
                update.add_db(tr)
        return explorer

    @staticmethod
    def get_summary(datasets, params, q=None):
        summarystats = {'s': None}
        # parse the query
        query = BeDballe.from_query_to_dic(q)

        arki_summary = None
        if 'datetimemin' in query:
            db_type = BeDballe.get_db_type(query['datetimemin'], query['datetimemax'])
        else:
            db_type = 'mixed'

        if db_type == 'mixed':
            arkimet_query = ''
            if 'datetimemin' in query:
                refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = BeDballe.split_reftimes(query['datetimemin'],
                                                                                                 query['datetimemax'])
                # set the datetimemin as limit to data in dballe
                query['datetimemin'] = refmin_dballe
                arkimet_query = BeDballe.build_arkimet_query(datemin=refmin_arki, datemax=refmax_arki)
            if 'network' in query:
                if not arkimet_query:
                    arkimet_query = BeDballe.build_arkimet_query(network=query['network'])
                else:
                    arkimet_query += BeDballe.build_arkimet_query(network=query['network'])
            arki_summary = arki.load_summary(datasets, arkimet_query)
        if db_type == 'arkimet':
            # redirect the query to arkimet to check if the data exists
            if 'network' in query:
                arkimet_query = BeDballe.build_arkimet_query(datemin=query['datetimemin'].strftime("%Y-%m-%d %H:%M"),
                                                             datemax=query['datetimemax'].strftime("%Y-%m-%d %H:%M"),
                                                             network=query['network'])
            else:
                arkimet_query = BeDballe.build_arkimet_query(datemin=query['datetimemin'].strftime("%Y-%m-%d %H:%M"),
                                                             datemax=query['datetimemax'].strftime("%Y-%m-%d %H:%M"))
            arki_summary = arki.load_summary(datasets, arkimet_query)

        # if there aren't networks, use dataset networks as filters
        if 'network' not in query:
            query['network'] = params

        log.info('Loading summary: query: {}'.format(query))

        fields, queries = BeDballe.from_query_to_lists(query)
        log.debug('Loading summary: fields: {}, queries: {}', fields, queries)

        # get all the possible combinations of queries to count the messages
        all_queries = list(itertools.product(*queries))
        message_count = 0
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            # count the items for each query
            DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,
                                                                            host=host, port=port))
            with DB.transaction() as tr:
                message_count += tr.query_data(dballe_query).remaining

        if arki_summary:
            # TODO this message count is approximate..do we need a real one?
            message_count += arki_summary['items']['summarystats']['c']

        summarystats['c'] = message_count
        if 'datetimemin' in query:
            if db_type == 'mixed' or db_type == 'arkimet':
                if 'b' in arki_summary['items']['summarystats']:
                    summarystats['b'] = arki_summary['items']['summarystats']['b']
                else:
                    summarystats['b'] = BeDballe.from_datetime_to_list(query['datetimemin'])
            else:
                summarystats['b'] = BeDballe.from_datetime_to_list(query['datetimemin'])
        elif db_type == 'mixed':
            if 'b' in arki_summary['items']['summarystats']:
                summarystats['b'] = arki_summary['items']['summarystats']['b']
        # else:
        #     summarystats['b'] = None
        if 'datetimemax' in query:
            if db_type == 'arkimet':
                if 'e' in arki_summary['items']['summarystats']:
                    summarystats['e'] = arki_summary['items']['summarystats']['e']
                else:
                    summarystats['e'] = BeDballe.from_datetime_to_list(query['datetimemax'])
            else:
                summarystats['e'] = BeDballe.from_datetime_to_list(query['datetimemax'])
        elif db_type == 'mixed':
            # the date is approximated because we can't get the datetimemax of data in dballe due to segmentation fault
            summarystats['e'] = BeDballe.from_datetime_to_list(datetime.utcnow())
        # else:
        #     summarystats['e'] = None
        return summarystats

    @staticmethod
    def load_filters(datasets, params, q=None):
        # create and update the explorer object
        explorer = BeDballe.build_explorer()

        # if not BeDballe.explorer:
            # BeDballe.explorer = BeDballe.build_explorer()
        # explorer = BeDballe.explorer

        # parse the query
        query = BeDballe.from_query_to_dic(q)
        log.info('Loading filters dataset: {}, query: {}', params, query)

        db_type = None
        # check where are the requested data
        if 'datetimemin' in query:
            db_type = BeDballe.get_db_type(query['datetimemin'], query['datetimemax'])
            log.debug('db type: {}', db_type)

            if db_type == 'mixed':
                refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = BeDballe.split_reftimes(query['datetimemin'],
                                                                                                 query['datetimemax'])
                # set the datetimemin as limit to data in dballe
                query['datetimemin'] = refmin_dballe
            if db_type == 'arkimet':
                # redirect the query to arkimet to check if the data exists
                if 'network' in query:
                    arkimet_query = BeDballe.build_arkimet_query(
                        datemin=query['datetimemin'].strftime("%Y-%m-%d %H:%M"),
                        datemax=query['datetimemax'].strftime("%Y-%m-%d %H:%M"),
                        network=query['network'])
                else:
                    arkimet_query = BeDballe.build_arkimet_query(
                        datemin=query['datetimemin'].strftime("%Y-%m-%d %H:%M"),
                        datemax=query['datetimemax'].strftime("%Y-%m-%d %H:%M"))
                datasize = arki.estimate_data_size(datasets, arkimet_query)
                if datasize == 0:
                    return None
                else:
                    # delete the datetimemin in query (i will check for filters in dballe in general)
                    query.pop('datetimemin', None)

        # check if requested networks are in that dataset
        query_networks_list = []
        if 'network' in query:
            if not all(elem in params for elem in query['network']):
                return None
            else:
                query_networks_list = query['network']
        else:
            # if there aren't requested network, data will be filtered only by dataset
            query_networks_list = params
        log.debug('Loading filters: query networks list : {}'.format(query_networks_list))

        # perform the queries in database to get the list of possible filters
        fields = {}
        networks_list = []
        variables = []
        levels = []
        tranges = []
        for n in query_networks_list:
            # filter the dballe database by network
            if not 'datetimemin' in query:
                explorer.set_filter({'report': n})
            else:
                explorer.set_filter(
                    {'report': n, 'datetimemin': query['datetimemin'], 'datetimemax': query['datetimemax']})

            # list of the variables of this network
            net_variables = []

            ######### VARIABLES FIELDS
            # get the list of all the variables of the network
            varlist = explorer.varcodes
            if not varlist and db_type:
                if db_type == 'mixed':
                    # check if arkimet has data
                    if 'network' in query:
                        arkimet_query = BeDballe.build_arkimet_query(
                            datemin=refmin_arki,
                            datemax=refmax_arki,
                            network=query['network'])
                    else:
                        arkimet_query = BeDballe.build_arkimet_query(
                            datemin=refmin_arki,
                            datemax=refmax_arki)
                    datasize = arki.estimate_data_size(datasets, arkimet_query)
                    if datasize != 0:
                        # filter dballe database again without reftime only to get the fields name
                        explorer.set_filter({'report': n})
                        varlist = explorer.varcodes
                        # delete the datetimemin in query (i will check for filters in dballe in general)
                        query.pop('datetimemin', None)

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
            level_fields, net_variables_temp = BeDballe.get_fields(explorer, n, net_variables, query, param='level')
            if not level_fields:
                continue
            # check if the temporary list of variable is not more little of the general one. If it is, replace the general list
            if not all(elem in net_variables_temp for elem in net_variables):
                net_variables = net_variables_temp

            ######### TIMERANGES FIELDS
            trange_fields, net_variables_temp, level_fields_temp = BeDballe.get_fields(explorer, n, net_variables,
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

            return fields
        else:
            return None

    @staticmethod
    def get_fields(explorer, network, variables, query, param):
        # filter the dballe database by list of variables (level and timerange depend on variable)
        if not 'datetimemin' in query:
            explorer.set_filter({'varlist': variables, 'report': network})
        else:
            explorer.set_filter({'varlist': variables, 'report': network, 'datetimemin': query['datetimemin'],
                                 'datetimemax': query['datetimemax']})

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
                            if not 'datetimemin' in query:
                                explorer.set_filter({'var': v})
                            else:
                                explorer.set_filter(
                                    {'var': v, 'datetimemin': query['datetimemin'],
                                     'datetimemax': query['datetimemax']})

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
                                if not 'datetimemin' in query:
                                    explorer.set_filter({'var': v})
                                else:
                                    explorer.set_filter(
                                        {'var': v, 'datetimemin': query['datetimemin'],
                                         'datetimemax': query['datetimemax']})

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
    def from_query_to_dic(q):
        # example of query string: string= "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;level:1,0,0,0 or 103,2000,0,0;product:B11001 or B13011;timerange:0,0,3600 or 1,0,900;network:fidupo or agrmet"
        params_list = ['reftime', 'network', 'product', 'level', 'timerange']
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
        if type == 'product' or type == 'network':
            description = value
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
        allowed_keys = ['level', 'network', 'product', 'timerange', 'datetimemin', 'datetimemax']
        dballe_keys = ['level', 'rep_memo', 'var', 'trange', 'datetimemin', 'datetimemax']

        for key, value in query.items():
            if key in allowed_keys:
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
                    queries.append(value)
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
        log.debug('extracting obs data from arkimet: {}',arki_query_cmd)
        proc = subprocess.Popen(arki_query_cmd, stdout=subprocess.PIPE)
        # write the result of the extraction on a temporary file
        with tempfile.SpooledTemporaryFile(max_size=10000000) as tmpf:
            tmpf.write(proc.stdout.read())
            tmpf.seek(0)
            with db.transaction() as tr:
                tr.load(tmpf, "BUFR")
        return db

    @staticmethod
    def extract_data(fields, queries, outfile=None, temp_db=None):
        if temp_db and outfile:
            log.debug('Mixed dbs: Extracting data from the temp db')
            # case of extracting from a temp db
            DB = temp_db
        # case of extracting from the general db or filling the temp db
        else:
            DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,host = host, port = port))
        # get all the possible combinations of queries
        all_queries = list(itertools.product(*queries))
        counter = 1
        cat_cmd = ['cat']
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            # set the filename for the partial extraction
            if outfile:
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
                # if there is the outfile do the extraction
                if outfile:
                    log.debug('Extract data from dballe. query: {}', dballe_query)
                    exporter = dballe.Exporter("BUFR")
                    with open(part_outfile, "wb") as out:
                        for row in tr.query_messages(dballe_query):
                            out.write(exporter.to_binary(row.message))
                # if there is not outfile, fill the temporary db
                else:
                    log.debug('Filling temp db with data from dballe. query: {}',dballe_query)
                    with temp_db.transaction() as temptr:
                        for cur in tr.query_messages(dballe_query):
                            temptr.import_messages(cur.message)

            if outfile:
                cat_cmd.append(part_outfile)
                # update counter
                counter += 1

        if outfile:
            if counter == 1:
                # any query has given a result
                raise Exception('Failure in data extraction: the query does not give any result')

            # join all the partial extractions
            with open(outfile, mode='w') as output:
                ext_proc = subprocess.Popen(cat_cmd, stdout=output)
                ext_proc.wait()
                if ext_proc.wait() != 0:
                    raise Exception('Failure in data extraction')
        else:
            return temp_db