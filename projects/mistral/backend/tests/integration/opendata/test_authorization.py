"""Test di integrazione sulle regole di autorizzazione dei dataset opendata privati.

Esercitano gli endpoint di endpoints/opendata.py: GET /api/datasets/<id>/opendata,
GET /api/opendata/<id>/download e GET /api/opendata/<filename>.
"""

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

from .support import authorize_user_for_dataset, create_private_opendata_env


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_private_dataset_endpoints_reject_unauthorized_access(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che gli endpoint opendata privati rifiutino anonimi e non autorizzati.

    Tutti e tre gli endpoint rispondono 401 sia senza login sia con un utente
    autenticato ma non collegato al dataset privato.
    """
    # arrange
    _, dataset, user, result = create_private_opendata_env(
        client,
        cleanup_registry,
    )
    list_endpoint = f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
    download_endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"
    file_endpoint = f"{API_URI}/opendata/{result.filename}"

    # act
    anonymous_list = client.get(list_endpoint)
    logged_list = client.get(list_endpoint, headers=user.headers)
    anonymous_download = client.get(download_endpoint)
    logged_download = client.get(download_endpoint, headers=user.headers)
    anonymous_file_download = client.get(file_endpoint)
    logged_file_download = client.get(file_endpoint, headers=user.headers)

    # assert
    assert anonymous_list.status_code == 401
    assert logged_list.status_code == 401
    assert anonymous_download.status_code == 401
    assert logged_download.status_code == 401
    assert anonymous_file_download.status_code == 401
    assert logged_file_download.status_code == 401


def test_private_dataset_endpoints_allow_authorized_user(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un utente autorizzato possa elencare e scaricare il dataset privato.

    L'utente viene collegato al dataset (``user.datasets``); elenco, download del
    dataset e download diretto del file rispondono 200 con il contenuto atteso.
    """
    # arrange
    db, dataset, user, result = create_private_opendata_env(
        client,
        cleanup_registry,
    )
    authorize_user_for_dataset(db, user.uuid, dataset.id)
    list_endpoint = f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
    download_endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"
    file_endpoint = f"{API_URI}/opendata/{result.filename}"

    # act
    list_response = client.get(list_endpoint, headers=user.headers)
    download_response = client.get(download_endpoint, headers=user.headers)
    cleanup_registry.add(download_response.close)
    file_response = client.get(file_endpoint, headers=user.headers)
    cleanup_registry.add(file_response.close)

    # assert
    list_content = BaseTests().get_content(list_response)
    assert list_response.status_code == 200
    assert len(list_content) == 1
    assert list_content[0]["filename"] == result.filename
    assert download_response.status_code == 200
    assert download_response.get_data(as_text=True) == result.content
    assert file_response.status_code == 200
    assert file_response.get_data(as_text=True) == result.content