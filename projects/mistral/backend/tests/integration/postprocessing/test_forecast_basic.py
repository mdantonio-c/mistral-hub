"""Integration tests for basic forecast extraction and single-step forecast postprocessors."""

import pytest

from .support import (
    assert_grib_contains_short_name,
    assert_grib_contains_short_name_other_than,
    assert_grib_contains_step_range,
    assert_grib_preserves_independent_fields,
    forecast_derived_variable_filters,
    forecast_derived_variable_postprocessor,
    forecast_statistic_elaboration_filters,
    forecast_statistic_elaboration_postprocessor,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


class TestForecastBasic:
    """Verify the simplest successful forecast postprocessing scenarios."""

    def test_simple_forecast_extraction_creates_output(self, pp_forecast_env) -> None:
        """Verify that a plain forecast extraction produces an output file."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_forecast_env.create_request()

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_forecast_env.execute(request_id)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_forecast_env.assert_success(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.exists()

    def test_derived_variables_emit_relhum_2m(self, pp_forecast_env) -> None:
        """Verify that derived-variable postprocessing emits `relhum_2m` while preserving other fields."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_forecast_env.create_request()

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_forecast_env.execute(
            request_id,
            filters=forecast_derived_variable_filters(),
            postprocessors=[forecast_derived_variable_postprocessor()],
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_contains_short_name(output_path, "relhum_2m")
        assert_grib_preserves_independent_fields(output_path, "relhum_2m")

    def test_statistic_elaboration_emits_tp_step_range(self, pp_forecast_env) -> None:
        """Verify that statistic elaboration emits the expected precipitation step range."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_forecast_env.create_request()

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_forecast_env.execute(
            request_id,
            filters=forecast_statistic_elaboration_filters(),
            postprocessors=[forecast_statistic_elaboration_postprocessor()],
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_contains_step_range(output_path, "tp", "3-6")
        assert_grib_contains_short_name_other_than(output_path, "tp", "sp")