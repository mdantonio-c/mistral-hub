"""Test di integrazione sul download opendata di un dataset e dei singoli file.

Esercitano GET /api/opendata/<dataset_id>/download e GET /api/opendata/<filename>
(endpoints/opendata.py).
"""

from uuid import uuid4

import pytest
from mistral.endpoints import OPENDATA_DIR
from mistral.tests.helpers.cleanup import CleanupRegistry
from mistral.tests.helpers.datasets import create_test_dataset
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from .support import FakeOpendataResult, create_download_env, zip_filenames


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def _run_teardown_and_assert_seeded_files_removed(
    cleanup_registry: CleanupRegistry,
    seeded_results: list[FakeOpendataResult],
) -> None:
    """Esegue il teardown registrato e verifica che tutti i file creati spariscano.

    Prima controlla che i file in ``OPENDATA_DIR`` esistano ancora, poi lancia il
    ``cleanup_registry`` e verifica che non ne resti nessuno.
    """
    output_paths = [OPENDATA_DIR / result.filename for result in seeded_results]
    missing_paths = [path for path in output_paths if not path.is_file()]
    assert not missing_paths, f"Seeded files missing before teardown: {missing_paths}"

    cleanup_registry.run()

    remaining_paths = [path for path in output_paths if path.exists()]
    assert not remaining_paths, f"Seeded files left after teardown: {remaining_paths}"


def test_dataset_download_unknown_dataset_returns_404(client: FlaskClient) -> None:
    """Verifica che il download da un dataset inesistente risponda 404.

    Esercita GET /api/opendata/<dataset_id>/download.
    """
    # arrange
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/opendata/{dataset_name}/download"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404


def test_dataset_download_rejects_invalid_reftime(
    client: FlaskClient,
) -> None:
    """Verifica che il download rifiuti con 400 un reftime in formato non valido.

    Esercita la validazione dei parametri di GET /api/opendata/<dataset_id>/download:
    avviene prima della ricerca del dataset, quindi basta un dataset inesistente.
    """
    # arrange
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/opendata/{dataset_name}/download?reftime=2020/31/01"

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 400
    assert content["reftime"]


def test_dataset_download_rejects_invalid_run(
    client: FlaskClient,
) -> None:
    """Verifica che il download rifiuti con 400 un run in formato non valido.

    Esercita la validazione dei parametri di GET /api/opendata/<dataset_id>/download:
    avviene prima della ricerca del dataset, quindi basta un dataset inesistente.
    """
    # arrange
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/opendata/{dataset_name}/download?run=2500"

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 400
    assert "run format not supported" in content["_schema"][0]


def test_dataset_download_returns_404_when_no_opendata_exist(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un dataset pubblico senza opendata dia 404 invece di uno zip vuoto.

    Esercita GET /api/opendata/<dataset_id>/download.
    """
    # arrange
    dataset = create_test_dataset(
        sqlalchemy.get_instance(),
        cleanup_registry,
        is_public=True,
    )
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"

    # act
    response = client.get(endpoint)

    # assert
    content = BaseTests().get_content(response)
    assert response.status_code == 404
    assert "No opendata found" in content


def test_dataset_download_returns_404_for_unmatched_reftime(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un filtro reftime senza file corrispondenti risponda 404.

    Esercita GET /api/opendata/<dataset_id>/download?reftime=....
    """
    # arrange
    dataset, _ = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download?reftime=20200103"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404


def test_dataset_download_returns_404_for_unmatched_run(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un filtro run senza file corrispondenti risponda 404.

    Esercita GET /api/opendata/<dataset_id>/download?run=....
    """
    # arrange
    dataset, _ = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download?run=15:00"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404


def test_dataset_download_returns_404_for_unmatched_reftime_and_run(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che filtri combinati rispondano 404 se nessun file li soddisfa entrambi.

    Esercita GET /api/opendata/<dataset_id>/download con reftime e run insieme.
    """
    # arrange
    dataset, _ = create_download_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/opendata/{dataset.arkimet_id}/download"
        "?reftime=2020-01-02&run=12:00"
    )

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404


def test_dataset_download_zips_all_results(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che il download senza filtri restituisca tutti i file in uno zip.

    Esercita GET /api/opendata/<dataset_id>/download e controlla anche il nome
    dello zip e la rimozione dei file al teardown.
    """
    # arrange
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"

    # act
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    zipfile_name = (
        response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert zipfile_name == f"opendata_{dataset.arkimet_id}.zip"
    assert zip_filenames(response) == sorted(
        result.filename for result in seeded_results
    )
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_dataset_download_zips_results_filtered_by_reftime(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che il filtro reftime limiti lo zip ai soli file corrispondenti.

    Esercita GET /api/opendata/<dataset_id>/download?reftime=....
    """
    # arrange
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/opendata/{dataset.arkimet_id}/download?reftime=2020-01-01"
    )

    # act
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    zipfile_name = (
        response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert zipfile_name == f"opendata_{dataset.arkimet_id}_reftime_2020-01-01.zip"
    assert zip_filenames(response) == sorted(
        result.filename for result in seeded_results[:2]
    )
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_dataset_download_zips_results_filtered_by_run(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che il filtro run limiti lo zip ai soli file corrispondenti.

    Esercita GET /api/opendata/<dataset_id>/download?run=....
    """
    # arrange
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download?run=00:00"

    # act
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    zipfile_name = (
        response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert zipfile_name == f"opendata_{dataset.arkimet_id}_run_00:00.zip"
    assert zip_filenames(response) == sorted(
        result.filename for result in (seeded_results[0], seeded_results[2])
    )
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_dataset_download_returns_single_file_when_query_matches_one_result(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un unico risultato venga inviato direttamente, senza zip.

    Esercita GET /api/opendata/<dataset_id>/download con reftime e run che
    selezionano un solo file.
    """
    # arrange
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/opendata/{dataset.arkimet_id}/download"
        "?reftime=20200101&run=12:00"
    )

    # act
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    assert response.status_code == 200
    assert response.mimetype == "application/octet-stream"
    assert response.get_data(as_text=True) == seeded_results[1].content
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_file_download_unknown_file_returns_404(client: FlaskClient) -> None:
    """Verifica che il download diretto di un file sconosciuto risponda 404.

    Esercita GET /api/opendata/<filename>.
    """
    # arrange
    endpoint = f"{API_URI}/opendata/{uuid4().hex}.grib"

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 404