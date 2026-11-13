# Test di POST, GET e DELETE /templates: upload, lettura e cancellazione dei template
# utente (endpoints/templates.py).
# Ambito: copre upload grib, upload zip shapefile completo, validazioni su zip incompleto,
# estensione non ammessa, errori imprevisti dell'upload, quota disco (superata, senza
# doppio conteggio), limite max_templates (anche per zip), get/delete di file esistenti
# o mancanti, rimozione dei soli sidecar con lo stesso stem e status OpenAPI.
# Finestra dati: nessun dato meteo reale viene usato; i file grib e shapefile sono byte
# sintetici creati per attraversare solo contratti HTTP e filesystem deterministici.
# Runtime fake: non vengono avviati GDAL, worker o broker; gli zip shapefile contengono
# nomi e byte minimi sufficienti al controller, senza conversione geojson.
# Cleanup: utenti e directory /data/<uuid>/uploads sono registrati con cleanup_registry;
# anche i rami di errore vengono confinati alla directory utente temporanea.

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import mistral.endpoints.templates as templates_endpoint
import pytest
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.integration.templates.support import (
    TEMPLATES_ENDPOINT,
    build_shapefile_zip,
    create_templates_user,
    seed_shapefile_sidecars,
    seed_template_file,
    template_folder,
    upload_payload,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_template_upload_accepts_valid_grib_file(
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
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    filename = "valid_grib_ext.grib"

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"GRIB EXT", filename),
    )

    # assert
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert content["format"] == "grib"
    assert Path(str(content["filepath"])).name == filename
    assert template_folder(user, "grib").joinpath(filename).exists()


def test_template_upload_accepts_complete_shapefile_zip(
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
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    archive = build_shapefile_zip("complete_zip_ext")

    # act
    # L'endpoint salva lo zip, lo estrae in uploads/shp e poi rimuove l'archivio.
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(archive, "complete_zip_ext.zip"),
    )

    # assert
    assert response.status_code == 200
    shp_folder = template_folder(user, "shp")
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
def test_template_upload_rejects_incomplete_shapefile_zip(
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
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    archive = build_shapefile_zip(
        "incomplete_zip_ext",
        include_shx=include_shx,
        include_dbf=include_dbf,
    )

    # act
    # Il controllo avviene prima dell'upload su disco, quindi la risposta deve essere un
    # errore di validazione BadRequest.
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(archive, "incomplete_zip_ext.zip"),
    )

    # assert
    # Oltre al 400 controlliamo il messaggio per distinguere chiaramente i due rami.
    assert response.status_code == 400
    assert BaseTests().get_content(response) == expected_message


def test_template_upload_rejects_wrong_extension(
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
    user = create_templates_user(client, cleanup_registry, max_templates=5)

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"not a template", "wrong_ext.txt"),
    )

    # assert
    # Il BadRequest di Uploader arriva al client invariato (status e messaggio) e la
    # pulizia dopo l'errore non deve fallire se la cartella non e mai stata creata.
    assert response.status_code == 400
    assert BaseTests().get_content(response) == "File extension not allowed"
    assert not template_folder(user, "shp").exists()


def test_template_upload_returns_403_when_disk_quota_is_exceeded(
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
    user = create_templates_user(
        client,
        cleanup_registry,
        max_templates=5,
        disk_quota=1,
    )
    archive = build_shapefile_zip("quota_zip_ext")

    sentinel = seed_template_file(cleanup_registry, user, "quota_zip_ext_old.shp")

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(archive, "quota_zip_ext.zip"),
    )

    # assert
    # Il rifiuto rimuove tutti i file creati dall'upload (zip ed estratti), ma non i
    # template preesistenti, anche se il loro nome inizia con lo stesso prefisso.
    assert response.status_code == 403
    assert BaseTests().get_content(response) == "Disk quota exceeded"
    assert sorted(p.name for p in template_folder(user, "shp").iterdir()) == [
        sentinel.name
    ]


def test_template_upload_returns_401_when_max_templates_is_reached(
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
    user = create_templates_user(client, cleanup_registry, max_templates=1)
    seed_template_file(cleanup_registry, user, "already_present_ext.grib")

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"second grib", "second_ext.grib"),
    )

    # assert
    # L'endpoint usa Unauthorized per il limite max_templates, come documentato dal ramo
    # attuale del controller.
    assert response.status_code == 401
    assert (
        BaseTests().get_content(response)
        == "user has reached the max number of templates of this kind"
    )


def test_template_get_existing_file_returns_filepath_and_format(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che GET /templates/<template_name> su file esistente risponda 200.

    La risposta contiene filepath e format del template (regressione TEMPLATES-001: il
    controllo di esistenza era invertito).
    """
    # arrange
    # Seediamo un grib fisico nel path esatto letto dal controller per evitare ambiguita
    # tra file mancante e bug del ramo get.
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    filepath = seed_template_file(cleanup_registry, user, "get_existing_ext.grib")

    # act
    response = client.get(
        f"{TEMPLATES_ENDPOINT}/{filepath.name}",
        headers=user.headers,
    )

    # assert
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert Path(str(content["filepath"])).name == filepath.name
    assert content["format"] == "grib"


def test_template_get_missing_file_returns_404(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che GET /templates/<template_name> su file mancante risponda 404.

    Regressione TEMPLATES-001: con il controllo invertito la risposta era 200 con un
    filepath inesistente.
    """
    # arrange
    # Creiamo soltanto l'utente, senza scrivere il file richiesto, per isolare il ramo
    # missing-template del controller.
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    missing_name = "missing_template_ext.grib"

    # act
    response = client.get(
        f"{TEMPLATES_ENDPOINT}/{missing_name}",
        headers=user.headers,
    )

    # assert
    assert response.status_code == 404
    assert BaseTests().get_content(response) == "The template doesn't exist"


def test_template_delete_missing_file_returns_404(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che DELETE /templates/<template_name> ritorni 404 su file assente.

    Questo ramo non dipende dal bug del GET: il controller delete verifica correttamente
    l'assenza del path prima di tentare la cancellazione dei sidecar.
    """
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=5)

    # act
    response = client.delete(
        f"{TEMPLATES_ENDPOINT}/missing_delete_ext.shp",
        headers=user.headers,
    )

    # assert
    assert response.status_code == 404
    assert BaseTests().get_content(response) == "The template doesn't exist"


def test_template_delete_removes_shapefile_sidecars_with_same_stem(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che DELETE rimuova .shp e sidecar con lo stesso stem, e solo quelli.

    Il backend cancella i file con esattamente lo stesso nome (estensione esclusa)
    dello shapefile. Un altro shapefile il cui nome inizia con lo stesso prefisso deve
    restare intatto. I file sono sintetici: niente shapefile validi o tool esterni.
    """
    # arrange
    # Prepariamo sidecar minimali e registriamo la cartella uploads per il cleanup anche
    # se la DELETE o un assert successivo dovessero fallire.
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    sidecar_paths = seed_shapefile_sidecars(cleanup_registry, user, "delete_ext")
    other_template_paths = seed_shapefile_sidecars(
        cleanup_registry, user, "delete_ext_nord"
    )
    target_name = "delete_ext.shp"

    # act
    # La DELETE deve rimuovere tutti i file che condividono lo stem, non solo il .shp.
    response = client.delete(
        f"{TEMPLATES_ENDPOINT}/{target_name}",
        headers=user.headers,
    )

    # assert
    assert response.status_code == 200
    assert BaseTests().get_content(response) == f"File {target_name} succesfully deleted"
    assert not any(path.exists() for path in sidecar_paths)
    assert all(path.exists() for path in other_template_paths)
    assert all(not path.exists() for path in sidecar_paths)


def test_template_delete_grib_removes_only_requested_file(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che DELETE di un grib non cancelli altri grib con lo stesso prefisso."""
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    target = seed_template_file(cleanup_registry, user, "alpha_ext.grib")
    other = seed_template_file(cleanup_registry, user, "alpha_ext2.grib")

    # act
    response = client.delete(
        f"{TEMPLATES_ENDPOINT}/{target.name}",
        headers=user.headers,
    )

    # assert
    assert response.status_code == 200
    assert not target.exists()
    assert other.exists()


def test_template_upload_grib_over_quota_returns_403_and_removes_the_file(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un grib oltre quota dia 403 e non resti su disco.

    I template gia presenti restano al loro posto.
    """
    # arrange
    user = create_templates_user(
        client,
        cleanup_registry,
        max_templates=5,
        disk_quota=1,
    )
    sentinel = seed_template_file(cleanup_registry, user, "quota_grib_ext_old.grib")

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"GRIB OVER QUOTA", "quota_grib_ext.grib"),
    )

    # assert
    assert response.status_code == 403
    assert BaseTests().get_content(response) == "Disk quota exceeded"
    assert sorted(p.name for p in template_folder(user, "grib").iterdir()) == [
        sentinel.name
    ]


def test_template_upload_within_quota_is_accepted(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica che la dimensione del nuovo file non venga contata due volte.

    `du` misura la cartella utente dopo l'upload, quindi include gia il nuovo file:
    con 95 byte usati su una quota di 100 un file da 10 byte rientra nella quota.
    """
    # arrange
    # Sostituiamo solo il nome `subprocess` del modulo endpoint: `du` restituisce
    # una misura controllata invece di quella reale della cartella.
    monkeypatch.setattr(
        templates_endpoint,
        "subprocess",
        SimpleNamespace(check_output=lambda *args, **kwargs: b"95\t/data/user\n"),
    )
    user = create_templates_user(
        client,
        cleanup_registry,
        max_templates=5,
        disk_quota=100,
    )
    filename = "within_quota_ext.grib"

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"0123456789", filename),
    )

    # assert
    assert response.status_code == 200
    assert template_folder(user, "grib").joinpath(filename).exists()


def test_template_upload_returns_401_when_templates_exceed_the_limit(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il rifiuto quando i template presenti superano gia il limite.

    Succede per esempio se l'amministratore abbassa max_templates.
    """
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=1)
    seed_template_file(cleanup_registry, user, "over_limit_ext_1.grib")
    seed_template_file(cleanup_registry, user, "over_limit_ext_2.grib")

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"third grib", "over_limit_ext_3.grib"),
    )

    # assert
    assert response.status_code == 401
    assert not template_folder(user, "grib").joinpath("over_limit_ext_3.grib").exists()


def test_template_upload_zip_is_counted_with_the_type_it_contains(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che uno zip con un grib sia contato tra i grib, non tra gli shapefile.

    Con il limite grib raggiunto l'upload e rifiutato senza scrivere file.
    """
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=1)
    existing = seed_template_file(cleanup_registry, user, "zip_limit_ext_old.grib")
    archive = io.BytesIO()
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr("zip_limit_ext.grib", b"synthetic grib")
    archive.seek(0)

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(archive, "zip_limit_ext.zip"),
    )

    # assert
    assert response.status_code == 401
    assert [p.name for p in template_folder(user, "grib").iterdir()] == [existing.name]
    assert not template_folder(user, "shp").exists()


def test_template_upload_zip_is_counted_with_all_the_templates_it_contains(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che uno zip con due shapefile non superi un limite di un template."""
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=1)
    cleanup_registry.add_path(template_folder(user, "shp").parent)
    archive = io.BytesIO()
    with ZipFile(archive, "w") as zip_file:
        for stem in ("two_shp_ext_a", "two_shp_ext_b"):
            for suffix in (".shp", ".shx", ".dbf"):
                zip_file.writestr(f"{stem}{suffix}", b"synthetic")
    archive.seek(0)

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(archive, "two_shp_ext.zip"),
    )

    # assert
    assert response.status_code == 401
    assert not template_folder(user, "shp").exists()


def test_template_upload_unexpected_error_removes_only_its_own_file(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica la pulizia dopo un errore imprevisto dell'upload.

    Viene rimosso solo il file scritto da questo upload: zip e geojson rimasti da
    upload precedenti nella stessa cartella non vengono toccati. Il client riceve
    l'errore generico del server.
    """
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    previous_zip = seed_template_file(cleanup_registry, user, "previous_ext.zip")
    previous_geojson = seed_template_file(
        cleanup_registry, user, "previous_ext.geojson"
    )

    def failing_upload(self, subfolder: Path, force: bool = False):
        # Simula un errore dopo la scrittura del file.
        subfolder.joinpath("failing_ext.zip").write_bytes(b"partial upload")
        raise RuntimeError("synthetic failure after writing the file")

    monkeypatch.setattr(templates_endpoint.Template, "upload", failing_upload)

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(build_shapefile_zip("failing_ext"), "failing_ext.zip"),
    )

    # assert
    assert response.status_code == 500
    assert BaseTests().get_content(response) == "Unable to upload the template file"
    assert not template_folder(user, "shp").joinpath("failing_ext.zip").exists()
    assert previous_zip.exists()
    assert previous_geojson.exists()


def test_template_upload_openapi_documents_the_returned_status(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che l'OpenAPI di POST /templates dichiari 200, come la risposta reale.

    La risposta reale dell'upload riuscito (200) e coperta dal test sul grib valido.
    """
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=5)

    # act
    response = client.get(f"{API_URI}/specs", headers=user.headers)

    # assert
    assert response.status_code == 200
    specs = BaseTests().get_content(response)
    responses = specs["paths"]["/api/templates"]["post"]["responses"]
    assert "200" in responses
    assert "202" not in responses


def test_template_upload_rejects_uploader_validation_errors_unchanged(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che un file gia presente resti intatto quando l'upload lo rifiuta.

    Il Conflict di Uploader (file gia esistente) arriva al client invariato e il file
    preesistente con lo stesso nome non viene cancellato dalla pulizia dell'errore.
    """
    # arrange
    user = create_templates_user(client, cleanup_registry, max_templates=5)
    existing = seed_template_file(
        cleanup_registry, user, "existing_ext.grib", content=b"original grib"
    )

    # act
    response = client.post(
        TEMPLATES_ENDPOINT,
        headers=user.headers,
        data=upload_payload(b"new grib", existing.name),
    )

    # assert
    assert response.status_code == 409
    assert existing.read_bytes() == b"original grib"
