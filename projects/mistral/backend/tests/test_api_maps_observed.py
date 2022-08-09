from datetime import datetime, timedelta

import dballe
import pytest
from faker import Faker
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.dballe import BeDballe
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient
from restapi.utilities.logs import log

# user = os.environ.get("ALCHEMY_USER")
# pw = os.environ.get("ALCHEMY_PASSWORD")
# host = os.environ.get("ALCHEMY_HOST")
# engine = os.environ.get("ALCHEMY_DBTYPE")
# port = os.environ.get("ALCHEMY_PORT")


class TestApp(BaseTests):
    @staticmethod
    def get_params_value(client, headers, db_type):

        db = sqlalchemy.get_instance()
        # get an existing dataset of observed data
        obs_dataset = arki.get_obs_datasets(None, None)
        date_from_dt = None
        date_to_dt = None
        for d in obs_dataset:
            network_list = arki.get_observed_dataset_params(d)
            for net in network_list:
                if db_type == "dballe":
                    db_dballe = dballe.DB.connect(
                        "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                            engine=db.variables.get("dbtype"),
                            user=db.variables.get("user"),
                            pw=db.variables.get("password"),
                            host=db.variables.get("host"),
                            port=db.variables.get("port"),
                        )
                    )
                    # get a valid reftime for dballe
                    with db_dballe.transaction() as tr:
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
                    db_dballe = dballe.DB.connect(
                        "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                            engine=db.variables.get("dbtype"),
                            user=db.variables.get("user"),
                            pw=db.variables.get("password"),
                            host=db.variables.get("host"),
                            port=db.variables.get("port"),
                        )
                    )
                    # get a valid reftime for dballe
                    with db_dballe.transaction() as tr:
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
                + "/fields?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&datasets={dataset}&SummaryStats=false".format(
                    date_from=date_from, date_to=date_to, dataset=d
                )
            )
            r = client.get(endpoint, headers=headers)

            assert r.status_code == 200

            response_data = TestApp.get_content(r)
            assert isinstance(response_data, dict)
            if response_data["items"]:
                log.debug(
                    "api fields db type {} : response data: {}", db_type, response_data
                )
                break

        assert isinstance(response_data, dict)
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
        for i in res["data"]:
            for e in i["prod"]:
                if e["var"] == product1:
                    check_product_1 = True
                if e["var"] == product2:
                    check_product_2 = True

            if check_product_1 and check_product_2:
                break
        return check_product_1, check_product_2

    def test_endpoint_without_login(self, client: FlaskClient) -> None:

        endpoint = API_URI + "/observations?q=license:CCBY_COMPLIANT"
        r = client.get(endpoint)
        assert r.status_code == 401

    def test_endpoint_without_license(self, client: FlaskClient) -> None:

        endpoint = API_URI + "/observations"
        r = client.get(endpoint)
        assert r.status_code == 400

    def test_for_dballe_dbtype(self, client: FlaskClient, faker: Faker) -> None:
        # create a fake user and login with it

        uuid, data = self.create_user(
            client, {"open_dataset": True, "allowed_obs_archive": True}
        )
        # Will be used to delete the user after the tests
        self.save("fake_uuid", uuid)
        user_header, _ = self.do_login(client, data.get("email"), data.get("password"))

        self.save("auth_header", user_header)
        # headers, _ = self.do_login(client, None, None)
        # self.save("auth_header", headers)

        q_params = self.get_params_value(client, user_header, "dballe")
        self.standard_observed_endpoint_testing(
            client, faker, user_header, q_params, db_type="dballe"
        )

    def test_for_arkimet_dbtype(self, client: FlaskClient, faker: Faker) -> None:
        headers = self.get("auth_header")

        q_params = self.get_params_value(client, headers, "arkimet")
        self.standard_observed_endpoint_testing(
            client, faker, headers, q_params, db_type="arkimet"
        )

    def test_for_mixed_dbtype(self, client: FlaskClient, faker: Faker) -> None:
        headers = self.get("auth_header")

        q_params = self.get_params_value(client, headers, "mixed")
        self.standard_observed_endpoint_testing(
            client, faker, headers, q_params, db_type="mixed"
        )

        uuid = self.get("fake_uuid")
        self.delete_user(client, uuid)

    def standard_observed_endpoint_testing(
        self, client, faker, headers, q_params, db_type
    ):

        # only reftime as argument
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT".format(
                date_from=q_params["date_from"], date_to=q_params["date_to"]
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert isinstance(response_data, dict)
        # check response code
        assert r.status_code == 200
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is True

        if db_type != "dballe":
            # test reftime with only date to
            endpoint = (
                API_URI
                + "/observations?q=reftime:<={date_to};license:CCBY_COMPLIANT".format(
                    date_to=q_params["date_to"]
                )
            )
            r = client.get(endpoint, headers=headers)
            # check response code
            assert r.status_code == 200

        if db_type != "arkimet":
            # test reftime with only date from
            endpoint = (
                API_URI
                + "/observations?q=reftime:>={date_from};license:CCBY_COMPLIANT".format(
                    date_from=q_params["date_from"]
                )
            )
            r = client.get(endpoint, headers=headers)
            response_data = self.get_content(r)
            assert r.status_code == 200

        # only network as argument
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&networks={network}".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=q_params["network"],
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert isinstance(response_data, dict)
        station_lat_example = response_data["data"][0]["stat"]["lat"]
        station_lon_example = response_data["data"][0]["stat"]["lon"]
        # check response code
        assert r.status_code == 200
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is True
        # check error with random net param
        random_net = faker.pystr()
        dfrom = q_params["date_from"]
        dto = q_params["date_to"]
        endpoint = f"{API_URI}/observations?q=reftime:>={dfrom},<={dto};license:CCBY_COMPLIANT&networks={random_net}"
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert r.status_code == 404

        # ### only bounding box as argument ####
        # Italy bounding-box
        lonmin = 6.7499
        latmin = 36.6199
        latmax = 47.1153
        lonmax = 18.4802
        endpoint = f"{API_URI}/observations?q=reftime:>={dfrom},<={dto};license:CCBY_COMPLIANT&lonmin={lonmin}&lonmax={lonmax}&latmin={latmin}&latmax={latmax}"
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert isinstance(response_data, dict)
        # check response code
        assert r.status_code == 200
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is True
        # check error with random param
        # random bounding-box
        rand_latmin = 6.7499
        rand_lonmin = 36.6199
        rand_latmax = 18.4802
        rand_lonmax = 47.1153
        date_from = q_params["date_from"]
        date_to = q_params["date_to"]
        endpoint = f"{API_URI}/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&lonmin={rand_lonmin}&lonmax={rand_lonmax}&latmin={rand_latmin}&latmax={rand_latmax}"
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert isinstance(response_data, dict)
        assert r.status_code == 200
        assert not response_data["data"]

        # ### only product as argument ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};product:{product};license:CCBY_COMPLIANT".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                product=q_params["product_1"],
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == 200
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
            + "/observations?q=reftime:>={date_from},<={date_to};product:{product};license:CCBY_COMPLIANT".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                product=fake_product,
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert isinstance(response_data, dict)
        assert r.status_code == 200
        assert not response_data["data"]

        # ### all arguments ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};product:{product};license:CCBY_COMPLIANT&&lonmin={lonmin}&lonmax={lonmax}&latmin={latmin}&latmax={latmax}&networks={network}".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                product=q_params["product_1"],
                lonmin=lonmin,
                lonmax=lonmax,
                latmin=latmin,
                latmax=latmax,
                network=q_params["network"],
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        # check response code
        assert r.status_code == 200
        # check response content
        check_product_1, check_product_2 = self.check_response_content(
            response_data, q_params["product_1"], q_params["product_2"]
        )
        assert check_product_1 is True
        assert check_product_2 is False

        # ### only stations ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&onlyStations=true".format(
                date_from=q_params["date_from"], date_to=q_params["date_to"]
            )
        )
        r = client.get(endpoint, headers=headers)
        response_data = self.get_content(r)
        assert isinstance(response_data, dict)
        # check response code
        assert r.status_code == 200
        # check response content
        assert not response_data["data"][0]["prod"]

        # get station details ####
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&networks={network}&lat={lat}&lon={lon}&stationDetails=true".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=q_params["network"],
                lat=station_lat_example,
                lon=station_lon_example,
            )
        )
        r = client.get(endpoint, headers=headers)
        # check response code
        assert r.status_code == 200
        # check random network
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&networks={network}&lat={lat}&lon={lon}&stationDetails=true".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=random_net,
                lat=station_lat_example,
                lon=station_lon_example,
            )
        )
        r = client.get(endpoint, headers=headers)
        # check response code
        assert r.status_code == 404
        # check missing params
        endpoint = (
            API_URI
            + "/observations?q=reftime:>={date_from},<={date_to};license:CCBY_COMPLIANT&networks={network}&stationDetails=true".format(
                date_from=q_params["date_from"],
                date_to=q_params["date_to"],
                network=q_params["network"],
            )
        )
        r = client.get(endpoint, headers=headers)
        # check response code
        assert r.status_code == 400
