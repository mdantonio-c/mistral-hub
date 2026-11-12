"""Test di integrazione su piu postprocessori forecast in catena nella stessa request.

Esercitano il task Celery ``data_extract`` (tasks/data_extraction.py) sul
dataset ``lm5``.
"""

import pytest

from .support import (
    assert_grib_contains_short_name,
    assert_grib_contains_step_range,
    assert_grib_messages_have_geometry,
    forecast_chaining_filters,
    forecast_derived_variable_postprocessor,
    forecast_statistic_elaboration_postprocessor,
    grid_cropping_postprocessor,
    grid_interpolation_without_template,
    require_spare_point_template_archive,
    spare_point_postprocessor,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


class TestForecastChaining:
    """Verifica che piu postprocessori forecast in catena non perdano output chiave."""

    def test_combined_postprocessors_keep_derived_statistic_and_geometry(
        self, pp_forecast_env
    ) -> None:
        """Verifica che la catena mantenga variabile derivata, statistica e geometria.

        Combina ``derived_variables``, ``statistic_elaboration``,
        ``grid_interpolation`` e ``grid_cropping`` nel task ``data_extract``.
        """
        # arrange
        request_id = pp_forecast_env.create_request()
        y_min = -10
        nx = 12
        postprocessors = [
            forecast_derived_variable_postprocessor(),
            forecast_statistic_elaboration_postprocessor(),
            grid_interpolation_without_template(x_min=-15, y_min=y_min, nx=nx),
            grid_cropping_postprocessor(
                initial_lon=10, initial_lat=40, final_lon=15, final_lat=45
            ),
        ]

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_chaining_filters(),
            postprocessors=postprocessors,
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_contains_short_name(output_path, "relhum_2m")
        assert_grib_contains_step_range(output_path, "tp", "3-6")
        assert_grib_messages_have_geometry(output_path, y_min, nx)

    def test_combined_postprocessors_can_export_json_after_spare_point(
        self, pp_forecast_env
    ) -> None:
        """Verifica che una catena con spare-point possa esportare l'output in JSON.

        Combina variabili derivate, statistica e ``spare_point_interpolation`` nel
        task ``data_extract``, con ``output_format="json"``.
        """
        # arrange
        request_id = pp_forecast_env.create_request()
        archive_path = require_spare_point_template_archive()
        upload_dir = pp_forecast_env.unzip_upload(archive_path)
        template_path = upload_dir / "template_for_spare_point.shp"
        postprocessors = [
            forecast_derived_variable_postprocessor(),
            forecast_statistic_elaboration_postprocessor(),
            spare_point_postprocessor(template_path),
        ]

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_chaining_filters(),
            postprocessors=postprocessors,
            output_format="json",
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert output_path.suffix == ".json"
        assert "grib" not in output_path.name
