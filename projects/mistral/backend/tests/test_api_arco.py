import json
from unittest.mock import MagicMock

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

    def test_03_arco_with_datasets(
        self, client: FlaskClient, fresh_access_key, monkeypatch
    ):
        headers_auth, valid_key = fresh_access_key
        email = "admin@nomail.org"

        # Mock dataset
        dataset_body = {
            "metadata": {
                ".zattrs": {
                    "southernmost_latitude": 45,
                    "northernmost_latitude": 50,
                    "westernmost_longitude": 10,
                    "easternmost_longitude": 15,
                    "other_attr": "value",
                }
            }
        }

        # Mock S3
        mock_s3 = MagicMock()
        # list_objects_v2 returns an object in the bucket
        mock_s3.client.list_objects_v2.return_value = {
            "CommonPrefixes": [{"Prefix": "ww3.zarr/"}, {"Prefix": "logs/"}],
            "IsTruncated": False,
        }

        # get_object returns .zmetadata
        mock_s3.client.get_object.return_value = {
            "Body": MagicMock(read=lambda: bytes(json.dumps(dataset_body), "utf-8"))
        }

        monkeypatch.setattr("mistral.connectors.s3.get_instance", lambda: mock_s3)

        headers = make_basic_auth(email, valid_key)
        resp = client.get(f"{API_URI}/arco/datasets", headers=headers)

        assert resp.status_code == 200

        data = resp.json
        assert len(data) == 1

        ds = data[0]
        assert ds["id"] == "ww3"
        assert ds["folder"] == "ww3.zarr"
        assert ds["fileformat"] == "zarr"
        assert "bounding" in ds
        assert ds["attrs"]["southernmost_latitude"] == 45
        assert ds["attrs"]["other_attr"] == "value"
