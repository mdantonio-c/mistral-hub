# -*- coding: utf-8 -*-

from mistral.services.requests_manager import RequestManager
from restapi.rest.definition import EndpointResource
from restapi import decorators as decorate
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class DataReady(EndpointResource):

    POST = {
        "/data/ready": {
            "summary": "Notify that a dataset is ready",
            "responses": {"202": {"description": "Notification received"}},
        }
    }

    @decorate.catch_error()
    @authentication.required()
    def post(self):

        data = self.get_input()

        cluster = data.get("Cluster")
        model = data.get("Model")
        rundate = data.get("rundate")

        log.info("Cluster = {}\tModel = {}\trundate = {}", cluster, model, rundate)

        db = self.get_service_instance('sqlalchemy')

        schedules_list = db.Schedule.query.all()
        for row in schedules_list:
            r = RequestManager._get_schedule_response(row)

            # e.g. 13
            request_id = r['id']

            # e.g. DEmo-scheduled
            request_name = r['name']

            name = "{} ({})".format(request_name, request_id)

            # e.g. True
            enabled = r['enabled']
            if not enabled:
                log.debug("Skipping {}: schedule is not enabled", name)
                continue

            # e.g. True
            on_data_ready = r['on_data_ready']
            if not on_data_ready:
                log.debug("Skipping {}: schedule is not on_data_ready", name)
                continue

            # e.g. '2019-12-13T15:52:30.834060'
            # creation_date = r['creation_date']

            # e.g. ['lm5']
            datasets = r['args']['datasets']

            if len(datasets) == 0:
                log.warning(
                    "Schedule {} requires no dataset: {}, skipping", name, datasets)
                continue

            if len(datasets) >= 2:
                log.warning(
                    "Schedule {} requires more than a dataset: {}. This is still unsupported, skipping", name, datasets)
                continue

            if datasets[0] != model:
                log.debug(
                    "Skipping {}: schedule is looking for dataset {}", name, datasets)
                continue

            log.info("Checking schedule: {}", name)
            # e.g. {
            #     'from': '2019-09-01T00:00:00.000Z',
            #     'to': '2019-09-30T12:02:00.000Z'
            # }
            # reftime = r['args']['reftime']

            # e.g. {'level': [{'desc': 'sfc Surface (of the Earth, which includes sea surface) 0 0', 'lt': 1, 's': 'GRIB1'}], 'product': [{'desc': 'P Pressure Pa', 'or': 80, 'pr': 1, 's': 'GRIB1', 'ta': 2}, {'desc': 'T Temperature K', 'or': 80, 'pr': 11, 's': 'GRIB1', 'ta': 2}, {'desc': 'Q Specific humidity kg kg^-1', 'or': 80, 'pr': 51, 's': 'GRIB1', 'ta': 2}], 'timerange': [{'desc': 'Forecast product valid at reference time + P1 (P1>0) - p1 0 time unit second', 'p1': 0, 'p2': 0, 's': 'GRIB1', 'ty': 0, 'un': 1}, {'desc': 'Forecast product valid at reference time + P1 (P1>0) - p1 3600 time unit second', 'p1': 1, 'p2': 0, 's': 'GRIB1', 'ty': 0, 'un': 1}, {'desc': 'Forecast product valid at reference time + P1 (P1>0) - p1 7200 time unit second', 'p1': 2, 'p2': 0, 's': 'GRIB1', 'ty': 0, 'un': 1}, {'desc': 'Forecast product valid at reference time + P1 (P1>0) - p1 10800 time unit second', 'p1': 3, 'p2': 0, 's': 'GRIB1', 'ty': 0, 'un': 1}, {'desc': 'Forecast product valid at reference time + P1 (P1>0) - p1 14400 time unit second', 'p1': 4, 'p2': 0, 's': 'GRIB1', 'ty': 0, 'un': 1}, {'desc': 'Forecast product valid at reference time + P1 (P1>0) - p1 18000 time unit second', 'p1': 5, 'p2': 0, 's': 'GRIB1', 'ty': 0, 'un': 1}]}
            # filters = r['args']['filters']

            # e.g. []
            # postprocessors = r['args']['postprocessors']

            log.info(r)

            # se tra gli args manca run significa che chiede sia 00 sia 12
            # reftime == 00 || reftime == 12,
            # quindi modificare reftime ricevuto per impostare la corsa successiva
            # == rundate at 00 || rundate at 12

        return self.force_response("1", code=hcodes.HTTP_OK_ACCEPTED)
