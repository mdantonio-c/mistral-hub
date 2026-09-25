"""Postprocessing-domain support helpers kept local to the postprocessing integration area."""

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
    """Temporary user metadata tailored to postprocessing scenarios."""

    uuid: str
    user_id: int
    headers: Any
    output_dir: Path

    @property
    def root_dir(self) -> Path:
        """Return the per-user root directory that contains outputs and uploads."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        return self.output_dir.parent

    @property
    def upload_dir(self) -> Path:
        """Return the upload directory used by template-based postprocessors."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        return self.root_dir / "uploads"


class PostprocessingSupport(BaseTests):
    """Small wrapper around BaseTests for request creation and extraction assertions."""

    def create_request(self, db, user_id: int, request_name: str) -> int:
        """Insert one request row and return its numeric identifier."""
        # Costruiamo lo stato controllato richiesto dal test, usando gli stessi canali
        # che il backend espone in produzione quando possibile.
        request = SqlApiDbManager.create_request_record(db, user_id, request_name, {})
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return request.id

    def assert_extraction_success(self, db, request_id: int, user_dir: Path) -> Path:
        """Assert that a request completed successfully and produced exactly one output file."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        request = db.Request.query.filter_by(id=request_id).first()
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert request is not None
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert request.status == "SUCCESS"

        file_output = request.fileoutput
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert file_output is not None

        output_path = user_dir / file_output.filename
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.exists()
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.stat().st_size != 0
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert len(list(user_dir.glob("*"))) == 1

        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return output_path

    def delete_request(self, client: FlaskClient, headers, request_id: int) -> None:
        """Delete one postprocessing request through the public requests endpoint."""
        # Rimuoviamo lo stato creato dal test per non lasciare dati che possano
        # influenzare gli scenari successivi.
        response = client.delete(f"{API_URI}/requests/{request_id}", headers=headers)
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine
        # prima di usare il payload.
        assert response.status_code == 200


@dataclass
class PostprocessingEnv:
    """Bundle together the app, DB, user, and cleanup handles for one test scenario."""

    base: PostprocessingSupport
    app: Flask
    client: FlaskClient
    faker: Faker
    db: Any
    cleanup_registry: Any
    dataset_name: str
    user: PostprocessingUser

    def create_request(self) -> int:
        """Create one request row and register DB cleanup for its identifier."""
        # Costruiamo lo stato controllato richiesto dal test, usando gli stessi canali
        # che il backend espone in produzione quando possibile.
        request_id = self.base.create_request(
            self.db, self.user.user_id, self.faker.pystr()
        )
        # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta
        # affidabile anche in caso di fallimento.
        self.cleanup_registry.add(lambda: delete_request_row(self.db, request_id))
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
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
        """Send the extraction task with the provided filters and postprocessors."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        if not expect_failure:
            # Intercettiamo l'invio del task per controllare quale lavoro asincrono
            # sarebbe stato richiesto dal backend.
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
            """Turn the failure callback into the ``Ignore`` path expected by the test.

            Failure-oriented scenarios want the extraction flow to stop exactly
            where the postprocessing code reports an error, without sending the
            test down the normal worker-side failure handling branch.
            """
            # Entriamo nel blocco operativo dell'helper post-processing, mantenendo
            # esplicito quale stato viene letto o prodotto.
            raise celery_connector.Ignore(str(exception))

        def raise_original_ignore(*args, exception, **kwargs):
            """Re-raise the original exception for hooks that already signal ignore.

            This keeps the failure semantics close to the production code while
            still letting the test intercept the error before email side effects
            or asynchronous cleanup are triggered.
            """
            # Entriamo nel blocco operativo dell'helper post-processing, mantenendo
            # esplicito quale stato viene letto o prodotto.
            raise exception

        celery_connector.mark_task_as_failed = raise_task_ignore
        celery_connector.mark_task_as_failed_ignore = raise_original_ignore
        data_extraction_task.notify_by_email = lambda *args, **kwargs: None
        try:
            # Intercettiamo l'invio del task per controllare quale lavoro asincrono
            # sarebbe stato richiesto dal backend.
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
        """Delegate to the shared success assertion and return the produced file path."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        return self.base.assert_extraction_success(
            self.db, request_id, self.user.output_dir
        )

    def assert_failure(
        self,
        request_id: int,
        expected_message: str | None = "Error in post-processing",
    ) -> None:
        """Assert that a request failed and optionally match part of its error message."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        request = self.db.Request.query.filter_by(id=request_id).first()
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert request is not None
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert request.status == "FAILURE"
        # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
        # succedere quando lo stato non e quello ideale.
        if expected_message is not None:
            # Controlliamo il contratto specifico dello scenario, non soltanto che il
            # codice sia arrivato fin qui senza eccezioni.
            assert expected_message in request.error_message

    def delete_request(self, request_id: int) -> None:
        """Delete one request owned by the scenario user through the public API.

        Tests call this when they need to remove a request explicitly, not only
        during teardown, for example before rebuilding a scenario with different
        postprocessors or filters.
        """
        # Rimuoviamo lo stato creato dal test per non lasciare dati che possano
        # influenzare gli scenari successivi.
        self.base.delete_request(self.client, self.user.headers, request_id)

    def ensure_upload_dir(self) -> Path:
        """Create the upload directory when missing and return its path."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        self.user.upload_dir.mkdir(parents=True, exist_ok=True)
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return self.user.upload_dir

    def copy_upload(self, source: Path, filename: str) -> Path:
        """Copy a file into the user's upload area under the requested filename."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        target = self.ensure_upload_dir() / filename
        shutil.copyfile(source, target)
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return target

    def unzip_upload(self, archive_path: Path) -> Path:
        """Extract a template archive inside the user's upload directory."""
        # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
        # quale stato viene letto o prodotto.
        upload_dir = self.ensure_upload_dir()
        # Apriamo lo zip prodotto dal backend per verificare i file effettivamente
        # consegnati all'utente.
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(upload_dir)
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return upload_dir


def delete_request_row(db, request_id: int) -> None:
    """Delete a request row directly from the database if it still exists."""
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    request = db.Request.query.get(request_id)
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if request is None:
        return

    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.delete(request)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.commit()


def create_postprocessing_user(
    base: BaseTests,
    client: FlaskClient,
    dataset_ids: list[int],
) -> PostprocessingUser:
    """Create a user allowed to run postprocessing on the selected datasets."""
    # Costruiamo lo stato controllato richiesto dal test, usando gli stessi canali che
    # il backend espone in produzione quando possibile.
    data = {
        "disk_quota": 1073741824,
        "max_output_size": 1073741824,
        "allowed_postprocessing": True,
        "open_dataset": True,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids]),
    }
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
    uuid, created_user = base.create_user(client, data)
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    headers, _ = base.do_login(
        client, created_user.get("email"), created_user.get("password")
    )

    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    db = sqlalchemy.get_instance()
    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    user = db.User.query.filter_by(uuid=uuid).first()
    # Controlliamo il contratto specifico dello scenario, non soltanto che il codice sia
    # arrivato fin qui senza eccezioni.
    assert user is not None

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
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
    """Register filesystem and user cleanup for a postprocessing scenario user."""
    # Registriamo subito il cleanup: anche se il test fallisce a meta, le risorse
    # temporanee verranno rimosse.
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.root_dir,
    )


def require_dataset(db, dataset_name: str):
    """Return a dataset or skip the test when the environment does not expose it."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    dataset = db.Datasets.query.filter(
        (db.Datasets.name == dataset_name) | (db.Datasets.arkimet_id == dataset_name)
    ).first()
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if dataset is None:
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(f"Dataset '{dataset_name}' is not available in this environment")
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return dataset


def require_observed_lastdays() -> int:
    """Derive a safe LASTDAYS override from real DBALLE observed data or skip."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    if not all(
        (
            ALCHEMY_USER,
            ALCHEMY_PASSWORD,
            ALCHEMY_HOST,
            ALCHEMY_DBTYPE,
            ALCHEMY_PORT,
        )
    ):
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
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
        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
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
            # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
            # direttamente nelle asserzioni.
            return (datetime.now() - last_dballe_date).days

    # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
    # contratto non sarebbe verificabile in modo significativo.
    pytest.skip("No DBALLE observed data available in this environment")


def forecast_pressure_filter() -> dict[str, Any]:
    """Return the baseline forecast pressure filter used by several scenarios."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return the postprocessor payload that computes forecast derived variables."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "derived_variables",
        "variables": ["B13003"],
    }


def forecast_derived_variable_filters() -> dict[str, Any]:
    """Return the valid forecast filters needed to compute derived humidity variables."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return the postprocessor payload for forecast statistic elaboration."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "statistic_elaboration",
        "input_timerange": 1,
        "output_timerange": 1,
        "interval": "hours",
        "step": 3,
    }


def forecast_statistic_elaboration_filters() -> dict[str, Any]:
    """Return the valid forecast filters for statistic elaboration on precipitation."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return an intentionally incomplete filter set for forecast derived-variable failures."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return an intentionally invalid filter set for statistic-elaboration failures."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return the combined forecast filters used by chained postprocessing scenarios."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return a grid interpolation payload with geometry defined inline."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return a grid interpolation payload that reuses geometry from a template file."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "grid_interpolation",
        "template": template_path,
        "trans_type": "inter",
        "sub_type": "bilin",
    }


def grid_cropping_postprocessor(*, initial_lon: int, initial_lat: int) -> dict[str, Any]:
    """Return a grid-cropping payload anchored to the provided initial coordinates."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "grid_cropping",
        "boundings": {
            "ilon": initial_lon,
            "ilat": initial_lat,
            "flon": 10,
            "flat": 5,
        },
        "trans_type": "zoom",
        "sub_type": "coord",
    }


def spare_point_postprocessor(template_path: Path) -> dict[str, Any]:
    """Return the spare-point interpolation payload that consumes a shapefile template."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "spare_point_interpolation",
        "coord_filepath": template_path,
        "file_format": "shp",
        "trans_type": "inter",
        "sub_type": "bilin",
    }


def require_spare_point_template_archive() -> Path:
    """Return the spare-point template archive or skip when it is unavailable."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    archive_path = Path("/data/templates_for_pp/template_for_spare_point.zip")
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if not archive_path.exists():
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip("Spare point template archive is not available in this environment")
    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return archive_path


def observed_derived_variable_postprocessor() -> dict[str, Any]:
    """Return the postprocessor payload that computes observed derived variables."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "derived_variables",
        "variables": ["B12103"],
    }


def observed_derived_variable_filters() -> dict[str, Any]:
    """Return the valid observed filters required by derived-variable postprocessing."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return an intentionally incomplete observed filter set for failure-path tests."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return the postprocessor payload for observed statistic elaboration."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    return {
        "processor_type": "statistic_elaboration",
        "input_timerange": 1,
        "output_timerange": 1,
        "interval": "hours",
        "step": 1,
    }


def observed_statistic_elaboration_filters() -> dict[str, Any]:
    """Return the valid observed filters for statistic elaboration scenarios."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Return the combined observed filters used by chained postprocessing tests."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
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
    """Yield GRIB handles one by one from a file and release them safely afterwards."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    with open(file_path, "rb") as file_handle:
        while True:
            gid = eccodes.codes_grib_new_from_file(file_handle)
            # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve
            # succedere quando lo stato non e quello ideale.
            if gid is None:
                break
            try:
                # Cediamo la fixture al test; quando il test termina, il codice sotto il
                # yield eseguira il teardown.
                yield gid
            finally:
                eccodes.codes_release(gid)


def assert_grib_contains_short_name(file_path: Path, short_name: str) -> None:
    """Assert that at least one GRIB message exposes the requested shortName."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    assert any(
        eccodes.codes_get(gid, "shortName") == short_name
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_preserves_independent_fields(
    file_path: Path, derived_short_name: str
) -> None:
    """Assert the output contains at least one field whose shortName differs from the derived one."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    assert any(
        eccodes.codes_get(gid, "shortName") != derived_short_name
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_contains_step_range(
    file_path: Path, short_name: str, step_range: str
) -> None:
    """Assert that one GRIB message matches both the expected shortName and stepRange."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    assert any(
        eccodes.codes_get(gid, "shortName") == short_name
        and eccodes.codes_get(gid, "stepRange") == step_range
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_contains_short_name_other_than(
    file_path: Path, excluded_short_name: str, expected_short_name: str
) -> None:
    """Assert the output contains a specific independent field (not the transformed one)."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    assert any(
        eccodes.codes_get(gid, "shortName") == expected_short_name
        for gid in iter_grib_messages(file_path)
    )


def assert_grib_geometry(file_path: Path, min_lat: int, nx: int) -> None:
    """Assert grid geometry for the first GRIB message in the produced file."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    for gid in iter_grib_messages(file_path):
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees") == min_lat
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert eccodes.codes_get(gid, "Ni") == nx
        return
    raise AssertionError(f"No GRIB messages found in {file_path}")


def assert_grib_messages_have_geometry(file_path: Path, min_lat: int, nx: int) -> None:
    """Assert identical grid geometry for every GRIB message in the produced file."""
    # Entriamo nel blocco operativo dell'helper post-processing, mantenendo esplicito
    # quale stato viene letto o prodotto.
    for gid in iter_grib_messages(file_path):
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees") == min_lat
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert eccodes.codes_get(gid, "Ni") == nx