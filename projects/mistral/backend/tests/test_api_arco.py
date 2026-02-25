import json
from unittest.mock import MagicMock

from mistral.endpoints.arco import DatasetSchema
from mistral.tests.test_api_access_key import make_basic_auth
from restapi.services.authentication import BaseAuthentication
from restapi.tests import API_URI, BaseTests, FlaskClient

BUCKET_NAME = "arco"
UNKNOWN = "UNKNOWN"


class MockAttribution:
    def __init__(self, name, descr, url):
        self.name = name
        self.descr = descr
        self.url = url


class MockLicense:
    def __init__(self, name, descr, url, group_license=None):
        self.name = name
        self.descr = descr
        self.url = url
        self.group_license = group_license


class MockGroupLicense:
    def __init__(self, name, descr):
        self.name = name
        self.descr = descr


class TestArcoAPI(BaseTests):
    def test_01_arco_unauthorized(self, client: FlaskClient):
        resp = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup")
        assert resp.status_code == 401

    def test_02_arco_authorized(
        self, client: FlaskClient, fresh_access_key, monkeypatch
    ):
        headers_auth, valid_key = fresh_access_key
        email = BaseAuthentication.default_user

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
        email = BaseAuthentication.default_user

        # Mock dataset zattrs
        dataset_body = {
            "metadata": {
                ".zattrs": {
                    "southernmost_latitude": 45,
                    "northernmost_latitude": 50,
                    "westernmost_longitude": 10,
                    "easternmost_longitude": 15,
                    "product_name": "WW3 Forecast",
                    "category": "forecast",
                    "attribution": "FBK",
                    "license": "CCBY",
                    "is_public": True,
                    "authorized": True,
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

        # Mock DB
        group_lic = MockGroupLicense(
            name="Open Licenses", descr="Open data license group"
        )
        monkeypatch.setattr(
            "mistral.endpoints.arco.sqlalchemy.get_instance",
            lambda: MagicMock(
                Attribution=MagicMock(
                    query=MagicMock(
                        all=lambda: [
                            MockAttribution(
                                "FBK", "Fondazione Bruno Kessler", "https://fbk.eu"
                            )
                        ]
                    )
                ),
                License=MagicMock(
                    query=MagicMock(
                        all=lambda: [
                            MockLicense(
                                "CCBY",
                                "Creative Commons BY",
                                "https://creativecommons.org/licenses/by/4.0/",
                                group_license=group_lic,
                            )
                        ]
                    )
                ),
            ),
        )

        headers = make_basic_auth(email, valid_key)
        resp = client.get(f"{API_URI}/arco/datasets", headers=headers)

        assert resp.status_code == 200

        data = resp.json
        assert len(data) == 1

        ds = data[0]

        # Basic fields
        assert ds["id"] == "ww3"
        assert ds["name"] == "WW3 Forecast"
        assert ds["format"] == "zarr"
        assert ds["source"] == "arco"
        assert ds["category"] == "forecast"
        assert ds["is_public"] is True
        assert ds["authorized"] is True

        # Bounding WKT
        assert "bounding" in ds
        expected_wkt = (
            "POLYGON((10.0 45.0, 15.0 45.0, 15.0 50.0, 10.0 50.0, 10.0 45.0))"
        )
        assert ds["bounding"] == expected_wkt

        # Attribution from DB
        assert ds["attribution"] == "FBK"
        assert ds["attribution_description"] == "Fondazione Bruno Kessler"
        assert ds["attribution_url"] == "https://fbk.eu"

        # License from DB
        assert ds["license"] == "CCBY"
        assert ds["license_description"] == "Creative Commons BY"
        assert ds["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
        assert ds["group_license"] == "Open Licenses"
        assert ds["group_license_description"] == "Open data license group"

        # Validate schema
        schema = DatasetSchema()
        result = schema.load(ds)  # Will raise ValidationError if invalid
        assert result["id"] == ds["id"]
