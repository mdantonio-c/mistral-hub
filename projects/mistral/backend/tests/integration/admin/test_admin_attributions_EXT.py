# EXTENSION TRACEABILITY - Prompt 06, endpoint admin attributions.
# Origine: questo modulo estende la suite backend con copertura CRUD per
# projects/mistral/backend/endpoints/admin_attributions.py, senza modificare i test
# legacy o aggiungere fixture globali.
# Ambito: verifica auth admin, creazione, listing con dataset collegati, update,
# delete, 404 su record mancanti e normalizzazione di url vuota a None.
# Finestra dati: nessun dato meteorologico reale viene usato; i dataset collegati sono
# record catalografici sintetici creati via API admin e ripuliti a fine test.
# Runtime fake: non sono necessari fake; i test attraversano Flask e SQLAlchemy reali.
# Cleanup: ogni attribution, license group, license e dataset creato viene registrato
# nel cleanup_registry tramite support_EXT, con ordine relazionale sicuro.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/admin.

from __future__ import annotations

import pytest
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tests.integration.admin.support_EXT import (
    ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
    ADMIN_MISSING_ID_EXT,
    admin_headers_EXT,
    attribution_payload_EXT,
    create_dataset_bundle_via_api_EXT,
    create_regular_user_EXT,
    created_id_from_response_EXT,
    delete_admin_records_EXT,
    find_list_item_EXT,
    response_content_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_admin_attributions_require_admin_role_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che /admin/attributions rifiuti anonimi e utenti non admin.

    Questo test protegge il perimetro esterno dell'endpoint: prima di esercitare il CRUD
    controlla che il decorator Role.ADMIN sia effettivamente attivo sia senza token sia
    con un utente temporaneo autenticato ma privo di ruolo admin.
    """
    # act - chiamata anonima senza alcun setup applicativo.
    anonymous_response = client.get(ADMIN_ATTRIBUTIONS_ENDPOINT_EXT)

    # arrange - utente reale non-admin con cleanup registrato subito dopo la creazione.
    regular_user = create_regular_user_EXT(client, cleanup_registry)

    # act - la seconda chiamata usa credenziali valide ma non autorizzate al ruolo admin.
    forbidden_response = client.get(
        ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
        headers=regular_user.headers,
    )

    # assert - il runtime restapi espone 401 sia per credenziali mancanti sia per
    # credenziali valide ma prive del ruolo admin richiesto dal decorator.
    assert anonymous_response.status_code == 401
    assert forbidden_response.status_code == 401


def test_admin_attribution_create_list_update_delete_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Copre il ciclo CRUD principale e la normalizzazione url vuota.

    La creazione passa `url=""` per attraversare il pre_load AttributionInput.null_url;
    il listing successivo deve esporre None, poi l'update cambia nome, descrizione e URL
    prima della cancellazione finale via endpoint.
    """
    # arrange - payload sintetico senza dipendenze esterne e con URL vuota intenzionale.
    db = sqlalchemy.get_instance()
    create_payload = attribution_payload_EXT(url="")

    # act - creazione reale via endpoint admin.
    create_response = client.post(
        ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
        headers=admin_headers_EXT,
        json=create_payload,
    )

    # assert - l'endpoint ritorna l'id scalare e il cleanup viene registrato subito.
    assert create_response.status_code == 200
    attribution_id = created_id_from_response_EXT(create_response)
    cleanup_registry.add(
        lambda attribution_id=attribution_id: delete_admin_records_EXT(
            db, attribution_ids=[attribution_id]
        )
    )

    # act - listing dopo la creazione per verificare schema e normalizzazione URL.
    list_response = client.get(
        ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
        headers=admin_headers_EXT,
    )
    assert list_response.status_code == 200
    created_item = find_list_item_EXT(response_content_EXT(list_response), attribution_id)
    assert created_item["name"] == create_payload["name"]
    assert created_item["descr"] == create_payload["descr"]
    assert created_item["url"] is None
    assert created_item["datasets"] == []

    # act - update completo dei campi modificabili.
    update_payload = attribution_payload_EXT(
        name=f"{create_payload['name']}_updated",
        descr="Updated synthetic attribution EXT",
        url="https://example.com/admin-attribution-updated",
    )
    update_response = client.put(
        f"{ADMIN_ATTRIBUTIONS_ENDPOINT_EXT}/{attribution_id}",
        headers=admin_headers_EXT,
        json=update_payload,
    )

    # assert - empty_response del controller deve essere 204 e il listing deve cambiare.
    assert update_response.status_code == 204
    refreshed_response = client.get(
        ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
        headers=admin_headers_EXT,
    )
    refreshed_item = find_list_item_EXT(
        response_content_EXT(refreshed_response), attribution_id
    )
    assert refreshed_item["name"] == update_payload["name"]
    assert refreshed_item["descr"] == update_payload["descr"]
    assert refreshed_item["url"] == update_payload["url"]

    # act/assert - delete via API e verifica DB diretta del side effect.
    delete_response = client.delete(
        f"{ADMIN_ATTRIBUTIONS_ENDPOINT_EXT}/{attribution_id}",
        headers=admin_headers_EXT,
    )
    assert delete_response.status_code == 204
    assert db.Attribution.query.get(attribution_id) is None


def test_admin_attribution_list_includes_related_datasets_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
    cleanup_registry,
) -> None:
    """Verifica che il listing annidi i dataset collegati all'attribution.

    Il bundle viene creato via API admin per coprire relazioni reali senza usare dati
    meteo. L'assert controlla il contratto di serializzazione: id dataset esposto come
    arkimet_id e nome dataset leggibile.
    """
    # arrange - crea attribution, license group, license e dataset sintetici.
    bundle = create_dataset_bundle_via_api_EXT(
        client,
        admin_headers_EXT,
        cleanup_registry,
    )

    # act - lista le attribution dal controller reale.
    response = client.get(
        ADMIN_ATTRIBUTIONS_ENDPOINT_EXT,
        headers=admin_headers_EXT,
    )

    # assert - il record deve includere il dataset collegato nello schema annidato.
    assert response.status_code == 200
    item = find_list_item_EXT(response_content_EXT(response), bundle.attribution_id)
    assert {"id": bundle.dataset_arkimet_id, "name": bundle.dataset_name} in item[
        "datasets"
    ]


def test_admin_attribution_missing_update_delete_return_404_EXT(
    client: FlaskClient,
    admin_headers_EXT: dict[str, str],
) -> None:
    """Verifica i rami NotFound per update e delete di attribution inesistente.

    Il test non crea dati: usa un id alto e controlla prima che non esista nel DB, cosi
    i 404 misurano il contratto applicativo e non un conflitto con stato residuo.
    """
    # arrange - precondizione DB chiara per l'id inesistente.
    db = sqlalchemy.get_instance()
    assert db.Attribution.query.get(ADMIN_MISSING_ID_EXT) is None
    payload = attribution_payload_EXT(url=None)

    # act - update e delete sullo stesso id mancante.
    update_response = client.put(
        f"{ADMIN_ATTRIBUTIONS_ENDPOINT_EXT}/{ADMIN_MISSING_ID_EXT}",
        headers=admin_headers_EXT,
        json=payload,
    )
    delete_response = client.delete(
        f"{ADMIN_ATTRIBUTIONS_ENDPOINT_EXT}/{ADMIN_MISSING_ID_EXT}",
        headers=admin_headers_EXT,
    )

    # assert - entrambi i rami devono restituire NotFound.
    assert update_response.status_code == 404
    assert delete_response.status_code == 404