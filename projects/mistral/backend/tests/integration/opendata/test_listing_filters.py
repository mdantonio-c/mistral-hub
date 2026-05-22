"""Integration tests for opendata listing filters on dataset-specific file catalogs."""

from datetime import timedelta
from uuid import uuid4

import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

from .support import create_listing_env


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_listing_unknown_dataset_returns_404(client: FlaskClient) -> None:
    """Verify that listing opendata for an unknown dataset id returns 404."""
    # arrange
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/datasets/{dataset_name}/opendata"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404


def test_listing_filters_by_run_returns_matching_package(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that a run filter returns only the package generated for that run."""
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/datasets/{dataset.arkimet_id}/opendata?q=run:MINUTE,00:00"
    )

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert len(content) == 1
    assert content[0]["filename"] == seeded_results[0].filename


def test_listing_filters_by_reftime_returns_matching_package(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that a reftime window returns only the package inside that window."""
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    query_from = (seeded_results[0].reftime + timedelta(minutes=1)).strftime(
        "%Y-%m-%d %H:%M"
    )
    query_to = seeded_results[1].reftime.strftime("%Y-%m-%d %H:%M")
    endpoint = (
        f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
        f"?q=reftime:>={query_from},<={query_to}"
    )

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert len(content) == 1
    assert content[0]["filename"] == seeded_results[1].filename


def test_listing_filters_by_reftime_and_run_can_exclude_results(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that combined reftime and run filters can legitimately return an empty listing."""
    # arrange
    dataset, seeded_results = create_listing_env(client, cleanup_registry)
    query_from = seeded_results[0].reftime.strftime("%Y-%m-%d %H:%M")
    query_to = (seeded_results[1].reftime - timedelta(minutes=1)).strftime(
        "%Y-%m-%d %H:%M"
    )
    endpoint = (
        f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
        f"?q=reftime:>={query_from},<={query_to};run:MINUTE,12:00"
    )

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 200
    assert content == []