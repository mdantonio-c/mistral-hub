from unittest.mock import MagicMock

import boto3
from mistral.tests.test_api_access_key import make_basic_auth
from restapi.tests import API_URI, BaseTests, FlaskClient

BUCKET_NAME = "arco"


class TestArcoAPI(BaseTests):
    def test_01_arco_unauthorized(self, client: FlaskClient):
        resp = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup")
        assert resp.status_code == 401

    def test_02_arco_authorized(
        self, client: FlaskClient, fresh_access_key, monkeypatch
    ):
        headers_auth, valid_key = fresh_access_key
        # using admin user?
        email = "admin@nomail.org"

        # Mock S3 get_object
        mock_s3 = MagicMock()
        mock_s3.client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b'{"zarr_format": 2}')
        }

        monkeypatch.setattr("mistral.connectors.s3.get_instance", lambda: mock_s3)

        headers = make_basic_auth(email, valid_key)
        resp = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup", headers=headers)

        assert resp.status_code == 200
        assert b"zarr_format" in resp.data
