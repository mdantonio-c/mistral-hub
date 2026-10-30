# EXTENSION TRACEABILITY - Prompt 05, contratti /usage e /hourly.
# Origine: questo modulo aggiunge copertura per endpoints user-facing di quota disco e
# limite richieste orarie non coperti dalla suite legacy rifattorizzata.
# Ambito: copre auth richiesta, usage con directory utente assente, usage con file fisico,
# quota restituita dal profilo utente, hourly senza limite e hourly con richieste nella
# finestra dell'ora corrente.
# Finestra dati: nessun dataset meteorologico reale viene usato; i file e le request sono
# sintetici e confinati all'utente temporaneo del singolo test.
# Runtime fake: il test hourly monkeypatcha solo datetime.utcnow del modulo endpoint per
# rendere deterministica la finestra temporale; non usa worker, broker o sleep.
# Cleanup: utenti, directory /data/<uuid> e request DB vengono registrati nel
# cleanup_registry prima degli assert che dipendono da essi.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/user_limits.

from __future__ import annotations

import datetime as datetime_module
import shutil
from pathlib import Path
from uuid import uuid4

import mistral.endpoints.request_hourly_report as hourly_endpoint_module
import pytest
from mistral.endpoints import DOWNLOAD_DIR
from mistral.tests.helpers.auth import (
    AuthenticatedTestUser,
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


USAGE_ENDPOINT_EXT = f"{API_URI}/usage"
HOURLY_ENDPOINT_EXT = f"{API_URI}/hourly"


def create_user_limits_user_EXT(
    client: FlaskClient,
    cleanup_registry,
    *,
    disk_quota: int = 4096,
    request_par_hour: int | None = 0,
) -> AuthenticatedTestUser:
    """Crea un utente temporaneo per i contratti usage/hourly.

    L'admin customizer assegna default anche quando un campo viene omesso. Questo helper
    imposta quindi esplicitamente quota e request_par_hour, e quando serve `None` aggiorna
    il record DB dopo la creazione per rappresentare davvero un utente senza limite.
    """
    # Prepariamo permessi minimi e indipendenti dai dataset: questi endpoint leggono solo
    # campi del profilo utente e request DB sintetiche.
    base = BaseTests()
    permissions = {
        "disk_quota": disk_quota,
        "max_output_size": disk_quota,
        "request_par_hour": request_par_hour if request_par_hour is not None else 0,
        "open_dataset": True,
    }
    user = create_authenticated_test_user(base, client, permissions)

    # Forziamo il valore nullable direttamente sul record quando il test deve simulare
    # assenza di limite, per evitare che i default del customizer mascherino lo scenario.
    db = sqlalchemy.get_instance()
    db_user = db.User.query.get(user.user_id)
    assert db_user is not None
    db_user.disk_quota = disk_quota
    db_user.request_par_hour = request_par_hour
    db.session.add(db_user)
    db.session.commit()

    # Registriamo il cleanup subito: usage crea file fisici e hourly crea request legate
    # all'utente, quindi la rimozione deve essere robusta anche se il test fallisce.
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=Path(DOWNLOAD_DIR, user.uuid),
    )
    return user


def user_root_EXT(user: AuthenticatedTestUser) -> Path:
    """Restituisce /data/<uuid> per l'utente temporaneo del test."""
    # Centralizzare il path evita di spargere nel test la convenzione filesystem usata da
    # Usage.get e dai cleanup registrati.
    return Path(DOWNLOAD_DIR, user.uuid)


def write_usage_file_EXT(
    cleanup_registry,
    user: AuthenticatedTestUser,
    *,
    relative_path: str = "outputs/usage_ext.txt",
    content: bytes = b"usage-ext-content",
) -> Path:
    """Scrive un file sintetico sotto la directory utente per il calcolo du.

    Usage.get misura l'intera directory /data/<uuid>. Questo helper crea un file minimo
    in una sottocartella controllata e registra la radice utente per il cleanup.
    """
    # Registriamo il path prima della scrittura, cosi un errore successivo non lascia
    # residui sotto /data.
    root = user_root_EXT(user)
    cleanup_registry.add_path(root)
    path = root.joinpath(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def seed_hourly_request_EXT(
    db,
    cleanup_registry,
    user: AuthenticatedTestUser,
    submission_date: datetime_module.datetime,
) -> int:
    """Inserisce una request sintetica con submission_date controllata.

    Il test hourly deve verificare solo il conteggio nell'ora corrente; creare righe DB
    dirette evita l'endpoint /data, Celery e qualsiasi dipendenza da dataset reali.
    """
    # Persistiamo una riga minima valida per il modello Request, con nome univoco per non
    # interferire con altri test o con lo stato del runtime.
    request_row = db.Request(
        user_id=user.user_id,
        name=f"hourly-ext-{uuid4().hex[:10]}",
        args={},
        submission_date=submission_date,
        status="SUCCESS",
    )
    db.session.add(request_row)
    db.session.commit()

    # La request deve sparire prima dell'utente nel teardown; registrarla dopo il cleanup
    # utente produce proprio questo ordine LIFO.
    request_id = request_row.id
    cleanup_registry.add(lambda: delete_hourly_request_EXT(db, request_id))
    return request_id


def delete_hourly_request_EXT(db, request_id: int) -> None:
    """Rimuove una request hourly sintetica se esiste ancora."""
    # Il cleanup e idempotente per non fallire se il backend o un test futuro rimuovono
    # gia la riga prima del teardown.
    request_row = db.Request.query.get(request_id)
    if request_row is not None:
        db.session.delete(request_row)
        db.session.commit()


class FixedHourlyDateTime_EXT(datetime_module.datetime):
    """Datetime controllato per rendere deterministico il calcolo dell'ora corrente."""

    @classmethod
    def utcnow(cls) -> "FixedHourlyDateTime_EXT":
        """Restituisce un istante fisso lontano dai bordi dell'ora."""
        # L'istante 10:30 evita edge case vicini al cambio ora e permette di creare righe
        # chiaramente dentro e fuori la finestra [10:00, 10:30).
        return cls(2026, 5, 29, 10, 30, 0)


def test_usage_endpoint_requires_authentication_EXT(client: FlaskClient) -> None:
    """Verifica che /usage richieda un utente autenticato."""
    # act
    # Nessun setup e necessario: senza header il decorator auth deve fermare la richiesta.
    response = client.get(USAGE_ENDPOINT_EXT)

    # assert
    # Il contratto di endpoint user-facing richiede 401 per chiamanti anonimi.
    assert response.status_code == 401


def test_usage_returns_zero_when_user_directory_is_absent_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica used=0 quando /data/<uuid> non esiste.

    Il test rimuove esplicitamente la radice utente temporanea se fosse stata creata da
    setup precedenti, cosi il ramo `if user_dir.is_dir()` resta il comportamento misurato.
    """
    # arrange
    # Creiamo un utente con quota nota e assicuriamo l'assenza della directory misurata da
    # Usage.get; la rimozione e confinata al solo uuid temporaneo.
    user = create_user_limits_user_EXT(
        client,
        cleanup_registry,
        disk_quota=12345,
        request_par_hour=0,
    )
    shutil.rmtree(user_root_EXT(user), ignore_errors=True)

    # act
    # La GET attraversa il controller reale e deve scegliere il ramo used_quota=0.
    response = client.get(USAGE_ENDPOINT_EXT, headers=user.headers)

    # assert
    # Verifichiamo sia la quota configurata sia l'assenza di uso disco.
    assert response.status_code == 200
    assert BaseTests().get_content(response) == {"quota": 12345, "used": 0}


def test_usage_returns_positive_used_when_user_directory_has_files_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che /usage misuri i file presenti sotto la directory utente.

    Il file e sintetico e piccolo: il contratto non dipende dalla dimensione esatta di du,
    che puo includere overhead di directory, ma dal fatto che used diventi positivo e che
    quota resti uguale a user.disk_quota.
    """
    # arrange
    # Prepariamo un file fisico sotto /data/<uuid>/outputs e registriamo la radice per il
    # cleanup tramite il helper locale.
    user = create_user_limits_user_EXT(
        client,
        cleanup_registry,
        disk_quota=67890,
        request_par_hour=0,
    )
    file_path = write_usage_file_EXT(
        cleanup_registry,
        user,
        content=b"usage ext file with deterministic bytes",
    )

    # act
    # Usage.get invoca `du -sb` sulla radice utente preparata sopra.
    response = client.get(USAGE_ENDPOINT_EXT, headers=user.headers)

    # assert
    # Non imponiamo il valore esatto di du, ma pretendiamo che includa almeno il payload
    # scritto e che la quota provenga dal profilo utente.
    assert response.status_code == 200
    content = BaseTests().get_content(response)
    assert content["quota"] == 67890
    assert content["used"] >= file_path.stat().st_size
    assert content["used"] > 0


def test_hourly_endpoint_requires_authentication_EXT(client: FlaskClient) -> None:
    """Verifica che /hourly richieda un utente autenticato."""
    # act
    # Senza header auth, il controller non deve leggere request o profilo utente.
    response = client.get(HOURLY_ENDPOINT_EXT)

    # assert
    # Il decorator auth deve restituire 401.
    assert response.status_code == 401


def test_hourly_returns_empty_object_when_user_has_no_hourly_limit_EXT(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica `{}` quando request_par_hour e assente sul profilo utente.

    Il backend usa un controllo truthy su user.request_par_hour; impostare None sul record
    DB documenta il caso di utente senza limite orario invece del default customizer.
    """
    # arrange
    # Creiamo un utente e forziamo request_par_hour=None per attraversare il ramo vuoto.
    user = create_user_limits_user_EXT(
        client,
        cleanup_registry,
        disk_quota=4096,
        request_par_hour=None,
    )

    # act
    # La GET deve rispondere con un oggetto vuoto senza interrogare il conteggio request.
    response = client.get(HOURLY_ENDPOINT_EXT, headers=user.headers)

    # assert
    # Il payload vuoto e il contratto user-facing per profili senza limite orario.
    assert response.status_code == 200
    assert BaseTests().get_content(response) == {}


def test_hourly_reports_submitted_total_and_remaining_in_current_hour_EXT(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica conteggio hourly con richieste dentro e fuori l'ora corrente.

    Il test fissa datetime.utcnow a 2026-05-29 10:30:00, inserisce due request dopo le
    10:00 e una alle 09:59, e controlla che il report conti solo le due request correnti.
    """
    # arrange
    # Monkeypatchiamo solo il modulo endpoint, non il modulo datetime globale: il fake e
    # confinato al singolo test e viene ripristinato automaticamente da pytest.
    monkeypatch.setattr(
        hourly_endpoint_module.datetime,
        "datetime",
        FixedHourlyDateTime_EXT,
    )
    user = create_user_limits_user_EXT(
        client,
        cleanup_registry,
        disk_quota=4096,
        request_par_hour=3,
    )
    db = sqlalchemy.get_instance()
    fixed_now = FixedHourlyDateTime_EXT.utcnow()
    seed_hourly_request_EXT(
        db,
        cleanup_registry,
        user,
        fixed_now - datetime_module.timedelta(minutes=10),
    )
    seed_hourly_request_EXT(
        db,
        cleanup_registry,
        user,
        fixed_now - datetime_module.timedelta(minutes=20),
    )
    seed_hourly_request_EXT(
        db,
        cleanup_registry,
        user,
        fixed_now.replace(hour=9, minute=59, second=0),
    )

    # act
    # La GET deve usare il tempo fake e interrogare solo le request dell'utente corrente.
    response = client.get(HOURLY_ENDPOINT_EXT, headers=user.headers)

    # assert
    # Con limite 3 e due request nella finestra corrente, remaining deve essere 1.
    assert response.status_code == 200
    assert BaseTests().get_content(response) == {
        "submitted": 2,
        "total": 3,
        "remaining": 1,
    }