from restapi.utilities.logs import log
import dballe
import os
user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")

DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,
                                                                            host=host, port=port))

class BeDballe():

    @staticmethod
    ####### TO DO prendere dentro anche una possibile query (pensare come) in maniera tale da creare un metodo che mi vada bene per l'idea futura di caricare i fields in maniera dinamica
    # cicli multipli tipo questi https://stackoverflow.com/questions/14379103/double-for-loops-in-python
    def load_filters(params,q=None):
        # create and update the explorer object
        explorer = dballe.Explorer()
        with explorer.rebuild() as update:
            with DB.transaction() as tr:
                update.add_db(tr)

        # parse the query
        query = BeDballe.from_query_to_dic(q)
        log.info('query: {}'.format(query))

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
        log.debug('query networks list : {}'.format(query_networks_list))

        # perform the queries in database to get the list of possible filters
        fields = {}
        networks_list = []
        variables = []
        levels = []
        for n in query_networks_list:
            # filter the dballe database by network
            explorer.set_filter({'report': n})

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
            # filter the dballe database by list of variables (level depends on variable)
            explorer.set_filter({'varlist': net_variables})
            # get the list of all the levels according to the variables
            level_list = explorer.levels
            # parse the dballe.Level object
            level_list_parsed = []
            for l in level_list:
                level = BeDballe.from_level_object_to_string(l)
                level_list_parsed.append(level)

            #### LEVEL is in the query filters
            if 'level' in query:
                temp_levels = []
                # check if the requested levels matches the one required for the given variables
                for e in query['level']:
                    if e in level_list_parsed:
                        # if there is append it to the temporary list of matching levels
                        temp_levels.append(e)
                if not temp_levels:
                    # if at the end of the cycle the temporary list of matching variables is still empty go to the next network
                    continue
                else:
                    # if only level is in query and not product, discard from the network variable list all products not matching the level
                    if 'product' not in query:
                        variables_by_levels = []
                        for ql in query['level']:
                            # for each variable i check if the level matches
                            for e in net_variables:
                                explorer.set_filter({'var': e})
                                level_list = explorer.levels
                                level_list_parsed = []
                                for l in level_list:
                                    level = BeDballe.from_level_object_to_string(l)
                                    level_list_parsed.append(level)
                                # if the level matches append the variable in a temporary list
                                if ql in level_list_parsed:
                                    variables_by_levels.append(e)
                        # the temporary list of variables matching the requested levels become the list of the variable of the network
                        net_variables = variables_by_levels
                    levels.extend(x for x in temp_levels if x not in levels)
            else:
                # if level is not in the query filter append all the levels of the network in the final list of the fields
                levels.extend(x for x in level_list_parsed if x not in levels)

            # append all the network variables in the final field list
            variables.extend(x for x in net_variables if x not in variables)

            # if there are results, this network can be in the final fields
            networks_list.append(n)

        # if matching fields were found network list can't be empty
        if networks_list:
            # create the final dictionary
            fields['network'] = networks_list
            fields['product'] = variables
            fields['level'] = levels
            return fields
        else:
            return None

        # TO DO: il reftime a che mi serve in questo caso??




    @staticmethod
    def from_query_to_dic(q):
        # example of query string: string= "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;level:1,0,0,0 or 103,2000,0,0;product:B11001 or B13011;timerange:0,0,3600 or 1,0,900;network:fidupo or agrmet"
        params_list = ['reftime','network','product','level','timerange']
        query_list = q.split(';')
        query_dic = {}
        for e in query_list:
            for p in params_list:
                if e.startswith(p):
                    val = e.split(p + ':')[1]
                    # ex. from 'level:1,0,0,0 or 103,2000,0,0' to '1,0,0,0 or 103,2000,0,0'

                    # reftime param has to be parsed differently
                    if p =='reftime':
                        refs = {}
                        reftimes = [x.strip() for x in val.split(',')]
                        # ex. from ' >=2020-02-01 01:00,<=2020-02-04 15:13' to ['>=2020-02-01 01:00', '<=2020-02-04 15:13']
                        for r in reftimes:
                            if r.startswith('>'):
                                refs['min_reftime'] = r.strip('>=')
                            if r.startswith('<'):
                                refs['max_reftime'] = r.strip('<=')
                            if r.startswith('='):
                                refs['min_reftime'] = refs['max_reftime'] = r.strip('=')
                        query_dic['reftime']=refs

                    # parsing all other parameters
                    else:
                        val_list = [x.strip() for x in val.split('or')]
                        query_dic[p] = val_list
        return query_dic

    @staticmethod
    def from_level_object_to_string(level):
        level_list=[]

        if level.ltype1:
            ltype1 = str(level.ltype1)
        else:
            ltype1= '0'
        level_list.append(ltype1)

        if level.l1:
            l1 = str(level.l1)
        else:
            l1= '0'
        level_list.append(l1)

        if level.ltype2:
            ltype2 = str(level.ltype2)
        else:
            ltype2= '0'
        level_list.append(ltype2)

        if level.l2:
            l2 = str(level.l2)
        else:
            l2= '0'
        level_list.append(l2)

        level_parsed = ','.join(level_list)
        return level_parsed


