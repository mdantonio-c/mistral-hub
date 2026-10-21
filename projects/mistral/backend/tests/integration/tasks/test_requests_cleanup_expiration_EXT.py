# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal prompt 07 del piano di
# estensione copertura backend per coprire rami di `requests_cleanup.automatic_cleanup`
# non presenti nella baseline legacy rifattorizzata.
# EXTENSION SCOPE: i test verificano archiviazione/cancellazione di request completate
# scadute, esclusioni per request recenti/archiviate/user disabilitato e cleanup di
# file orfani. Non toccano endpoint HTTP ne flussi postprocessing gia coperti altrove.
# EXTENSION DATA WINDOW: nessun dato meteo reale viene usato. Le date sono sintetiche
# e relative a `datetime.now()` solo per superare o non superare grace period e
# requests_expiration_days.
# EXTENSION RUNTIME: il task viene invocato in-process con `.run()`; non c'e Celery
# worker reale. Il DB e quello di test perche il contratto da proteggere e sui record
# Request/FileOutput, mentre i file fisici sono confinati a utenti temporanei o a una
# cartella orphan sintetica sotto DOWNLOAD_DIR.
# EXTENSION CLEANUP: utenti temporanei, request, fileoutput e directory output sono
# registrati nel cleanup_registry. I file che il task cancella vengono verificati con
# assert idempotenti, mentre quelli recenti rimasti sono rimossi dal teardown.

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from celery import states
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tasks import requests_cleanup
from mistral.tests.integration.tasks.support_EXT import (
    create_task_test_user_EXT,
    delete_requests_for_user_EXT,
    seed_fileoutput_EXT,
    seed_request_EXT,
    touch_mtime_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAutomaticCleanupExpirationEXT:
    """Verifica i rami di expiration request non coperti dal pending-stale legacy."""

    def test_automatic_cleanup_archives_deletes_and_preserves_expected_requests_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
    ) -> None:
        """Request completate scadute vengono archiviate o cancellate in base al profilo.

        Lo scenario prepara due utenti temporanei con policy opposte. Per l'utente che
        archivia controlliamo anche che request recenti e gia archiviate restino fuori
        dal ramo distruttivo; per l'utente che cancella controlliamo la rimozione del
        record. I file fisici sono sintetici e servono solo a osservare il side effect
        di `delete_request_record` invocato dal task.
        """
        # arrange
        # Costruiamo righe DB e file fisici minimali: il task legge solo end_date,
        # archived, policy utente e FileOutput collegato alla request.
        db = sqlalchemy.get_instance()
        now = dt.datetime.now()
        expired_end_date = now - dt.timedelta(days=5)
        recent_end_date = now
        archive_user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            requests_expiration_days=1,
            requests_expiration_delete=False,
        )
        delete_user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            requests_expiration_days=1,
            requests_expiration_delete=True,
        )
        cleanup_registry.add(lambda: delete_requests_for_user_EXT(db, archive_user.user_id))
        cleanup_registry.add(lambda: delete_requests_for_user_EXT(db, delete_user.user_id))

        archived_request_id = seed_request_EXT(
            db,
            archive_user.user_id,
            name="archive-expired-ext",
            status=states.SUCCESS,
            end_date=expired_end_date,
        )
        _, archived_file_path = seed_fileoutput_EXT(
            db,
            cleanup_registry,
            archive_user,
            archived_request_id,
            filename=f"archive-{uuid4().hex}.grib",
        )
        deleted_request_id = seed_request_EXT(
            db,
            delete_user.user_id,
            name="delete-expired-ext",
            status=states.SUCCESS,
            end_date=expired_end_date,
        )
        _, deleted_file_path = seed_fileoutput_EXT(
            db,
            cleanup_registry,
            delete_user,
            deleted_request_id,
            filename=f"delete-{uuid4().hex}.grib",
        )
        recent_request_id = seed_request_EXT(
            db,
            archive_user.user_id,
            name="recent-completed-ext",
            status=states.SUCCESS,
            end_date=recent_end_date,
        )
        already_archived_request_id = seed_request_EXT(
            db,
            archive_user.user_id,
            name="already-archived-ext",
            status=states.SUCCESS,
            end_date=expired_end_date,
            archived=True,
        )

        # act
        # Eseguiamo il task direttamente in-process: vogliamo verificare il codice del
        # cleanup, non la consegna Celery o il beat scheduler.
        requests_cleanup.automatic_cleanup.run()

        # assert
        # La request scaduta dell'utente con delete=False viene mantenuta ma marcata
        # archived, mentre il FileOutput e il file fisico collegato sono rimossi.
        archived_request = db.Request.query.get(archived_request_id)
        assert archived_request is not None
        assert archived_request.archived is True
        assert db.FileOutput.query.filter_by(request_id=archived_request_id).first() is None
        assert not archived_file_path.exists()

        # La request scaduta dell'utente con delete=True viene cancellata del tutto e
        # anche il file fisico non resta nella directory output temporanea.
        assert db.Request.query.get(deleted_request_id) is None
        assert db.FileOutput.query.filter_by(request_id=deleted_request_id).first() is None
        assert not deleted_file_path.exists()

        # Le request completate ma recenti, o gia archiviate prima del task, devono
        # restare presenti e non cambiare ramo a causa degli altri record scaduti.
        recent_request = db.Request.query.get(recent_request_id)
        assert recent_request is not None
        assert recent_request.archived is False
        already_archived_request = db.Request.query.get(already_archived_request_id)
        assert already_archived_request is not None
        assert already_archived_request.archived is True

    def test_automatic_cleanup_ignores_user_with_expiration_disabled_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
    ) -> None:
        """Un utente con requests_expiration_days=0 non deve perdere request vecchie.

        Il task costruisce la mappa utenti solo per valori truthy di expiration_days.
        Questo test protegge quel contratto preparando una request completata e vecchia
        che sarebbe scaduta per qualunque policy attiva, ma deve restare intatta quando
        l'utente disabilita esplicitamente l'autocleaning.
        """
        # arrange
        # Il record e vecchio e completato, ma l'utente ha expiration disabilitata:
        # questa e l'unica differenza rispetto ai rami distruttivi del test precedente.
        db = sqlalchemy.get_instance()
        disabled_user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            requests_expiration_days=0,
            requests_expiration_delete=True,
        )
        cleanup_registry.add(lambda: delete_requests_for_user_EXT(db, disabled_user.user_id))
        disabled_request_id = seed_request_EXT(
            db,
            disabled_user.user_id,
            name="disabled-expiration-ext",
            status=states.SUCCESS,
            end_date=dt.datetime.now() - dt.timedelta(days=30),
        )

        # act
        requests_cleanup.automatic_cleanup.run()

        # assert
        # Il task deve saltare l'utente prima di archiviare o cancellare la request.
        disabled_request = db.Request.query.get(disabled_request_id)
        assert disabled_request is not None
        assert disabled_request.archived is False
        assert disabled_request.status == states.SUCCESS

    def test_automatic_cleanup_removes_only_old_orphan_files_EXT(
        self,
        cleanup_registry,
    ) -> None:
        """I file orfani oltre grace period vengono rimossi, quelli recenti restano.

        Questo scenario usa una directory utente sintetica sotto DOWNLOAD_DIR per
        attraversare il ramo filesystem del task senza appoggiarsi a output reali. I
        file non hanno FileOutput DB associato per scelta: il contratto e proprio la
        rimozione degli orfani, distinta dalla cancellazione di request scadute.
        """
        # arrange
        # Creiamo una directory output sintetica riconoscibile e registriamo il cleanup
        # del parent; se il task elimina i file vecchi, il teardown resta comunque
        # idempotente.
        now = dt.datetime.now()
        old_mtime = now - requests_cleanup.GRACE_PERIOD - dt.timedelta(minutes=5)
        recent_mtime = now
        orphan_root = requests_cleanup.DOWNLOAD_DIR / f"orphan-ext-{uuid4().hex}"
        orphan_output_dir = orphan_root / "outputs"
        orphan_output_dir.mkdir(parents=True, exist_ok=True)
        cleanup_registry.add_path(orphan_root)

        old_tmp_file = orphan_output_dir / "old-orphan.tmp"
        old_output_file = orphan_output_dir / "old-orphan.grib"
        recent_output_file = orphan_output_dir / "recent-orphan.grib"
        touch_mtime_EXT(old_tmp_file, old_mtime)
        touch_mtime_EXT(old_output_file, old_mtime)
        touch_mtime_EXT(recent_output_file, recent_mtime)

        # act
        requests_cleanup.automatic_cleanup.run()

        # assert
        # I due file oltre grace period vengono cancellati; quello recente resta fino al
        # cleanup_registry per dimostrare che il task rispetta la soglia temporale.
        assert not old_tmp_file.exists()
        assert not old_output_file.exists()
        assert recent_output_file.exists()