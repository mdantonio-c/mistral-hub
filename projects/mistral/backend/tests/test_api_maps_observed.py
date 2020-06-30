import os
from datetime import datetime, timedelta

import dballe
import pytest
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe
from restapi.rest.definition import EndpointResource
from restapi.tests import API_URI, BaseTests
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")


class TestApp(BaseTests):
    BeDballe.LASTDAYS = None

    @staticmethod
    def get_params_value(client, headers, db_type):
        # get an existing dataset of observed data
        obs_dataset = arki.get_obs_datasets(None, None)
        date_from_dt = None
        date_to_dt = None
        for d in obs_dataset:
            network_list = arki.get_observed_dataset_params(d)
            for net in network_list:
                if db_type == "dballe":
                    db = dballe.DB.connect(
                        "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                            engine=engine, user=user, pw=pw, host=host, port=port
                        )
                    )
                    # get a valid reftime for dballe
                    with db.transaction() as tr:
                        for row in tr.query_data({"rep_memo": net}):
                            date_to_dt = datetime(
                                row["year"],
                                row["month"],
                                row["day"],
                                row["hour"],
                                row["min"],
                            ) + timedelta(hours=1)
                            date_from_dt = date_to_dt - timedelta(hours=1)
                            today = datetime.now()
                            last_dballe_date = date_from_dt - timedelta(days=1)
                            time_delta = today - last_dballe_date
                            BeDballe.LASTDAYS = time_delta.days
                            log.debug("lastdays: {}", BeDballe.LASTDAYS)
                            break
                elif db_type == "arkimet":
                    # get a valid reftime for arkimet
                    arki_summary = arki.load_summary(datasets=[d])
                    if (
                        "e" in arki_summary["items"]["summarystats"]
                    ):  # this means that the dataset contains data
                        summary_to = arki_summary["items"]["summarystats"]["e"]
                        date_to_dt = datetime(
                            summary_to[0],
                            summary_to[1],
                            summary_to[2],
                            summary_to[3],
                            summary_to[4],
                        )
                        summary_from = arki_summary["items"]["summarystats"]["b"]
                        date_from_dt = datetime(
                            summary_from[0],
                            summary_from[1],
                            summary_from[2],
                            summary_from[3],
                            summary_from[4],
                        )
                elif db_type == "mixed":
                    db = dballe.DB.connect(
                        "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                            engine=engine, user=user, pw=pw, host=host, port=port
                        )
                    )
                    # get a valid reftime for dballe
                    with db.transaction() as tr:
                        for row in tr.query_data({"rep_memo": net}):
                            date_to_dt = datetime(
                                row["year"],
                                row["month"],
                                row["day"],
                                row["hour"],
                                row["min"],
                            ) + timedelta(hours=1)
                            break

                    # get a valid reftime for arkimet
                    arki_summary = arki.load_summary(datasets=[d])
                    if (
                        "e" in arki_summary["items"]["summarystats"]
                    ):  # this means that the dataset contains data
                        summary_from = arki_summary["items"]["summarystats"]["b"]
                        date_from_dt = datetime(
                            summary_from[0],
                            summary_from[1],
                            summary_from[2],
                            summary_from[3],
                            summary_from[4],
                        )

                if date_from_dt and date_to_dt:
                    date_from = date_from_dt.strftime("%Y-%m-%d %H:%M")
                    date_to = date_to_dt.strftime("%Y-%m-%d %H:%M")
                    break

        if not date_from_dt or not date_to_dt:
            pytest.fail("No valid reftime found")

        for d in obs_dataset:
            endpoint = (
                API_URI
                + "/fields?q=reftime:>={date_from},<={date_to}&datasets={dataset}&SummaryStats=false".format(
                    date_from=date_from, date_to=date_to, dataset=d
                )
            )
            r = client.get(endpoint, headers=headers)
            response_data = TestApp.get_content(r)
            if response_data["items"]:
                log.debug(
                    "api fields db type {} : response data: {}", db_type, response_data
                )
                break

        if not response_data["items"]:
            pytest.fail("No results obtained from DBALLE")

        # from the response pick a network and a product
        params_value = {}
        params_value["date_from"] = date_from
        params_value["date_to"] = date_to
        params_value["network"] = response_data["items"]["network"][0]["code"]
        if len(response_data["items"]["product"]) >= 2:
            params_value["product_1"] = response_data["items"]["product"][0]["code"]
            params_value["product_2"] = response_data["items"]["product"][1]["code"]
        else:
            pytest.fail("Products in DBALLE are less than 2 ")

        log.debug("test_params: {}", params_value)

        return params_value

    @staticmethod
    def check_response_content(res, product1, product2):
        # log.debug('check contents : response data: {}', res)
        check_product_1 = False
        check_product_2 = False
        for i in res:
            for e in i["products"]:
                if e["varcode"] == product1:
                    check_product_1 = True
                if e["varcode"] == product2:
                    check_product_2 = True

            if check_product_1 and check_product_2:
                break
        return check_product_1, check_product_2

    def test_endpoint_without_login(self, client):

        endpoint = API_URI + "/observations"
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED

    def test_for_dballe_dbtype(self, client):
        headers, _ = self.do_login(client, None, None)
        self.save("auth_header", headers)
        headers = self.get("auth_header")

        q_params = self.get_params_value(client, headers, "dballe")
        self.standard_observed_endpoint_testing(client, headers, q_params)

    def test_for_arkimet_dbtype(self, client):
        headers = self.get("auth_header")

        q_params = self.get_params_value(client, headers, "arkimet")
        self.standard_observed_endpoint_testing(client, headers, q_params)

    def test_for_mixed_dbtype(self, client):
        headers = self.get("auth_header")

        q_params = self.get_params_value(client, headers, "mixed")
        self.standard_observed_endpoint_testing(client, headers, q_params)

    def standard_observed_endpoint_testing(self, client, headers, q_params):

        #### only reftime as argument ####
        endpoint = API_URI + "/observations?q=reftime:>={date_from},<={date_to}".format(
            date_from=q_params["date_from"], date_to=q_params["date_to"]
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, "MapStations")
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is True

        #### only network as argument ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to}&networks={network}".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=q_params["network"],
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        station_lat_example = response_data[0]["station"]["lat"]
        station_lon_example = response_data[0]["station"]["lon"]
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, "MapStations")
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is True
        # check error with random net param
        random_net = self.randomString()
        dfrom = q_params["date_from"]
        dto = q_params["date_to"]
        net = random_net
        endpoint = f"{API_URI}/observations?q=reftime:>={dfrom},<={dto}&networks={net}"
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        assert not response_data

        # ### only bounding box as argument ####
        # Italy bounding-box
        bbox = "latmin:36.6199,lonmin:6.7499,latmax:47.1153,lonmax:18.4802"
        endpoint = (
            f"{API_URI}/observations?q=reftime:>={dfrom},<={dto}&bounding_box={bbox}"
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, "MapStations")
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is True
        # check error with random param
        # random bounding-box
        random_bbox = "latmin:6.7499,lonmin:36.6199,latmax:18.4802,lonmax:47.1153"
        date_from = q_params["date_from"]
        date_to = q_params["date_to"]
        endpoint = f"{API_URI}/observations?q=reftime:>={date_from},<={date_to}&bounding_box={random_bbox}"
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        assert not response_data

        # ### only product as argument ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};product:{product}".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                product=q_params["product_1"],
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, "MapStations")
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is False
        # check error with random param
        fake_product = "B11111"
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};product:{product}".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                product=fake_product,
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        assert not response_data

        # ### all arguments ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};product:{product}&bounding_box={bbox}&networks={network}".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                product=q_params["product_1"],
                bbox=bbox,
                network=q_params["network"],
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, "MapStations")
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is False

        # ### only stations ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to}&onlyStations=true".format(
                date_from=q_params["date_from"], date_to=q_params["date_to"]
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # validate response schema
        EndpointResource.validate_input(response_data, "MapStations")
        # check response content
        assert "data" not in response_data[0]

        #### get station details ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to}&networks={network}&lat={lat}&lon={lon}&stationDetails=true".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=q_params["network"],
                lat=station_lat_example,
                lon=station_lon_example,
            )
        )
        r = client.get(endpoint, headers=headers)
        # check response code
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # check random network
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to}&networks={network}&lat={lat}&lon={lon}&stationDetails=true".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=random_net,
                lat=station_lat_example,
                lon=station_lon_example,
            )
        )
        r = client.get(endpoint, headers=headers)
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND
        # check missing params
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to}&networks={network}&stationDetails=true".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=q_params["network"],
            )
        )
        r = client.get(endpoint, headers=headers)
        # check response code
        assert r.status_code == hcodes.HTTP_BAD_REQUEST
