# EXTENSION TRACEABILITY - Prompt 05, contratti GET /templates.
# Origine: questo modulo aggiunge copertura dedicata per Templates.get senza modificare
# i test legacy o introdurre fixture globali.
# Ambito: copre autenticazione richiesta, lista vuota grib/shp, filtro format, conteggio
# get_total e flag max_allowed quando l'utente raggiunge max_templates.
# Finestra dati: nessun dato meteo reale viene usato; i file grib/shp sono placeholder
# sintetici creati sotto /data/<uuid>/uploads del solo utente temporaneo.
# Runtime fake: non servono monkeypatch o servizi esterni; il controller legge solo il
# filesystem preparato dal test e il campo max_templates dell'utente creato via API.
# Cleanup: create_templates_user_EXT registra /data/<uuid> con cleanup_registry.add_path;
# i seed diretti registrano anche la cartella uploads locale.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/templates.

from __future__ import annotations

import pytest
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.integration.templates.support_EXT import (
    TEMPLATES_ENDPOINT_EXT,
    create_templates_user_EXT,
    listed_filenames_EXT,
    seed_template_file_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_templates_listing_requires_authentication_EXT(client: FlaskClient) -> None:
    """Verifica che il listing template non sia accessibile senza login.

    Questo scenario protegge il bordo esterno dell'endpoint prima dei dettagli di
    filesystem: senza credenziali il backend deve fermarsi sulla decorazione auth e non
    leggere alcuna cartella utente.
    """
    # act
    # Eseguiamo una GET anonima, senza preparare file o utenti temporanei: il contratto
    # qui e soltanto l'autenticazione obbligatoria.
    response = client.get(TEMPLATES_ENDPOINT_EXT)

    # assert
    # Il backend deve rifiutare il chiamante anonimo con 401, come gli altri endpoint
    # user-facing della suite.
    assert response.status_code == 401


def test_templates_listing_returns_empty_grib_and_shp_lists_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica la forma del listing quando l'utente non ha ancora upload.

    L'utente temporaneo non riceve directory uploads precreate: il test documenta che il
    controller deve comunque restituire le due sezioni grib/shp con liste vuote e senza
    segnalare max_allowed.
    """
    # arrange
    # Creiamo un utente isolato con limite template superiore a zero, ma senza file su
    # disco, per misurare il comportamento della glob su cartelle assenti.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=3)

    # act
    # Attraversiamo il vero endpoint HTTP per verificare routing, auth e serializzazione.
    response = client.get(TEMPLATES_ENDPOINT_EXT, headers=user.headers)

    # assert
    # La risposta deve contenere entrambe le famiglie di template, ordinate come nel
    # controller, senza dipendere dall'esistenza fisica delle directory uploads.
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert content == [
        {"type": "grib", "files": [], "max_allowed": False},
        {"type": "shp", "files": [], "max_allowed": False},
    ]


def test_templates_listing_filters_by_format_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che il parametro format limiti la lista al tipo richiesto.

    Il setup crea un grib e uno shapefile sintetico. La richiesta con format=grib deve
    restituire solo la sezione grib, evitando duplicazioni di assert sui dettagli upload.
    """
    # arrange
    # Seediamo direttamente i file per isolare il ramo GET dal comportamento di POST e
    # dalla quota disco, che hanno test dedicati nel modulo upload/delete.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    grib_path = seed_template_file_EXT(cleanup_registry, user, "filter_ext.grib")
    seed_template_file_EXT(cleanup_registry, user, "filter_ext.shp")

    # act
    # Usiamo query_string invece di concatenare parametri a mano, cosi il test resta
    # focalizzato sul contratto dell'endpoint.
    response = client.get(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        query_string={"format": "grib"},
    )

    # assert
    # Il payload deve contenere una sola sezione e la lista deve riferire il file grib
    # preparato, indipendentemente dal prefisso assoluto serializzato dal backend.
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert len(content) == 1
    assert content[0]["type"] == "grib"
    assert listed_filenames_EXT(content[0]["files"]) == {grib_path.name}


def test_templates_listing_get_total_counts_all_and_filtered_templates_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica get_total sul totale complessivo e sul filtro grib.

    Il controller ha un ramo separato per get_total che ritorna subito senza costruire
    gli oggetti grib/shp. Questo test lo copre con file sintetici gia presenti su disco.
    """
    # arrange
    # Creiamo un file per tipo cosi il totale non filtrato e il totale filtrato possano
    # essere distinti in modo leggibile.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    seed_template_file_EXT(cleanup_registry, user, "total_ext.grib")
    seed_template_file_EXT(cleanup_registry, user, "total_ext.shp")

    # act
    # Prima chiediamo il totale globale, poi il totale del solo formato grib.
    total_response = client.get(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        query_string={"get_total": True},
    )
    grib_total_response = client.get(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        query_string={"get_total": True, "format": "grib"},
    )

    # assert
    # Entrambe le risposte devono attraversare il ramo compatto {total: ...}; il codice
    # HTTP resta 200 per questo endpoint.
    assert total_response.status_code == 200
    assert grib_total_response.status_code == 200
    assert BaseTests().get_content(total_response) == {"total": 2}
    assert BaseTests().get_content(grib_total_response) == {"total": 1}


def test_templates_listing_marks_max_allowed_when_limit_is_reached_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica max_allowed quando ogni famiglia raggiunge max_templates.

    Il flag e calcolato nel listing, non nell'upload: il test crea quindi un file grib e
    un file shp con max_templates=1 e controlla che entrambe le sezioni espongano il
    limite raggiunto.
    """
    # arrange
    # Usiamo un limite pari a uno per evitare setup voluminoso e rendere immediata la
    # condizione len(files) >= max_templates del controller.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=1)
    seed_template_file_EXT(cleanup_registry, user, "max_ext.grib")
    seed_template_file_EXT(cleanup_registry, user, "max_ext.shp")

    # act
    # Il listing non modifica stato: una sola GET basta a verificare entrambi i rami.
    response = client.get(TEMPLATES_ENDPOINT_EXT, headers=user.headers)

    # assert
    # Ogni sezione deve dichiarare max_allowed=True quando il numero di template del tipo
    # corrispondente raggiunge il limite configurato sull'utente.
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    by_type = {item["type"]: item for item in content}
    assert by_type["grib"]["max_allowed"] is True
    assert by_type["shp"]["max_allowed"] is True