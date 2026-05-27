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
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    _, dataset, user, result = create_private_opendata_env(
        client,
        cleanup_registry,
    )
    list_endpoint = f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
    download_endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"
    file_endpoint = f"{API_URI}/opendata/{result.filename}"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    anonymous_list = client.get(list_endpoint)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    logged_list = client.get(list_endpoint, headers=user.headers)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    anonymous_download = client.get(download_endpoint)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    logged_download = client.get(download_endpoint, headers=user.headers)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    anonymous_file_download = client.get(file_endpoint)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    logged_file_download = client.get(file_endpoint, headers=user.headers)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    assert anonymous_list.status_code == 401
    # Verifichiamo che la risposta richieda credenziali quando l'utente non e
    # autenticato prima di usare il payload.
    assert logged_list.status_code == 401
    # Verifichiamo che la risposta richieda credenziali quando l'utente non e
    # autenticato prima di usare il payload.
    assert anonymous_download.status_code == 401
    # Verifichiamo che la risposta richieda credenziali quando l'utente non e
    # autenticato prima di usare il payload.
    assert logged_download.status_code == 401
    # Verifichiamo che la risposta richieda credenziali quando l'utente non e
    # autenticato prima di usare il payload.
    assert anonymous_file_download.status_code == 401
    # Verifichiamo che la risposta richieda credenziali quando l'utente non e
    # autenticato prima di usare il payload.
    assert logged_file_download.status_code == 401


def test_private_dataset_endpoints_allow_authorized_user(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verify that a user explicitly authorized on a private dataset can list and download it."""
    # arrange
    # Prepariamo lo scenario opendata con dati minimi e controllati, cosi la verifica
    # successiva resta legata a un comportamento preciso.
    db, dataset, user, result = create_private_opendata_env(
        client,
        cleanup_registry,
    )
    authorize_user_for_dataset(db, user.uuid, dataset.id)
    list_endpoint = f"{API_URI}/datasets/{dataset.arkimet_id}/opendata"
    download_endpoint = f"{API_URI}/opendata/{dataset.arkimet_id}/download"
    file_endpoint = f"{API_URI}/opendata/{result.filename}"

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    list_response = client.get(list_endpoint, headers=user.headers)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    download_response = client.get(download_endpoint, headers=user.headers)
    # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
    # autorizzazione e serializzazione vengono verificati insieme.
    file_response = client.get(file_endpoint, headers=user.headers)

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    list_content = BaseTests().get_content(list_response)
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert list_response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert len(list_content) == 1
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert list_content[0]["filename"] == result.filename
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert download_response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert download_response.get_data(as_text=True) == result.content
    download_response.close()
    # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine prima di
    # usare il payload.
    assert file_response.status_code == 200
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert file_response.get_data(as_text=True) == result.content
    file_response.close()