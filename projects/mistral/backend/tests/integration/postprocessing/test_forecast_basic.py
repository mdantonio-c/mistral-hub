"""Test di integrazione sull'estrazione forecast e sui postprocessori singoli.

Esercitano il task Celery ``data_extract`` (tasks/data_extraction.py) sul
dataset ``lm5`` e leggono i GRIB prodotti.
"""

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
    """Verifica gli scenari forecast di successo piu semplici."""

    def test_simple_forecast_extraction_creates_output(self, pp_forecast_env) -> None:
        """Verifica che un'estrazione forecast senza postprocessori produca un file.

        Esercita il task ``data_extract`` con estrazione Arkimet reale.
        """
        # arrange
        request_id = pp_forecast_env.create_request()

        # act
        pp_forecast_env.execute(request_id)

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert output_path.exists()

    def test_derived_variables_emit_relhum_2m(self, pp_forecast_env) -> None:
        """Verifica che le variabili derivate producano `relhum_2m`.

        Anche gli altri campi devono restare nel file. Esercita
        ``tools/derived_variables.py`` dentro il task ``data_extract``.
        """
        # arrange
        request_id = pp_forecast_env.create_request()

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_derived_variable_filters(),
            postprocessors=[forecast_derived_variable_postprocessor()],
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_contains_short_name(output_path, "relhum_2m")
        assert_grib_preserves_independent_fields(output_path, "relhum_2m")

    def test_statistic_elaboration_emits_tp_step_range(self, pp_forecast_env) -> None:
        """Verifica che la statistica produca la precipitazione con lo stepRange atteso.

        Esercita ``tools/statistic_elaboration.py`` dentro il task ``data_extract``.
        """
        # arrange
        request_id = pp_forecast_env.create_request()

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_statistic_elaboration_filters(),
            postprocessors=[forecast_statistic_elaboration_postprocessor()],
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_contains_step_range(output_path, "tp", "3-6")
        assert_grib_contains_short_name_other_than(output_path, "tp", "sp")