# import time
import json

from restapi.services.detect import detector
from restapi.tests import API_URI, BaseTests
from restapi.utilities.htmlcodes import hcodes

# from restapi.utilities.logs import log

__author__ = "Beatrice Chiavarini (b.chiavarini@cineca.it)"


class TestApp(BaseTests):
    def test_endpoint_without_login(self, client, faker):
        endpoint = API_URI + "/datasets"
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED

        endpoint = API_URI + "/datasets/lm5"
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED

        # trying a dataset that doesn't exists
        endpoint = API_URI + "/datasets/" + faker.pystr()
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED

    def test_endpoint_with_login(self, client, faker):

        # create a fake user
        admin_headers, _ = self.do_login(client, None, None)
        schema = self.getDynamicInputSchema(client, "admin/users", admin_headers)
        data = self.buildData(schema)
        # get the group license id for user authorization
        obj = detector.get_debug_instance("sqlalchemy")
        group_lic_to_auth = obj.GroupLicense.query.filter_by(
            name="CCBY_COMPLIANT"
        ).first()
        # get the special dataset id for user authorization
        dataset_to_auth = obj.Datasets.query.filter_by(
            name="sa_dataset_special"
        ).first()

        data["is_active"] = True
        data["group_license"] = [str(group_lic_to_auth.id)]
        data["group_license"] = json.dumps(data["group_license"])
        data["datasets"] = [str(dataset_to_auth.id)]
        data["datasets"] = json.dumps(data["datasets"])

        r = client.post(f"{API_URI}/admin/users", data=data, headers=admin_headers)
        assert r.status_code == 200

        uuid = self.get_content(r)

        # login of the new user
        user_header, _ = self.do_login(client, data.get("email"), data.get("password"))

        self.save("auth_header", user_header)

        endpoint = API_URI + "/datasets"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_OK_BASIC

        # check response type
        response_data = self.get_content(r)
        # print("________all dataset response______ "+str(data))
        assert type(response_data) == list

        endpoint = API_URI + "/datasets/lm5"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_OK_BASIC

        # check response type
        response_data = self.get_content(r)
        # print("________single dataset response______ " + str(data))
        assert type(response_data) == dict

        # trying a dataset that doesn't exists
        endpoint = API_URI + "/datasets/" + faker.pystr()
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

        # trying a dataset in an unauthorized license group
        endpoint = API_URI + "/datasets/sa_dataset"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

        # trying an authorized dataset in an unauthorized license group
        endpoint = API_URI + "/datasets/sa_dataset_special"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_OK_BASIC

        # trying error dataset
        endpoint = API_URI + "/datasets/error"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

        # trying duplicates dataset
        endpoint = API_URI + "/datasets/duplicates"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

        # delete the fake user
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
