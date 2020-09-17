# import time
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

        headers, _ = self.do_login(client, None, None)
        self.save("auth_header", headers)

        endpoint = API_URI + "/datasets"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_OK_BASIC

        endpoint = API_URI + "/datasets/lm5"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_OK_BASIC

        # trying a dataset that doesn't exists
        endpoint = API_URI + "/datasets/" + faker.pystr()
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

    def test_api_response_type(self, client):
        endpoint = API_URI + "/datasets"
        r = client.get(endpoint, headers=self.get("auth_header"))
        response_data = self.get_content(r)
        # print("________all dataset response______ "+str(data))
        assert type(response_data) == list

        endpoint = API_URI + "/datasets/lm5"
        r = client.get(endpoint, headers=self.get("auth_header"))
        response_data = self.get_content(r)
        # print("________single dataset response______ " + str(data))
        assert type(response_data) == dict

    def test_error_duplicates_datasets(self, client):
        endpoint = API_URI + "/datasets/error"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

        endpoint = API_URI + "/datasets/duplicates"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

    # ##### TO DO: correct this method that at the moment raises an error
    # def test_schema (self,client):
    #     endpoint = API_URI + '/datasets'
    # r_schema = self.getInputSchema(
    #     client, endpoint, headers=self.get("auth_header"))
    #     #print("________schema______ " + str(r_schema))
    #     validation=self.validate_input(r_schema, 'Datasets')
    #     assert validation==True
