"""Integration tests for authorization rules on private opendata datasets."""

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
    """Verify that private opendata endpoints reject both anonymous and unauthorized users."""
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
    """Verify that a user explicitly authorized on a private dataset can list and download it."""
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
    file_response = client.get(file_endpoint, headers=user.headers)

    # assert
    list_content = BaseTests().get_content(list_response)
    assert list_response.status_code == 200
    assert len(list_content) == 1
    assert list_content[0]["filename"] == result.filename
    assert download_response.status_code == 200
    assert download_response.get_data(as_text=True) == result.content
    download_response.close()
    assert file_response.status_code == 200
    assert file_response.get_data(as_text=True) == result.content
    file_response.close()