"""Fixtures that assemble reusable environments for postprocessing scenarios.

Postprocessing tests need more than authenticated headers: they need a prepared
request helper, a dataset-specific user, database access, cleanup wiring, and in
the observed case a temporary ``LASTDAYS`` override. These fixtures build those
complete environments once per test.
"""

import pytest
from faker import Faker
from flask import Flask
from mistral.services.dballe import BeDballe
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from .support import (
    PostprocessingEnv,
    PostprocessingSupport,
    create_postprocessing_user,
    register_user_cleanup,
    require_dataset,
    require_observed_lastdays,
)


@pytest.fixture
def pp_forecast_env(
    app: Flask,
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
) -> PostprocessingEnv:
    """Create a complete forecast postprocessing environment bound to ``lm5``.

    The returned environment bundles together the app, client, faker, DB handle,
    cleanup registry, dedicated user, and dataset name that forecast scenarios
    need to create requests and assert on their outcomes.
    """
    # arrange
    # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
    db = sqlalchemy.get_instance()
    dataset = require_dataset(db, "lm5")
    base = PostprocessingSupport()
    user = create_postprocessing_user(base, client, [dataset.id])
    register_user_cleanup(base, client, cleanup_registry, user)

    # act
    # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
    # verifica dal setup.
    env = PostprocessingEnv(
        base=base,
        app=app,
        client=client,
        faker=faker,
        db=db,
        cleanup_registry=cleanup_registry,
        dataset_name="lm5",
        user=user,
    )

    # assert
    # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
    # questo test vuole proteggere.
    return env


@pytest.fixture
def pp_observed_env(
    app: Flask,
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
    test_runtime,
) -> PostprocessingEnv:
    """Create a complete observed postprocessing environment bound to ``agrmet``.

    In addition to the resources used by forecast scenarios, observed tests also
    need a temporary ``BeDballe.LASTDAYS`` override derived from real data so the
    selected observed slice stays visible during the test.
    """
    # arrange
    # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
    db = sqlalchemy.get_instance()
    dataset = require_dataset(db, "agrmet")
    observed_lastdays = require_observed_lastdays()
    base = PostprocessingSupport()
    user = create_postprocessing_user(base, client, [dataset.id])
    register_user_cleanup(base, client, cleanup_registry, user)

    # Sostituiamo temporaneamente la dipendenza esterna con un fake controllato, cosi il
    # test resta deterministico.
    with test_runtime.override_attr(BeDballe, "LASTDAYS", observed_lastdays):
        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        env = PostprocessingEnv(
            base=base,
            app=app,
            client=client,
            faker=faker,
            db=db,
            cleanup_registry=cleanup_registry,
            dataset_name="agrmet",
            user=user,
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        yield env
