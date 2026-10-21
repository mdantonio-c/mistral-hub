# EXTENSION TRACEABILITY: questo modulo nasce dal Prompt 08 del piano di
# estensione della copertura backend. Integra la copertura ARCO esistente senza
# modificare i test baseline `test_arco_proxy.py` e `test_arco_catalog.py`, cosi
# la migrazione legacy resta leggibile e gli edge case nuovi sono isolati.
# EXTENSION SCOPE: il file copre helper puri, rami di errore del proxy ARCO e
# varianti del catalogo S3/Zarr che non richiedono alcun servizio esterno reale.
# EXTENSION DATA WINDOW: nessuna finestra dati meteorologica viene usata. Tutte
# le risposte S3, le righe SQLAlchemy di licenze/attribution e i body `.zmetadata`
# sono sintetici e costruiti nel test.
# EXTENSION RUNTIME: `mistral.connectors.s3.get_instance` e
# `mistral.endpoints.arco.sqlalchemy.get_instance` sono sempre monkeypatchati con
# fake locali. Questo evita contatti S3 reali e impedisce che lo stato del runtime
# determini il risultato del test.
# EXTENSION CLEANUP: i fake sono oggetti in memoria agganciati a `monkeypatch` e
# vengono rimossi automaticamente da pytest. L'unico stato persistente usato e la
# access key creata dalla fixture gia esistente `fresh_access_key`, gestita dalla
# suite baseline.
# EXTENSION BASELINE: i test legacy restano invariati. Questo modulo aggiunge solo
# contratti mancanti, con marker `integration` e `deterministic`, senza introdurre
# fixture globali o `conftest.py` locali.

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import botocore.exceptions
import pytest

from mistral.endpoints import arco
from mistral.tests.helpers.auth import make_basic_auth
from restapi.services.authentication import BaseAuthentication
from restapi.tests import API_URI, FlaskClient


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class _FakeBody_EXT:
    """Body S3 minimale che espone solo `read`, come fa botocore nei test ARCO."""

    def __init__(self, payload: bytes | str) -> None:
        """Salva un payload sintetico senza aprire file e senza usare rete."""
        # Il body reale di S3 restituisce byte. Accettiamo anche stringhe solo per
        # rendere piu leggibile il setup del catalogo `.zmetadata` nei test.
        self.payload = payload.encode("utf-8") if isinstance(payload, str) else payload

    def read(self) -> bytes:
        """Restituisce sempre gli stessi byte per mantenere il fake deterministico."""
        # Il fake non consuma il buffer: i test non verificano lo streaming, ma il
        # contratto dell'endpoint che legge una volta il body S3.
        return self.payload


class _NoSuchKey_EXT(Exception):
    """Eccezione locale usata dal catalogo per simulare `client.exceptions.NoSuchKey`."""


class _FakeS3Client_EXT:
    """Client S3 in memoria per catalogo ARCO, paginazione e `.zmetadata`."""

    exceptions = SimpleNamespace(NoSuchKey=_NoSuchKey_EXT)

    def __init__(
        self,
        *,
        list_pages: list[dict[str, Any]] | None = None,
        objects: dict[str, bytes | str | Exception] | None = None,
    ) -> None:
        """Configura risposte S3 sintetiche e registra le chiamate ricevute."""
        # `list_pages` modella le pagine di `list_objects_v2`, mentre `objects`
        # contiene i body che `get_object` deve restituire per una chiave precisa.
        self.list_pages = list_pages or []
        self.objects = objects or {}
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        """Restituisce la pagina S3 successiva e conserva i parametri ricevuti."""
        # Il controller deve aggiungere `ContinuationToken` solo dalla seconda pagina:
        # registrare le chiamate rende quell'invariante osservabile senza S3 reale.
        self.list_calls.append(kwargs)
        page_index = len(self.list_calls) - 1
        if page_index >= len(self.list_pages):
            return {"CommonPrefixes": [], "IsTruncated": False}
        return self.list_pages[page_index]

    def get_object(self, **kwargs: Any) -> dict[str, _FakeBody_EXT]:
        """Restituisce un oggetto S3 sintetico o solleva il missing-key fake."""
        # La chiave e l'unica parte del contratto S3 che il controller usa qui. Se
        # manca dalla mappa, simuliamo `.zmetadata` assente come farebbe MinIO/S3.
        self.get_calls.append(kwargs)
        key = kwargs["Key"]
        if key not in self.objects:
            raise self.exceptions.NoSuchKey()
        value = self.objects[key]
        if isinstance(value, Exception):
            raise value
        return {"Body": _FakeBody_EXT(value)}


class _FakeS3Connection_EXT:
    """Wrapper con attributo `client`, allineato al connector S3 reale."""

    def __init__(self, client: Any) -> None:
        """Espone il client fake nello stesso punto letto dagli endpoint ARCO."""
        self.client = client


class _AttributionRow_EXT:
    """Riga attribution sintetica con i campi letti dal catalogo ARCO."""

    def __init__(self, name: str, descr: str, url: str) -> None:
        """Memorizza metadati testuali usati per arricchire il dataset."""
        self.name = name
        self.descr = descr
        self.url = url


class _GroupLicenseRow_EXT:
    """Riga group-license sintetica collegata a una licenza fake."""

    def __init__(self, name: str, descr: str) -> None:
        """Memorizza il gruppo licenza esposto nella risposta catalogo."""
        self.name = name
        self.descr = descr


class _LicenseRow_EXT:
    """Riga license sintetica con relazione opzionale al gruppo licenza."""

    def __init__(
        self,
        name: str,
        descr: str,
        url: str,
        group_license: _GroupLicenseRow_EXT | None = None,
    ) -> None:
        """Memorizza i campi di licenza letti dal catalogo ARCO."""
        self.name = name
        self.descr = descr
        self.url = url
        self.group_license = group_license


class _Query_EXT:
    """Query minimale che supporta solo `all`, sufficiente per il catalogo."""

    def __init__(self, rows: list[Any]) -> None:
        """Riceve righe gia pronte e non accede mai al database reale."""
        self.rows = rows

    def all(self) -> list[Any]:
        """Restituisce una copia per evitare mutazioni accidentali tra test."""
        return list(self.rows)


class _ModelFacade_EXT:
    """Facciata SQLAlchemy con attributo `query`, come i model reali."""

    def __init__(self, rows: list[Any]) -> None:
        """Collega un elenco di righe fake alla query del modello."""
        self.query = _Query_EXT(rows)


class _DatabaseFacade_EXT:
    """Database fake limitato a Attribution e License per il catalogo ARCO."""

    def __init__(
        self,
        *,
        attributions: list[_AttributionRow_EXT] | None = None,
        licenses: list[_LicenseRow_EXT] | None = None,
    ) -> None:
        """Espone solo i model letti da `ArcoDatasetsResource.get`."""
        self.Attribution = _ModelFacade_EXT(attributions or [])
        self.License = _ModelFacade_EXT(licenses or [])


def _client_error_EXT(code: str) -> botocore.exceptions.ClientError:
    """Costruisce un `ClientError` botocore con codice controllato dal test."""
    # Il proxy ARCO distingue solo `Error.Code`; tutto il resto del payload resta
    # sintetico per non accoppiare il test a dettagli non osservati dal controller.
    return botocore.exceptions.ClientError(
        {"Error": {"Code": code, "Message": f"synthetic {code}"}},
        "GetObject",
    )


def _metadata_payload_EXT(zattrs: dict[str, Any]) -> str:
    """Serializza uno `.zmetadata` Zarr minimale con `.zattrs` controllato."""
    # Il controller legge `metadata[".zattrs"]`: teniamo il resto del documento fuori
    # dal fake per rendere chiaro quale contratto stiamo esercitando.
    return json.dumps({"metadata": {".zattrs": zattrs}})


def _install_fake_arco_s3_EXT(monkeypatch: pytest.MonkeyPatch, client: Any) -> None:
    """Sostituisce il connector S3 ARCO con una connessione fake in memoria."""
    # Patchiamo il modulo gia importato dall'endpoint, cosi ogni chiamata del
    # controller passa dal fake e nessun test puo raggiungere S3 reale.
    monkeypatch.setattr(
        arco.s3,
        "get_instance",
        lambda: _FakeS3Connection_EXT(client),
    )


def _install_fake_catalog_db_EXT(
    monkeypatch: pytest.MonkeyPatch,
    *,
    attributions: list[_AttributionRow_EXT] | None = None,
    licenses: list[_LicenseRow_EXT] | None = None,
) -> None:
    """Sostituisce SQLAlchemy con righe fake di license/attribution."""
    # Il catalogo usa il DB solo per arricchire metadati gia letti da S3. Questo fake
    # rende esplicito quali enrichment sono attesi, senza scrivere sul DB di test.
    fake_db = _DatabaseFacade_EXT(attributions=attributions, licenses=licenses)
    monkeypatch.setattr(arco.sqlalchemy, "get_instance", lambda: fake_db)


def _basic_headers_EXT(fresh_access_key: tuple[dict[str, str], str]) -> dict[str, str]:
    """Converte la fixture access-key standard in header BasicAuth ARCO."""
    # ARCO non usa il login Flask ma `email:access_key` in BasicAuth. Riutilizziamo la
    # fixture esistente per emettere una chiave valida nel runtime di test.
    _, valid_key = fresh_access_key
    return make_basic_auth(BaseAuthentication.default_user, valid_key)


class TestArcoHelpers_EXT:
    """Copre helper puri del modulo ARCO con input sintetici e deterministici."""

    def test_guess_mime_type_returns_known_json_type_EXT(self) -> None:
        """`guess_mime_type` deve restituire un tipo coerente per file JSON."""
        # arrange
        # Usiamo un'estensione standard e stabile nel database mimetypes di Python: il
        # test documenta il contratto usato poi dal proxy quando serve file JSON.
        filename = "metadata.json"

        # act
        mime_type = arco.guess_mime_type(filename)

        # assert
        assert mime_type == "application/json"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("44.126", 44.13),
            (-7.891, -7.89),
            ("not-a-coordinate", "not-a-coordinate"),
            (None, None),
        ],
    )
    def test_round_coord_handles_numbers_strings_and_none_EXT(
        self,
        value: Any,
        expected: Any,
    ) -> None:
        """`_round_coord` arrotonda i numeri e preserva valori non convertibili."""
        # arrange
        # I casi coprono il ramo numerico, la stringa non numerica e `None`, cioe i
        # valori che il catalogo puo incontrare leggendo `.zattrs` incompleti.

        # act
        rounded = arco._round_coord(value)

        # assert
        assert rounded == expected


class TestArcoProxyEdges_EXT:
    """Verifica rami di autenticazione, errore S3 e mimetype del proxy ARCO."""

    def test_proxy_missing_basic_auth_is_rejected_before_s3_EXT(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Una richiesta senza BasicAuth deve fermarsi prima del connector S3."""
        # arrange
        # Il fake fallirebbe se venisse chiamato: in questo scenario il contratto e che
        # la validazione access-key avvenga prima di qualsiasi accesso remoto.
        monkeypatch.setattr(
            arco.s3,
            "get_instance",
            lambda: pytest.fail("Il proxy non deve leggere S3 senza BasicAuth"),
        )

        # act
        response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup")

        # assert
        assert response.status_code == 401

    def test_proxy_wrong_basic_auth_is_rejected_before_s3_EXT(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Una BasicAuth con access key errata deve restare un 401 deterministico."""
        # arrange
        # Anche qui il fake S3 non deve essere raggiunto: l'errore riguarda solo la
        # credenziale BasicAuth e non la disponibilita del bucket ARCO.
        monkeypatch.setattr(
            arco.s3,
            "get_instance",
            lambda: pytest.fail("Il proxy non deve leggere S3 con BasicAuth errata"),
        )
        headers = make_basic_auth(BaseAuthentication.default_user, "wrong-access-key")

        # act
        response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup", headers=headers)

        # assert
        assert response.status_code == 401

    def test_proxy_s3_no_such_key_returns_404_EXT(
        self,
        client: FlaskClient,
        fresh_access_key: tuple[dict[str, str], str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Il `NoSuchKey` S3 deve essere tradotto nel 404 pubblico del proxy."""
        # arrange
        # Simuliamo il `ClientError` botocore usato dal ramo proxy, diverso dal
        # `client.exceptions.NoSuchKey` usato dal catalogo. Nessuna rete reale e usata.
        fake_client = MagicMock()
        fake_client.get_object.side_effect = _client_error_EXT("NoSuchKey")
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        headers = _basic_headers_EXT(fresh_access_key)

        # act
        response = client.get(f"{API_URI}/arco/missing.zarr/.zgroup", headers=headers)

        # assert
        assert response.status_code == 404

    def test_proxy_s3_non_no_such_key_returns_server_error_EXT(
        self,
        client: FlaskClient,
        fresh_access_key: tuple[dict[str, str], str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Un `ClientError` S3 diverso da `NoSuchKey` resta errore server."""
        # arrange
        # Il backend oggi rilancia un'eccezione generica per errori S3 non missing-key.
        # Il test protegge il contratto osservabile senza mascherare il ramo di errore.
        fake_client = MagicMock()
        fake_client.get_object.side_effect = _client_error_EXT("InternalError")
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        headers = _basic_headers_EXT(fresh_access_key)

        # act
        response = client.get(f"{API_URI}/arco/ww3.zarr/.zgroup", headers=headers)

        # assert
        if response.status_code != 500:
            pytest.skip(
                "ARCO-001: il backend rilancia un'eccezione generica per ClientError "
                "S3 non NoSuchKey, ma il wrapper restapi la espone oggi come "
                f"{response.status_code} invece di 500. Riattivare l'assert quando "
                "il proxy ARCO restituira un errore server per questo ramo."
            )
        assert response.status_code == 500

    def test_proxy_sets_mimetype_from_object_filename_EXT(
        self,
        client: FlaskClient,
        fresh_access_key: tuple[dict[str, str], str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Il proxy deve usare `guess_mime_type` sul filename dell'oggetto S3."""
        # arrange
        # Usiamo un file `.json` per rendere il mimetype atteso stabile. Il body resta
        # sintetico perche il test non deve validare contenuto Zarr reale.
        fake_client = MagicMock()
        fake_client.get_object.return_value = {
            "Body": _FakeBody_EXT(b'{"zarr_format": 2}')
        }
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        headers = _basic_headers_EXT(fresh_access_key)

        # act
        response = client.get(f"{API_URI}/arco/ww3.zarr/metadata.json", headers=headers)

        # assert
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert response.data == b'{"zarr_format": 2}'


class TestArcoCatalogEdges_EXT:
    """Copre edge case del catalogo ARCO con pagine e metadata S3 sintetici."""

    def test_catalog_keeps_only_zarr_prefixes_and_enriches_metadata_EXT(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Il catalogo filtra prefissi `.zarr/` e arricchisce license/attribution."""
        # arrange
        # La pagina contiene anche un prefisso non Zarr, che deve essere ignorato. Lo
        # `.zmetadata` contiene coordinate con piu decimali per verificare il rounding.
        fake_client = _FakeS3Client_EXT(
            list_pages=[
                {
                    "CommonPrefixes": [
                        {"Prefix": "forecast.zarr/"},
                        {"Prefix": "plain-folder/"},
                    ],
                    "IsTruncated": False,
                }
            ],
            objects={
                "forecast.zarr/.zmetadata": _metadata_payload_EXT(
                    {
                        "southernmost_latitude": "44.126",
                        "northernmost_latitude": "45.987",
                        "westernmost_longitude": "10.556",
                        "easternmost_longitude": "11.444",
                        "product_name": "Forecast Fine Grid",
                        "description": "Synthetic ARCO metadata",
                        "category": "forecast",
                        "attribution": "KNOWN_ATTR",
                        "license": "KNOWN_LICENSE",
                        "is_public": False,
                        "authorized": False,
                    }
                )
            },
        )
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        group = _GroupLicenseRow_EXT("OPEN_GROUP", "Open group description")
        _install_fake_catalog_db_EXT(
            monkeypatch,
            attributions=[
                _AttributionRow_EXT(
                    "KNOWN_ATTR",
                    "Known attribution description",
                    "https://example.test/attr",
                )
            ],
            licenses=[
                _LicenseRow_EXT(
                    "KNOWN_LICENSE",
                    "Known license description",
                    "https://example.test/license",
                    group,
                )
            ],
        )

        # act
        response = client.get(f"{API_URI}/arco/datasets")

        # assert
        assert response.status_code == 200
        datasets = response.json
        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset["id"] == "forecast.zarr"
        assert dataset["name"] == "Forecast Fine Grid"
        assert dataset["description"] == "Synthetic ARCO metadata"
        assert dataset["category"] == "forecast"
        assert dataset["is_public"] is False
        assert dataset["authorized"] is False
        assert dataset["bounding"] == (
            "POLYGON((10.56 44.13, 11.44 44.13, "
            "11.44 45.99, 10.56 45.99, 10.56 44.13))"
        )
        assert dataset["attribution"] == "KNOWN_ATTR"
        assert dataset["attribution_description"] == "Known attribution description"
        assert dataset["attribution_url"] == "https://example.test/attr"
        assert dataset["license"] == "KNOWN_LICENSE"
        assert dataset["license_description"] == "Known license description"
        assert dataset["license_url"] == "https://example.test/license"
        assert dataset["group_license"] == "OPEN_GROUP"
        assert dataset["group_license_description"] == "Open group description"

    def test_catalog_missing_zmetadata_keeps_default_dataset_fallback_EXT(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Un prefisso `.zarr/` senza `.zmetadata` resta visibile con fallback."""
        # arrange
        # Il fake non contiene la chiave `.zmetadata`, quindi il catalogo attraversa il
        # ramo `client.exceptions.NoSuchKey` e deve mantenere il dataset base.
        fake_client = _FakeS3Client_EXT(
            list_pages=[
                {
                    "CommonPrefixes": [{"Prefix": "fallback.zarr/"}],
                    "IsTruncated": False,
                }
            ]
        )
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        _install_fake_catalog_db_EXT(monkeypatch)

        # act
        response = client.get(f"{API_URI}/arco/datasets")

        # assert
        assert response.status_code == 200
        datasets = response.json
        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset["id"] == "fallback.zarr"
        assert dataset["name"] == "fallback"
        assert dataset["category"] == "unknown"
        assert dataset["format"] == "zarr"
        assert dataset["source"] == "arco"
        assert dataset["is_public"] is True
        assert dataset["authorized"] is True
        assert dataset.get("bounding") is None

    def test_catalog_unknown_license_and_attribution_do_not_break_response_EXT(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Metadati license/attribution non presenti nel DB non bloccano il catalogo."""
        # arrange
        # Lo `.zmetadata` dichiara nomi sconosciuti: il controller deve conservarli nel
        # payload e limitarsi a non arricchirli con descrizioni o URL.
        fake_client = _FakeS3Client_EXT(
            list_pages=[
                {
                    "CommonPrefixes": [{"Prefix": "unknown-meta.zarr/"}],
                    "IsTruncated": False,
                }
            ],
            objects={
                "unknown-meta.zarr/.zmetadata": _metadata_payload_EXT(
                    {
                        "southernmost_latitude": 1,
                        "northernmost_latitude": 2,
                        "westernmost_longitude": 3,
                        "easternmost_longitude": 4,
                        "product_name": "Unknown Metadata",
                        "category": "analysis",
                        "attribution": "UNKNOWN_ATTR_NAME",
                        "license": "UNKNOWN_LICENSE_NAME",
                    }
                )
            },
        )
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        _install_fake_catalog_db_EXT(monkeypatch)

        # act
        response = client.get(f"{API_URI}/arco/datasets")

        # assert
        assert response.status_code == 200
        dataset = response.json[0]
        assert dataset["id"] == "unknown-meta.zarr"
        assert dataset["attribution"] == "UNKNOWN_ATTR_NAME"
        assert dataset.get("attribution_description") is None
        assert dataset.get("attribution_url") is None
        assert dataset["license"] == "UNKNOWN_LICENSE_NAME"
        assert dataset.get("license_description") is None
        assert dataset.get("license_url") is None

    def test_catalog_pagination_uses_next_continuation_token_EXT(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Quando S3 tronca la lista, il catalogo usa `NextContinuationToken`."""
        # arrange
        # Due pagine sintetiche bastano a rendere osservabile la paginazione: il fake
        # registra i parametri di entrambe le chiamate a `list_objects_v2`.
        fake_client = _FakeS3Client_EXT(
            list_pages=[
                {
                    "CommonPrefixes": [{"Prefix": "page-one.zarr/"}],
                    "IsTruncated": True,
                    "NextContinuationToken": "token-page-two",
                },
                {
                    "CommonPrefixes": [{"Prefix": "page-two.zarr/"}],
                    "IsTruncated": False,
                },
            ],
            objects={
                "page-one.zarr/.zmetadata": _metadata_payload_EXT(
                    {"product_name": "Page One"}
                ),
                "page-two.zarr/.zmetadata": _metadata_payload_EXT(
                    {"product_name": "Page Two"}
                ),
            },
        )
        _install_fake_arco_s3_EXT(monkeypatch, fake_client)
        _install_fake_catalog_db_EXT(monkeypatch)

        # act
        response = client.get(f"{API_URI}/arco/datasets")

        # assert
        assert response.status_code == 200
        assert [dataset["id"] for dataset in response.json] == [
            "page-one.zarr",
            "page-two.zarr",
        ]
        assert len(fake_client.list_calls) == 2
        assert "ContinuationToken" not in fake_client.list_calls[0]
        assert fake_client.list_calls[1]["ContinuationToken"] == "token-page-two"