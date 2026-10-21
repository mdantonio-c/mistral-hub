# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal piano di estensione
# della copertura backend, fase quick wins, per coprire parser puri del service
# Arkimet senza modificare la suite legacy esistente.
# EXTENSION SCOPE: i test verificano `is_filter_allowed`, `parse_reftime`,
# `parse_matchers` e `decode_run`, cioe trasformazioni di dizionari/stringhe in query
# Arkimet. Non chiamano `arki-query`, non aprono configurazioni dataset e non eseguono
# estrazioni.
# EXTENSION DATA WINDOW: nessun dataset reale viene usato. Le date sono stringhe
# sintetiche scelte solo per verificare la formattazione inclusiva del reftime.
# EXTENSION RUNTIME: il fake non e necessario perche le funzioni esercitate sono pure;
# eventuali errori di toolchain Arkimet reale appartengono agli smoke gia presenti.
# EXTENSION CLEANUP: nessuna risorsa esterna viene creata; i test non hanno side effect
# da ripulire oltre allo stato locale Python.

import pytest

from mistral.services.arkimet import BeArkimet


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestArkimetQueryParsing:
    """Verify pure Arkimet query parsing helpers."""

    def test_is_filter_allowed_accepts_known_filter_and_rejects_unknown(self):
        """The allow-list exposes supported filter names without runtime access."""
        # arrange
        # Usiamo un filtro noto e uno inventato per proteggere il contratto booleano
        # minimo dell'allow-list, senza costruire una query Arkimet completa.
        known_filter = "run"
        unknown_filter = "not-a-filter"

        # act
        known_result = BeArkimet.is_filter_allowed(known_filter)
        unknown_result = BeArkimet.is_filter_allowed(unknown_filter)

        # assert
        assert known_result is True
        assert unknown_result is False

    def test_parse_reftime_formats_inclusive_arkimet_bounds(self):
        """ISO-like bounds are converted to the Arkimet reftime matcher string."""
        # arrange
        # Le date sono sintetiche e non corrispondono a finestre dataset reali: qui si
        # testa solo la conversione stringa -> matcher con operatori inclusivi.
        from_str = "2026-05-28T00:00:00Z"
        to_str = "2026-05-28T03:30:00Z"

        # act
        matcher = BeArkimet.parse_reftime(from_str, to_str)

        # assert
        assert matcher == "reftime: >=2026-05-28 00:00,<=2026-05-28 03:30"

    def test_parse_matchers_decodes_run_and_quantity_filters(self):
        """Structured filters are joined in the matcher syntax expected by Arkimet."""
        # arrange
        # Il filtro usa solo decoder puri: `run` esercita la conversione minuti -> HH:MM
        # e `quantity` protegge il join di valori multipli. Nessun matcher viene inviato
        # a una sessione Arkimet reale.
        filters = {
            "run": [
                {"style": "MINUTE", "value": 360},
                {"style": "MINUTE", "value": 0},
            ],
            "quantity": [{"value": ["B13011", "B11001"]}],
        }

        # act
        matcher = BeArkimet.parse_matchers(filters)

        # assert
        assert matcher == (
            "run:MINUTE,06:00 or MINUTE,00:00; quantity:B13011,B11001"
        )

    def test_decode_run_valid_minute_style_returns_hour_minute(self):
        """A MINUTE run dictionary is normalized to zero-padded HH:MM syntax."""
        # arrange
        # Settantacinque minuti coprono sia il quoziente ora sia il resto minuti, piu
        # utile di un valore tondo per intercettare regressioni sulla formattazione.
        run_filter = {"style": "MINUTE", "value": 75}

        # act
        decoded_run = BeArkimet.decode_run(run_filter)

        # assert
        assert decoded_run == "MINUTE,01:15"

    def test_decode_run_invalid_input_type_raises_type_error(self):
        """Non-dictionary input is rejected before style-specific parsing."""
        # arrange
        invalid_run_filter = "MINUTE,01:00"

        # act / assert
        with pytest.raises(TypeError):
            BeArkimet.decode_run(invalid_run_filter)

    def test_decode_run_invalid_style_raises_value_error(self):
        """Unsupported run styles fail explicitly instead of producing a matcher."""
        # arrange
        invalid_run_filter = {"style": "HOUR", "value": 1}

        # act / assert
        with pytest.raises(ValueError):
            BeArkimet.decode_run(invalid_run_filter)