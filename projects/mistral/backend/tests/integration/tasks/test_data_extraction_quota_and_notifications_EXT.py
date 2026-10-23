# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal prompt 07 del piano di
# estensione copertura backend per coprire rami ad alto rischio di
# `tasks.data_extraction` non esercitati dagli happy path postprocessing esistenti.
# EXTENSION SCOPE: i test proteggono quota utente, disabilitazione schedule su quota,
# duplicate data-ready, notification email/AMQP e package license. Non rieseguono
# estrazioni meteorologiche reali e non duplicano i flussi `integration/postprocessing`.
# EXTENSION DATA WINDOW: nessun dataset runtime reale viene usato. Le reftime sono
# dizionari sintetici per confronti duplicate data-ready e non rappresentano finestre
# meteo reali.
# EXTENSION RUNTIME: Arkimet size estimation, SMTP, RabbitMQ, Celery periodic deletion
# e sleep retry sono fake locali via monkeypatch. Il DB di test viene usato solo dove
# il task legge o scrive User/Schedule/Request/FileOutput.
# EXTENSION CLEANUP: utenti temporanei, request, schedule e directory output sono
# registrati nel cleanup_registry; i file package vivono in tmp_path e sono rimossi dal
# registry oltre che dal cleanup pytest.

from __future__ import annotations

import tarfile
from types import SimpleNamespace

import pytest
from celery import states
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.exceptions import DiskQuotaException, MaxOutputSizeExceeded
from mistral.tasks import data_extraction
from mistral.tests.integration.tasks.support_EXT import (
    RecordingPeriodicTaskDeletionEXT,
    RecordingRabbitFactoryEXT,
    RetryThenSuccessSmtpFactoryEXT,
    create_task_test_user_EXT,
    delete_requests_for_user_EXT,
    delete_schedule_EXT,
    seed_request_EXT,
    seed_schedule_EXT,
)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestCheckUserQuotaEXT:
    """Verifica i rami quota senza usare Arkimet, du o Celery reali."""

    def test_check_user_quota_raises_when_estimate_exceeds_max_output_size_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Una stima oltre max_output_size deve sollevare MaxOutputSizeExceeded.

        Il test sostituisce `arki.estimate_data_size` con un valore sintetico per
        evitare query Arkimet reali. Non serve creare dataset: il contratto di questa
        funzione comincia dopo la stima, sul confronto con i limiti utente persistiti.
        """
        # arrange
        # Creiamo un utente con limite per-singola-request molto basso e una directory
        # output temporanea sotto il suo root, poi facciamo restituire al fake una stima
        # appena superiore al limite.
        db = sqlalchemy.get_instance()
        user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            max_output_size=128,
            disk_quota=1024 * 1024,
        )
        user.output_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            data_extraction.arki,
            "estimate_data_size",
            lambda datasets, query: 129,
        )

        # act / assert
        # L'eccezione e il messaggio sono l'effetto osservabile del ramo quota; nessun
        # file viene creato o cancellato in questo scenario.
        with pytest.raises(MaxOutputSizeExceeded, match="single request"):
            data_extraction.check_user_quota(
                user.user_id,
                user.output_dir,
                db,
                datasets=["synthetic-task-ext"],
                query="product:synthetic",
            )

    def test_check_user_quota_raises_when_disk_quota_is_insufficient_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Una stima che supera lo spazio libero utente deve sollevare DiskQuotaException.

        Qui il fake `du -sb` evita dipendenze dal filesystem reale: il task riceve un
        used_quota controllato e calcola il free space come farebbe in produzione.
        """
        # arrange
        # max_output_size e volutamente None per attraversare il secondo controllo quota
        # invece del limite per singola request.
        db = sqlalchemy.get_instance()
        user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            max_output_size=None,
            disk_quota=1000,
        )
        user.output_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            data_extraction.arki,
            "estimate_data_size",
            lambda datasets, query: 200,
        )
        monkeypatch.setattr(
            data_extraction.subprocess,
            "check_output",
            lambda command: b"900\t/synthetic-output-dir\n",
        )

        # act / assert
        # 900 byte gia usati + 200 stimati supera quota 1000, quindi il ramo deve
        # produrre DiskQuotaException con un messaggio leggibile.
        with pytest.raises(DiskQuotaException, match="Disk quota exceeded"):
            data_extraction.check_user_quota(
                user.user_id,
                user.output_dir,
                db,
                datasets=["synthetic-task-ext"],
                query="product:synthetic",
            )

    def test_check_user_quota_disables_periodic_schedule_on_quota_failure_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Una schedule periodica viene disabilitata e rimossa da Celery su quota error.

        Il ramo e side-effect heavy: aggiorna la schedule DB e chiama
        `CeleryExt.delete_periodic_task`. Usiamo una schedule seedata e un fake callable
        per verificare entrambi senza RedBeat o worker reali.
        """
        # arrange
        # Il limite max_output_size garantisce il failure prima del controllo disco; la
        # schedule on_data_ready=False forza il ramo che cancella il periodic task.
        db = sqlalchemy.get_instance()
        user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            max_output_size=10,
            disk_quota=1024 * 1024,
        )
        schedule_id = seed_schedule_EXT(
            db,
            user.user_id,
            name="quota-disable-schedule-ext",
            enabled=True,
            on_data_ready=False,
        )
        cleanup_registry.add(lambda: delete_schedule_EXT(db, schedule_id))
        user.output_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            data_extraction.arki,
            "estimate_data_size",
            lambda datasets, query: 64,
        )
        fake_delete_periodic = RecordingPeriodicTaskDeletionEXT()
        monkeypatch.setattr(
            data_extraction.CeleryExt,
            "delete_periodic_task",
            fake_delete_periodic,
        )

        # act / assert
        # L'errore quota deve disabilitare la schedule e includere nel messaggio il
        # motivo della disattivazione temporanea.
        with pytest.raises(MaxOutputSizeExceeded) as exc_info:
            data_extraction.check_user_quota(
                user.user_id,
                user.output_dir,
                db,
                datasets=["synthetic-task-ext"],
                query="product:synthetic",
                schedule_id=schedule_id,
            )

        schedule = db.Schedule.query.get(schedule_id)
        assert schedule is not None
        assert schedule.is_enabled is False
        assert fake_delete_periodic.calls == [
            {"args": (), "kwargs": {"name": str(schedule_id)}}
        ]
        assert "temporary disabled" in str(exc_info.value)

    def test_check_user_quota_skips_user_limits_for_opendata_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Le estrazioni opendata non devono applicare max_output_size o disk_quota utente.

        La funzione calcola comunque la stima, ma con `opendata=True` non entra nei
        controlli quota personali. Un fake `du` che fallirebbe il test dimostra che il
        ramo filesystem non viene consultato.
        """
        # arrange
        # I limiti utente sono volutamente inferiori alla stima per dimostrare che il
        # flag opendata bypassa entrambi i controlli personali.
        db = sqlalchemy.get_instance()
        user = create_task_test_user_EXT(
            client,
            cleanup_registry,
            max_output_size=1,
            disk_quota=1,
        )
        monkeypatch.setattr(
            data_extraction.arki,
            "estimate_data_size",
            lambda datasets, query: 4096,
        )

        def fail_if_du_is_used_EXT(command):
            """Protegge il ramo opendata: `du` non deve essere chiamato."""
            raise AssertionError("du should not be used for opendata quota checks")

        monkeypatch.setattr(
            data_extraction.subprocess,
            "check_output",
            fail_if_du_is_used_EXT,
        )

        # act
        estimated_size = data_extraction.check_user_quota(
            user.user_id,
            user.output_dir,
            db,
            datasets=["synthetic-task-ext"],
            query="product:synthetic",
            opendata=True,
        )

        # assert
        # La stima viene restituita al chiamante senza sollevare eccezioni nonostante i
        # limiti personali volutamente insufficienti.
        assert estimated_size == 4096


class TestDataExtractDataReadyEXT:
    """Verifica il ramo duplicate data-ready senza estrazione reale."""

    def test_data_extract_duplicate_data_ready_returns_without_new_output_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
    ) -> None:
        """Se l'ultima request success ha la stessa reftime, il task non crea output.

        Il ramo duplicate avviene prima di autorizzazioni dataset, query Arkimet e
        creazione output_dir. Seedare schedule e ultima request basta quindi a coprire
        il contratto senza dataset reali o tool meteo.
        """
        # arrange
        # Prepariamo una schedule data-ready e una request SUCCESS precedente con la
        # stessa reftime che verra passata al task.
        db = sqlalchemy.get_instance()
        user = create_task_test_user_EXT(client, cleanup_registry)
        schedule_id = seed_schedule_EXT(
            db,
            user.user_id,
            name="duplicate-data-ready-ext",
            enabled=True,
            on_data_ready=True,
        )
        cleanup_registry.add(lambda: delete_schedule_EXT(db, schedule_id))
        cleanup_registry.add(lambda: delete_requests_for_user_EXT(db, user.user_id))
        duplicate_reftime = {
            "from": "2026-05-29T00:00:00.000000Z",
            "to": "2026-05-29T01:00:00.000000Z",
        }
        previous_request_id = seed_request_EXT(
            db,
            user.user_id,
            name="previous-data-ready-ext",
            args={
                "datasets": ["synthetic-task-ext"],
                "reftime": duplicate_reftime,
                "filters": None,
                "postprocessors": None,
                "output_format": None,
            },
            status=states.SUCCESS,
            schedule_id=schedule_id,
        )
        before_request_ids = {
            request.id for request in db.Request.query.filter_by(schedule_id=schedule_id)
        }

        # act
        # Chiamiamo il task direttamente; il duplicate check deve ritornare prima di
        # qualunque accesso ad Arkimet, filesystem output o notification.
        data_extraction.data_extract.run(
            user.user_id,
            ["synthetic-task-ext"],
            duplicate_reftime,
            None,
            [],
            None,
            None,
            False,
            None,
            schedule_id,
            True,
            False,
        )

        # assert
        # Nessuna nuova request o fileoutput deve essere creato; la request precedente
        # resta l'unico effetto persistito per la schedule.
        after_request_ids = {
            request.id for request in db.Request.query.filter_by(schedule_id=schedule_id)
        }
        assert before_request_ids == {previous_request_id}
        assert after_request_ids == before_request_ids
        assert db.FileOutput.query.filter_by(user_id=user.user_id).count() == 0
        if user.output_dir.exists():
            assert list(user.output_dir.iterdir()) == []


class TestDataExtractionNotificationsEXT:
    """Verifica notification email e AMQP con fake locali."""

    def test_notify_by_email_retries_with_sleep_noop_and_sends_payload_EXT(
        self,
        client: FlaskClient,
        cleanup_registry,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Il primo errore SMTP viene ritentato senza sleep reale e poi invia email.

        Il fake template rende ispezionabile title/status/message, mentre il fake SMTP
        fallisce una sola volta. Monkeypatchiamo `time.sleep` a no-op registrato, come
        richiesto dal prompt, per non rallentare la suite.
        """
        # arrange
        # Usiamo un utente DB reale solo per recuperare l'email destinataria con la
        # stessa query del task. Tutto il resto del percorso notification e fake.
        db = sqlalchemy.get_instance()
        user = create_task_test_user_EXT(client, cleanup_registry)
        db_user = db.User.query.get(user.user_id)
        assert db_user is not None
        captured_template: dict[str, object] = {}

        def fake_html_template_EXT(template_name, replaces):
            """Registra i dati template e restituisce body sintetici."""
            captured_template["template_name"] = template_name
            captured_template["replaces"] = dict(replaces)
            return f"html:{replaces['status']}:{replaces['message']}", "plain-body-ext"

        smtp_factory = RetryThenSuccessSmtpFactoryEXT(failures_before_success=1)
        sleep_calls: list[int] = []
        monkeypatch.setattr(data_extraction, "get_html_template", fake_html_template_EXT)
        monkeypatch.setattr(
            data_extraction.smtp,
            "get_instance",
            smtp_factory.get_instance_EXT,
        )
        monkeypatch.setattr(
            data_extraction.time,
            "sleep",
            lambda seconds: sleep_calls.append(seconds),
        )
        request = SimpleNamespace(
            name="email-notification-ext",
            status=states.FAILURE,
            error_message="synthetic failure",
        )

        # act
        # La funzione non deve propagare il primo errore SMTP: deve fare retry e poi
        # registrare un invio riuscito nel fake.
        data_extraction.notify_by_email(db, user.user_id, request, " after retry")

        # assert
        # Verifichiamo subject fisso, destinatario DB, corpo costruito dal template e
        # presenza del retry con sleep no-op.
        assert smtp_factory.send_attempts == 2
        assert len(smtp_factory.sent_messages) == 1
        sent = smtp_factory.sent_messages[0]
        assert sent.subject == "MeteoHub: data extraction completed"
        assert sent.recipient == db_user.email
        assert sent.body == "html:FAILURE:synthetic failure after retry"
        assert sent.plain_body == "plain-body-ext"
        assert captured_template == {
            "template_name": "data_extraction_result.html",
            "replaces": {
                "title": "email-notification-ext",
                "status": states.FAILURE,
                "message": "synthetic failure after retry",
            },
        }
        assert sleep_calls == [data_extraction.SLEEP_TIME]
        assert smtp_factory.get_instance_calls == [
            {"retries": 5, "retry_wait": 10},
            {"retries": 5, "retry_wait": 10},
        ]

    def test_notify_by_amqp_queue_sends_success_payload_with_download_url_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """La notifica AMQP success include status, reftime, filename e download_url.

        Il fake Rabbit registra il JSON che sarebbe stato inviato alla queue. Non serve
        una request DB reale: la funzione legge attributi gia caricati dal task dopo il
        commit, quindi un SimpleNamespace rende il contratto piu diretto e isolato.
        """
        # arrange
        # Sostituiamo broker e backend URL con fake controllati, poi costruiamo una
        # request sintetica di successo con fileoutput minimo.
        rabbit_factory = RecordingRabbitFactoryEXT()
        monkeypatch.setattr(
            data_extraction.rabbitmq,
            "get_instance",
            rabbit_factory.get_instance_EXT,
        )
        monkeypatch.setattr(
            data_extraction,
            "get_backend_url",
            lambda: "https://backend.example.invalid",
        )
        reftime = {
            "from": "2026-05-29T00:00:00.000000Z",
            "to": "2026-05-29T01:00:00.000000Z",
        }
        request = SimpleNamespace(
            name="amqp-notification-ext",
            status=states.SUCCESS,
            args={"reftime": reftime},
            error_message=None,
            fileoutput=SimpleNamespace(filename="synthetic-output.grib"),
        )

        # act
        data_extraction.notify_by_amqp_queue("queue.notification.ext", request)

        # assert
        # Il payload deve contenere i campi consumabili dal client AMQP e deve essere
        # pubblicato sulla routing key dell'utente, senza broker reale.
        assert rabbit_factory.connection.sent_messages == [
            {
                "payload": {
                    "request_name": "amqp-notification-ext",
                    "status": states.SUCCESS,
                    "reftime": reftime,
                    "filename": "synthetic-output.grib",
                    "download_url": "https://backend.example.invalid/api/data/synthetic-output.grib",
                },
                "routing_key": "queue.notification.ext",
            }
        ]
        assert rabbit_factory.connection.disconnected is True


class TestPackageDataLicenseEXT:
    """Mantiene nel prompt 07 il controllo filesystem del package license."""

    def test_package_data_license_archives_license_and_removes_original_EXT(
        self,
        tmp_path,
        cleanup_registry,
    ) -> None:
        """Il tar contiene output e LICENSE, mentre il file output originale sparisce.

        Questo helper era gia coperto nei quick wins, ma il prompt 07 richiede di
        mantenerne il contratto accanto ai side effect data_extraction. Usiamo tmp_path
        e lo registriamo anche nel cleanup_registry per documentare esplicitamente il
        teardown filesystem.
        """
        # arrange
        # I file sono contenuto sintetico puro: nessun output meteo reale o postprocessor
        # viene coinvolto nella creazione del tar.
        cleanup_registry.add_path(tmp_path)
        out_file = tmp_path / "task-output.grib"
        license_file = tmp_path / "license.txt"
        out_file.write_text("synthetic output", encoding="utf-8")
        license_file.write_text("synthetic license", encoding="utf-8")

        # act
        tar_filename = data_extraction.package_data_license(
            tmp_path,
            out_file,
            license_file,
        )

        # assert
        # Il package finale deve essere leggibile, contenere i due nomi attesi e aver
        # rimosso il file output originale, lasciando LICENSE sorgente intatta.
        tar_path = tmp_path / tar_filename
        assert tar_path.exists()
        assert not out_file.exists()
        assert license_file.exists()
        with tarfile.open(tar_path, "r:gz") as tar:
            assert sorted(tar.getnames()) == ["LICENSE", "task-output.grib"]
            output_member = tar.extractfile("task-output.grib")
            license_member = tar.extractfile("LICENSE")
            assert output_member is not None
            assert license_member is not None
            assert output_member.read().decode("utf-8") == "synthetic output"
            assert license_member.read().decode("utf-8") == "synthetic license"