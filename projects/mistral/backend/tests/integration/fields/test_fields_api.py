# Test di GET /fields (Fields.get in endpoints/fields.py): filtri e statistiche.
# Ambito: copre OBS map mode, OBS dataset mode, errori di autorizzazione e validazione
# (bbox incluse, anche con coordinate a zero) e FOR dataset mode con lm5/lm2.2, incluse
# le descriptions e SummaryStats=False.
# Finestra dati: OBS usa solo agrmet DBALLE 2020-04-06 00:00-01:00 e agrmet Arkimet
# 2020-03-31/2020-04-01; FOR usa solo lm5 2021-10-19 o lm2.2 2019-09-10.
# Runtime fake: i rami multi-dataset non richiedono dati Arkimet reali e usano dataset
# sintetici piu monkeypatch mirati del calcolo categoria per raggiungere il controller;
# i rami happy path interrogano il runtime reale nelle finestre consentite.
# Cleanup: utenti temporanei, dataset sintetici e licenze sintetiche sono registrati nel
# cleanup_registry; il catalogo reale (agrmet compreso) viene solo letto.

from __future__ import annotations

from uuid import uuid4

import mistral.endpoints.fields as fields_endpoint_module
import pytest
from mistral.models.sqlalchemy import DatasetCategories
from mistral.services.arkimet import BeArkimet
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.auth import create_dataset_test_user
from mistral.tests.helpers.datasets import create_private_test_network
from mistral.tests.helpers.observed_windows import (
    OBSERVED_DATASET_NAME,
    OBSERVED_LICENSE_GROUP,
    OBSERVED_MISMATCH_LICENSE_GROUP,
    OBSERVED_NETWORK,
    dballe_window_override,
    parse_response,
    require_observed_dataset_user,
)
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tests.integration.fields.support import (
    OBS_ARCHIVE_QUERY,
    OBS_DBALLE_QUERY,
    OBS_DBALLE_QUERY_WITHOUT_LICENSE,
    create_fields_synthetic_dataset,
    create_private_observed_dataset_for_all_available_products,
    fields_url,
    get_or_create_multim_forecast_dataset,
    require_forecast_fields_case,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


def test_fields_observed_map_mode_returns_recent_agrmet_filters(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica GET /fields in OBS map mode su agrmet DBALLE 2020-04-06 00:00-01:00.

    Il ramo senza `datasets` e quello usato dalle mappe: il test passa network e license
    dentro q, forza solo la classificazione DBALLE e controlla summary/network/product.
    """
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY)

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert content["items"]["summarystats"]["c"] > 0
    assert any(
        item["code"] == OBSERVED_NETWORK for item in content["items"].get("network", [])
    )
    assert content["items"].get("product")


def test_fields_observed_dataset_mode_returns_agrmet_filters(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
) -> None:
    """Verifica GET /fields in OBS dataset mode con utente autenticato.

    Usa agrmet DBALLE 2020-04-06 e si aspetta 200 con summarystats e network.
    """
    # arrange
    user = require_observed_dataset_user(client, cleanup_registry)
    endpoint = fields_url(
        datasets=OBSERVED_DATASET_NAME,
        q=OBS_DBALLE_QUERY_WITHOUT_LICENSE,
    )

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=user.headers)

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert content["items"]["summarystats"]["c"] > 0
    assert content["items"].get("network")


def test_fields_observed_archived_map_mode_rejects_anonymous_user(
    client: FlaskClient,
) -> None:
    """Verifica il 401 di GET /fields per un anonimo su dati archiviati.

    Usa la finestra agrmet Arkimet 2020-03-31/2020-04-01.
    """
    # arrange
    endpoint = fields_url(q=OBS_ARCHIVE_QUERY)

    # act
    response = client.get(endpoint)

    # assert
    assert response.status_code == 401


def test_fields_observed_archived_map_mode_rejects_user_without_archive_permission(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il 401 di GET /fields su dati archiviati per utente senza permesso.

    L'utente non ha allowed_obs_archive; le date sono quelle Arkimet ammesse.
    """
    # arrange
    user = require_observed_dataset_user(client, cleanup_registry, allowed_obs_archive=False)

    # act
    response = client.get(fields_url(q=OBS_ARCHIVE_QUERY), headers=user.headers)

    # assert
    assert response.status_code == 401


def test_fields_observed_unknown_network_returns_not_found(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 404 di GET /fields per network inesistente in OBS map mode."""
    # arrange
    query = OBS_DBALLE_QUERY.replace(OBSERVED_NETWORK, f"missing_{uuid4().hex}")

    # act
    with dballe_window_override(test_runtime):
        response = client.get(fields_url(q=query), headers=auth_headers)

    # assert
    assert response.status_code == 404


def test_fields_observed_private_network_returns_unauthorized_without_local_oracle(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
    monkeypatch,
) -> None:
    """Verifica il 401 di GET /fields su una rete OBS privata senza permesso.

    La rete e il dataset privato sono sintetici e creati dal test.
    """
    # arrange
    # Il dataset reale agrmet non viene modificato: la rete sintetica punta a un dataset
    # privato creato dal test e l'utente non ha grant su di esso.
    db = sqlalchemy.get_instance()
    private_network = create_private_test_network(
        db,
        cleanup_registry,
        monkeypatch,
        prefix="fields_ext_private",
    )
    user = create_dataset_test_user(client, cleanup_registry, [])
    query = OBS_DBALLE_QUERY.replace(OBSERVED_NETWORK, private_network)

    # act
    with dballe_window_override(test_runtime):
        response = client.get(fields_url(q=query), headers=user.headers)

    # assert
    assert response.status_code == 401


def test_fields_observed_missing_license_group_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 di GET /fields quando OBS map mode non riceve license in q."""
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY_WITHOUT_LICENSE)

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_unknown_license_group_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 di GET /fields per gruppo licenza OBS inesistente."""
    # arrange
    query = OBS_DBALLE_QUERY.replace(OBSERVED_LICENSE_GROUP, f"missing_{uuid4().hex}")

    # act
    with dballe_window_override(test_runtime):
        response = client.get(fields_url(q=query), headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_mismatch_network_license_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 di GET /fields se agrmet ha un gruppo licenza diverso dal suo."""
    # arrange
    query = OBS_DBALLE_QUERY.replace(
        OBSERVED_LICENSE_GROUP,
        OBSERVED_MISMATCH_LICENSE_GROUP,
    )

    # act
    with dballe_window_override(test_runtime):
        response = client.get(fields_url(q=query), headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_missing_dataset_returns_not_found(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 404 di GET /fields in dataset mode per un dataset inesistente."""
    # arrange
    endpoint = fields_url(datasets=f"missing_dataset_{uuid4().hex}")

    # act
    response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 404


def test_fields_observed_incomplete_bbox_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 di GET /fields per bbox incompleta in OBS map mode.

    La query usa la finestra DBALLE ammessa.
    """
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, lonmin=10.0)

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_bbox_with_zero_coordinates_is_applied(
    client: FlaskClient,
    auth_headers,
    test_runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica che una bbox completa con estremi a zero venga passata alla query.

    Lo zero (meridiano di Greenwich, equatore) e una coordinata valida, non un valore
    mancante. Il caricamento dei filtri DB-All.e e sostituito da un fake che registra
    la query ricevuta.
    """
    # arrange
    received_queries: list[dict] = []

    def fake_load_filters(*args, query_dic=None, **kwargs):
        received_queries.append(dict(query_dic))
        return {}, {}

    monkeypatch.setattr(BeDballe, "load_filters", staticmethod(fake_load_filters))
    endpoint = fields_url(
        q=OBS_DBALLE_QUERY, lonmin=0.0, latmin=0.0, lonmax=20.0, latmax=50.0
    )

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 200
    assert len(received_queries) == 1
    bbox = {
        key: received_queries[0][key]
        for key in ("lonmin", "latmin", "lonmax", "latmax")
    }
    assert bbox == {"lonmin": 0.0, "latmin": 0.0, "lonmax": 20.0, "latmax": 50.0}


def test_fields_observed_bbox_without_lonmin_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 di GET /fields per una bbox parziale senza lonmin.

    Una bbox parziale deve essere segnalata qualunque estremo manchi, non ignorata.
    """
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, latmin=40.0, lonmax=12.0, latmax=46.0)

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 400
    assert parse_response(response) == "Coordinates for bounding box are missing"


def test_fields_observed_only_summary_stats_returns_stats_only(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica che GET /fields con onlySummaryStats=true dia solo le statistiche.

    Usa agrmet DBALLE 2020-04-06 in OBS map mode.
    """
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, onlySummaryStats="true")

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert "c" in content
    assert "items" not in content


def test_fields_observed_summary_stats_false_omits_summary_stats(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica che GET /fields con SummaryStats=False ometta summarystats.

    Scenario OBS map mode su agrmet DBALLE 2020-04-06.
    """
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, SummaryStats="false")

    # act
    with dballe_window_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert "summarystats" not in content["items"]


def test_fields_observed_all_available_products_excludes_unauthorized_private_group(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
) -> None:
    """Verifica che allAvailableProducts non includa gruppi OBS privati non autorizzati.

    Il test interroga GET /fields su dati reali agrmet, ma crea un gruppo OBS privato
    sintetico come controllo negativo per l'elenco all_licenses autorizzato dell'utente.
    """
    # arrange
    db = sqlalchemy.get_instance()
    private_group_name = create_private_observed_dataset_for_all_available_products(
        db,
        cleanup_registry,
    )
    user = require_observed_dataset_user(client, cleanup_registry)

    # act
    with dballe_window_override(test_runtime):
        response = client.get(
            fields_url(q=OBS_DBALLE_QUERY, allAvailableProducts="true"),
            headers=user.headers,
        )

    # assert
    content = parse_response(response)
    all_license_codes = {
        item["code"] for item in content["items"].get("all_licenses", [])
    }
    assert response.status_code == 200
    assert OBSERVED_LICENSE_GROUP in all_license_codes
    assert private_group_name not in all_license_codes


def test_fields_forecast_dataset_mode_returns_descriptions_for_allowed_window(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica GET /fields in FOR dataset mode su lm5 2021-10-19 o lm2.2 2019-09-10.

    L'utente viene autorizzato esplicitamente al dataset scelto, cosi il test resta
    portabile tra locale e CI e controlla le descriptions quando summarystats.c > 0.
    """
    # arrange
    forecast_case = require_forecast_fields_case(client, cleanup_registry)

    # act
    content = forecast_case.content

    # assert
    assert content["items"]["summarystats"]["c"] > 0
    assert "descriptions" in content
    assert content["descriptions"].get("leveltypes")
    assert content["descriptions"].get("timerangetypes")


def test_fields_forecast_missing_dataset_returns_not_found(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 404 di GET /fields per dataset forecast inesistente."""
    # arrange
    endpoint = fields_url(datasets=f"missing_forecast_{uuid4().hex}")

    # act
    response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 404


def test_fields_forecast_multiple_categories_return_bad_request(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 400 di GET /fields per dataset con categorie diverse.

    I record DB sintetici arrivano fino al controllo categoria; il monkeypatch ritorna
    None come farebbe Arkimet quando riceve categorie incompatibili.
    """
    # arrange
    db = sqlalchemy.get_instance()
    forecast_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    observed_dataset = create_fields_synthetic_dataset(
        db,
        cleanup_registry,
        category=DatasetCategories.OBS,
        fileformat="bufr",
        dballe_dsn="DBALLE",
    )
    user = create_dataset_test_user(
        client,
        cleanup_registry,
        [forecast_dataset.id, observed_dataset.id],
    )
    monkeypatch.setattr(
        fields_endpoint_module.arki,
        "get_datasets_category",
        lambda datasets: None,
    )

    # act
    response = client.get(
        fields_url(
            datasets=f"{forecast_dataset.arkimet_id},{observed_dataset.arkimet_id}"
        ),
        headers=user.headers,
    )

    # assert
    assert response.status_code == 400


def test_fields_forecast_multiple_license_groups_return_bad_request(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch,
) -> None:
    """Verifica il 400 di GET /fields per dataset forecast di gruppi licenza diversi.

    I dataset sono sintetici; il monkeypatch fa risultare FOR la categoria comune,
    cosi la richiesta arriva al controllo dei gruppi licenza.
    """
    # arrange
    db = sqlalchemy.get_instance()
    first_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    second_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    user = create_dataset_test_user(
        client,
        cleanup_registry,
        [first_dataset.id, second_dataset.id],
    )
    monkeypatch.setattr(
        fields_endpoint_module.arki,
        "get_datasets_category",
        lambda datasets: "FOR",
    )

    # act
    response = client.get(
        fields_url(datasets=f"{first_dataset.arkimet_id},{second_dataset.arkimet_id}"),
        headers=user.headers,
    )

    # assert
    assert response.status_code == 400


def test_fields_forecast_multimodel_multi_dataset_returns_bad_request(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica il 400 di GET /fields per piu dataset insieme a multim-forecast."""
    # arrange
    db = sqlalchemy.get_instance()
    multim_dataset = get_or_create_multim_forecast_dataset(db, cleanup_registry)
    companion_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    user = create_dataset_test_user(
        client,
        cleanup_registry,
        [multim_dataset.id, companion_dataset.id],
    )

    # act
    response = client.get(
        fields_url(datasets=f"multim-forecast,{companion_dataset.arkimet_id}"),
        headers=user.headers,
    )

    # assert
    assert response.status_code == 400


def test_fields_forecast_only_summary_stats_returns_stats_only(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che GET /fields con onlySummaryStats=true dia solo le statistiche.

    Scenario forecast nella sola finestra ammessa.
    """
    # arrange
    forecast_case = require_forecast_fields_case(client, cleanup_registry)

    # act
    response = client.get(
        fields_url(
            datasets=forecast_case.dataset_name,
            q=forecast_case.query,
            onlySummaryStats="true",
        ),
        headers=forecast_case.headers,
    )

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert "c" in content
    assert "items" not in content


def test_fields_forecast_summary_stats_false_omits_summarystats(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Verifica che SummaryStats=False sul forecast ometta summarystats.

    Regressione FIELDS-001: il blocco finale di `Fields.get` usava `resulting_fields`,
    definito solo nel ramo OBS, e nel ramo forecast falliva con `UnboundLocalError`.
    Ora `summarystats` viene tolto dall'oggetto restituito in entrambi i rami.
    """
    # arrange
    forecast_case = require_forecast_fields_case(client, cleanup_registry)

    # act
    response = client.get(
        fields_url(
            datasets=forecast_case.dataset_name,
            q=forecast_case.query,
            SummaryStats="false",
        ),
        headers=forecast_case.headers,
    )

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert "summarystats" not in content["items"]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"SummaryStats": "false"}, {"items": {"level": []}}),
        ({"SummaryStats": "false", "onlySummaryStats": "true"}, {"c": 0, "s": 0}),
    ],
    ids=["summary-stats-false", "only-summary-stats-wins"],
)
def test_fields_forecast_summary_stats_with_controlled_arkimet_summary(
    client: FlaskClient,
    cleanup_registry,
    monkeypatch: pytest.MonkeyPatch,
    params: dict[str, str],
    expected: dict,
) -> None:
    """Verifica SummaryStats=False sul forecast senza dipendere dai dati Arkimet.

    Il summary Arkimet e sostituito da un valore controllato. Con onlySummaryStats=true
    la risposta contiene comunque solo le statistiche, anche se SummaryStats=false.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = db.Datasets.query.filter_by(arkimet_id="lm5").first()
    if dataset is None:
        pytest.skip("Dataset 'lm5' is not available in this environment")
    user = create_dataset_test_user(client, cleanup_registry, [dataset.id])
    monkeypatch.setattr(
        BeArkimet,
        "load_summary",
        staticmethod(
            lambda datasets=[], query="": {
                "items": {"summarystats": {"c": 0, "s": 0}, "level": []}
            }
        ),
    )

    # act
    response = client.get(
        fields_url(datasets="lm5", q="reftime:>=2021-10-19 00:00", **params),
        headers=user.headers,
    )

    # assert
    assert response.status_code == 200
    assert parse_response(response) == expected
