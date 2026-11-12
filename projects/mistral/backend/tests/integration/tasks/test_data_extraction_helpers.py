# Ambito: i test verificano `human_size`, `adapt_reftime` e `package_data_license`
# di tasks/data_extraction.py, cioe helper puri del task di estrazione dati con
# contratto locale e input controllabili.
# Finestra dati: nessun dataset reale viene letto. Le date usate sono valori
# sintetici fissati nel test e non rappresentano finestre runtime meteorologiche.
# Runtime: non vengono eseguiti Celery, SMTP, Rabbit o tool meteo. Il fake
# dell'orologio basta perche `adapt_reftime` dipende solo da `utcnow`, dalla schedule
# sintetica e dal reftime iniziale salvato nella schedule.
# Cleanup: `tmp_path` isola i file creati dal test tar.gz; il file dati
# cancellato da `package_data_license` e intenzionalmente verificato, mentre pytest
# rimuove la directory temporanea a fine test.

import datetime as dt
import json
import tarfile
from types import SimpleNamespace

import pytest

from mistral.tasks import data_extraction


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


# Helper locale del modulo: sostituisce il namespace `datetime` visto dal modulo task
# con un orologio stabile. Non viene promosso in `helpers/` perche serve solo ai test
# deterministici di `adapt_reftime` in questo file.
class _FixedDataExtractionDateTime(dt.datetime):
    """Sottoclasse di ``datetime`` con ``utcnow`` e ``now`` fissi a 2026-05-28 12:30."""

    @classmethod
    def utcnow(cls):
        return cls(2026, 5, 28, 12, 30, 0)

    @classmethod
    def now(cls, tz=None):
        fixed_now = cls.utcnow()
        if tz is None:
            return fixed_now
        return fixed_now.replace(tzinfo=dt.timezone.utc).astimezone(tz)


@pytest.fixture
def frozen_data_extraction_clock(monkeypatch):
    """Congela l'orologio visto da tasks/data_extraction.py e restituisce l'ora fissa.

    Serve ai test di ``adapt_reftime``, che calcola la finestra partendo da ``utcnow``.
    """
    # arrange
    # `data_extraction` importa il modulo datetime completo. Sostituiamo solo il
    # namespace del modulo target con un oggetto minimale che offre `datetime` e
    # `timedelta`, evitando di alterare il modulo standard globale durante il test.
    frozen_datetime_namespace = SimpleNamespace(
        datetime=_FixedDataExtractionDateTime,
        timedelta=dt.timedelta,
    )
    monkeypatch.setattr(data_extraction, "datetime", frozen_datetime_namespace)

    return _FixedDataExtractionDateTime.utcnow()


class TestDataExtractionHelpers:
    """Raggruppa i test sugli helper puri usati dal task di estrazione dati."""

    @pytest.mark.parametrize(
        ("byte_count", "expected"),
        [
            (0, "0 bytes"),
            (1023, "1023 bytes"),
            (1024, "1KB"),
            (1024 * 1024, "1MB"),
        ],
    )
    def test_human_size_formats_existing_thresholds(self, byte_count, expected):
        """Verifica che ``human_size`` formatti le soglie byte/KB/MB come interi."""
        # arrange
        # I valori scelti attraversano il limite byte/KB/MB senza introdurre decimali:
        # questo documenta il comportamento storico dell'helper invece di imporre un
        # formato nuovo.

        # act
        rendered_size = data_extraction.human_size(byte_count)

        # assert
        assert rendered_size == expected

    def test_package_data_license_archives_license_and_removes_source_file(
        self, tmp_path
    ):
        """Verifica che ``package_data_license`` crei un tar.gz con dati e LICENSE.

        Il file dati originale deve essere cancellato dopo l'archiviazione.
        """
        # arrange
        # Creiamo due file temporanei sintetici: non hanno contenuto meteorologico reale,
        # perche il contratto qui e solo filesystem/tar. Il cleanup e affidato a tmp_path.
        out_file = tmp_path / "forecast.grib"
        license_file = tmp_path / "license.txt"
        out_file.write_text("synthetic-data", encoding="utf-8")
        license_file.write_text("synthetic-license", encoding="utf-8")

        # act
        tar_filename = data_extraction.package_data_license(
            tmp_path, out_file, license_file
        )

        # assert
        # Verifichiamo sia il package prodotto sia il side effect intenzionale di
        # cancellazione del file dati originale, senza dipendere dal timestamp nel nome.
        tar_path = tmp_path / tar_filename
        assert tar_filename.startswith("data-")
        assert tar_filename.endswith(".tar.gz")
        assert tar_path.exists()
        assert not out_file.exists()

        with tarfile.open(tar_path, "r:gz") as tar:
            assert sorted(tar.getnames()) == ["LICENSE", "forecast.grib"]
            license_member = tar.extractfile("LICENSE")
            assert license_member is not None
            assert license_member.read().decode("utf-8") == "synthetic-license"

    def test_adapt_reftime_daily_periodic_schedule_moves_window_forward(
        self, frozen_data_extraction_clock
    ):
        """Verifica che ``adapt_reftime`` su schedule giornaliera mantenga l'offset.

        La nuova finestra conserva la distanza originale tra submission e reftime.
        """
        # arrange
        # La schedule fake rappresenta una richiesta giornaliera nata un giorno dopo il
        # proprio reftime iniziale. Con l'orologio congelato al 2026-05-28 12:30, il
        # nuovo `to` atteso resta un giorno prima del fake now e il `from` rispetta la
        # durata originale della finestra.
        del frozen_data_extraction_clock
        schedule = SimpleNamespace(
            is_crontab=False,
            period=SimpleNamespace(name="days"),
            every=1,
            time_delta=dt.timedelta(hours=6),
            args={"reftime": {"to": "2026-05-24T12:30:00.000000Z"}},
            submission_date=dt.datetime(2026, 5, 25, 12, 30, 0),
        )

        # act
        adapted_reftime = data_extraction.adapt_reftime(schedule, reftime={"set": True})

        # assert
        assert adapted_reftime == {
            "from": "2026-05-27T06:30:00.000000Z",
            "to": "2026-05-27T12:30:00.000000Z",
        }

    def test_adapt_reftime_hourly_periodic_schedule_moves_window_forward(
        self, frozen_data_extraction_clock
    ):
        """Verifica che ``adapt_reftime`` su schedule oraria avanzi la finestra.

        La finestra si sposta in avanti del numero di intervalli orari trascorsi.
        """
        # arrange
        # Il fake mantiene minuti e secondi allineati tra submission, reftime iniziale e
        # now. Questo evita ambiguita di arrotondamento e isola il ramo `hours` della
        # funzione, che normalizza i minuti della submission prima del calcolo.
        del frozen_data_extraction_clock
        schedule = SimpleNamespace(
            is_crontab=False,
            period=SimpleNamespace(name="hours"),
            every=1,
            time_delta=dt.timedelta(hours=1),
            args={"reftime": {"to": "2026-05-28T07:30:00.000000Z"}},
            submission_date=dt.datetime(2026, 5, 28, 8, 30, 0),
        )

        # act
        adapted_reftime = data_extraction.adapt_reftime(schedule, reftime={"set": True})

        # assert
        assert adapted_reftime == {
            "from": "2026-05-28T10:30:00.000000Z",
            "to": "2026-05-28T11:30:00.000000Z",
        }

    def test_adapt_reftime_base_crontab_schedule_uses_daily_interval(
        self, frozen_data_extraction_clock
    ):
        """Verifica che ``adapt_reftime`` tratti una crontab semplice come giornaliera.

        Senza chiavi settimanali o mensili l'intervallo usato e di un giorno.
        """
        # arrange
        # Il ramo crontab viene coperto con settings minimi e JSON valido. Non serve un
        # vero scheduler RedBeat per questo contratto: l'helper legge solo il JSON della
        # schedule e calcola una finestra temporale sintetica.
        del frozen_data_extraction_clock
        schedule = SimpleNamespace(
            is_crontab=True,
            crontab_settings=json.dumps({}),
            time_delta=dt.timedelta(hours=12),
            args={"reftime": {"to": "2026-05-25T12:30:00.000000Z"}},
            submission_date=dt.datetime(2026, 5, 26, 12, 30, 0),
        )

        # act
        adapted_reftime = data_extraction.adapt_reftime(schedule, reftime={"set": True})

        # assert
        assert adapted_reftime == {
            "from": "2026-05-27T00:30:00.000000Z",
            "to": "2026-05-27T12:30:00.000000Z",
        }