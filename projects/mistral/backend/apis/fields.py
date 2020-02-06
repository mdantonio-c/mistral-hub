# -*- coding: utf-8 -*-

from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from restapi.utilities.logs import log


class Fields(EndpointResource):

    # schema_expose = True
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

    @catch_error()
    @authentication.required()
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
            # TO DO split between arkimet and dballe. For now there is only the dballe case

            resulting_fields={}
            for ds in datasets:
                # get dataset params (to filter dballe according the requested dataset)
                ds_params = arki.get_observed_dataset_params(ds)
                log.info('dataset: {}, networks: {}'.format(ds,ds_params))
                fields = dballe.load_filters(ds_params,query)
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

            if resulting_fields:
                summary = resulting_fields
            else:
                raise RestApiException(
                        "Invalid set of filters : the applied filters does not give any result",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )



        ########## ARKIMET ###########
        else:
            summary = arki.load_summary(datasets, query)

        ########## ONLY ARKIMET SUMMARY ###########
        onlySummaryStats = params.get('onlySummaryStats')
        if isinstance(onlySummaryStats, str) and (
            onlySummaryStats == '' or onlySummaryStats.lower() == 'true'
        ):
            onlySummaryStats = True
        elif type(onlySummaryStats) == bool:
            # do nothing
            pass
        else:
            onlySummaryStats = False
        if onlySummaryStats:
            # we want to return ONLY summary Stats with no fields
            log.debug('ONLY Summary Stats')
            summary = summary['items']['summarystats']
        return self.force_response(summary)
        # js = json.dumps(summary)
        # return Response(js, status=200, mimetype='application/json')
