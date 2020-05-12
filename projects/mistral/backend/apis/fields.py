# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi import decorators
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from restapi.utilities.logs import log
from mistral.exceptions import AccessToDatasetDenied

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
                {'name': 'bounding-box', 'in': 'query', 'type': 'string',
                 'description': 'coordinates of a bounding box'},
                {
                    'name': 'onlySummaryStats',
                    'in': 'query',
                    'type': 'boolean',
                    'default': False,
                    'allowEmptyValue': True,
                },
                {
                    'name': 'SummaryStats',
                    'in': 'query',
                    'type': 'boolean',
                    'default': True,
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
        bbox = params.get('bounding-box')
        bbox_list = bbox.split(',') if bbox is not None else []
        bounding_box = {}
        if bbox_list:
            log.debug(bbox_list)
            for i in bbox_list:
                split = i.split(':')
                bounding_box[split[0]] = split[1]

        ########## QUERY FOR    SUMMARY ###########
        summary_stats = params.get('SummaryStats')
        if isinstance(summary_stats, str) and (
            summary_stats == '' or summary_stats.lower() == 'true'
        ):
            only_summary_stats = True
        elif type(summary_stats) == bool:
            # do nothing
            pass
        else:
            summary_stats = False

        datasets = ds.split(',') if ds is not None else []

        # check for existing dataset(s)
        if datasets:
            for ds_name in datasets:
                found = next(
                    (ds for ds in arki.load_datasets() if ds.get('id', '') == ds_name), None
                )
                if not found:
                    raise RestApiException(
                        "Dataset '{}' not found".format(ds_name),
                        status_code=hcodes.HTTP_BAD_NOTFOUND,
                    )

            data_type = arki.get_datasets_category(datasets)
            if not data_type:
                raise RestApiException(
                    "Invalid set of datasets : datasets categories are different",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        else:
            # if data_type is forecast always dataset has to be specified. If dataset is not in query data_type can't be 'FOR'
            data_type = 'OBS'

        ########## OBSERVED DATA ###########
        if data_type == 'OBS':
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
            if bounding_box:
                for key, value in bounding_box.items():
                    query_dic[key] = value
            if 'datetimemin' in query_dic:
                db_type = dballe.get_db_type(query_dic['datetimemin'], query_dic['datetimemax'])
            else:
                db_type = 'mixed'
            log.debug('db type: {}', db_type)

            if datasets:
                for ds in datasets:
                    # get dataset params (to filter dballe according the requested dataset)
                    ds_params = arki.get_observed_dataset_params(ds)
                    for net in ds_params:
                        requested_nets.append(net)
                    log.info('dataset: {}, networks: {}'.format(ds, ds_params))
                    try:
                        if db_type == 'mixed':
                            fields, summary = dballe.load_filter_for_mixed(datasets, ds_params, summary_stats, query=query_dic)
                        else:
                            fields, summary = dballe.load_filters(datasets, ds_params, summary_stats, db_type=db_type, query_dic=query_dic)
                    except AccessToDatasetDenied:
                        raise RestApiException(
                            'Access to dataset denied',
                            status_code=hcodes.HTTP_SERVER_ERROR,
                        )
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
                        if summary_stats:
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
            else:
                ds_params = []
                if db_type == 'mixed':
                    fields, summary = dballe.load_filter_for_mixed(datasets, ds_params,summary_stats, query=query_dic)
                else:
                    fields, summary = dballe.load_filters(datasets, ds_params,summary_stats, db_type=db_type, query_dic=query_dic)
                if fields:
                    for key in fields:
                        resulting_fields[key] = fields[key]
                    if summary_stats:
                        for key in summary:
                            resulting_fields['summarystats'][key]=summary[key]
                    else:
                        resulting_fields.pop('summarystats', None)
            summary = {'items': resulting_fields}

        ########## ARKIMET ###########
        else:
            try:
                summary = arki.load_summary(datasets, query)
            except AccessToDatasetDenied:
                raise RestApiException(
                    'Access to dataset denied',
                    status_code=hcodes.HTTP_SERVER_ERROR,
                )

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
