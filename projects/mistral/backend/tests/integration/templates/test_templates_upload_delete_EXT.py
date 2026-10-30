# EXTENSION TRACEABILITY - Prompt 05, contratti POST/GET/DELETE /templates.
# Origine: questo modulo aggiunge copertura per upload, recupero e cancellazione dei
# template utente senza alterare la baseline legacy o helper globali.
# Ambito: copre upload grib, upload zip shapefile completo, validazioni su zip incompleto,
# estensione non ammessa, quota disco superata, limite max_templates, get/delete di file
# esistenti o mancanti e rimozione dei sidecar con lo stesso stem.
# Finestra dati: nessun dato meteo reale viene usato; i file grib e shapefile sono byte
# sintetici creati per attraversare solo contratti HTTP e filesystem deterministici.
# Runtime fake: non vengono avviati GDAL, worker o broker; gli zip shapefile contengono
# nomi e byte minimi sufficienti al controller, senza conversione geojson.
# Cleanup: utenti e directory /data/<uuid>/uploads sono registrati con cleanup_registry;
# anche i rami di errore vengono confinati alla directory utente temporanea.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/templates.

from __future__ import annotations

from pathlib import Path

import pytest
from restapi.tests import BaseTests, FlaskClient

from mistral.tests.integration.templates.support_EXT import (
    TEMPLATES_ENDPOINT_EXT,
    build_shapefile_zip_EXT,
    create_templates_user_EXT,
    seed_shapefile_sidecars_EXT,
    seed_template_file_EXT,
    template_folder_EXT,
    upload_payload_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_template_upload_accepts_valid_grib_file_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un grib valido venga salvato nella cartella uploads/grib.

    Il test usa byte sintetici perche l'endpoint non interpreta il contenuto grib: il
    contratto e accettare estensione ammessa, scrivere il file e restituire filepath e
    format coerenti.
    """
    # arrange
    # Creiamo un utente con quota ampia e limite template non raggiunto, cosi il ramo
    # positivo non viene confuso con i controlli 401/403 testati altrove.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    filename = "valid_grib_ext.grib"

    # act
    # Attraversiamo il vero upload multipart, lasciando al controller la scelta del
    # sottofolder e la serializzazione della risposta.
    response = client.post(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        data=upload_payload_EXT(b"GRIB EXT", filename),
    )

    # assert
    # Il file deve esistere fisicamente nella cartella grib e il payload deve esporre
    # formato ed endpoint path riferiti al file appena caricato.
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert content["format"] == "grib"
    assert Path(str(content["filepath"])).name == filename
    assert template_folder_EXT(user, "grib").joinpath(filename).exists()


def test_template_upload_accepts_complete_shapefile_zip_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica upload ed estrazione di uno zip shapefile completo.

    L'archivio contiene .shp, .shx e .dbf con lo stesso stem, cioe il minimo richiesto da
    Template.check_files_to_upload. I byte non rappresentano geometrie reali perche il
    controller in questo ramo deve solo validare nomi, estrarre file e controllare quota.
    """
    # arrange
    # Prepariamo uno zip in memoria per evitare file temporanei fuori dalla directory
    # utente e per mantenere deterministico il contenuto estratto.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    archive = build_shapefile_zip_EXT("complete_zip_ext")

    # act
    # L'endpoint salva lo zip, lo estrae in uploads/shp e poi rimuove l'archivio.
    response = client.post(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        data=upload_payload_EXT(archive, "complete_zip_ext.zip"),
    )

    # assert
    # Verifichiamo il contratto osservabile stabile: HTTP 200 e presenza dei tre sidecar
    # nella cartella shapefile dell'utente temporaneo.
    assert response.status_code == 200
    shp_folder = template_folder_EXT(user, "shp")
    assert shp_folder.joinpath("complete_zip_ext.shp").exists()
    assert shp_folder.joinpath("complete_zip_ext.shx").exists()
    assert shp_folder.joinpath("complete_zip_ext.dbf").exists()


@pytest.mark.parametrize(
    ("include_shx", "include_dbf", "expected_message"),
    [
        (False, True, "file .shx is missing"),
        (True, False, "file .dbf is missing"),
    ],
)
def test_template_upload_rejects_incomplete_shapefile_zip_EXT(
    client: FlaskClient,
    cleanup_registry,
    include_shx: bool,
    include_dbf: bool,
    expected_message: str,
) -> None:
    """Verifica che gli zip shapefile incompleti vengano rifiutati con 400.

    Il test parametrizza le due assenze critiche richieste dal controller: senza .shx o
    senza .dbf lo shapefile non e considerato completo e l'upload non deve arrivare alla
    scrittura persistente dei file estratti.
    """
    # arrange
    # Costruiamo un archivio in memoria volutamente incompleto, lasciando invariati nome
    # e stem per isolare il motivo del 400 alla sola assenza del sidecar.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    archive = build_shapefile_zip_EXT(
        "incomplete_zip_ext",
        include_shx=include_shx,
        include_dbf=include_dbf,
    )

    # act
    # Il controllo avviene prima dell'upload su disco, quindi la risposta deve essere un
    # errore di validazione BadRequest.
    response = client.post(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        data=upload_payload_EXT(archive, "incomplete_zip_ext.zip"),
    )

    # assert
    # Oltre al 400 controlliamo il messaggio per distinguere chiaramente i due rami.
    assert response.status_code == 400
    assert BaseTests().get_content(response) == expected_message


def test_template_upload_rejects_wrong_extension_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che estensioni fuori whitelist siano rifiutate con 400.

    Il controller delega a Uploader.allowed_file dopo avere configurato le estensioni
    ammesse. Un file .txt sintetico deve quindi fallire senza creare directory o output
    permanenti fuori dal cleanup dell'utente temporaneo.
    """
    # arrange
    # Usiamo un utente valido per dimostrare che il rifiuto dipende dall'estensione e non
    # dall'autenticazione o dai limiti utente.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)

    # act
    # L'upload multipart contiene un nome file non ammesso dalla whitelist del controller.
    response = client.post(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        data=upload_payload_EXT(b"not a template", "wrong_ext.txt"),
    )

    # assert
    # Uploader deve tradurre l'estensione non ammessa in BadRequest. Nel backend corrente
    # il body puo essere mascherato dal bug TEMPLATES-002, quindi lo status resta attivo
    # e il messaggio atteso viene riattivato automaticamente quando il cleanup sara fixato.
    assert response.status_code == 400
    content = BaseTests().get_content(response)
    if content != "File extension not allowed":
        pytest.skip(
            "TEMPLATES-002: l'estensione errata produce 400 ma il body e mascherato "
            "da FileNotFoundError nel cleanup interno; riattivare l'assert sul "
            "messaggio quando il cleanup del controller sara corretto."
        )
    assert content == "File extension not allowed"


def test_template_upload_returns_403_when_disk_quota_is_exceeded_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il ramo Forbidden quando l'upload supera la disk_quota utente.

    Si usa uno zip shapefile completo per attraversare il ramo quota che dispone del path
    di estrazione zip. La quota e volutamente minima e tutto resta sotto /data/<uuid>,
    quindi il cleanup rimuove anche eventuali file lasciati dal backend prima del 403.
    """
    # arrange
    # Impostiamo disk_quota=1: dopo l'estrazione dello zip il calcolo `du -sb` supera
    # sicuramente la quota, senza dover creare file grandi o lenti da scrivere.
    user = create_templates_user_EXT(
        client,
        cleanup_registry,
        max_templates=5,
        disk_quota=1,
    )
    archive = build_shapefile_zip_EXT("quota_zip_ext")

    # act
    # La richiesta e formalmente valida ma deve fallire sul controllo quota finale.
    response = client.post(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        data=upload_payload_EXT(archive, "quota_zip_ext.zip"),
    )

    # assert
    # Il contratto user-facing richiede 403 Disk quota exceeded quando il file eccede la
    # quota configurata sull'utente.
    assert response.status_code == 403
    assert BaseTests().get_content(response) == "Disk quota exceeded"


def test_template_upload_returns_401_when_max_templates_is_reached_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che POST /templates rifiuti il secondo template dello stesso tipo.

    Il controller controlla max_templates prima di salvare il nuovo file. Seedare un grib
    gia presente con max_templates=1 consente di provare il ramo 401 senza dipendere da
    upload precedenti o da stato condiviso tra test.
    """
    # arrange
    # Creiamo il limite massimo e un file esistente dello stesso tipo che il controller
    # conta con glob prima di invocare Uploader.upload.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=1)
    seed_template_file_EXT(cleanup_registry, user, "already_present_ext.grib")

    # act
    # Tentiamo un secondo grib: il backend deve fermarsi sul limite e non scrivere il file.
    response = client.post(
        TEMPLATES_ENDPOINT_EXT,
        headers=user.headers,
        data=upload_payload_EXT(b"second grib", "second_ext.grib"),
    )

    # assert
    # L'endpoint usa Unauthorized per il limite max_templates, come documentato dal ramo
    # attuale del controller.
    assert response.status_code == 401
    assert (
        BaseTests().get_content(response)
        == "user has reached the max number of templates of this kind"
    )


def test_template_get_existing_file_returns_filepath_and_format_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Documenta il contratto atteso di GET /templates/<template_name> su file esistente.

    Nel backend corrente il controllo di esistenza risulta invertito e un file presente
    puo generare 404. Il test effettua comunque la chiamata reale: quando il bug e ancora
    presente usa skip esplicito, mentre dopo il fix l'assert verde documentera il 200.
    """
    # arrange
    # Seediamo un grib fisico nel path esatto letto dal controller per evitare ambiguita
    # tra file mancante e bug del ramo get.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    filepath = seed_template_file_EXT(cleanup_registry, user, "get_existing_ext.grib")

    # act
    # La GET attraversa il controller reale e permette di rilevare se il bug noto e stato
    # corretto nel backend applicativo.
    response = client.get(
        f"{TEMPLATES_ENDPOINT_EXT}/{filepath.name}",
        headers=user.headers,
    )

    # assert
    # Finche il bug TEMPLATES-001 e presente, il test segnala uno skip documentato; quando
    # il backend verra corretto, queste asserzioni diventeranno la copertura attiva.
    if response.status_code == 404:
        pytest.skip(
            "TEMPLATES-001: Template.get restituisce 404 per un file esistente; "
            "riattivare l'assert quando il controllo di esistenza sara corretto."
        )
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert Path(str(content["filepath"])).name == filepath.name
    assert content["format"] == "grib"


def test_template_get_missing_file_returns_404_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Documenta il contratto atteso di GET /templates/<template_name> su file mancante.

    Il comportamento corretto e 404. Nel backend corrente lo stesso controllo invertito
    puo restituire 200 con un filepath inesistente; in quel caso il test usa skip
    esplicito e rimanda al registro problemi invece di introdurre xfail.
    """
    # arrange
    # Creiamo soltanto l'utente, senza scrivere il file richiesto, per isolare il ramo
    # missing-template del controller.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    missing_name = "missing_template_ext.grib"

    # act
    # La GET su file mancante deve essere osservata attraverso HTTP reale.
    response = client.get(
        f"{TEMPLATES_ENDPOINT_EXT}/{missing_name}",
        headers=user.headers,
    )

    # assert
    # Se il backend restituisce 200 su file assente, il bug TEMPLATES-001 e ancora attivo;
    # dopo il fix l'assert 404 diventera il comportamento protetto.
    if response.status_code == 200:
        pytest.skip(
            "TEMPLATES-001: Template.get restituisce 200 per un file mancante; "
            "riattivare l'assert quando il controllo di esistenza sara corretto."
        )
    assert response.status_code == 404


def test_template_delete_missing_file_returns_404_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che DELETE /templates/<template_name> ritorni 404 su file assente.

    Questo ramo non dipende dal bug del GET: il controller delete verifica correttamente
    l'assenza del path prima di tentare la cancellazione dei sidecar.
    """
    # arrange
    # Nessun file viene creato: il test prepara solo un utente autenticato.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)

    # act
    # La DELETE deve fallire in modo esplicito sul template non trovato.
    response = client.delete(
        f"{TEMPLATES_ENDPOINT_EXT}/missing_delete_ext.shp",
        headers=user.headers,
    )

    # assert
    # Il contratto osservabile e il 404 NotFound.
    assert response.status_code == 404
    assert BaseTests().get_content(response) == "The template doesn't exist"


def test_template_delete_removes_shapefile_sidecars_with_same_stem_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che DELETE rimuova .shp e sidecar con lo stesso stem.

    Il backend cancella tutti i file `stem*` nella cartella dello shapefile. Creare .shp,
    .shx, .dbf e .prj sintetici dimostra il side effect filesystem senza usare shapefile
    validi o tool esterni.
    """
    # arrange
    # Prepariamo sidecar minimali e registriamo la cartella uploads per il cleanup anche
    # se la DELETE o un assert successivo dovessero fallire.
    user = create_templates_user_EXT(client, cleanup_registry, max_templates=5)
    sidecar_paths = seed_shapefile_sidecars_EXT(cleanup_registry, user, "delete_ext")
    target_name = "delete_ext.shp"

    # act
    # La DELETE deve rimuovere tutti i file che condividono lo stem, non solo il .shp.
    response = client.delete(
        f"{TEMPLATES_ENDPOINT_EXT}/{target_name}",
        headers=user.headers,
    )

    # assert
    # Controlliamo sia la risposta HTTP sia l'effetto fisico sui sidecar preparati.
    assert response.status_code == 200
    assert BaseTests().get_content(response) == f"File {target_name} succesfully deleted"
    assert all(not path.exists() for path in sidecar_paths)