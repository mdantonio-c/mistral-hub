# EXTENSION TRACEABILITY - Prompt 02, contratto GET /data/<filename> lato file download.
# Origine: questo modulo aggiunge copertura EXT per projects/mistral/backend/endpoints/file.py
# senza toccare il baseline auth o i moduli legacy di altri domini.
# Ambito: copre download del file posseduto, negazione per file non posseduto e 404
# quando il record FileOutput esiste ma il file fisico manca dal filesystem utente.
# Finestra dati: non usa dati meteorologici reali; i contenuti file sono stringhe
# sintetiche scritte nella directory output del solo utente temporaneo di test.
# Runtime fake: non serve monkeypatch di worker o servizi esterni, perche il contratto
# di file.py dipende solo da DB, ownership e presenza fisica del file su disco.
# Cleanup: ogni utente temporaneo, request sintetica e directory output viene registrato
# nel cleanup_registry tramite helper locali di support_EXT.py.
# Baseline non toccata: il file vive nel perimetro *_EXT richiesto e non modifica suite preesistente.

"""Test di download file per l'endpoint GET /data/<filename> con stato sintetico locale."""

from __future__ import annotations

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, FlaskClient

from mistral.tests.integration.data.support_EXT import (
    create_data_endpoint_user,
    create_file_download_record,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_file_download_returns_owned_output_content(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che il proprietario possa scaricare il proprio output sintetico.

    Lo scenario prepara una request di successo e un FileOutput nel path utente previsto
    dal backend. Il test usa poi l'endpoint reale per confermare ownership, lookup DB e
    invio del contenuto fisico come attachment.
    """
    # arrange
    # Prepariamo un solo utente proprietario e il suo file sintetico su disco, cosi il
    # test resta focalizzato sul contratto di download e non sulla creazione della request.
    db = sqlalchemy.get_instance()
    owner = create_data_endpoint_user(client, cleanup_registry)
    filename = create_file_download_record(
        db,
        cleanup_registry,
        owner,
        content="owned-file-download-ext",
    )
    endpoint = f"{API_URI}/data/{filename}"

    # act
    # La richiesta attraversa il controllo reale di ownership e la consegna del file dal
    # filesystem dell'utente temporaneo appena preparato.
    response = client.get(endpoint, headers=owner.headers)

    # assert
    # Il contratto osservabile e il 200 con il contenuto esatto del file sintetico.
    assert response.status_code == 200
    assert response.mimetype == "application/octet-stream"
    assert response.get_data(as_text=True) == "owned-file-download-ext"
    response.close()


def test_file_download_denies_non_owned_output(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un utente diverso dal proprietario riceva 404 sul download diretto.

    L'endpoint delega a SqlApiDbManager.check_fileoutput, che nasconde i file non propri
    con un NotFound. Il test crea quindi due utenti temporanei per proteggere proprio quel
    contratto di non disclosure dell'ownership.
    """
    # arrange
    # Costruiamo il file per il proprietario e poi eseguiamo il download con un secondo
    # utente autenticato, senza condividere nessuna autorizzazione aggiuntiva.
    db = sqlalchemy.get_instance()
    owner = create_data_endpoint_user(client, cleanup_registry)
    other_user = create_data_endpoint_user(client, cleanup_registry)
    filename = create_file_download_record(
        db,
        cleanup_registry,
        owner,
        content="not-for-other-user",
    )
    endpoint = f"{API_URI}/data/{filename}"

    # act
    # La richiesta passa con credenziali valide ma deve fallire sul controllo ownership.
    response = client.get(endpoint, headers=other_user.headers)

    # assert
    # Il backend deve mascherare il file come non esistente per l'utente non proprietario.
    assert response.status_code == 404


def test_file_download_returns_404_when_db_row_exists_but_file_is_missing(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il 404 quando esiste il FileOutput ma il file fisico non e presente.

    Questo scenario protegge il ramo finale di file.py: dopo il controllo DB e ownership,
    il backend deve verificare la presenza del path fisico. Lasciare apposta il file
    assente consente di testare quel contratto senza dipendere da errori runtime esterni.
    """
    # arrange
    # Prepariamo il record FileOutput senza creare il file su disco, cosi il backend deve
    # attraversare i controlli precedenti e fallire solo sull'esistenza fisica del path.
    db = sqlalchemy.get_instance()
    owner = create_data_endpoint_user(client, cleanup_registry)
    filename = create_file_download_record(db, cleanup_registry, owner, content=None)
    endpoint = f"{API_URI}/data/{filename}"

    # act
    # La richiesta usa il proprietario corretto proprio per dimostrare che il 404 deriva
    # dall'assenza del file fisico e non da auth o ownership.
    response = client.get(endpoint, headers=owner.headers)

    # assert
    # Il contratto richiede 404 quando il record esiste ma il file non puo essere letto.
    assert response.status_code == 404