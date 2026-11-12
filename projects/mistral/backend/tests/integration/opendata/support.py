"""Helper di supporto locali ai test di integrazione degli opendata.

I test opendata creano dataset, utenti, righe Request sintetiche e file finti da
scaricare. Questo modulo raccoglie quel setup, cosi i file di test possono
concentrarsi su autorizzazione, elenco e download (endpoints/opendata.py) senza
costruire ogni volta a mano tutti i record di supporto.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4
from zipfile import ZipFile

from mistral.endpoints import OPENDATA_DIR
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from mistral.tests.helpers.datasets import create_test_dataset
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

@dataclass(frozen=True)
class OpendataSeedSpec:
    """Descrizione dichiarativa di un pacchetto opendata finto da creare nel test."""

    reftime: datetime
    content: str
    run: str | None = None
    archived: bool = False
    submission_date: datetime | None = None


@dataclass(frozen=True)
class FakeOpendataResult:
    """Metadati di una riga Request opendata creata dal test e del suo file su disco."""

    request_id: int
    filename: str
    content: str
    reftime: datetime
    run: str | None


def create_opendata_user(
    client: FlaskClient,
    dataset_ids: list[int] | None = None,
    *,
    allow_schedule: bool = False,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo per i test opendata, eventualmente gia autorizzato.

    L'helper puo dare accesso a dataset specifici e, se serve, abilitare anche le
    operazioni sugli schedule, cosi lo stesso helper serve sia agli scenari
    opendata pubblici sia a quelli privati. Usa le API reali di creazione utente
    e login tramite ``create_authenticated_test_user``.
    """
    permissions: dict[str, Any] = {
        "disk_quota": 1073741824,
        "max_output_size": 1073741824,
        "allowed_postprocessing": True,
        "open_dataset": True,
        "datasets": json.dumps([str(dataset_id) for dataset_id in dataset_ids or []]),
    }
    if allow_schedule:
        permissions["allowed_schedule"] = True

    return create_authenticated_test_user(BaseTests(), client, permissions)


def register_user_cleanup(
    client: FlaskClient,
    cleanup_registry,
    user: AuthenticatedTestUser,
) -> None:
    """Registra il cleanup standard dell'utente e della sua cartella su disco."""
    register_test_user_cleanup(
        BaseTests(),
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )


def authorize_user_for_dataset(db, user_uuid: str, dataset_id: int) -> None:
    """Autorizza un utente esistente su un dataset esistente, se non lo e gia.

    Scrive l'associazione ``user.datasets`` usata dal backend per i dataset
    privati.
    """
    user = db.User.query.filter_by(uuid=user_uuid).first()
    dataset = db.Datasets.query.get(dataset_id)
    assert user is not None
    assert dataset is not None

    if all(authorized_dataset.id != dataset_id for authorized_dataset in user.datasets):
        user.datasets.append(dataset)
        db.session.add(user)
        db.session.commit()


def create_fake_opendata_result(
    db,
    cleanup_registry,
    request_owner_id: int,
    dataset_id: str,
    reftime: datetime,
    file_content: str,
    *,
    run: str | None = None,
    archived: bool = False,
    submission_date: datetime | None = None,
) -> FakeOpendataResult:
    """Crea una Request opendata in SUCCESS con il relativo file di output su disco.

    Scrive le righe ``Request`` e ``FileOutput`` direttamente nel database e il
    file in ``OPENDATA_DIR``, cioe lo stato letto dagli endpoint opendata;
    registra subito il cleanup di riga e file.
    """
    request = db.Request(
        user_id=request_owner_id,
        name=f"opendata_{uuid4().hex}",
        args=_build_opendata_args(dataset_id, reftime, run),
        status="SUCCESS",
        opendata=True,
        archived=archived,
        submission_date=submission_date or datetime.utcnow(),
    )
    db.session.add(request)
    db.session.commit()
    request_id = request.id
    cleanup_registry.add(lambda: _delete_request_row(db, request_id))

    filename = f"{uuid4().hex}.grib"
    output_path = Path(OPENDATA_DIR, filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(file_content, encoding="utf-8")
    cleanup_registry.add(lambda: _delete_file(output_path))

    file_output = db.FileOutput(
        user_id=request_owner_id,
        filename=filename,
        size=len(file_content.encode("utf-8")),
        request_id=request.id,
    )
    db.session.add(file_output)
    db.session.commit()

    return FakeOpendataResult(
        request_id=request.id,
        filename=filename,
        content=file_content,
        reftime=reftime,
        run=run,
    )


def seed_opendata_results(
    db,
    cleanup_registry,
    request_owner_id: int,
    dataset_id: str,
    seeds: Sequence[OpendataSeedSpec],
) -> list[FakeOpendataResult]:
    """Crea piu risultati opendata finti da una lista di ``OpendataSeedSpec``."""
    return [
        create_fake_opendata_result(
            db,
            cleanup_registry,
            request_owner_id,
            dataset_id,
            seed.reftime,
            seed.content,
            run=seed.run,
            archived=seed.archived,
            submission_date=seed.submission_date,
        )
        for seed in seeds
    ]


def create_private_opendata_env(client: FlaskClient, cleanup_registry):
    """Crea un dataset privato, un utente proprietario e un risultato opendata.

    L'utente non e autorizzato sul dataset: serve ai test di autorizzazione degli
    endpoint opendata. Restituisce ``(db, dataset, user, result)``.
    """
    db = sqlalchemy.get_instance()
    dataset = create_test_dataset(db, cleanup_registry, is_public=False)
    user = create_opendata_user(client)
    register_user_cleanup(client, cleanup_registry, user)
    result = create_fake_opendata_result(
        db,
        cleanup_registry,
        user.user_id,
        dataset.arkimet_id,
        datetime(2020, 1, 1, 0, 0),
        "private-opendata-content",
        run="00:00",
    )
    return db, dataset, user, result


def create_listing_env(client: FlaskClient, cleanup_registry):
    """Crea un dataset pubblico con due risultati opendata per i test dell'elenco.

    I due risultati hanno run e reftime diversi, cosi i filtri di
    GET /api/datasets/<id>/opendata possono distinguerli.
    """
    db = sqlalchemy.get_instance()
    dataset = create_test_dataset(db, cleanup_registry, is_public=True)
    request_owner = create_opendata_user(client)
    register_user_cleanup(client, cleanup_registry, request_owner)
    seeded_results = seed_opendata_results(
        db,
        cleanup_registry,
        request_owner.user_id,
        dataset.arkimet_id,
        [
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 1, 0, 0),
                run="00:00",
                content="listing-run-00",
            ),
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 2, 0, 0),
                run="12:00",
                content="listing-run-12",
            ),
        ],
    )
    return dataset, seeded_results


def create_download_env(client: FlaskClient, cleanup_registry):
    """Crea un dataset pubblico con tre file opendata per i test di download.

    Le combinazioni di reftime e run permettono di verificare i filtri di
    GET /api/opendata/<dataset_id>/download.
    """
    db = sqlalchemy.get_instance()
    dataset = create_test_dataset(db, cleanup_registry, is_public=True)
    request_owner = create_opendata_user(client)
    register_user_cleanup(client, cleanup_registry, request_owner)
    seeded_results = seed_opendata_results(
        db,
        cleanup_registry,
        request_owner.user_id,
        dataset.arkimet_id,
        [
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 1, 0, 0),
                run="00:00",
                content="download-20200101-run-00",
            ),
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 1, 0, 0),
                run="12:00",
                content="download-20200101-run-12",
            ),
            OpendataSeedSpec(
                reftime=datetime(2020, 1, 2, 0, 0),
                run="00:00",
                content="download-20200102-run-00",
            ),
        ],
    )
    return dataset, seeded_results


def zip_filenames(response) -> list[str]:
    """Estrae e ordina i nomi dei file contenuti nello zip di una risposta."""
    archive_data = io.BytesIO(response.get_data())
    with ZipFile(archive_data, "r") as archive:
        return sorted(archive.namelist())


def _build_opendata_args(
    dataset_id: str,
    reftime: datetime,
    run: str | None,
) -> dict[str, Any]:
    """Costruisce il campo ``args`` salvato nelle Request opendata sintetiche.

    La forma deve combaciare con le query JSONB costruite da endpoints/opendata.py,
    altrimenti i filtri non trovano le righe create dal test.
    """
    reftime_value = reftime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return {
        "filters": {"run": _build_run_filter(run)} if run else None,
        "reftime": {"from": reftime_value, "to": reftime_value},
        "datasets": [dataset_id],
    }


def _build_run_filter(run: str) -> list[dict[str, Any]]:
    """Converte un run "HH:MM" nella struttura di filtro MINUTE salvata su DB.

    ``value`` deve restare un intero (minuti totali): il backend lo decodifica con
    ``BeArkimet.decode_run`` quando elenca gli opendata.
    """
    hours, minutes = [int(part) for part in run.split(":", maxsplit=1)]
    total_minutes = (hours * 60) + minutes
    return [
        {
            "desc": f"MINUTE({run})",
            "style": "MINUTE",
            "value": total_minutes,
            "active": True,
        }
    ]


def _delete_request_row(db, request_id: int) -> None:
    """Cancella una Request sintetica, se esiste ancora, e verifica la rimozione."""
    request = db.Request.query.get(request_id)
    if request is None:
        return

    db.session.delete(request)
    db.session.commit()
    assert db.Request.query.get(request_id) is None


def _delete_file(path: Path) -> None:
    """Cancella dal disco un file opendata generato e verifica che non esista piu."""
    if path.exists():
        path.unlink()
    assert not path.exists()