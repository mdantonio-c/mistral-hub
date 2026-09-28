# EXTENSION TRACEABILITY - Prompt 06, customizer utente.
# Origine: questo modulo copre direttamente projects/mistral/backend/customization.py,
# superficie emersa dal blueprint ma non coperta dalla suite legacy rifattorizzata.
# Ambito: verifica custom_user_properties_pre, custom_user_properties_post,
# manipulate_profile, get_custom_input_fields e get_custom_output_fields.
# Finestra dati: nessun dataset reale viene usato; il solo dataset necessario a
# custom_user_properties_post e una riga catalografica sintetica creata nel test.
# Runtime fake: non servono API HTTP, worker o filesystem; i test chiamano funzioni pure
# o DB-locali del customizer con oggetti dummy controllati.
# Cleanup: il dataset sintetico e le sue relazioni license/group/attribution sono
# eliminati in teardown via cleanup_registry.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/customizer.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from mistral.customization import Customizer
from mistral.models.sqlalchemy import DatasetCategories
from restapi.connectors import sqlalchemy
from restapi.customizer import BaseCustomizer
from restapi.exceptions import NotFound


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


@dataclass
class DummyCustomizerUser_EXT:
    """Oggetto utente minimale per manipolate_profile e post hook.

    Il customizer legge solo attributi custom e assegna `datasets`; usare un dataclass
    evita di creare utenti reali quando il contratto sotto test non e l'API admin users.
    """

    disk_quota: int = 2048
    amqp_queue: str | None = "queue-ext"
    requests_expiration_days: int = 30
    requests_expiration_delete: bool = True
    open_dataset: bool = False
    datasets: list[Any] | None = None
    max_templates: int = 3
    max_output_size: int = 4096
    allowed_postprocessing: bool = True
    allowed_schedule: bool = False
    allowed_obs_archive: bool = False
    request_par_hour: int = 7
    notify_on_successful_request: bool = False


def seed_customizer_dataset_EXT(db, cleanup_registry) -> int:
    """Crea un dataset catalografico sintetico per custom_user_properties_post.

    Il post hook accetta id dataset e risolve righe Datasets reali. Questo helper crea
    una catena minima group/license/attribution/dataset senza usare cataloghi runtime.
    """
    # Prepariamo nomi unici per evitare collisioni con dati iniziali o test paralleli.
    token = uuid4().hex[:12]
    group_license = db.GroupLicense(
        name=f"customizer_group_ext_{token}",
        descr="Synthetic customizer group EXT",
        is_public=True,
    )
    db.session.add(group_license)
    db.session.flush()

    license_entry = db.License(
        name=f"customizer_license_ext_{token}",
        descr="Synthetic customizer license EXT",
        group_license_id=group_license.id,
    )
    db.session.add(license_entry)
    db.session.flush()

    attribution = db.Attribution(
        name=f"customizer_attr_ext_{token}",
        descr="Synthetic customizer attribution EXT",
        url="https://example.com/customizer-ext",
    )
    db.session.add(attribution)
    db.session.flush()

    dataset = db.Datasets(
        arkimet_id=f"customizer_dataset_ext_{token}",
        name=f"customizer_dataset_ext_{token}",
        description="Synthetic dataset for customizer EXT",
        source="arkimet",
        license_id=license_entry.id,
        attribution_id=attribution.id,
        category=DatasetCategories.FOR,
        fileformat="grib",
        bounding="POLYGON ((10 44, 11 44, 11 45, 10 45, 10 44))",
        supports_variable_browsing=False,
    )
    db.session.add(dataset)
    db.session.commit()

    # Registriamo un cleanup unico in ordine relazionale, idempotente rispetto a
    # eventuali assegnazioni user.datasets fatte dal customizer.
    cleanup_registry.add(
        lambda dataset_id=dataset.id, license_id=license_entry.id, group_id=group_license.id, attribution_id=attribution.id: delete_customizer_dataset_EXT(
            db,
            dataset_id=dataset_id,
            license_id=license_id,
            group_id=group_id,
            attribution_id=attribution_id,
        )
    )
    return dataset.id


def delete_customizer_dataset_EXT(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_id: int,
    attribution_id: int,
) -> None:
    """Rimuove il bundle dataset sintetico usato dal customizer.

    Il cleanup svuota anche le associazioni user/dataset, cosi un eventuale test che
    assegna il dataset a un utente dummy o reale non blocca la rimozione del record.
    """
    dataset = db.Datasets.query.get(dataset_id)
    if dataset is not None:
        for user in dataset.users.all():
            dataset.users.remove(user)
        db.session.delete(dataset)
        db.session.flush()

    license_entry = db.License.query.get(license_id)
    if license_entry is not None:
        db.session.delete(license_entry)
        db.session.flush()

    group_license = db.GroupLicense.query.get(group_id)
    if group_license is not None:
        db.session.delete(group_license)
        db.session.flush()

    attribution = db.Attribution.query.get(attribution_id)
    if attribution is not None:
        db.session.delete(attribution)
        db.session.flush()

    db.session.commit()


def test_custom_user_properties_pre_sets_defaults_and_extracts_datasets_EXT() -> None:
    """Verifica default utente e separazione del campo datasets.

    Il pre hook deve togliere `datasets` dai campi utente diretti, conservarlo in
    extra_properties e riempire i default custom senza sovrascrivere valori espliciti.
    """
    # arrange - properties con un valore esplicito e datasets da spostare.
    properties = {"datasets": ["1", "2"], "disk_quota": 99}

    # act - chiamata diretta al pre hook.
    updated_properties, extra_properties = Customizer.custom_user_properties_pre(
        properties
    )

    # assert - datasets viene separato e i default principali sono presenti.
    assert "datasets" not in updated_properties
    assert extra_properties == {"datasets": ["1", "2"]}
    assert updated_properties["disk_quota"] == 99
    assert updated_properties["open_dataset"] is True
    assert updated_properties["requests_expiration_days"] == 180
    assert updated_properties["requests_expiration_delete"] is False
    assert updated_properties["max_templates"] == 1
    assert updated_properties["allowed_schedule"] is True
    assert updated_properties["notify_on_successful_request"] is True


def test_custom_user_properties_post_associates_valid_datasets_EXT(
    cleanup_registry,
) -> None:
    """Verifica che il post hook risolva id dataset validi e li assegni all'utente.

    Il dataset e sintetico e DB-only: serve a esercitare la query del customizer senza
    usare finestre meteo reali o passare dall'API admin users.
    """
    # arrange - dataset valido e utente dummy con lista datasets vuota.
    db = sqlalchemy.get_instance()
    dataset_id = seed_customizer_dataset_EXT(db, cleanup_registry)
    user = DummyCustomizerUser_EXT(datasets=[])

    # act - associazione via post hook.
    Customizer.custom_user_properties_post(
        user,
        {},
        {"datasets": [str(dataset_id)]},
        db,
    )

    # assert - l'utente riceve il record Datasets reale risolto dal DB.
    assert user.datasets is not None
    assert [dataset.id for dataset in user.datasets] == [dataset_id]


def test_custom_user_properties_post_missing_dataset_raises_notfound_EXT() -> None:
    """Verifica NotFound quando extra_properties cita un dataset inesistente.

    Il test usa un id alto non presente nel DB e non crea dati, cosi l'eccezione misura
    solo il ramo di validazione del customizer.
    """
    # arrange - utente dummy e id dataset sicuramente assente.
    db = sqlalchemy.get_instance()
    missing_dataset_id = 987654321
    assert db.Datasets.query.get(missing_dataset_id) is None
    user = DummyCustomizerUser_EXT(datasets=[])

    # act/assert - il post hook deve segnalare esplicitamente il dataset mancante.
    with pytest.raises(NotFound):
        Customizer.custom_user_properties_post(
            user,
            {},
            {"datasets": [str(missing_dataset_id)]},
            db,
        )


def test_manipulate_profile_includes_all_custom_fields_EXT() -> None:
    """Verifica che il profilo serializzato includa tutti i campi custom.

    L'utente dummy espone valori non-default per rendere visibile ogni assegnazione
    effettuata da manipulate_profile.
    """
    # arrange - utente dummy con campi custom valorizzati.
    user = DummyCustomizerUser_EXT(datasets=[{"id": "dataset-ext"}])

    # act - manipolazione diretta del payload profilo.
    profile = Customizer.manipulate_profile(None, user, {"email": "user@example.com"})

    # assert - i campi custom richiesti dal frontend/profilo sono tutti esposti.
    assert profile["email"] == "user@example.com"
    assert profile["disk_quota"] == user.disk_quota
    assert profile["amqp_queue"] == user.amqp_queue
    assert profile["requests_expiration_days"] == user.requests_expiration_days
    assert profile["requests_expiration_delete"] == user.requests_expiration_delete
    assert profile["open_dataset"] == user.open_dataset
    assert profile["datasets"] == user.datasets
    assert profile["max_templates"] == user.max_templates
    assert profile["max_output_size"] == user.max_output_size
    assert profile["allowed_postprocessing"] == user.allowed_postprocessing
    assert profile["allowed_schedule"] == user.allowed_schedule
    assert profile["allowed_obs_archive"] == user.allowed_obs_archive
    assert profile["request_par_hour"] == user.request_par_hour
    assert profile["notify_on_successful_request"] == user.notify_on_successful_request


def test_custom_input_and_output_fields_by_scope_EXT() -> None:
    """Verifica gli schema custom per ADMIN, PROFILE, REGISTRATION e output.

    Passare request=None evita query a startup e rispetta il ramo previsto dal codice;
    qui interessa la presenza dei campi per scope, non la lista runtime dei dataset.
    """
    # act - richieste dirette degli schema custom per ogni scope supportato.
    admin_fields = Customizer.get_custom_input_fields(None, BaseCustomizer.ADMIN)
    profile_fields = Customizer.get_custom_input_fields(None, BaseCustomizer.PROFILE)
    registration_fields = Customizer.get_custom_input_fields(
        None,
        BaseCustomizer.REGISTRATION,
    )
    output_fields = Customizer.get_custom_output_fields(None)

    # assert - ADMIN espone il set operativo completo.
    assert {
        "disk_quota",
        "requests_expiration_days",
        "open_dataset",
        "datasets",
        "max_templates",
        "max_output_size",
        "allowed_postprocessing",
        "allowed_schedule",
        "allowed_obs_archive",
        "request_par_hour",
        "notify_on_successful_request",
        "amqp_queue",
    }.issubset(admin_fields)

    # assert - PROFILE espone solo i campi modificabili dall'utente.
    assert set(profile_fields) == {
        "requests_expiration_days",
        "requests_expiration_delete",
        "notify_on_successful_request",
    }
    assert registration_fields == {}

    # assert - output espone tutti i campi custom serializzabili.
    assert {
        "disk_quota",
        "requests_expiration_days",
        "requests_expiration_delete",
        "open_dataset",
        "datasets",
        "max_templates",
        "max_output_size",
        "allowed_postprocessing",
        "allowed_schedule",
        "allowed_obs_archive",
        "request_par_hour",
        "amqp_queue",
        "notify_on_successful_request",
    }.issubset(output_fields)