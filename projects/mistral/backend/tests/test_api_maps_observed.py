# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import os
from restapi.tests import BaseTests, API_URI
# from restapi.tests import AUTH_URI, BaseAuthentication
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log

LASTDAYS = os.environ.get("LASTDAYS")


class TestApp(BaseTests):

    @staticmethod
    def get_params_value(client, headers, reftime):
        # get an existing dataset of observed data
        obs_dataset = arki.get_obs_datasets(None, None)
        # q params può essere una lista e la risposta è un vocabolario con nome parametro:valore
        # networks, bounding-box,
        date_from = reftime['datetime_min'].strftime("%Y-%m-%d %H:%M")
        date_to = reftime['datetime_max'].strftime("%Y-%m-%d %H:%M")
        for dataset in obs_dataset:
            endpoint = API_URI + '/fields?q=reftime:>={date_from},<={date_to}&datasets={dataset}&SummaryStats=false'.format(
                date_from=date_from, date_to=date_to, dataset=dataset)
            r = client.get(endpoint, headers=headers)
            response_data = TestApp.get_content(r)
            if response_data['items']:
                break
        # from the response pick a network and a product
        params_value = {}
        params_value['date_from'] = date_from
        params_value['date_to'] = date_to
        params_value['network'] = response_data['items']['network'][0]['dballe_p']
        params_value['product_1'] = response_data['items']['product'][0]['dballe_p']
        params_value['product_2'] = response_data['items']['product'][1]['dballe_p']

        log.debug('test_params: {}', params_value)

        return params_value

    @staticmethod
    def get_reftime(q_db_type):
        q_reftime = {}
        if q_db_type == 'dballe':
            q_reftime['datetime_max'] = datetime.utcnow()
            q_reftime['datetime_min'] = datetime.utcnow() - timedelta(hours=1)
        elif q_db_type == 'arkimet':
            q_reftime['datetime_max'] = datetime.utcnow() - timedelta(days=int(LASTDAYS) + 1)
            q_reftime['datetime_min'] = q_reftime['datetime_max'] - timedelta(hours=1)
        elif q_db_type == 'mixed':
            q_reftime['datetime_max'] = datetime.utcnow() - timedelta(days=int(LASTDAYS) - 1)
            q_reftime['datetime_min'] = datetime.utcnow() - timedelta(days=int(LASTDAYS) + 1)
        return q_reftime

    @staticmethod
    def check_response_content(res, product1, product2):
        check_product_1 = False
        check_product_2 = False
        for i in res:
            if product1 in i['data']:
                check_product_1 = True
            if product2 in i['data']:
                check_product_2 = True
            if check_product_1 and check_product_2:
                break
        return check_product_1, check_product_2


    def test_endpoint_without_login(self, client):

        endpoint = API_URI + '/observations'
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED

        endpoint = API_URI + '/observations/1'
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED

    def test_for_dballe_dbtype(self, client):
        headers, _ = self.do_login(client, None, None)
        self.save("auth_header", headers)
        headers = self.get("auth_header")
        dballe_reftime = self.get_reftime('dballe')

        ##### local tests
        # dballe_reftime = {'datetime_max': datetime(2015, 12, 1, 1, 0), 'datetime_min': datetime(2015, 12, 1, 0, 0)}

        q_params = self.get_params_value(client, headers, dballe_reftime)
        self.standard_observed_endpoint_testing(client, headers, q_params)

    def test_for_arkimet_dbtype(self, client):
        headers = self.get("auth_header")
        arki_reftime = self.get_reftime('arkimet')

        ##### local tests
        # arki_reftime = {'datetime_max': datetime(2006, 1, 1, 1, 0), 'datetime_min': datetime(2006, 1, 1, 0, 0)}

        q_params = self.get_params_value(client, headers, arki_reftime)
        self.standard_observed_endpoint_testing(client, headers, q_params)

    def test_for_mixed_dbtype(self, client):
        headers = self.get("auth_header")
        mixed_reftime = self.get_reftime('mixed')

        ##### local tests
        # mixed_reftime = {'datetime_max': datetime(2015, 12, 1, 1, 0), 'datetime_min': datetime(2006, 1, 31, 0, 0)}

        q_params = self.get_params_value(client, headers, mixed_reftime)
        self.standard_observed_endpoint_testing(client, headers, q_params)

    def standard_observed_endpoint_testing(self, client, headers, q_params):

        #### only reftime as argument ####
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'])
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        station_id_example = response_data[0]['station']['id']
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, 'MapStations')
        # check response content
        check_product_1, check_product_2 = self.check_response_content(response_data, q_params['product_1'],
                                                                          q_params['product_2'])
        assert check_product_1 is True
        assert check_product_2 is True

        #### only network as argument ####
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to}&networks={network}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], network=q_params['network'])
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, 'MapStations')
        # check response content
        check_product_1, check_product_2 = self.check_response_content(response_data, q_params['product_1'],
                                                                          q_params['product_2'])
        assert check_product_1 is True
        assert check_product_2 is True
        # check error with random net param
        random_net = self.randomString()
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to}&networks={network}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], network=random_net)
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        assert not response_data

        #### only bounding box as argument ####
        # Italy bounding-box
        bbox = 'latmin:36.6199,lonmin:6.7499,latmax:47.1153,lonmax:18.4802'
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to}&bounding-box={bbox}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], bbox=bbox)
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, 'MapStations')
        # check response content
        check_product_1, check_product_2 = self.check_response_content(response_data, q_params['product_1'],
                                                                          q_params['product_2'])
        assert check_product_1 is True
        assert check_product_2 is True
        # check error with random param
        # random bounding-box
        random_bbox = 'latmin:6.7499,lonmin:36.6199,latmax:18.4802,lonmax:47.1153'
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to}&bounding-box={bbox}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], bbox=random_bbox)
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        assert not response_data

        #### only product as argument ####
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to};product:{product}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], product=q_params['product_1'])
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, 'MapStations')
        # check response content
        check_product_1, check_product_2 = self.check_response_content(response_data, q_params['product_1'],
                                                                       q_params['product_2'])
        assert check_product_1 is True
        assert check_product_2 is False
        # check error with random param
        fake_product = 'B11111'
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to};product:{product}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], product=fake_product)
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        assert not response_data

        #### all arguments ####
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to};product:{product}&bounding-box={bbox}&networks={network}'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'], product=q_params['product_1'],bbox=bbox,network=q_params['network'])
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, 'MapStations')
        # check response content
        check_product_1, check_product_2 = self.check_response_content(response_data, q_params['product_1'],
                                                                       q_params['product_2'])
        assert check_product_1 is True
        assert check_product_2 is False

        #### only stations ####
        endpoint = API_URI + '/observations?q=reftime:>={date_from},<={date_to}&onlyStations=true'.format(
            date_from=q_params['date_from'], date_to=q_params['date_to'])
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, 'MapStations')
        # check response content
        assert 'data' not in response_data[0]

        #### get station data by id ####
        endpoint = API_URI + '/observations/{station_id}?q=reftime:>={date_from},<={date_to}'.format(
            station_id=station_id_example, date_from=q_params['date_from'], date_to=q_params['date_to'])
        r = client.get(endpoint, headers=headers)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # check random network
        endpoint = API_URI + '/observations/{station_id}?q=reftime:>={date_from},<={date_to}&networks={network}'.format(
            station_id=station_id_example,date_from=q_params['date_from'], date_to=q_params['date_to'], network=random_net)
        r = client.get(endpoint, headers=headers)
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND
