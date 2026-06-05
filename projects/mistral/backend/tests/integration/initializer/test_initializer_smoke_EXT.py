# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal Prompt 08 per dare
# uno smoke test mirato a `mistral.initialization.Initializer`, superficie finora
# coperta solo indirettamente dallo startup del progetto.
# EXTENSION SCOPE: il test importa il modulo, attraversa il costruttore con fake
# SQLAlchemy, Arkimet e Celery, e aggiunge uno smoke import-only delle revisioni
# Alembic. Non prova ogni riga di seed ne esegue upgrade/downgrade, ma protegge
# invarianti sostenibili: nessuna creazione duplicata quando le righe risultano gia
# presenti, ricreazione del cron `requests_cleanup` con task `automatic_cleanup` e
# importabilita dei migration script versionati.
# EXTENSION DATA WINDOW: nessun dataset reale viene letto da Arkimet. Il fake
# `load_datasets` restituisce un solo dataset sintetico gia presente nel DB fake.
# EXTENSION RUNTIME: `sqlalchemy.get_instance`, `celery.get_instance` e
# `arki.load_datasets` sono monkeypatchati. Non vengono avviati Celery, DB reale,
# migrazioni operative o servizi esterni; le revisioni Alembic sono solo importate
# come moduli Python, senza chiamare `upgrade` o `downgrade`.
# EXTENSION CLEANUP: tutti i fake sono in memoria e durano solo per il test. Non ci
# sono righe DB, cron reali o file da cancellare.
# EXTENSION BASELINE: non vengono modificati initializer, migration script o suite
# legacy. Il file e intenzionalmente uno smoke deterministico, non una replica
# fragile dell'intero seeding applicativo.

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class _AlwaysMatchingValue_EXT:
    """Valore sentinella che rappresenta un campo DB gia allineato al seed."""

    def __eq__(self, other: Any) -> bool:
        """Risulta uguale a ogni valore atteso dall'initializer."""
        # Il fake serve a modellare righe esistenti e gia aggiornate senza duplicare nel
        # test tutte le stringhe descrittive del seed applicativo.
        del other
        return True

    def __ne__(self, other: Any) -> bool:
        """Evita che i confronti `!=` attivino rami di update duplicati."""
        del other
        return False

    def __bool__(self) -> bool:
        """Rende vero il valore quando il codice controlla campi opzionali."""
        return True


class _ExistingSeedRow_EXT:
    """Riga DB fake che appare gia presente e coerente con qualunque seed."""

    def __init__(self, *, name: str | None = None, arkimet_id: str | None = None) -> None:
        """Espone i campi letti dall'initializer senza creare modelli reali."""
        self.id = 101
        self.name = name or "synthetic-dataset"
        self.arkimet_id = arkimet_id or "synthetic-dataset"
        self.descr = _AlwaysMatchingValue_EXT()
        self.url = _AlwaysMatchingValue_EXT()
        self.is_public = _AlwaysMatchingValue_EXT()
        self.dballe_dsn = _AlwaysMatchingValue_EXT()
        self.group_license_id = _AlwaysMatchingValue_EXT()
        self.description = _AlwaysMatchingValue_EXT()
        self.license_id = _AlwaysMatchingValue_EXT()
        self.attribution_id = _AlwaysMatchingValue_EXT()
        self.category = _AlwaysMatchingValue_EXT()
        self.fileformat = _AlwaysMatchingValue_EXT()
        self.bounding = _AlwaysMatchingValue_EXT()


class _FilteredQuery_EXT:
    """Risultato di `query.filter_by(...)` per il fake SQLAlchemy."""

    def __init__(self, model_name: str, filters: dict[str, Any]) -> None:
        """Conserva modello e filtri solo per costruire righe coerenti."""
        self.model_name = model_name
        self.filters = filters

    def first(self) -> _ExistingSeedRow_EXT:
        """Restituisce sempre una riga esistente per evitare seed duplicati."""
        # Questo e il cuore dello smoke: ogni lookup del seed trova una riga gia
        # presente, quindi il costruttore non dovrebbe istanziare nuovi model.
        del self.model_name
        return _ExistingSeedRow_EXT(
            name=self.filters.get("name"),
            arkimet_id=self.filters.get("arkimet_id"),
        )

    def all(self) -> list[_ExistingSeedRow_EXT]:
        """Restituisce righe gia coerenti per i controlli post-seed."""
        # Le scansioni `filter_by().all()` servono solo a produrre warning diagnostici
        # su righe extra nel DB. Lo smoke copre i lookup puntuali con `first`, quindi qui
        # restituiamo vuoto per non generare rumore non pertinente nel log del test.
        return []


class _Query_EXT:
    """Query object minimale che supporta `filter_by` come SQLAlchemy."""

    def __init__(self, model_name: str) -> None:
        """Memorizza il nome del model solo per messaggi e righe fake."""
        self.model_name = model_name

    def filter_by(self, **kwargs: Any) -> _FilteredQuery_EXT:
        """Restituisce una query filtrata senza leggere alcun database."""
        return _FilteredQuery_EXT(self.model_name, kwargs)


class _NoDuplicateModel_EXT:
    """Model fake che fallisce se l'initializer prova a creare una nuova riga."""

    query: _Query_EXT

    def __init__(self, **kwargs: Any) -> None:
        """Blocca creazioni: in questo smoke tutte le righe devono gia esistere."""
        raise AssertionError(f"Initializer attempted duplicate seed creation: {kwargs}")


def _model_class_EXT(model_name: str) -> type[_NoDuplicateModel_EXT]:
    """Crea una classe model fake con query dedicata al nome richiesto."""
    # Usiamo classi distinte per imitare gli attributi `sql.GroupLicense`,
    # `sql.License`, `sql.Attribution` e `sql.Datasets` letti dall'initializer.
    return type(
        f"_Fake{model_name}Model_EXT",
        (_NoDuplicateModel_EXT,),
        {"query": _Query_EXT(model_name)},
    )


class _FakeSession_EXT:
    """Sessione SQLAlchemy fake che registra add/commit senza persistere nulla."""

    def __init__(self) -> None:
        """Prepara recorder vuoti per verificare side effect indesiderati."""
        self.added: list[Any] = []
        self.commit_count = 0

    def add(self, obj: Any) -> None:
        """Registra ogni update/add che lo smoke non si aspetta di vedere."""
        self.added.append(obj)

    def commit(self) -> None:
        """Conta i commit dell'initializer senza toccare un DB reale."""
        self.commit_count += 1


class _FakeSqlAlchemy_EXT:
    """Facciata SQLAlchemy fake con model e sessione usati dall'initializer."""

    def __init__(self) -> None:
        """Costruisce tutti i model necessari al costruttore `Initializer`."""
        self.session = _FakeSession_EXT()
        self.GroupLicense = _model_class_EXT("GroupLicense")
        self.License = _model_class_EXT("License")
        self.Attribution = _model_class_EXT("Attribution")
        self.Datasets = _model_class_EXT("Datasets")


class _FakeCelery_EXT:
    """Celery fake che modella un cron cleanup gia esistente e ricreato."""

    def __init__(self) -> None:
        """Prepara recorder per get/delete/create del periodic task."""
        self.requested_tasks: list[str] = []
        self.deleted_tasks: list[str] = []
        self.created_crontab_tasks: list[dict[str, Any]] = []

    def get_periodic_task(self, *, name: str) -> dict[str, str]:
        """Simula la presenza del task periodico da ricreare."""
        self.requested_tasks.append(name)
        return {"name": name}

    def delete_periodic_task(self, *, name: str) -> bool:
        """Registra la cancellazione del cron esistente."""
        self.deleted_tasks.append(name)
        return True

    def create_crontab_task(self, **kwargs: Any) -> None:
        """Registra il nuovo cron senza comunicare con Celery/RedBeat."""
        self.created_crontab_tasks.append(kwargs)


def _fake_arkimet_datasets_EXT() -> list[dict[str, str]]:
    """Restituisce un dataset sintetico gia rappresentato dal DB fake."""
    # Questo evita di leggere configurazioni Arkimet reali e mantiene il test fuori
    # dalle finestre dati meteorologiche documentate per i test runtime-sensitive.
    return [
        {
            "id": "synthetic-dataset",
            "name": "synthetic-dataset",
            "description": "Synthetic dataset already present in fake DB",
            "license": "CCBY4.0",
            "attribution": "ARPAE-SIMC",
            "category": "forecast",
        }
    ]


def _load_migration_module_EXT(module_path: Path) -> Any:
    """Importa una singola revisione Alembic senza eseguirne le operazioni.

    Le migrazioni non sono un package Python con `__init__.py`, quindi il test usa
    `spec_from_file_location`. Questo e volutamente uno smoke strutturale: importa il
    file, legge i metadati Alembic e non chiama mai `upgrade` o `downgrade`, per evitare
    side effect su database o schema.
    """
    # Il nome modulo e sintetico e stabile: serve solo a isolare l'import durante il
    # collect/test e non viene riusato dal runtime applicativo.
    module_name = f"_mistral_migration_EXT_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestInitializerSmoke_EXT:
    """Smoke deterministico per import e wiring principale dell'initializer."""

    def test_initializer_module_imports_without_running_seed_EXT(self) -> None:
        """Il modulo initializer deve essere importabile senza avviare il seeding."""
        # arrange / act
        # L'import e volutamente separato dal test del costruttore: importare il modulo
        # non deve connettere DB, Celery o Arkimet, mentre istanziare `Initializer` si.
        initialization = importlib.import_module("mistral.initialization")

        # assert
        assert hasattr(initialization, "Initializer")

    def test_migration_versions_import_without_running_upgrade_EXT(self) -> None:
        """Le revisioni Alembic devono essere importabili senza toccare il DB.

        Questo test copre il perimetro migration richiesto dal Prompt 08 in modo
        non invasivo: verifica che ogni file versione esponga metadati Alembic minimi,
        che gli id di revisione siano univoci e che esista almeno una head. Non prova la
        correttezza dello schema, che resta demandata al runtime Alembic/CI.
        """
        # arrange
        # Deriviamo il path dal modulo initializer importato nel container, cosi il test
        # funziona sia da host sia nel mount `tests/custom` senza hardcodare `/code`.
        initialization = importlib.import_module("mistral.initialization")
        backend_root = Path(initialization.__file__).resolve().parent
        versions_dir = backend_root / "migrations" / "versions"
        migration_paths = sorted(versions_dir.glob("*.py"))

        # act
        # Importiamo ogni revision come modulo isolato. Le funzioni upgrade/downgrade
        # vengono solo controllate come callable e non invocate, evitando migrazioni reali.
        migration_modules = [
            _load_migration_module_EXT(path) for path in migration_paths
        ]

        # assert
        assert migration_modules
        revisions = [module.revision for module in migration_modules]
        down_revisions = [module.down_revision for module in migration_modules]
        assert len(revisions) == len(set(revisions))
        assert all(isinstance(revision, str) and revision for revision in revisions)
        assert all(hasattr(module, "upgrade") for module in migration_modules)
        assert all(callable(module.upgrade) for module in migration_modules)
        assert all(hasattr(module, "downgrade") for module in migration_modules)
        assert all(callable(module.downgrade) for module in migration_modules)
        assert any(down_revision is None for down_revision in down_revisions)
        assert any(
            revision not in {item for item in down_revisions if item is not None}
            for revision in revisions
        )

    def test_initializer_recreates_cleanup_cron_without_duplicate_seed_EXT(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Con righe gia presenti, lo smoke non crea duplicati e reinstalla cleanup."""
        # arrange
        # Fakes locali: SQLAlchemy vede tutto gia presente, Arkimet restituisce un solo
        # dataset sintetico e Celery espone un cron preesistente da eliminare/ricreare.
        initialization = importlib.import_module("mistral.initialization")
        fake_sql = _FakeSqlAlchemy_EXT()
        fake_celery = _FakeCelery_EXT()
        monkeypatch.setattr(
            initialization.sqlalchemy,
            "get_instance",
            lambda: fake_sql,
        )
        monkeypatch.setattr(
            initialization.celery,
            "get_instance",
            lambda: fake_celery,
        )
        monkeypatch.setattr(
            initialization.arki,
            "load_datasets",
            _fake_arkimet_datasets_EXT,
        )

        # act
        initializer = initialization.Initializer()

        # assert
        assert initializer is not None
        assert fake_sql.session.added == []
        assert fake_sql.session.commit_count >= 3
        assert fake_celery.requested_tasks == ["requests_cleanup"]
        assert fake_celery.deleted_tasks == ["requests_cleanup"]
        assert fake_celery.created_crontab_tasks == [
            {
                "name": "requests_cleanup",
                "task": "automatic_cleanup",
                "hour": "3",
                "minute": "45",
                "args": [],
            }
        ]