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
    # N.B. ricordarsi alla fine di pulire la lista e tirare via gli elementi doppi
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
        filters = {}
        networks_list = []
        variables = []
        for n in query_networks_list:
            explorer.set_filter({'report': n})
            varlist = explorer.varcodes
            variables_temp = []
            if 'product' in query:
                # check if the requested variables are in the already filtered data
                for e in query['product']:
                    if e in varlist:
                        variables_temp.append(e)
                if not variables_temp:
                    continue
                else:
                    variables.extend(x for x in variables_temp if x not in variables)
            else:
                variables.extend(x for x in varlist if x not in variables)
            if variables:  # maybe all the variables have been discarded by the previous filters
                filters['product'] = variables
            else:
                continue
            networks_list.append(n)

            # levels = []
            # if 'level' in query:
            #     level_params = []
            #     for l in query['level']:
            #         # get the single params describing a level
            #         level_params = l.split(',')
            #         for v in variables:
            #             # forse non c'è bisogno del report?
            #             explorer.set_filter({'report': n,'var':v})
            #             level_list = explorer.levels

        if networks_list:
            filters['network'] = networks_list
            return filters
        else:
            return None


        # TO DO: ricordarsi di pulire la lista dai doppi
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
