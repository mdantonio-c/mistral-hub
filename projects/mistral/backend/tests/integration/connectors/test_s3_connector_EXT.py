# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal Prompt 08 per
# coprire il connector S3 custom di Meteo-Hub senza modificare il codice
# applicativo e senza dipendere da MinIO, AWS o rete reale.
# EXTENSION SCOPE: i test verificano parametri obbligatori, costruzione endpoint,
# endpoint esplicito, `verify_ssl`, gestione fallimento `list_buckets`, stato di
# connessione e cleanup di `disconnect`.
# EXTENSION DATA WINDOW: nessun dataset meteorologico, bucket reale o oggetto S3
# viene letto. I bucket sono rappresentati da un fake client in memoria.
# EXTENSION RUNTIME: `boto3.Session` viene monkeypatchato in ogni test che chiama
# `connect`, cosi nessuna credenziale reale e nessun endpoint esterno vengono usati.
# EXTENSION CLEANUP: `monkeypatch` ripristina `Connector.services`, `S3Ext.app` e
# `boto3.Session` a fine test. Gli oggetti connector sono locali al singolo test.
# EXTENSION BASELINE: non vengono introdotti `conftest.py` o helper condivisi; la
# copertura resta confinata a questo file `_EXT.py` nel dominio `connectors`.

from __future__ import annotations

from typing import Any

import pytest

from mistral.connectors import s3 as s3_connector
from restapi.connectors import Connector
from restapi.exceptions import ServiceUnavailable


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class _FakeS3Client_EXT:
    """Client S3 minimale che registra `list_buckets` e puo fallire a comando."""

    def __init__(self, *, fail_list_buckets: bool = False) -> None:
        """Configura se il probe di connessione deve riuscire o fallire."""
        self.fail_list_buckets = fail_list_buckets
        self.list_buckets_calls = 0

    def list_buckets(self) -> dict[str, list[Any]]:
        """Simula il probe usato da `connect` e `is_connected`."""
        # Il connector non legge i bucket, usa solo il successo della chiamata come
        # prova di disponibilita. Per questo il fake restituisce una lista vuota.
        self.list_buckets_calls += 1
        if self.fail_list_buckets:
            raise RuntimeError("synthetic bucket probe failure")
        return {"Buckets": []}


class _FakeSession_EXT:
    """Sessione boto3 fake che restituisce sempre il client controllato dal test."""

    def __init__(self, recorder: dict[str, Any], client: _FakeS3Client_EXT) -> None:
        """Mantiene recorder e client senza aprire connessioni esterne."""
        self.recorder = recorder
        self.client_to_return = client

    def client(self, service_name: str, **kwargs: Any) -> _FakeS3Client_EXT:
        """Registra i parametri del client S3 richiesto dal connector."""
        # Salviamo endpoint, SSL e config per poterli assertare senza ispezionare boto3
        # reale. Il fake accetta solo il service name passato dal connector.
        self.recorder["client_calls"].append(
            {"service_name": service_name, "kwargs": kwargs}
        )
        return self.client_to_return


def _new_s3_connector_EXT(
    monkeypatch: pytest.MonkeyPatch,
    variables: dict[str, Any] | None = None,
) -> s3_connector.S3Ext:
    """Crea un connector S3 isolato con variabili di servizio controllate."""
    # `Connector.__init__` si aspetta una app gia inizializzata. Il test non ha bisogno
    # di Flask, quindi imposta un placeholder locale e ripristinato da monkeypatch.
    monkeypatch.setattr(s3_connector.S3Ext, "app", object(), raising=False)
    monkeypatch.setitem(Connector.services, "s3", variables or {})
    return s3_connector.S3Ext()


def _install_fake_boto3_session_EXT(
    monkeypatch: pytest.MonkeyPatch,
    fake_client: _FakeS3Client_EXT,
) -> dict[str, Any]:
    """Sostituisce `boto3.Session` e restituisce un recorder per le asserzioni."""
    # Il connector importa il modulo boto3 dentro `mistral.connectors.s3`. Patchiamo
    # quel riferimento diretto per garantire che nessun test apra sessioni reali.
    recorder: dict[str, Any] = {"session_calls": [], "client_calls": []}

    def fake_session_factory_EXT(**kwargs: Any) -> _FakeSession_EXT:
        """Registra credenziali sintetiche e restituisce una sessione fake."""
        recorder["session_calls"].append(kwargs)
        return _FakeSession_EXT(recorder, fake_client)

    monkeypatch.setattr(s3_connector.boto3, "Session", fake_session_factory_EXT)
    return recorder


class TestS3Connector_EXT:
    """Contratti deterministici del connector S3 custom di Meteo-Hub."""

    def test_connect_requires_host_key_id_and_access_key_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`connect` deve fallire in modo esplicito se mancano variabili richieste."""
        # arrange
        # Forziamo un servizio S3 senza variabili, evitando che eventuali env locali
        # rendano il test dipendente dalla macchina o dal container.
        connector = _new_s3_connector_EXT(monkeypatch, variables={})

        # act / assert
        with pytest.raises(ServiceUnavailable) as exc_info:
            connector.connect()

        assert "host" in str(exc_info.value)
        assert "key_id" in str(exc_info.value)
        assert "access_key" in str(exc_info.value)

    def test_connect_builds_endpoint_from_host_port_scheme_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Senza endpoint esplicito, il connector compone scheme, host e port."""
        # arrange
        # Il fake boto3 cattura l'endpoint costruito e conferma che il probe bucket e
        # stato eseguito una sola volta durante la connessione.
        fake_client = _FakeS3Client_EXT()
        recorder = _install_fake_boto3_session_EXT(monkeypatch, fake_client)
        connector = _new_s3_connector_EXT(monkeypatch, variables={})

        # act
        returned = connector.connect(
            host="minio.test",
            port="9001",
            scheme="http",
            key_id="synthetic-id",
            access_key="synthetic-secret",
            verify_ssl="false",
        )

        # assert
        assert returned is connector
        assert recorder["session_calls"] == [
            {
                "aws_access_key_id": "synthetic-id",
                "aws_secret_access_key": "synthetic-secret",
            }
        ]
        client_call = recorder["client_calls"][0]
        assert client_call["service_name"] == "s3"
        assert client_call["kwargs"]["endpoint_url"] == "http://minio.test:9001"
        assert client_call["kwargs"]["verify"] is False
        assert connector.client is fake_client
        assert fake_client.list_buckets_calls == 1

    def test_connect_respects_explicit_endpoint_and_verify_ssl_variable_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Endpoint esplicito e `verify_ssl` dalle variabili devono prevalere."""
        # arrange
        # Le variabili del servizio imitano la configurazione letta da Rapydo. Anche se
        # `host` e presente per il check richiesto, l'endpoint esplicito deve vincere.
        fake_client = _FakeS3Client_EXT()
        recorder = _install_fake_boto3_session_EXT(monkeypatch, fake_client)
        connector = _new_s3_connector_EXT(
            monkeypatch,
            variables={
                "host": "ignored-for-endpoint.test",
                "key_id": "service-id",
                "access_key": "service-secret",
                "endpoint": "https://s3.explicit.test/custom",
                "verify_ssl": "true",
            },
        )

        # act
        connector.connect()

        # assert
        client_call = recorder["client_calls"][0]
        assert client_call["kwargs"]["endpoint_url"] == "https://s3.explicit.test/custom"
        assert client_call["kwargs"]["verify"] is True

    def test_connect_raises_service_unavailable_when_bucket_probe_fails_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Un fallimento di `list_buckets` deve bloccare la connessione S3."""
        # arrange
        # Il client fake fallisce solo sul probe finale, dopo che sessione e client sono
        # stati creati. Questo isola il ramo di errore del connector.
        fake_client = _FakeS3Client_EXT(fail_list_buckets=True)
        _install_fake_boto3_session_EXT(monkeypatch, fake_client)
        connector = _new_s3_connector_EXT(monkeypatch, variables={})

        # act / assert
        with pytest.raises(ServiceUnavailable) as exc_info:
            connector.connect(
                host="minio.test",
                key_id="synthetic-id",
                access_key="synthetic-secret",
            )

        assert "Unable to connect to S3" in str(exc_info.value)
        assert fake_client.list_buckets_calls == 1

    def test_is_connected_returns_true_or_false_from_bucket_probe_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`is_connected` riflette il client corrente e lo stato disconnected."""
        # arrange
        # Qui non serve `connect`: impostiamo direttamente il client per coprire in modo
        # locale i tre esiti osservabili di `is_connected`.
        connector = _new_s3_connector_EXT(monkeypatch, variables={})
        healthy_client = _FakeS3Client_EXT()
        failing_client = _FakeS3Client_EXT(fail_list_buckets=True)

        # act / assert
        connector.client = healthy_client
        connector.disconnected = False
        assert connector.is_connected() is True

        connector.client = failing_client
        connector.disconnected = False
        assert connector.is_connected() is False

        connector.client = healthy_client
        connector.disconnected = True
        assert connector.is_connected() is False

    def test_disconnect_resets_client_and_marks_connector_disconnected_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`disconnect` deve rimuovere il client e segnare il connector come chiuso."""
        # arrange
        # Usiamo un client fake gia assegnato per verificare solo il cleanup locale del
        # connector, senza coinvolgere boto3 o variabili ambiente.
        connector = _new_s3_connector_EXT(monkeypatch, variables={})
        connector.client = _FakeS3Client_EXT()

        # act
        connector.disconnect()

        # assert
        assert connector.client is None
        assert connector.disconnected is True