# EXTENSION TRACEABILITY - Prompt 05, supporto locale per il dominio templates.
# Origine: questo modulo e stato aggiunto per evitare duplicazione tra i nuovi test
# di listing e upload/delete dell'endpoint projects/mistral/backend/endpoints/templates.py.
# Ambito: prepara utenti temporanei con quota e limite template espliciti, crea file
# template sintetici nelle cartelle uploads/grib e uploads/shp, e costruisce archivi zip
# minimali per validare il wiring HTTP senza invocare strumenti GDAL reali.
# Finestra dati: nessun dataset meteorologico reale viene letto o richiesto; tutti i
# contenuti sono byte/stringhe sintetiche scritte sotto la directory utente temporanea.
# Runtime fake: non servono worker, broker o servizi esterni; l'unico comportamento di
# runtime e il filesystem locale del container, sempre ripulito dal cleanup_registry.
# Cleanup: ogni utente viene cancellato via API admin e la directory /data/<uuid> viene
# registrata con cleanup_registry.add_path; gli upload diretti registrano anche uploads.
# Baseline non toccata: il modulo e un nuovo artefatto *_EXT.py e non crea fixture
# globali ne conftest.py locali, mantenendo confinata l'estensione al dominio templates.

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

from mistral.endpoints import DOWNLOAD_DIR
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.config import DATA_PATH
from restapi.tests import API_URI, BaseTests, FlaskClient


TEMPLATES_ENDPOINT_EXT = f"{API_URI}/templates"


def create_templates_user_EXT(
    client: FlaskClient,
    cleanup_registry,
    *,
    max_templates: int | None = 5,
    disk_quota: int = 1073741824,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo con permessi template controllati.

    Il helper passa dal canale API usato dalla suite per creare utenti, poi registra
    cleanup sia applicativo sia filesystem. I test possono variare max_templates e
    disk_quota per raggiungere i rami 401/403 dell'endpoint senza dipendere da profili
    preesistenti nel runtime locale o CI.
    """
    # Prepariamo uno stato utente chiuso: quota disco e numero massimo di template sono
    # il contratto osservabile di questo prompt, quindi vengono sempre dichiarati qui.
    permissions = {
        "disk_quota": disk_quota,
        "max_output_size": disk_quota,
        "max_templates": max_templates,
        "open_dataset": True,
    }
    base = BaseTests()
    user = create_authenticated_test_user(base, client, permissions)

    # Registriamo subito la rimozione dell'utente e della sua directory /data/<uuid>:
    # i test di upload creano file fisici e devono poter fallire senza lasciare residui.
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=Path(DOWNLOAD_DIR, user.uuid),
    )
    return user


def uploads_root_EXT(user: AuthenticatedTestUser) -> Path:
    """Restituisce la radice uploads del solo utente temporaneo sotto test."""
    # Centralizziamo il path per evitare che i test ricostruiscano a mano la struttura
    # /data/<uuid>/uploads e rischino di puntare a una cartella non ripulita.
    return DATA_PATH.joinpath(user.uuid, "uploads")


def template_folder_EXT(user: AuthenticatedTestUser, template_format: str) -> Path:
    """Restituisce la cartella grib o shp usata dall'endpoint templates."""
    # Il controller separa i template per formato; il helper mantiene la stessa regola
    # in un unico punto cosi listing, max_allowed e delete usano uno scenario coerente.
    return uploads_root_EXT(user).joinpath(template_format)


def seed_template_file_EXT(
    cleanup_registry,
    user: AuthenticatedTestUser,
    filename: str,
    *,
    content: bytes = b"template-ext-content",
) -> Path:
    """Crea un template sintetico nella cartella dedotta dall'estensione.

    Il listing dell'endpoint legge direttamente dal filesystem, quindi questo helper
    prepara file minimi senza passare dall'upload quando il test deve isolare i rami GET
    o DELETE. La directory uploads viene registrata esplicitamente nel cleanup_registry.
    """
    # Scegliamo il sottofolder con la stessa convenzione dell'endpoint: i grib stanno in
    # uploads/grib, mentre shapefile e sidecar stanno in uploads/shp.
    suffix = Path(filename).suffix.lower()
    template_format = "grib" if suffix == ".grib" else "shp"
    folder = template_folder_EXT(user, template_format)
    folder.mkdir(parents=True, exist_ok=True)
    cleanup_registry.add_path(uploads_root_EXT(user))

    # Scriviamo contenuti sintetici: il contratto sotto test non legge semantica meteo o
    # shapefile reali, ma solo presenza, nome, dimensione e rimozione dei file.
    filepath = folder.joinpath(filename)
    filepath.write_bytes(content)
    return filepath


def seed_shapefile_sidecars_EXT(
    cleanup_registry,
    user: AuthenticatedTestUser,
    stem: str = "shape_ext",
    *,
    suffixes: Iterable[str] = (".shp", ".shx", ".dbf", ".prj"),
) -> list[Path]:
    """Crea un set di sidecar shapefile con stesso stem per testare DELETE.

    Il backend cancella con glob sullo stem del file .shp. Generare piu sidecar con lo
    stesso prefisso consente al test di verificare il cleanup applicativo senza ricorrere
    a shapefile reali o conversioni GDAL.
    """
    # Prepariamo i file nello stesso folder letto dall'endpoint, registrando il cleanup
    # prima della scrittura per garantire rimozione anche se un assert successivo fallisce.
    folder = template_folder_EXT(user, "shp")
    folder.mkdir(parents=True, exist_ok=True)
    cleanup_registry.add_path(uploads_root_EXT(user))

    created_paths: list[Path] = []
    for suffix in suffixes:
        path = folder.joinpath(f"{stem}{suffix}")
        path.write_bytes(f"{stem}{suffix}".encode("utf-8"))
        created_paths.append(path)
    return created_paths


def build_shapefile_zip_EXT(
    stem: str = "shape_ext",
    *,
    include_shx: bool = True,
    include_dbf: bool = True,
) -> io.BytesIO:
    """Costruisce in memoria uno zip shapefile minimale per l'upload HTTP.

    Il controller valida solo nomi ed estensioni prima di estrarre l'archivio; i byte non
    devono essere uno shapefile reale. Questo evita dipendenze da GDAL e mantiene il test
    completamente deterministico sul filesystem temporaneo dell'utente.
    """
    # Costruiamo lo zip in memoria, cosi il test non crea file temporanei fuori dalla
    # directory utente e non richiede cleanup aggiuntivo oltre agli upload estratti.
    archive = io.BytesIO()
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr(f"{stem}.shp", b"synthetic shp")
        if include_shx:
            zip_file.writestr(f"{stem}.shx", b"synthetic shx")
        if include_dbf:
            zip_file.writestr(f"{stem}.dbf", b"synthetic dbf")
    archive.seek(0)
    return archive


def upload_payload_EXT(content: bytes | io.BytesIO, filename: str) -> dict[str, object]:
    """Restituisce il payload multipart atteso dal client Flask per Template.post.

    Tenere il dettaglio `file: (stream, filename)` in un helper locale rende esplicito
    che i test stanno attraversando il vero endpoint HTTP e non chiamando direttamente
    Uploader.upload o funzioni interne del controller.
    """
    # Normalizziamo i bytes in BytesIO solo qui, lasciando ai test il compito di indicare
    # quale nome file e quale estensione vogliono esercitare.
    stream = content if isinstance(content, io.BytesIO) else io.BytesIO(content)
    stream.seek(0)
    return {"file": (stream, filename)}


def listed_filenames_EXT(files: list[object]) -> set[str]:
    """Estrae i nomi file da una lista serializzata di Path restituita dal listing."""
    # Il serializer REST puo restituire Path come stringhe assolute: confrontare solo il
    # nome rende gli assert stabili rispetto al prefisso /data del container.
    return {Path(str(file_item)).name for file_item in files}