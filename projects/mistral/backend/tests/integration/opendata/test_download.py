"""Integration tests for opendata dataset downloads and direct file downloads."""

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
    """Run the registered teardown and verify every seeded file disappears."""
    output_paths = [OPENDATA_DIR / result.filename for result in seeded_results]
    missing_paths = [path for path in output_paths if not path.is_file()]
    assert not missing_paths, f"Seeded files missing before teardown: {missing_paths}"

    cleanup_registry.run()

    remaining_paths = [path for path in output_paths if path.exists()]
    assert not remaining_paths, f"Seeded files left after teardown: {remaining_paths}"


def test_dataset_download_unknown_dataset_returns_404(client: FlaskClient) -> None:
    """Verify that downloading from an unknown dataset id returns 404."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/opendata/{dataset_name}/download"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 404


def test_dataset_download_rejects_invalid_reftime(
    client: FlaskClient,
) -> None:
    """Verify that the download endpoint validates reftime query formatting."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/opendata/{dataset_name}/download?reftime=2020/31/01"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    content = BaseTests().get_content(response)
    # Verifichiamo che la risposta rifiuti input non validi con un errore client
    # esplicito prima di usare il payload.
    assert response.status_code == 400
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert content["reftime"]


def test_dataset_download_rejects_invalid_run(
    client: FlaskClient,
) -> None:
    """Verify that the download endpoint validates run query formatting."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset_name = f"missing_{uuid4().hex}"
    endpoint = f"{API_URI}/opendata/{dataset_name}/download?run=2500"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    content = BaseTests().get_content(response)
    # Verifichiamo che la risposta rifiuti input non validi con un errore client
    # esplicito prima di usare il payload.
    assert response.status_code == 400
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert "run format not supported" in content["_schema"][0]


def test_dataset_download_returns_404_when_no_opendata_exist(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that an empty public dataset returns 404 instead of an empty archive."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset = create_test_dataset(
        sqlalchemy.get_instance(),
        cleanup_registry,
        is_public=True,
    )
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    content = BaseTests().get_content(response)
    # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
    # visibile prima di usare il payload.
    assert response.status_code == 404
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert "No opendata found" in content


def test_dataset_download_returns_404_for_unmatched_reftime(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that reftime filters with no matching file return 404."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, _ = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download?reftime=20200103"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 404


def test_dataset_download_returns_404_for_unmatched_run(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that run filters with no matching file return 404."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, _ = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download?run=15:00"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 404


def test_dataset_download_returns_404_for_unmatched_reftime_and_run(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that combined filters return 404 when no opendata file satisfies both."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, _ = create_download_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/opendata/{dataset.arkimet_id}/download"
        "?reftime=2020-01-02&run=12:00"
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 404


def test_dataset_download_zips_all_results(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that downloading without filters returns all seeded files inside a zip archive."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    zipfile_name = (
        response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
    )
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert response.mimetype == "application/zip"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert zipfile_name == f"opendata_{dataset.arkimet_id}.zip"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert zip_filenames(response) == sorted(
        result.filename for result in seeded_results
    )
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_dataset_download_zips_results_filtered_by_reftime(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that reftime filtering narrows the zip archive to matching files only."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/opendata/{dataset.arkimet_id}/download?reftime=2020-01-01"
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    zipfile_name = (
        response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
    )
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert response.mimetype == "application/zip"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert zipfile_name == f"opendata_{dataset.arkimet_id}_reftime_2020-01-01.zip"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert zip_filenames(response) == sorted(
        result.filename for result in seeded_results[:2]
    )
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_dataset_download_zips_results_filtered_by_run(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that run filtering narrows the zip archive to matching files only."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download?run=00:00"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    zipfile_name = (
        response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
    )
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert response.mimetype == "application/zip"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert zipfile_name == f"opendata_{dataset.arkimet_id}_run_00:00.zip"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert zip_filenames(response) == sorted(
        result.filename for result in (seeded_results[0], seeded_results[2])
    )
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_dataset_download_returns_single_file_when_query_matches_one_result(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that a single matching result is streamed directly instead of being zipped."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    dataset, seeded_results = create_download_env(client, cleanup_registry)
    endpoint = (
        f"{API_URI}/opendata/{dataset.arkimet_id}/download"
        "?reftime=20200101&run=12:00"
    )

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)
    cleanup_registry.add(response.close)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert response.mimetype == "application/octet-stream"
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert response.get_data(as_text=True) == seeded_results[1].content
    _run_teardown_and_assert_seeded_files_removed(cleanup_registry, seeded_results)


def test_file_download_unknown_file_returns_404(client: FlaskClient) -> None:
    """Verify that direct file download returns 404 for an unknown filename."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    endpoint = f"{API_URI}/opendata/{uuid4().hex}.grib"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    response = client.get(endpoint)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert response.status_code == 404