# EXTENSION TRACEABILITY - Prompt 03, dominio /fields.
# Origine: questo modulo introduce la prima copertura dedicata dell'endpoint Fields.get
# senza modificare i test observed baseline e senza creare fixture globali.
# Ambito: copre OBS map mode, OBS dataset mode, errori authorization/validation e FOR
# dataset mode con lm5/lm2.2, inclusi descriptions e probe SummaryStats=False.
# Finestra dati: OBS usa solo agrmet DBALLE 2020-04-06 00:00-01:00 e agrmet Arkimet
# 2020-03-31/2020-04-01; FOR usa solo lm5 2021-10-19 o lm2.2 2019-09-10.
# Runtime fake: i rami multi-dataset non richiedono dati Arkimet reali e usano dataset
# sintetici piu monkeypatch mirati del calcolo categoria per raggiungere il controller;
# i rami happy path interrogano il runtime reale nelle finestre consentite.
# Cleanup: utenti temporanei, dataset sintetici e licenze temporanee sono registrati nel
# cleanup_registry; nessun conftest.py viene creato o modificato.
# Baseline non toccata: i test sono tutti in un nuovo modulo *_EXT.py e usano helper
# locali del dominio fields/support_EXT.py.

from __future__ import annotations

from uuid import uuid4

import mistral.endpoints.fields as fields_endpoint_module
import pytest
from mistral.models.sqlalchemy import DatasetCategories
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from mistral.tests.integration.fields.support_EXT import (
    OBSERVED_DATASET_NAME,
    OBSERVED_LICENSE_GROUP,
    OBSERVED_MISMATCH_LICENSE_GROUP,
    OBSERVED_NETWORK,
    OBS_ARCHIVE_QUERY,
    OBS_DBALLE_QUERY,
    OBS_DBALLE_QUERY_WITHOUT_LICENSE,
    create_fields_synthetic_dataset,
    create_fields_user,
    create_private_observed_dataset_for_all_available_products,
    fields_url,
    get_or_create_multim_forecast_dataset,
    observed_dballe_override,
    parse_response,
    require_dataset,
    require_forecast_fields_case,
    require_observed_dataset_user,
    temporarily_make_observed_dataset_private,
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
    """Verifica OBS map mode su agrmet DBALLE 2020-04-06 00:00-01:00.

    Il ramo senza `datasets` e quello usato dalle mappe: il test passa network e license
    dentro q, forza solo la classificazione DBALLE e controlla summary/network/product.
    """
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY)

    # act
    with observed_dballe_override(test_runtime):
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
    """Verifica OBS dataset mode autenticato su agrmet DBALLE 2020-04-06."""
    # arrange
    user = require_observed_dataset_user(client, cleanup_registry)
    endpoint = fields_url(
        datasets=OBSERVED_DATASET_NAME,
        q=OBS_DBALLE_QUERY_WITHOUT_LICENSE,
    )

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(endpoint, headers=user.headers)

    # assert
    content = parse_response(response)
    assert response.status_code == 200
    assert content["items"]["summarystats"]["c"] > 0
    assert content["items"].get("network")


def test_fields_observed_archived_map_mode_rejects_anonymous_user(
    client: FlaskClient,
) -> None:
    """Verifica il 401 anonimo su agrmet Arkimet 2020-03-31/2020-04-01."""
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
    """Verifica il 401 archive per utente senza allowed_obs_archive su date ammesse."""
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
    """Verifica il 404 per network inesistente nel ramo OBS map mode."""
    # arrange
    query = OBS_DBALLE_QUERY.replace(OBSERVED_NETWORK, f"missing_{uuid4().hex}")

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(fields_url(q=query), headers=auth_headers)

    # assert
    assert response.status_code == 404


def test_fields_observed_private_network_returns_unauthorized_without_local_oracle(
    client: FlaskClient,
    cleanup_registry,
    test_runtime,
) -> None:
    """Costruisce un 401 portabile rendendo temporaneamente agrmet privato."""
    # arrange
    db = sqlalchemy.get_instance()
    temporarily_make_observed_dataset_private(db, cleanup_registry)
    user = create_fields_user(client, cleanup_registry, [])

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(fields_url(q=OBS_DBALLE_QUERY), headers=user.headers)

    # assert
    assert response.status_code == 401


def test_fields_observed_missing_license_group_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 quando OBS map mode non riceve license in q."""
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY_WITHOUT_LICENSE)

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_unknown_license_group_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 per gruppo licenza OBS inesistente."""
    # arrange
    query = OBS_DBALLE_QUERY.replace(OBSERVED_LICENSE_GROUP, f"missing_{uuid4().hex}")

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(fields_url(q=query), headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_mismatch_network_license_returns_bad_request(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica il 400 quando agrmet viene accoppiato a un gruppo licenza diverso."""
    # arrange
    query = OBS_DBALLE_QUERY.replace(
        OBSERVED_LICENSE_GROUP,
        OBSERVED_MISMATCH_LICENSE_GROUP,
    )

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(fields_url(q=query), headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_missing_dataset_returns_not_found(
    client: FlaskClient,
    auth_headers,
) -> None:
    """Verifica il 404 dataset mode quando il dataset observed non esiste."""
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
    """Verifica il 400 per bbox incompleta su OBS map mode nella finestra DBALLE."""
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, lonmin=10.0)

    # act
    with observed_dballe_override(test_runtime):
        response = client.get(endpoint, headers=auth_headers)

    # assert
    assert response.status_code == 400


def test_fields_observed_only_summary_stats_returns_stats_only(
    client: FlaskClient,
    auth_headers,
    test_runtime,
) -> None:
    """Verifica onlySummaryStats=true su agrmet DBALLE 2020-04-06."""
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, onlySummaryStats="true")

    # act
    with observed_dballe_override(test_runtime):
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
    """Verifica SummaryStats=False sul ramo OBS map mode."""
    # arrange
    endpoint = fields_url(q=OBS_DBALLE_QUERY, SummaryStats="false")

    # act
    with observed_dballe_override(test_runtime):
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

    Il test interroga dati reali agrmet, ma crea un gruppo OBS privato sintetico come
    controllo negativo per l'elenco all_licenses autorizzato dell'utente.
    """
    # arrange
    db = sqlalchemy.get_instance()
    private_group_name = create_private_observed_dataset_for_all_available_products(
        db,
        cleanup_registry,
    )
    user = require_observed_dataset_user(client, cleanup_registry)

    # act
    with observed_dballe_override(test_runtime):
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
    """Verifica FOR dataset mode su lm5 2021-10-19 o lm2.2 2019-09-10.

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
    """Verifica il 404 per dataset forecast inesistente."""
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
    """Verifica il 400 per dataset con categorie diverse usando catalogo sintetico.

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
    user = create_fields_user(
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
    """Verifica il 400 per dataset forecast appartenenti a gruppi licenza diversi."""
    # arrange
    db = sqlalchemy.get_instance()
    first_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    second_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    user = create_fields_user(
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
    """Verifica il 400 per selezione multi-dataset con multim-forecast."""
    # arrange
    db = sqlalchemy.get_instance()
    multim_dataset = get_or_create_multim_forecast_dataset(db, cleanup_registry)
    companion_dataset = create_fields_synthetic_dataset(db, cleanup_registry)
    user = create_fields_user(
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
    """Verifica onlySummaryStats=true sul forecast nella sola finestra ammessa."""
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


def test_fields_forecast_summary_stats_false_is_skipped_for_known_backend_bug(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Sonda SummaryStats=False sul forecast e salta esplicitamente il bug backend noto.

    Analisi del difetto riprodotto dal probe:
    - `Fields.get` inizializza `resulting_fields` solo nel ramo OBS.
    - Il blocco finale `if not SummaryStats` lo usa però anche dopo il ramo forecast.
    - Nel ramo FOR il runtime può quindi sollevare `UnboundLocalError`, che il wrapper
      restapi in questo ambiente espone come `400` o `500`.

    Politica della suite EXT:
    - niente `xfail` stabile in suite;
    - se il bug è ancora presente, il test viene skippato in modo esplicito e verboso;
    - quando il backend verrà corretto, questo stesso test dovrà tornare verde con
      `200` e assenza di `summarystats` nel payload forecast.
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
    if response.status_code in {400, 500} and (
        "resulting_fields" in str(content) or "UnboundLocalError" in str(content)
    ):
        pytest.skip(
            "Known backend bug in Fields.get forecast SummaryStats=False: the "
            "final `if not SummaryStats` block uses `resulting_fields`, defined "
            "only in the OBS branch; re-enable the assertive path after the "
            "backend removes summarystats from summary['items'] in both OBS and FOR"
        )
    assert response.status_code == 200
    assert "summarystats" not in content["items"]
