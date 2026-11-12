# Test di GET /templates: listing dei template dell'utente (endpoints/templates.py).
# Ambito: copre autenticazione richiesta, lista vuota grib/shp, filtro format, conteggio
# get_total e flag max_allowed quando l'utente raggiunge max_templates.
# Finestra dati: nessun dato meteo reale viene usato; i file grib/shp sono placeholder
# sintetici creati sotto /data/<uuid>/uploads del solo utente temporaneo.
# Runtime fake: non servono monkeypatch o servizi esterni; il controller legge solo il
# filesystem preparato dal test e il campo max_templates dell'utente creato via API.
# Cleanup: create_templates_user registra /data/<uuid> con cleanup_registry.add_path;
# i seed diretti registrano anche la cartella uploads locale.

from __future__ import annotations

import pytest
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.integration.templates.support import (
    TEMPLATES_ENDPOINT,
    create_templates_user,
    listed_filenames,
    seed_template_file,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_templates_listing_requires_authentication(client: FlaskClient) -> None:
    """Verifica che il listing template non sia accessibile senza login.

    Questo scenario protegge il bordo esterno dell'endpoint prima dei dettagli di
    filesystem: senza credenziali il backend deve fermarsi sulla decorazione auth e non
    leggere alcuna cartella utente.
    """
    # act
    response = client.get(TEMPLATES_ENDPOINT)

    # assert
    assert response.status_code == 401


def test_templates_listing_returns_empty_grib_and_shp_lists(
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
    user = create_templates_user(client, cleanup_registry, max_templates=3)

    # act
    response = client.get(TEMPLATES_ENDPOINT, headers=user.headers)

    # assert
    # La risposta deve contenere entrambe le famiglie di template, ordinate come nel
    # controller, senza dipendere dall'esistenza fisica delle directory uploads.
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert content == [
        {"type": "grib", "files": [], "max_allowed": False},
        {"type": "shp", "files": [], "max_allowed": False},
    ]


def test_templates_listing_filters_by_format(
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
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    grib_path = seed_template_file(cleanup_registry, user, "filter_ext.grib")
    seed_template_file(cleanup_registry, user, "filter_ext.shp")

    # act
    response = client.get(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        query_string={"format": "grib"},
    )

    # assert
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert len(content) == 1
    assert content[0]["type"] == "grib"
    assert listed_filenames(content[0]["files"]) == {grib_path.name}


def test_templates_listing_get_total_counts_all_and_filtered_templates(
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
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    seed_template_file(cleanup_registry, user, "total_ext.grib")
    seed_template_file(cleanup_registry, user, "total_ext.shp")

    # act
    total_response = client.get(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        query_string={"get_total": True},
    )
    grib_total_response = client.get(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        query_string={"get_total": True, "format": "grib"},
    )

    # assert
    assert total_response.status_code == 200
    assert grib_total_response.status_code == 200
    assert BaseTests().get_content(total_response) == {"total": 2}
    assert BaseTests().get_content(grib_total_response) == {"total": 1}


def test_templates_listing_marks_max_allowed_when_limit_is_reached(
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
    user = create_templates_user(client, cleanup_registry, max_templates=1)
    seed_template_file(cleanup_registry, user, "max_ext.grib")
    seed_template_file(cleanup_registry, user, "max_ext.shp")

    # act
    # Il listing non modifica stato: una sola GET basta a verificare entrambi i rami.
    response = client.get(TEMPLATES_ENDPOINT, headers=user.headers)

    # assert
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    by_type = {item["type"]: item for item in content}
    assert by_type["grib"]["max_allowed"] is True
    assert by_type["shp"]["max_allowed"] is True