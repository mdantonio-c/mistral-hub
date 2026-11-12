"""Helper locali ai test di integrazione del postprocessing.

Creano utenti e request, eseguono il task Celery ``data_extract``
(tasks/data_extraction.py) con filtri e postprocessori e verificano l'esito
leggendo la tabella Request e i file GRIB prodotti.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

import dballe
import eccodes
import pytest
from faker import Faker
from flask import Flask
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager
import mistral.tasks.data_extraction as data_extraction_task
import restapi.connectors.celery as celery_connector
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

from mistral.tests.helpers.auth import register_test_user_cleanup

TASK_NAME = "data_extract"

ALCHEMY_USER = os.environ.get("ALCHEMY_USER")
ALCHEMY_PASSWORD = os.environ.get("ALCHEMY_PASSWORD")
ALCHEMY_HOST = os.environ.get("ALCHEMY_HOST")
ALCHEMY_DBTYPE = os.environ.get("ALCHEMY_DBTYPE")
ALCHEMY_PORT = os.environ.get("ALCHEMY_PORT")


@dataclass(frozen=True)
class PostprocessingUser:
    """Dati dell'utente temporaneo creato per uno scenario di postprocessing."""

    uuid: str
    user_id: int
    headers: Any
    output_dir: Path

    @property
    def root_dir(self) -> Path:
        """Restituisce la cartella dell'utente che contiene outputs e uploads."""
        return self.output_dir.parent

    @property
    def upload_dir(self) -> Path:
        """Restituisce la cartella uploads usata dai postprocessori con template."""
        return self.root_dir / "uploads"


class PostprocessingSupport(BaseTests):
    """Piccola estensione di BaseTests per creare request e verificarne l'esito."""

    def create_request(self, db, user_id: int, request_name: str) -> int:
        """Inserisce una riga Request e ne restituisce l'id.

        Usa ``SqlApiDbManager.create_request_record``, lo stesso service del backend.
        """
        request = SqlApiDbManager.create_request_record(db, user_id, request_name, {})
        return request.id

    def assert_extraction_success(self, db, request_id: int, user_dir: Path) -> Path:
        """Verifica che la request sia in SUCCESS e abbia prodotto un solo file.

        Il file deve esistere e non essere vuoto; viene restituito il suo percorso.
        """
        request = db.Request.query.filter_by(id=request_id).first()
        assert request is not None
        assert request.status == "SUCCESS"

        file_output = request.fileoutput
        assert file_output is not None

        output_path = user_dir / file_output.filename
        assert output_path.exists()
        assert output_path.stat().st_size != 0
        assert len(list(user_dir.glob("*"))) == 1

        return output_path

    def delete_request(self, client: FlaskClient, headers, request_id: int) -> None:
        """Cancella una request tramite l'endpoint DELETE /api/requests/<id>."""
        response = client.delete(f"{API_URI}/requests/{request_id}", headers=headers)
        assert response.status_code == 200


@dataclass
class PostprocessingEnv:
    """Raccoglie app, DB, utente e handle di cleanup di un singolo scenario."""

    base: PostprocessingSupport
    app: Flask
    client: FlaskClient
    faker: Faker
    db: Any
    cleanup_registry: Any
    dataset_name: str
    user: PostprocessingUser

    def create_request(self) -> int:
        """Crea una riga Request e registra subito il suo cleanup nel database."""
        request_id = self.base.create_request(
            self.db, self.user.user_id, self.faker.pystr()
        )
        self.cleanup_registry.add(lambda: delete_request_row(self.db, request_id))
        return request_id

    def execute(
        self,
        request_id: int,
        *,
        filters: dict[str, Any] | None = None,
        postprocessors: list[dict[str, Any]] | None = None,
        output_format: str | None = None,
        only_reliable: bool | None = None,
        expect_failure: bool = False,
    ) -> None:
        """Esegue il task Celery ``data_extract`` con i filtri e i postprocessori dati.

        Il task gira in modo sincrono tramite ``BaseTests.send_task``. Con
        ``expect_failure=True`` gli hook di fallimento di Celery e
        ``notify_by_email`` vengono sostituiti temporaneamente, cosi l'errore del
        postprocessing emerge come eccezione ``Ignore`` intercettabile dal test.
        """
        if not expect_failure:
            self.base.send_task(
                self.app,
                TASK_NAME,
                self.user.user_id,
                [self.dataset_name],
                None,
                filters,
                postprocessors or [],
                output_format,
                request_id,
                only_reliable,
            )
            return

        original_mark_task_as_failed = celery_connector.mark_task_as_failed
        original_mark_task_as_failed_ignore = celery_connector.mark_task_as_failed_ignore
        original_notify_by_email = data_extraction_task.notify_by_email

        def raise_task_ignore(*args, exception, **kwargs):
            """Trasforma il callback di fallimento nel ramo ``Ignore`` atteso dal test.

            Gli scenari di errore vogliono che l'estrazione si fermi esattamente
            dove il codice di postprocessing segnala l'errore, senza passare dalla
            normale gestione dei fallimenti lato worker.
            """
            raise celery_connector.Ignore(str(exception))

        def raise_original_ignore(*args, exception, **kwargs):
            """Rilancia l'eccezione originale per l'hook che segnala gia un ignore.

            Cosi la semantica del fallimento resta vicina al codice di produzione,
            ma il test intercetta l'errore prima che partano email o cleanup
            asincroni.
            """
            raise exception

        celery_connector.mark_task_as_failed = raise_task_ignore
        celery_connector.mark_task_as_failed_ignore = raise_original_ignore
        data_extraction_task.notify_by_email = lambda *args, **kwargs: None
        try:
            self.base.send_task(
                self.app,
                TASK_NAME,
                self.user.user_id,
                [self.dataset_name],
                None,
                filters,
                postprocessors or [],
                output_format,
                request_id,
                only_reliable,
            )
        finally:
            celery_connector.mark_task_as_failed = original_mark_task_as_failed
            celery_connector.mark_task_as_failed_ignore = (
                original_mark_task_as_failed_ignore
            )
            data_extraction_task.notify_by_email = original_notify_by_email

    def assert_success(self, request_id: int) -> Path:
        """Delega alla verifica di successo comune e restituisce il file prodotto."""
        return self.base.assert_extraction_success(
            self.db, request_id, self.user.output_dir
        )

    def assert_failure(
        self,
        request_id: int,
        expected_message: str | None = "Error in post-processing",
    ) -> None:
        """Verifica che la request sia in FAILURE.

        Se ``expected_message`` non e None, verifica anche che sia contenuto in
        ``request.error_message``.
        """
        request = self.db.Request.query.filter_by(id=request_id).first()
        assert request is not None
        assert request.status == "FAILURE"
        if expected_message is not None:
            assert expected_message in request.error_message

    def delete_request(self, request_id: int) -> None:
        """Cancella una request dell'utente dello scenario tramite l'API pubblica.

        Usa DELETE /api/requests/<id>. I test la chiamano quando devono rimuovere
        una request in modo esplicito, non solo nel teardown, ad esempio prima di
        ricostruire uno scenario con postprocessori o filtri diversi.
        """
        self.base.delete_request(self.client, self.user.headers, request_id)

    def ensure_upload_dir(self) -> Path:
        """Crea la cartella uploads se manca e ne restituisce il percorso."""
        self.user.upload_dir.mkdir(parents=True, exist_ok=True)
        return self.user.upload_dir

    def copy_upload(self, source: Path, filename: str) -> Path:
        """Copia un file nella cartella uploads dell'utente con il nome indicato."""
        target = self.ensure_upload_dir() / filename
        shutil.copyfile(source, target)
        return target

    def unzip_upload(self, archive_path: Path) -> Path:
        """Estrae un archivio di template nella cartella uploads dell'utente."""
        upload_dir = self.ensure_upload_dir()
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(upload_dir)
        return upload_dir


def delete_request_row(db, request_id: int) -> None:
    """Cancella direttamente dal database una riga Request, se esiste ancora."""
    request = db.Request.query.get(request_id)
    if request is None:
        return

    db.session.delete(request)
    db.session.commit()


def create_postprocessing_user(
    base: BaseTests,
    client: FlaskClient,
    dataset_ids: list[int],
) -> PostprocessingUser:
    """Crea un utente abilitato al postprocessing sui dataset indicati.

    Usa ``BaseTests.create_user`` e ``do_login`` (API reali di creazione utente e
    login) e restituisce id, header autenticati e cartella di output dell'utente.
    """
    data = {
        "disk_quota": 1073741824,
        "max_output_size": 1073741824,
        "allowed_postprocessing": True,
        "open_dataset": True,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids]),
    }
    uuid, created_user = base.create_user(client, data)
    headers, _ = base.do_login(
        client, created_user.get("email"), created_user.get("password")
    )

    db = sqlalchemy.get_instance()
    user = db.User.query.filter_by(uuid=uuid).first()
    assert user is not None

    return PostprocessingUser(
        uuid=uuid,
        user_id=user.id,
        headers=headers,
        output_dir=Path(DOWNLOAD_DIR, uuid, "outputs"),
    )


def register_user_cleanup(
    base: BaseTests,
    client: FlaskClient,
    cleanup_registry,
    user: PostprocessingUser,
) -> None:
    """Registra il cleanup dell'utente di test e della sua cartella su disco."""
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.root_dir,
    )


def require_observed_lastdays() -> int:
    """Calcola un override di LASTDAYS dai dati observed reali in DBALLE, o fa skip.

    Fa skip se le variabili ``ALCHEMY_*`` non sono configurate o se DBALLE non
    contiene dati observed. Il valore viene usato per ``BeDballe.LASTDAYS``
    (services/dballe.py).
    """
    if not all(
        (
            ALCHEMY_USER,
            ALCHEMY_PASSWORD,
            ALCHEMY_HOST,
            ALCHEMY_DBTYPE,
            ALCHEMY_PORT,
        )
    ):
        pytest.skip("DBALLE connection variables are not configured")

    dballe_db = dballe.DB.connect(
        "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
            engine=ALCHEMY_DBTYPE,
            user=ALCHEMY_USER,
            pw=ALCHEMY_PASSWORD,
            host=ALCHEMY_HOST,
            port=ALCHEMY_PORT,
        )
    )
    with dballe_db.transaction() as transaction:
        for row in transaction.query_data({}):
            date_to_dt = datetime(
                row["year"],
                row["month"],
                row["day"],
                row["hour"],
                row["min"],
            ) + timedelta(hours=1)
            date_from_dt = date_to_dt - timedelta(hours=1)
            last_dballe_date = date_from_dt - timedelta(days=1)
            return (datetime.now() - last_dballe_date).days

    pytest.skip("No DBALLE observed data available in this environment")


def forecast_pressure_filter() -> dict[str, Any]:
    """Restituisce il filtro forecast di base (pressione) usato da piu scenari."""
    return {
        "product": [
            {
                "desc": "P Pressure Pa",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 1,
                "active": "true",
            }
        ]
    }


def forecast_derived_variable_postprocessor() -> dict[str, Any]:
    """Restituisce il postprocessore ``derived_variables`` per i dati forecast.

    Chiede la variabile B13003 (umidita relativa), calcolata nel task
    ``data_extract`` da ``tools/derived_variables.py``.
    """
    return {
        "processor_type": "derived_variables",
        "variables": ["B13003"],
    }


def forecast_derived_variable_filters() -> dict[str, Any]:
    """Restituisce i filtri forecast validi per calcolare l'umidita derivata."""
    return {
        "product": [
            {
                "desc": "P Pressure Pa",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 1,
                "active": "true",
            },
            {
                "desc": "T Temperature K",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 11,
                "active": "true",
            },
            {
                "desc": "None Dew-point temperature K",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 17,
                "active": "true",
            },
            {
                "desc": "Q Specific humidity kg kg^-1",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 51,
                "active": "true",
            },
        ]
    }


def forecast_statistic_elaboration_postprocessor() -> dict[str, Any]:
    """Restituisce il postprocessore ``statistic_elaboration`` per i dati forecast.

    Elabora intervalli di 3 ore; nel task ``data_extract`` viene eseguito da
    ``tools/statistic_elaboration.py``.
    """
    return {
        "processor_type": "statistic_elaboration",
        "input_timerange": 1,
        "output_timerange": 1,
        "interval": "hours",
        "step": 3,
    }


def forecast_statistic_elaboration_filters() -> dict[str, Any]:
    """Restituisce i filtri forecast validi per la statistica sulla precipitazione."""
    return {
        "product": [
            {
                "desc": "TP Total precipitation kg m^-2",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 61,
                "active": "true",
            },
            {
                "desc": "P Pressure Pa",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 1,
                "active": "true",
            },
        ]
    }


def forecast_derived_variable_missing_filters() -> dict[str, Any]:
    """Restituisce filtri forecast volutamente incompleti (solo pressione).

    Servono ai test di errore: ``derived_variables`` non trova i campi necessari.
    """
    return {
        "product": [
            {
                "style": "GRIB1",
                "origin": 80,
                "product": 1,
                "table": 2,
                "desc": "P Pressure Pa",
                "active": "true",
            }
        ]
    }


def forecast_statistic_elaboration_missing_filters() -> dict[str, Any]:
    """Restituisce filtri forecast volutamente non validi per la statistica.

    Servono ai test di errore: il timerange selezionato non e adatto al
    postprocessore ``statistic_elaboration``.
    """
    return {
        "product": [
            {
                "desc": "TP Total precipitation kg m^-2",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 61,
                "active": "true",
            }
        ],
        "timerange": [
            {
                "style": "GRIB1",
                "p1": 0,
                "p2": 0,
                "trange_type": 0,
                "unit": 1,
                "desc": "Forecast product valid at reference time + P1 (P1>0) - time unit 1",
                "active": "true",
            }
        ],
    }


def forecast_chaining_filters() -> dict[str, Any]:
    """Restituisce i filtri forecast per gli scenari con postprocessori in catena."""
    return {
        "product": [
            {
                "desc": "P Pressure Pa",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 1,
                "active": "true",
            },
            {
                "desc": "T Temperature K",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 11,
                "active": "true",
            },
            {
                "desc": "None Dew-point temperature K",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 17,
                "active": "true",
            },
            {
                "desc": "Q Specific humidity kg kg^-1",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 51,
                "active": "true",
            },
            {
                "desc": "TP Total precipitation kg m^-2",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 61,
                "active": "true",
            },
        ]
    }


def grid_interpolation_without_template(
    *, x_min: int, y_min: int, nx: int
) -> dict[str, Any]:
    """Restituisce il postprocessore ``grid_interpolation`` con geometria esplicita."""
    return {
        "processor_type": "grid_interpolation",
        "boundings": {
            "x_min": x_min,
            "x_max": 20,
            "y_min": y_min,
            "y_max": 10,
        },
        "nodes": {"nx": nx, "ny": nx},
        "trans_type": "inter",
        "sub_type": "bilin",
    }


def grid_interpolation_with_template(template_path: Path) -> dict[str, Any]:
    """Restituisce il postprocessore ``grid_interpolation`` basato su un template.

    La geometria della griglia viene presa dal file GRIB indicato in
    ``template_path``.
    """
    return {
        "processor_type": "grid_interpolation",
        "template": template_path,
        "trans_type": "inter",
        "sub_type": "bilin",
    }


def grid_cropping_postprocessor(
    *, initial_lon: int, initial_lat: int, final_lon: int, final_lat: int
) -> dict[str, Any]:
    """Restituisce il postprocessore ``grid_cropping`` (ritaglio della griglia).

    L'area deve intersecare la griglia: con aree esterne lo zoom di libsim 8.0.0
    va in crash.
    """
    return {
        "processor_type": "grid_cropping",
        "boundings": {
            "ilon": initial_lon,
            "ilat": initial_lat,
            "flon": final_lon,
            "flat": final_lat,
        },
        "trans_type": "zoom",
        "sub_type": "coord",
    }


def spare_point_postprocessor(template_path: Path) -> dict[str, Any]:
    """Restituisce il postprocessore ``spare_point_interpolation`` con shapefile."""
    return {
        "processor_type": "spare_point_interpolation",
        "coord_filepath": template_path,
        "file_format": "shp",
        "trans_type": "inter",
        "sub_type": "bilin",
    }


def require_spare_point_template_archive() -> Path:
    """Restituisce l'archivio template per lo spare-point, o fa skip se manca."""
    archive_path = Path("/data/templates_for_pp/template_for_spare_point.zip")
    if not archive_path.exists():
        pytest.skip("Spare point template archive is not available in this environment")
    return archive_path


def observed_derived_variable_postprocessor() -> dict[str, Any]:
    """Restituisce il postprocessore ``derived_variables`` per i dati observed.

    Chiede la variabile B12103 (temperatura di rugiada).
    """
    return {
        "processor_type": "derived_variables",
        "variables": ["B12103"],
    }


def observed_derived_variable_filters() -> dict[str, Any]:
    """Restituisce i filtri observed validi richiesti dalle variabili derivate."""
    return {
        "product": [
            {
                "code": "B12101",
                "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                "active": "true",
            },
            {
                "code": "B13003",
                "desc": "RELATIVE HUMIDITY",
                "active": "true",
            },
        ]
    }


def observed_derived_variable_missing_filters() -> dict[str, Any]:
    """Restituisce filtri observed volutamente incompleti per i test di errore."""
    return {
        "product": [
            {
                "code": "B12101",
                "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                "active": "true",
            }
        ]
    }


def observed_statistic_elaboration_postprocessor() -> dict[str, Any]:
    """Restituisce il postprocessore ``statistic_elaboration`` per i dati observed."""
    return {
        "processor_type": "statistic_elaboration",
        "input_timerange": 1,
        "output_timerange": 1,
        "interval": "hours",
        "step": 1,
    }


def observed_statistic_elaboration_filters() -> dict[str, Any]:
    """Restituisce i filtri observed validi per l'elaborazione statistica."""
    return {
        "product": [
            {
                "code": "B12101",
                "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                "active": "true",
            },
            {
                "code": "B13011",
                "desc": "TOTAL PRECIPITATION / TOTAL WATER EQUIVALENT",
                "active": "true",
            },
        ]
    }


def observed_chaining_filters() -> dict[str, Any]:
    """Restituisce i filtri observed per i test con postprocessori in catena."""
    return {
        "product": [
            {
                "code": "B12101",
                "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                "active": "true",
            },
            {
                "code": "B13003",
                "desc": "RELATIVE HUMIDITY",
                "active": "true",
            },
            {
                "code": "B13011",
                "desc": "TOTAL PRECIPITATION / TOTAL WATER EQUIVALENT",
                "active": "true",
            },
        ]
    }


def iter_grib_messages(file_path: Path) -> Iterator[int]:
    """Restituisce uno alla volta gli handle GRIB di un file e li rilascia dopo."""
    with open(file_path, "rb") as file_handle:
        while True:
            gid = eccodes.codes_grib_new_from_file(file_handle)
            if gid is None:
                break
            try:
                yield gid
            finally:
                eccodes.codes_release(gid)


def assert_grib_contains_short_name(file_path: Path, short_name: str) -> None:
    """Verifica che almeno un messaggio GRIB abbia lo shortName richiesto."""
    assert any(
        eccodes.codes_get(gid, "shortName") == short_name
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_preserves_independent_fields(
    file_path: Path, derived_short_name: str
) -> None:
    """Verifica che l'output contenga almeno un campo diverso da quello derivato.

    Cioe un messaggio GRIB con shortName diverso da ``derived_short_name``.
    """
    assert any(
        eccodes.codes_get(gid, "shortName") != derived_short_name
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_contains_step_range(
    file_path: Path, short_name: str, step_range: str
) -> None:
    """Verifica che un messaggio GRIB abbia sia lo shortName sia lo stepRange attesi."""
    assert any(
        eccodes.codes_get(gid, "shortName") == short_name
        and eccodes.codes_get(gid, "stepRange") == step_range
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_contains_short_name_other_than(
    file_path: Path, excluded_short_name: str, expected_short_name: str
) -> None:
    """Verifica che l'output contenga un campo indipendente (non quello trasformato).

    Nota: ``excluded_short_name`` non viene usato; si controlla solo la presenza
    di ``expected_short_name``.
    """
    assert any(
        eccodes.codes_get(gid, "shortName") == expected_short_name
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_geometry(file_path: Path, min_lat: int, nx: int) -> None:
    """Verifica la geometria della griglia sul primo messaggio GRIB del file."""
    for gid in iter_grib_messages(file_path):
        assert eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees") == min_lat
        assert eccodes.codes_get(gid, "Ni") == nx
        return
    raise AssertionError(f"No GRIB messages found in {file_path}")


def assert_grib_messages_have_geometry(file_path: Path, min_lat: int, nx: int) -> None:
    """Verifica la stessa geometria di griglia su tutti i messaggi GRIB del file."""
    for gid in iter_grib_messages(file_path):
        assert eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees") == min_lat
        assert eccodes.codes_get(gid, "Ni") == nx