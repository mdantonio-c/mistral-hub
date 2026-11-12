"""Fixture che preparano ambienti riusabili per gli scenari di postprocessing.

Ai test di postprocessing non bastano header autenticati: servono un helper per
creare le request, un utente abilitato al dataset, l'accesso al database, il
cleanup e, nel caso observed, un override temporaneo di ``LASTDAYS``. Queste
fixture costruiscono l'ambiente completo una volta per ogni test.
"""

import pytest
from faker import Faker
from flask import Flask
from mistral.services.dballe import BeDballe
from mistral.tests.helpers.datasets import require_dataset
from restapi.connectors import sqlalchemy
from restapi.tests import FlaskClient

from .support import (
    PostprocessingEnv,
    PostprocessingSupport,
    create_postprocessing_user,
    register_user_cleanup,
    require_observed_lastdays,
)


@pytest.fixture
def pp_forecast_env(
    app: Flask,
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
) -> PostprocessingEnv:
    """Crea un ambiente completo di postprocessing forecast sul dataset ``lm5``.

    L'ambiente restituito raccoglie app, client, faker, handle del DB, cleanup
    registry, utente dedicato e nome del dataset: e quanto serve agli scenari
    forecast per creare request, eseguire il task Celery ``data_extract`` e
    verificarne l'esito. Fa skip se il dataset ``lm5`` non esiste.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = require_dataset(db, "lm5")
    base = PostprocessingSupport()
    user = create_postprocessing_user(base, client, [dataset.id])
    register_user_cleanup(base, client, cleanup_registry, user)

    # act
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
    return env


@pytest.fixture
def pp_observed_env(
    app: Flask,
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
    test_runtime,
) -> PostprocessingEnv:
    """Crea un ambiente completo di postprocessing observed sul dataset ``agrmet``.

    Oltre alle risorse usate dagli scenari forecast, i test observed hanno
    bisogno di un override temporaneo di ``BeDballe.LASTDAYS`` derivato dai dati
    reali, cosi la porzione di dati observed selezionata resta visibile durante il
    test. Fa skip se mancano il dataset, la configurazione DBALLE o i dati.
    """
    # arrange
    db = sqlalchemy.get_instance()
    dataset = require_dataset(db, "agrmet")
    observed_lastdays = require_observed_lastdays()
    base = PostprocessingSupport()
    user = create_postprocessing_user(base, client, [dataset.id])
    register_user_cleanup(base, client, cleanup_registry, user)

    # LASTDAYS decide il confine tra dati recenti (DBALLE) e storici (Arkimet):
    # l'override fa ricadere i dati observed reali nella finestra DBALLE. Lo yield
    # sta dentro il with, cosi l'override resta attivo per tutta la durata del test.
    with test_runtime.override_attr(BeDballe, "LASTDAYS", observed_lastdays):
        # act
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
        yield env
