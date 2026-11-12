"""Test di integrazione dell'endpoint pubblico del catalogo dataset ARCO.

Il modulo verifica che la vista catalogo specifica di ARCO (GET /api/arco/datasets)
resti raggiungibile e restituisca i dati nella forma attesa dai client API.
"""

import json
from unittest.mock import MagicMock

import pytest

from mistral.endpoints.arco import DatasetSchema
from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class MockAttribution:
    """Sostituto semplice delle righe Attribution restituite da SQLAlchemy."""

    def __init__(self, name, descr, url):
        """Salva i soli campi di attribution letti dallo schema ARCO."""
        self.name = name
        self.descr = descr
        self.url = url


class MockLicense:
    """Sostituto semplice delle righe License restituite da SQLAlchemy."""

    def __init__(self, name, descr, url, group_license=None):
        """Salva i soli campi di license letti dallo schema ARCO."""
        self.name = name
        self.descr = descr
        self.url = url
        self.group_license = group_license


class MockGroupLicense:
    """Sostituto semplice della relazione group license usata dallo schema ARCO."""

    def __init__(self, name, descr):
        """Salva i campi del group license esposti nelle risposte del catalogo."""
        self.name = name
        self.descr = descr


def test_arco_catalog_returns_dataset_metadata(
    client: FlaskClient,
    monkeypatch,
) -> None:
    """Verifica che il catalogo ARCO unisca metadati S3 e SQL in un unico dataset.

    L'endpoint GET /api/arco/datasets (ArcoDatasetsResource.get) e pubblico: la
    richiesta non porta credenziali e il test non crea ne ruota alcuna access key.
    """
    # arrange
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
    mock_s3 = MagicMock()
    mock_s3.client.list_objects_v2.return_value = {
        "CommonPrefixes": [{"Prefix": "ww3.zarr/"}, {"Prefix": "logs/"}],
        "IsTruncated": False,
    }
    mock_s3.client.get_object.return_value = {
        "Body": MagicMock(read=lambda: bytes(json.dumps(dataset_body), "utf-8"))
    }
    monkeypatch.setattr("mistral.connectors.s3.get_instance", lambda: mock_s3)

    group_license = MockGroupLicense(
        name="Open Licenses",
        descr="Open data license group",
    )
    monkeypatch.setattr(
        "mistral.endpoints.arco.sqlalchemy.get_instance",
        lambda: MagicMock(
            Attribution=MagicMock(
                query=MagicMock(
                    all=lambda: [
                        MockAttribution(
                            "FBK",
                            "Fondazione Bruno Kessler",
                            "https://fbk.eu",
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
                            group_license=group_license,
                        )
                    ]
                )
            ),
        ),
    )

    # act
    response = client.get(f"{API_URI}/arco/datasets")

    # assert
    assert response.status_code == 200
    data = response.json
    assert len(data) == 1

    dataset = data[0]
    assert dataset["id"] == "ww3.zarr"
    assert dataset["name"] == "WW3 Forecast"
    assert dataset["format"] == "zarr"
    assert dataset["source"] == "arco"
    assert dataset["category"] == "forecast"
    assert dataset["is_public"] is True
    assert dataset["authorized"] is True
    assert dataset["bounding"] == (
        "POLYGON((10.0 45.0, 15.0 45.0, 15.0 50.0, 10.0 50.0, 10.0 45.0))"
    )
    assert dataset["attribution"] == "FBK"
    assert dataset["attribution_description"] == "Fondazione Bruno Kessler"
    assert dataset["attribution_url"] == "https://fbk.eu"
    assert dataset["license"] == "CCBY"
    assert dataset["license_description"] == "Creative Commons BY"
    assert dataset["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert dataset["group_license"] == "Open Licenses"
    assert dataset["group_license_description"] == "Open data license group"

    schema = DatasetSchema()
    result = schema.load(dataset)
    assert result["id"] == dataset["id"]