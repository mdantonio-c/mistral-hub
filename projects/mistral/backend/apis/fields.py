# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi import decorators
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from restapi.utilities.logs import log

from datetime import datetime

class Fields(EndpointResource):

    labels = ['field']
    GET = {
        '/fields': {
            'summary': 'Get summary fields for given dataset(s).',
            'parameters': [
                {
                    'name': 'datasets',
                    'in': 'query',
                    'type': 'array',
                    'uniqueItems': True,
                    'collectionFormat': 'csv',
                    'items': {'type': 'string'},
                },
                {'name': 'q', 'in': 'query', 'type': 'string', 'default': ''},
                {
                    'name': 'onlySummaryStats',
                    'in': 'query',
                    'type': 'boolean',
                    'default': False,
                    'allowEmptyValue': True,
                },
            ],
            'responses': {
                '200': {
                    'description': 'List of fields successfully retrieved',
                    'schema': {'$ref': '#/definitions/Summary'},
                }
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self):
        """ Get all fields for given datasets"""
        params = self.get_input()
        ds = params.get('datasets')
        query = params.get('q')
        datasets = ds.split(',') if ds is not None else []

        # check for existing dataset(s)
        for ds_name in datasets:
            found = next(
                (ds for ds in arki.load_datasets() if ds.get('id', '') == ds_name), None
            )
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )

        # check if the datasets are of the same type
        dataset_format = arki.get_datasets_format(datasets)
        if not dataset_format:
            raise RestApiException(
                "Invalid set of datasets : datasets have different formats",
                status_code=hcodes.HTTP_BAD_REQUEST,
            )
        ########## OBSERVED DATA ###########
        if dataset_format == 'bufr':
            summary = None
            log.debug('Dataset(s) for observed data: {}'.format(datasets))

            resulting_fields = {
                'summarystats': {'c': 0, 's': 0}
            }
            requested_nets = []
            # check db type
            query_dic = {}
            if query:
                query_dic = dballe.from_query_to_dic(query)
            if 'datetimemin' in query_dic:
                db_type = dballe.get_db_type(query_dic['datetimemin'], query_dic['datetimemax'])
            else:
                db_type = 'mixed'
            log.debug('db type: {}', db_type)

            for ds in datasets:
                # get dataset params (to filter dballe according the requested dataset)
                ds_params = arki.get_observed_dataset_params(ds)
                for net in ds_params:
                    requested_nets.append(net)
                log.info('dataset: {}, networks: {}'.format(ds, ds_params))
                if db_type == 'mixed':
                    fields, summary = dballe.load_filter_for_mixed(datasets, ds_params, query=query_dic)
                else:
                    fields, summary = dballe.load_filters(datasets, ds_params, db_type=db_type, query_dic=query_dic)
                if not fields:
                    continue
                else:
                    for key in fields:
                        # check and integrate the filter dic
                        if key not in resulting_fields:
                            resulting_fields[key] = fields[key]
                        else:
                            # merge the two lists
                            resulting_fields[key].extend(x for x in fields[key] if x not in resulting_fields[key])
                    # update the summary
                    resulting_fields['summarystats']['c'] += summary['c']
                    if not 'e' in resulting_fields['summarystats']:
                        resulting_fields['summarystats']['e'] = summary['e']
                    else:
                        summary_date = datetime(*resulting_fields['summarystats']['e'])
                        new_date = datetime(*summary['e'])
                        if new_date > summary_date:
                            resulting_fields['summarystats']['e'] = summary['e']
                    if not 'b' in resulting_fields['summarystats']:
                        resulting_fields['summarystats']['b'] = summary['b']
                    else:
                        summary_date = datetime(*resulting_fields['summarystats']['b'])
                        new_date = datetime(*summary['b'])
                        if new_date < summary_date:
                            resulting_fields['summarystats']['b'] = summary['b']

            summary = {'items': resulting_fields}

        ########## ARKIMET ###########
        else:
            summary = arki.load_summary(datasets, query)

        ########## ONLY ARKIMET SUMMARY ###########
        only_summary_stats = params.get('onlySummaryStats')
        if isinstance(only_summary_stats, str) and (
            only_summary_stats == '' or only_summary_stats.lower() == 'true'
        ):
            only_summary_stats = True
        elif type(only_summary_stats) == bool:
            # do nothing
            pass
        else:
            only_summary_stats = False
        if only_summary_stats:
            # we want to return ONLY summary Stats with no fields
            log.debug('ONLY Summary Stats')
            summary = summary['items']['summarystats']
        return self.response(summary)
