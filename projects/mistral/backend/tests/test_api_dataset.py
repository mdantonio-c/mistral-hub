# import time
import json

from restapi.services.detect import detector
from restapi.tests import API_URI, BaseTests
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log

__author__ = "Beatrice Chiavarini (b.chiavarini@cineca.it)"


class TestApp(BaseTests):
    def test_endpoint_without_login(self, client, faker):
        endpoint = API_URI + "/datasets"
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_OK_BASIC
        # check that there aren't authorization specs
        data = self.get_content(r)
        assert "authorized" not in data[0]

        endpoint = API_URI + "/datasets/lm5"
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_OK_BASIC

        # trying a dataset that doesn't exists
        endpoint = API_URI + "/datasets/" + faker.pystr()
        r = client.get(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_NOTFOUND

    def test_endpoint_with_login(self, client, faker):

        # create a fake user
        admin_headers, _ = self.do_login(client, None, None)
        schema = self.getDynamicInputSchema(client, "admin/users", admin_headers)
        data = self.buildData(schema)
        # get the group license id for user authorization
        obj = detector.get_debug_instance("sqlalchemy")
        # get the special dataset id for user authorization
        dataset_to_auth = obj.Datasets.query.filter_by(
            name="sa_dataset_special"
        ).first()

        # create a fake copyright group
        fake_private_group = obj.GroupLicense(
            name="private_group", descr="mock private_group", is_public=False
        )
        obj.session.add(fake_private_group)
        obj.session.flush()
        # create a fake copyright license
        fake_private_lic = obj.License(
            name="private auth license",
            descr="mock private license",
            group_license_id=fake_private_group.id,
        )
        obj.session.add(fake_private_lic)
        obj.session.flush()
        # link the dataset to the fake copyright license
        unauth_dataset = obj.Datasets.query.filter_by(name="sa_dataset").first()
        unauth_dataset.license_id = fake_private_lic.id
        obj.session.add(unauth_dataset)
        dataset_to_auth.license_id = fake_private_lic.id
        obj.session.add(dataset_to_auth)
        obj.session.commit()

        data["is_active"] = True
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
        assert r.status_code == hcodes.HTTP_OK_BASIC
        response_data = self.get_content(r)
        # the dataset is not public
        assert response_data["is_public"] is False
        # the user cannot access
        assert response_data["authorized"] is False

        # trying an authorized dataset in an unauthorized license group
        endpoint = API_URI + "/datasets/sa_dataset_special"
        r = client.get(endpoint, headers=self.get("auth_header"))
        assert r.status_code == hcodes.HTTP_OK_BASIC
        response_data = self.get_content(r)
        # the dataset is not public
        assert response_data["is_public"] is False
        # the user can access
        assert response_data["authorized"] is True

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

        # delete the mock licence and licence group
        obj.session.delete(fake_private_group)
        obj.session.delete(fake_private_lic)

        # get a new existing license to the mock private datasets
        correct_license = obj.License.query.filter_by().first()
        unauth_dataset.license_id = correct_license.id
        obj.session.add(unauth_dataset)
        dataset_to_auth.license_id = correct_license.id
        obj.session.add(dataset_to_auth)

        obj.session.commit()
