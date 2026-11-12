"""Helper per record di dataset isolati usati dai test di integrazione."""

from __future__ import annotations

from uuid import uuid4

import pytest
from mistral.models.sqlalchemy import DatasetCategories
from mistral.services.arkimet import BeArkimet


def require_dataset(db, dataset_name: str):
    """Restituisce un dataset reale del catalogo (tabella ``Datasets``).

    Cerca per ``name`` o ``arkimet_id``; se il dataset manca, salta il test.
    """
    dataset = db.Datasets.query.filter(
        (db.Datasets.name == dataset_name) | (db.Datasets.arkimet_id == dataset_name)
    ).first()
    if dataset is None:
        pytest.skip(f"Dataset '{dataset_name}' is not available in this environment")
    return dataset


def delete_test_dataset_bundle(
    db,
    *,
    dataset_id: int,
    license_id: int,
    group_license_id: int,
    attribution_id: int | None,
) -> None:
    """Rimuove un dataset sintetico e tutti i suoi record di supporto.

    Il cleanup e difensivo: le righe gia sparite vengono saltate, cosi un setup
    costruito a meta non nasconde il fallimento originale. Passare
    ``attribution_id=None`` quando il dataset riusa un'attribution reale che va
    conservata.
    """
    db.session.rollback()
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

    group_license = db.GroupLicense.query.get(group_license_id)
    if group_license is not None:
        db.session.delete(group_license)
        db.session.flush()

    if attribution_id is not None:
        attribution = db.Attribution.query.get(attribution_id)
        if attribution is not None:
            db.session.delete(attribution)
            db.session.flush()

    db.session.commit()
    assert db.Datasets.query.get(dataset_id) is None
    assert db.License.query.get(license_id) is None
    assert db.GroupLicense.query.get(group_license_id) is None
    if attribution_id is not None:
        assert db.Attribution.query.get(attribution_id) is None


def create_test_dataset(
    db,
    cleanup_registry,
    *,
    is_public: bool,
    prefix: str = "dataset_test",
):
    """Crea un bundle di dataset isolato e ne registra il teardown completo.

    Il bundle comprende ``GroupLicense`` (pubblica o privata secondo ``is_public``),
    ``Attribution``, ``License`` e un ``Datasets`` OBS/BUFR con nome univoco.
    """
    dataset_name = f"{prefix}_{uuid4().hex[:12]}"
    group_license = db.GroupLicense(
        name=f"{dataset_name}_group",
        descr=f"Synthetic license group for {dataset_name}",
        is_public=is_public,
    )
    attribution = db.Attribution(
        name=f"{dataset_name}_attribution",
        descr=f"Synthetic attribution for {dataset_name}",
        url="https://example.invalid/dataset-test-attribution",
    )
    db.session.add(group_license)
    db.session.add(attribution)
    db.session.flush()

    license_entry = db.License(
        name=f"{dataset_name}_license",
        descr=f"Synthetic license for {dataset_name}",
        group_license_id=group_license.id,
    )
    db.session.add(license_entry)
    db.session.flush()

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Synthetic dataset for {dataset_name}",
        source="arkimet",
        license_id=license_entry.id,
        attribution_id=attribution.id,
        category=DatasetCategories.OBS,
        fileformat="bufr",
    )
    db.session.add(dataset)
    db.session.commit()
    dataset_id = dataset.id
    license_id = license_entry.id
    group_license_id = group_license.id
    attribution_id = attribution.id
    cleanup_registry.add(
        lambda: delete_test_dataset_bundle(
            db,
            dataset_id=dataset_id,
            license_id=license_id,
            group_license_id=group_license_id,
            attribution_id=attribution_id,
        )
    )
    return dataset


def create_private_test_network(
    db,
    cleanup_registry,
    monkeypatch,
    *,
    prefix: str = "private_network_test",
) -> str:
    """Crea un dataset privato sintetico raggiungibile tramite una rete sintetica.

    Solo la rete sintetica viene instradata verso il dataset privato; ogni altra rete
    mantiene la mappatura Arkimet reale (``BeArkimet.from_network_to_dataset``) e
    l'autorizzazione sui dataset resta reale, cosi gli utenti senza grant esplicito
    ricevono un 401 portabile senza toccare il catalogo reale.
    """
    dataset = create_test_dataset(
        db,
        cleanup_registry,
        is_public=False,
        prefix=prefix,
    )
    dataset_name = dataset.arkimet_id
    network = f"{dataset_name}_net"
    real_from_network_to_dataset = BeArkimet.from_network_to_dataset

    def from_network_to_dataset(requested_network: str):
        if requested_network == network:
            return dataset_name
        return real_from_network_to_dataset(requested_network)

    monkeypatch.setattr(
        BeArkimet,
        "from_network_to_dataset",
        staticmethod(from_network_to_dataset),
    )
    return network