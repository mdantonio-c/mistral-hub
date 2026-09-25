"""Integration tests for chaining multiple forecast postprocessors in one request."""

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
    """Verify that multiple forecast postprocessors can be composed without losing key outputs."""

    def test_combined_postprocessors_keep_derived_statistic_and_geometry(
        self, pp_forecast_env
    ) -> None:
        """Verify that chained postprocessors preserve derived values, statistics, and grid geometry."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_forecast_env.create_request()
        y_min = -10
        nx = 12
        postprocessors = [
            forecast_derived_variable_postprocessor(),
            forecast_statistic_elaboration_postprocessor(),
            grid_interpolation_without_template(x_min=-15, y_min=y_min, nx=nx),
            grid_cropping_postprocessor(initial_lon=-10, initial_lat=-5),
        ]

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_forecast_env.execute(
            request_id,
            filters=forecast_chaining_filters(),
            postprocessors=postprocessors,
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_contains_short_name(output_path, "relhum_2m")
        assert_grib_contains_step_range(output_path, "tp", "3-6")
        assert_grib_messages_have_geometry(output_path, y_min, nx)

    def test_combined_postprocessors_can_export_json_after_spare_point(
        self, pp_forecast_env
    ) -> None:
        """Verify that a chained spare-point workflow can still export the final output as JSON."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
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
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_forecast_env.execute(
            request_id,
            filters=forecast_chaining_filters(),
            postprocessors=postprocessors,
            output_format="json",
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_forecast_env.assert_success(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.suffix == ".json"
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert "grib" not in output_path.name
