# Test di stato reale di `mistral.initialization.Initializer` (initialization.py): seed
# di gruppi di licenze, licenze, attribution e dataset e installazione del cron di
# cleanup delle richieste. Affianca `test_initializer_smoke.py` senza sostituirlo.
# Ambito: tre scenari eseguiti su PostgreSQL e modelli SQLAlchemy
# reali: prima creazione del seed, doppia esecuzione idempotente e ripristino di un
# singolo campo modificato. Le asserzioni rileggono le righe dal DB dopo `expire_all`.
# Finestra dati: nessun dato meteorologico. `arki.load_datasets` restituisce un
# solo dataset sintetico con `arkimet_id`/`name` univoci (uuid).
# Runtime: DB reale nella stessa transazione del test. `session.commit` e
# sostituito da `session.flush`, quindi INSERT/UPDATE e vincoli vengono eseguiti davvero
# ma nulla viene reso permanente. Celery e un recorder in memoria con stato, per non
# toccare RedBeat; Arkimet e monkeypatchato.
# Cleanup: `session.rollback()` a fine test annulla tutto; il fixture verifica
# poi che le tabelle seed abbiano esattamente le righe presenti prima del test.
# Bug noto: il test xfail strict documenta che ogni rerun riscrive
# `datasets.category` (enum confrontato con stringa Arkimet). Il bug maschera anche i
# confronti degli altri campi dataset nel ramo di update.

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from restapi.connectors import sqlalchemy
from sqlalchemy import event

from mistral.models.sqlalchemy import DatasetCategories


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


# Aspettative scritte esplicitamente: il test non importa le liste dal codice di
# produzione, cosi una modifica accidentale del seed viene rilevata.
EXPECTED_GROUPS: dict[str, dict[str, Any]] = {
    "CCBY_COMPLIANT": {
        "descr": "Group of licenses CC BY compliant",
        "is_public": True,
        "dballe_dsn": "DBALLE",
    },
    "CCBY-SA_COMPLIANT": {
        "descr": "Group of licenses CC BY-SA compliant",
        "is_public": True,
        "dballe_dsn": None,
    },
}

EXPECTED_LICENSES: dict[str, dict[str, Any]] = {
    "CCBY4.0": {
        "group": "CCBY_COMPLIANT",
        "descr": "CC BY 4.0",
        "url": "https://creativecommons.org/licenses/by/4.0/legalcode",
    },
    "CCBY-SA4.0": {
        "group": "CCBY-SA_COMPLIANT",
        "descr": "CC BY-SA 4.0",
        "url": "https://creativecommons.org/licenses/by-sa/4.0/",
    },
    "CCBY-NC-SA 3.0": {
        "group": "CCBY-SA_COMPLIANT",
        "descr": "CC BY-NC-SA 3.0",
        "url": "https://creativecommons.org/licenses/by-nc-sa/3.0/",
    },
}

# I nomi sono il contratto usato dalle configurazioni Arkimet (`_attribution`): li
# verifichiamo tutti. Per descr/url controlliamo un campione rappresentativo, incluso
# un caso con url vuota.
EXPECTED_ATTRIBUTION_NAMES = frozenset(
    {
        "ARPAE-SIMC",
        "AM ARPAE ARPAP",
        "DPCN",
        "ECMWF-MISTRAL",
        "ARPAP-MISTRAL",
        "ARPAP-DRNA",
        "ARPAL-APPP-CFR",
        "ARPACAMP-CFR",
        "ARPACAL-CFR",
        "R-UMBRIA-SIR",
        "R-LIGURIA-ARPAL",
        "MISTRAL",
        "R-MARCHE-PC",
        "P-BOLZANO-PC",
        "ARPAS-METEO",
        "R-VENETO-ARPAV",
        "R-SICILIA-ARPA",
        "P-TRENTO-SPR",
        "MeteoNetwork",
    }
)

EXPECTED_ATTRIBUTION_SAMPLES: dict[str, dict[str, str]] = {
    "ARPAE-SIMC": {
        "descr": "Arpae Emilia-Romagna Idro-Meteo-Clima Service",
        "url": "https://www.arpae.it/sim/",
    },
    "AM ARPAE ARPAP": {
        "descr": (
            "LAMI agreement between Italian Air Force Meteorological Service, "
            "Arpae Emilia-Romagna Idro-Meteo-Clima Service and Arpa Piemonte"
        ),
        "url": "",
    },
    "MeteoNetwork": {
        "descr": "MeteoNetwork Association OdV",
        "url": "https://www.meteonetwork.it/",
    },
}

EXPECTED_CLEANUP_CRON = {
    "name": "requests_cleanup",
    "task": "automatic_cleanup",
    "hour": "3",
    "minute": "45",
    "args": [],
}

SEED_MODELS = ("GroupLicense", "License", "Attribution", "Datasets")

KNOWN_CATEGORY_REWRITE = (
    "UPDATE datasets SET category=%(category)s WHERE datasets.id = %(datasets_id)s"
)


@contextmanager
def _capture_writes(db: Any) -> Iterator[list[str]]:
    """Registra gli statement INSERT/UPDATE/DELETE inviati al DB nel blocco."""
    engine = db.session.get_bind()
    writes: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany) -> None:
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield writes
    finally:
        event.remove(engine, "before_cursor_execute", record)


class _RecordingCelery:
    """Celery fake con stato: ricorda i periodic task installati e le chiamate."""

    def __init__(self) -> None:
        """Parte senza task installati, come una prima installazione."""
        self.installed: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str]] = []

    def get_periodic_task(self, *, name: str) -> dict[str, Any] | None:
        """Restituisce il task solo se e stato creato in precedenza."""
        self.calls.append(("get", name))
        return self.installed.get(name)

    def delete_periodic_task(self, *, name: str) -> bool:
        """Rimuove il task e segnala se esisteva davvero."""
        self.calls.append(("delete", name))
        return self.installed.pop(name, None) is not None

    def create_crontab_task(self, **kwargs: Any) -> None:
        """Installa il task; un secondo create senza delete sarebbe un duplicato."""
        name = kwargs["name"]
        self.calls.append(("create", name))
        assert name not in self.installed, f"Duplicate periodic task {name}"
        self.installed[name] = kwargs


@dataclass
class _InitializerHarness:
    """Raccoglie DB, configurazione sintetica e recorder usati da un test."""

    db: Any
    dataset_config: dict[str, str]
    celery: _RecordingCelery
    commits: list[int] = field(default_factory=list)

    def run(self) -> None:
        """Esegue l'initializer reale e forza la rilettura successiva dal DB."""
        initialization = importlib.import_module("mistral.initialization")
        initialization.Initializer()
        self.db.session.expire_all()

    def dataset_row(self) -> Any:
        """Rilegge la riga del dataset sintetico tramite chiave Arkimet."""
        rows = self.db.Datasets.query.filter_by(
            arkimet_id=self.dataset_config["id"]
        ).all()
        assert len(rows) == 1
        return rows[0]


def _table_state(db: Any) -> dict[str, list[tuple[int, str]]]:
    """Fotografa id e name delle tabelle toccate dall'initializer."""
    db.session.expire_all()
    return {
        model: sorted((row.id, row.name) for row in getattr(db, model).query.all())
        for model in SEED_MODELS
    }


def _row_values(row: Any) -> dict[str, Any]:
    """Restituisce tutti i valori di colonna di una riga ORM."""
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


def _single_row(db: Any, model: str, **filters: Any) -> Any:
    """Rilegge una riga e verifica che non esistano duplicati per quella chiave."""
    rows = getattr(db, model).query.filter_by(**filters).all()
    assert len(rows) == 1, f"{model} {filters}: expected 1 row, found {len(rows)}"
    return rows[0]


def _hide_existing_seed_rows(db: Any) -> set[tuple[str, int]]:
    """Rinomina le righe seed esistenti per simulare un DB non ancora inizializzato.

    Cancellarle non e possibile per via delle FK dei dataset reali; rinominarle nella
    transazione del test ha lo stesso effetto sui lookup per nome dell'initializer.
    """
    hidden: set[tuple[str, int]] = set()
    for model in ("GroupLicense", "License", "Attribution"):
        for row in getattr(db, model).query.all():
            row.name = f"__initializer_ext_hidden_{model}_{row.id}"
            hidden.add((model, row.id))
    db.session.flush()
    db.session.expire_all()
    return hidden


def _seed_snapshot(harness: _InitializerHarness) -> dict[str, Any]:
    """Valori persistiti di tutte le righe seed e del dataset sintetico."""
    db = harness.db
    return {
        "groups": {
            name: _row_values(_single_row(db, "GroupLicense", name=name))
            for name in EXPECTED_GROUPS
        },
        "licenses": {
            name: _row_values(_single_row(db, "License", name=name))
            for name in EXPECTED_LICENSES
        },
        "attributions": {
            name: _row_values(_single_row(db, "Attribution", name=name))
            for name in EXPECTED_ATTRIBUTION_NAMES
        },
        "dataset": _row_values(harness.dataset_row()),
        "table_state": _table_state(db),
    }


@pytest.fixture
def initializer_harness(
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[_InitializerHarness]:
    """Prepara DB reale transazionale, Arkimet sintetico e Celery recorder."""
    del app  # garantisce l'app context Flask richiesto dal connettore SQLAlchemy
    db = sqlalchemy.get_instance()
    session = db.session
    session.rollback()
    state_before = _table_state(db)

    suffix = uuid4().hex[:12]
    dataset_config = {
        "id": f"initializer_ext_{suffix}",
        "name": f"initializer-ext-{suffix}",
        "description": f"Synthetic initializer dataset {suffix}",
        "license": "CCBY4.0",
        "attribution": "ARPAE-SIMC",
        "category": "OBS",
        "format": "bufr",
        "bounding": "POLYGON ((10 44, 12 44, 12 45, 10 44))",
    }
    harness = _InitializerHarness(
        db=db,
        dataset_config=dataset_config,
        celery=_RecordingCelery(),
    )

    def _commit_as_flush() -> None:
        # Le istruzioni SQL vengono inviate al DB, ma la transazione resta aperta e
        # verra annullata dal rollback di teardown.
        harness.commits.append(1)
        session.flush()

    monkeypatch.setattr(session, "commit", _commit_as_flush)
    initialization = importlib.import_module("mistral.initialization")
    monkeypatch.setattr(initialization.celery, "get_instance", lambda: harness.celery)
    monkeypatch.setattr(
        initialization.arki, "load_datasets", lambda: [dict(dataset_config)]
    )

    try:
        yield harness
    finally:
        session.rollback()
        assert _table_state(db) == state_before


class TestInitializerSeed:
    """Verifica lo stato persistito dall'initializer su DB reale."""

    def test_first_run_creates_full_seed_and_installs_cron(
        self,
        initializer_harness: _InitializerHarness,
    ) -> None:
        """Su un DB senza seed vengono create tutte le righe con valori e relazioni."""
        # arrange
        db = initializer_harness.db
        hidden = _hide_existing_seed_rows(db)
        for name in EXPECTED_GROUPS:
            assert db.GroupLicense.query.filter_by(name=name).first() is None
        for name in EXPECTED_ATTRIBUTION_NAMES:
            assert db.Attribution.query.filter_by(name=name).first() is None

        # act
        initializer_harness.run()

        # assert - gruppi
        for name, expected in EXPECTED_GROUPS.items():
            group = _single_row(db, "GroupLicense", name=name)
            assert ("GroupLicense", group.id) not in hidden
            assert group.descr == expected["descr"]
            assert group.is_public is expected["is_public"]
            assert group.dballe_dsn == expected["dballe_dsn"]

        # assert - licenze collegate ai gruppi appena creati
        for name, expected in EXPECTED_LICENSES.items():
            license_row = _single_row(db, "License", name=name)
            assert ("License", license_row.id) not in hidden
            assert license_row.descr == expected["descr"]
            assert license_row.url == expected["url"]
            assert license_row.group_license.name == expected["group"]
            assert ("GroupLicense", license_row.group_license_id) not in hidden

        # assert - attribution
        for name in EXPECTED_ATTRIBUTION_NAMES:
            attribution = _single_row(db, "Attribution", name=name)
            assert ("Attribution", attribution.id) not in hidden
        for name, expected in EXPECTED_ATTRIBUTION_SAMPLES.items():
            attribution = _single_row(db, "Attribution", name=name)
            assert attribution.descr == expected["descr"]
            assert attribution.url == expected["url"]

        # assert - dataset collegato a license/attribution nuove
        config = initializer_harness.dataset_config
        dataset = initializer_harness.dataset_row()
        assert dataset.name == config["name"]
        assert dataset.description == config["description"]
        assert dataset.source == "arkimet"
        assert dataset.category is DatasetCategories.OBS
        assert dataset.fileformat == config["format"]
        assert dataset.bounding == config["bounding"]
        assert dataset.dataset_license.name == "CCBY4.0"
        assert dataset.dataset_attribution.name == "ARPAE-SIMC"
        assert ("License", dataset.license_id) not in hidden
        assert ("Attribution", dataset.attribution_id) not in hidden

        # assert - transazioni e cron (prima installazione: nessun delete)
        assert len(initializer_harness.commits) == 3
        assert initializer_harness.celery.calls == [
            ("get", "requests_cleanup"),
            ("create", "requests_cleanup"),
        ]
        assert initializer_harness.celery.installed == {
            "requests_cleanup": EXPECTED_CLEANUP_CRON
        }

    def test_second_run_keeps_rows_ids_and_values(
        self,
        initializer_harness: _InitializerHarness,
    ) -> None:
        """Una seconda esecuzione non crea duplicati e non altera id o valori."""
        # arrange - partiamo da un DB senza seed, cosi il primo run crea tutto
        _hide_existing_seed_rows(initializer_harness.db)
        initializer_harness.run()
        after_first_run = _seed_snapshot(initializer_harness)

        # act
        with _capture_writes(initializer_harness.db) as writes:
            initializer_harness.run()

        # assert
        after_second_run = _seed_snapshot(initializer_harness)
        assert after_second_run == after_first_run
        # Nessun INSERT e nessun UPDATE sulle tabelle seed; l'unica scrittura tollerata
        # e la riscrittura di `category` documentata dal test xfail qui sotto.
        assert set(writes) <= {KNOWN_CATEGORY_REWRITE}
        assert len(initializer_harness.commits) == 6
        assert initializer_harness.celery.calls == [
            ("get", "requests_cleanup"),
            ("create", "requests_cleanup"),
            ("get", "requests_cleanup"),
            ("delete", "requests_cleanup"),
            ("create", "requests_cleanup"),
        ]
        assert initializer_harness.celery.installed == {
            "requests_cleanup": EXPECTED_CLEANUP_CRON
        }

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            "Bug noto in Initializer: `ds_entry.category` (enum DatasetCategories) "
            "viene confrontato con la stringa Arkimet (es. 'OBS'), quindi risulta "
            "sempre diverso e ogni avvio riscrive il dataset. Rimuovere il marker "
            "quando il confronto sara corretto."
        ),
    )
    def test_second_run_on_aligned_state_writes_nothing(
        self,
        initializer_harness: _InitializerHarness,
    ) -> None:
        """Con DB gia allineato, il rerun non deve emettere alcuna scrittura SQL."""
        # arrange
        harness = initializer_harness
        harness.run()

        # act
        with _capture_writes(harness.db) as writes:
            harness.run()

        # assert
        assert writes == []


def _row_id_by_name(model: str, name: str) -> Callable[[Any], int]:
    """Valore stale che punta a un'altra riga seed esistente."""
    return lambda db: _single_row(db, model, name=name).id


@dataclass(frozen=True)
class _DriftCase:
    """Modifica di un solo campo da far correggere all'initializer."""

    model: str
    lookup: str | None
    field: str
    stale_value: Any


DRIFT_CASES = [
    pytest.param(
        _DriftCase("GroupLicense", "CCBY_COMPLIANT", "descr", "stale descr"),
        id="group-descr",
    ),
    pytest.param(
        _DriftCase("GroupLicense", "CCBY_COMPLIANT", "is_public", False),
        id="group-is_public",
    ),
    pytest.param(
        _DriftCase("GroupLicense", "CCBY_COMPLIANT", "dballe_dsn", "STALE"),
        id="group-dballe_dsn",
    ),
    pytest.param(
        _DriftCase("License", "CCBY4.0", "descr", "stale descr"),
        id="license-descr",
    ),
    pytest.param(
        _DriftCase("License", "CCBY4.0", "url", "https://stale.invalid/"),
        id="license-url",
    ),
    pytest.param(
        _DriftCase(
            "License",
            "CCBY4.0",
            "group_license_id",
            _row_id_by_name("GroupLicense", "CCBY-SA_COMPLIANT"),
        ),
        id="license-group_license_id",
    ),
    pytest.param(
        _DriftCase("Attribution", "ARPAE-SIMC", "descr", "stale descr"),
        id="attribution-descr",
    ),
    pytest.param(
        _DriftCase("Attribution", "ARPAE-SIMC", "url", "https://stale.invalid/"),
        id="attribution-url",
    ),
    pytest.param(
        _DriftCase("Datasets", None, "name", "initializer-ext-stale-name"),
        id="dataset-name",
    ),
    pytest.param(
        _DriftCase("Datasets", None, "description", "stale description"),
        id="dataset-description",
    ),
    pytest.param(
        _DriftCase(
            "Datasets",
            None,
            "license_id",
            _row_id_by_name("License", "CCBY-SA4.0"),
        ),
        id="dataset-license_id",
    ),
    pytest.param(
        _DriftCase(
            "Datasets",
            None,
            "attribution_id",
            _row_id_by_name("Attribution", "MISTRAL"),
        ),
        id="dataset-attribution_id",
    ),
    pytest.param(
        _DriftCase("Datasets", None, "category", DatasetCategories.FOR),
        id="dataset-category",
    ),
    pytest.param(
        _DriftCase("Datasets", None, "fileformat", "grib"),
        id="dataset-fileformat",
    ),
    pytest.param(
        _DriftCase(
            "Datasets", None, "bounding", "POLYGON ((0 0, 1 0, 1 1, 0 0))"
        ),
        id="dataset-bounding",
    ),
]


class TestInitializerSingleFieldDrift:
    """Ogni campo gestito dall'initializer viene riallineato singolarmente."""

    @pytest.mark.parametrize("case", DRIFT_CASES)
    def test_rerun_restores_single_drifted_field(
        self,
        initializer_harness: _InitializerHarness,
        case: _DriftCase,
    ) -> None:
        """Con un solo campo divergente, il rerun lo ripristina sulla stessa riga."""
        # arrange - stato allineato, poi modifica di un solo campo persistita nel DB
        harness = initializer_harness
        db = harness.db
        harness.run()

        def load_row() -> Any:
            if case.model == "Datasets":
                return harness.dataset_row()
            return _single_row(db, case.model, name=case.lookup)

        expected_values = _row_values(load_row())
        stale_value = (
            case.stale_value(db) if callable(case.stale_value) else case.stale_value
        )
        assert stale_value != expected_values[case.field]
        setattr(load_row(), case.field, stale_value)
        db.session.flush()
        db.session.expire_all()
        assert getattr(load_row(), case.field) == stale_value

        # act
        harness.run()

        # assert - stessa riga (stesso id), tutti i campi riallineati
        assert _row_values(load_row()) == expected_values
