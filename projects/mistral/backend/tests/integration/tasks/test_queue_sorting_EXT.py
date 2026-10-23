# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal piano di estensione
# della copertura backend, fase quick wins, per proteggere un helper puro dei task
# senza modificare la baseline legacy gia rifattorizzata.
# EXTENSION SCOPE: i test coprono solo `queue_sorting`, cioe la scelta della coda
# Celery in base a categoria dataset e freschezza del reftime; non dispatchano task,
# non aprono connessioni al broker e non leggono dataset reali.
# EXTENSION DATA WINDOW: nessun dato meteorologico reale viene usato. Il tempo e
# congelato con un fake locale per rendere deterministica la distinzione tra code
# operative e archiviate.
# EXTENSION RUNTIME: il fake basta perche il contratto osservabile della funzione e
# una stringa di routing calcolata da input Python gia normalizzati; il runtime Celery
# reale non aggiungerebbe informazione a questo livello.
# EXTENSION CLEANUP: non vengono creati file, record DB o risorse esterne; il solo
# side effect e il monkeypatch dell'orologio del modulo, ripristinato da pytest.

import datetime as dt

import pytest

from mistral.tasks import data_extraction_utilities


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


# Helper locale del modulo: congela `datetime.now(timezone.utc)` usato da
# `queue_sorting`. Rimane qui, invece che in un support module, perche serve a un solo
# file e perche evita dipendenze da data corrente, dataset reali o worker Celery.
class _FixedQueueSortingDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        fixed_now = cls(2026, 5, 28, 12, 0, 0, tzinfo=dt.timezone.utc)
        if tz is None:
            return fixed_now.replace(tzinfo=None)
        return fixed_now.astimezone(tz)


@pytest.fixture
def frozen_queue_sorting_now(monkeypatch):
    """Freeze the task utility clock so queue freshness checks are deterministic."""
    # arrange
    # Il helper sotto test importa direttamente la classe `datetime`, quindi il
    # monkeypatch viene applicato al simbolo del modulo target e non al modulo standard.
    monkeypatch.setattr(data_extraction_utilities, "datetime", _FixedQueueSortingDateTime)

    return _FixedQueueSortingDateTime.now(dt.timezone.utc)


class TestQueueSorting:
    """Verify deterministic queue routing for forecast and observed categories."""

    @pytest.mark.parametrize(
        ("dataset_type", "expected_recent", "expected_old"),
        [
            ("FOR", "operational_forecast", "archived_forecast"),
            ("SEA", "operational_forecast", "archived_forecast"),
            ("RAD", "operational_observed", "archived_observed"),
            ("OBS", "operational_observed", "archived_observed"),
        ],
    )
    def test_queue_sorting_dataset_type_routes_recent_and_old_reftimes(
        self,
        frozen_queue_sorting_now,
        dataset_type,
        expected_recent,
        expected_old,
    ):
        """Recent reftimes use operational queues, older ones use archived queues."""
        # arrange
        # Prepariamo due reftime sintetici rispetto all'orologio congelato: uno dentro
        # la finestra operativa di tre giorni e uno appena oltre. La matrice copre tutte
        # le categorie riconosciute dalla funzione senza coinvolgere Celery reale.
        recent_reftime = {"date_from": frozen_queue_sorting_now - dt.timedelta(days=2)}
        old_reftime = {"date_from": frozen_queue_sorting_now - dt.timedelta(days=4)}

        # act
        # Eseguiamo la funzione pura con input minimi e gia normalizzati, mantenendo il
        # test sul contratto di routing e non sul chiamante HTTP/task.
        recent_queue = data_extraction_utilities.queue_sorting(
            dataset_type, recent_reftime
        )
        old_queue = data_extraction_utilities.queue_sorting(dataset_type, old_reftime)

        # assert
        # Verifichiamo le stringhe esposte ai task Celery: sono l'effetto osservabile
        # che un errore di regressione cambierebbe immediatamente.
        assert recent_queue == expected_recent
        assert old_queue == expected_old

    @pytest.mark.parametrize(
        ("dataset_type", "expected_queue"),
        [
            ("FOR", "operational_forecast"),
            ("OBS", "operational_observed"),
        ],
    )
    def test_queue_sorting_naive_reftime_is_treated_as_utc(
        self,
        frozen_queue_sorting_now,
        dataset_type,
        expected_queue,
    ):
        """Naive datetimes are promoted to UTC before freshness is evaluated."""
        # arrange
        # Il ramo naive e importante per i chiamanti che passano datetime senza tzinfo.
        # La data sintetica e recente rispetto al fake, quindi deve finire sulle code
        # operative anche dopo la normalizzazione interna a UTC.
        del frozen_queue_sorting_now
        naive_recent_reftime = {"date_from": dt.datetime(2026, 5, 27, 12, 0, 0)}

        # act
        queue = data_extraction_utilities.queue_sorting(
            dataset_type, naive_recent_reftime
        )

        # assert
        assert queue == expected_queue

    @pytest.mark.parametrize(
        ("dataset_type", "expected_queue"),
        [
            ("FOR", "archived_forecast"),
            ("SEA", "archived_forecast"),
            ("RAD", "archived_observed"),
            ("OBS", "archived_observed"),
        ],
    )
    def test_queue_sorting_missing_reftime_routes_to_archived_queue(
        self,
        frozen_queue_sorting_now,
        dataset_type,
        expected_queue,
    ):
        """A missing reftime cannot be operational and must use archived routing."""
        # arrange
        # `None` rappresenta il chiamante che non puo stimare la freschezza della
        # richiesta. Il fake clock resta attivo per simmetria con gli altri test, ma il
        # ramo esercitato non legge alcuna data di input.
        del frozen_queue_sorting_now

        # act
        queue = data_extraction_utilities.queue_sorting(dataset_type, reftime=None)

        # assert
        assert queue == expected_queue