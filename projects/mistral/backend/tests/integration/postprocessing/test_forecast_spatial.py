"""Test di integrazione sui postprocessori forecast spaziali (interpolazione, ritaglio).

Esercitano il task Celery ``data_extract`` (tasks/data_extraction.py) sul
dataset ``lm5``.
"""

import pytest

from .support import (
    assert_grib_geometry,
    forecast_pressure_filter,
    grid_cropping_postprocessor,
    grid_interpolation_with_template,
    grid_interpolation_without_template,
    require_spare_point_template_archive,
    spare_point_postprocessor,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


class TestForecastSpatial:
    """Verifica i postprocessori forecast che cambiano la geometria e lo spare-point."""

    def test_grid_interpolation_without_template_updates_geometry(
        self, pp_forecast_env
    ) -> None:
        """Verifica che l'interpolazione senza template applichi la geometria richiesta.

        Esercita ``grid_interpolation`` (tools/grid_interpolation.py) nel task
        ``data_extract``.
        """
        # arrange
        request_id = pp_forecast_env.create_request()
        y_min = -10
        nx = 12
        postprocessor = grid_interpolation_without_template(
            x_min=-15,
            y_min=y_min,
            nx=nx,
        )

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_pressure_filter(),
            postprocessors=[postprocessor],
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_geometry(output_path, y_min, nx)

    def test_grid_interpolation_with_template_reuses_template_geometry(
        self, pp_forecast_env
    ) -> None:
        """Verifica che l'interpolazione con template copi la geometria dal GRIB dato.

        Esercita ``grid_interpolation`` con template nel task ``data_extract``. Il
        template viene prodotto da una prima request, poi cancellata.
        """
        # arrange
        seed_request_id = pp_forecast_env.create_request()
        y_min = -10
        nx = 12
        seed_postprocessor = grid_interpolation_without_template(
            x_min=-15,
            y_min=y_min,
            nx=nx,
        )
        pp_forecast_env.execute(
            seed_request_id,
            filters=forecast_pressure_filter(),
            postprocessors=[seed_postprocessor],
        )
        template_source = pp_forecast_env.assert_success(seed_request_id)
        template_path = pp_forecast_env.copy_upload(template_source, "gi_template.grib")
        pp_forecast_env.delete_request(seed_request_id)
        request_id = pp_forecast_env.create_request()

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_pressure_filter(),
            postprocessors=[grid_interpolation_with_template(template_path)],
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert_grib_geometry(output_path, y_min, nx)

    def test_grid_cropping_completes_successfully(self, pp_forecast_env) -> None:
        """Verifica che il ritaglio della griglia su dati forecast vada a buon fine.

        Esercita ``grid_cropping`` (tools/grid_cropping.py) nel task ``data_extract``.
        """
        # arrange
        request_id = pp_forecast_env.create_request()
        postprocessor = grid_cropping_postprocessor(
            initial_lon=10, initial_lat=40, final_lon=15, final_lat=45
        )

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_pressure_filter(),
            postprocessors=[postprocessor],
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert output_path.exists()

    def test_spare_point_interpolation_outputs_bufr(self, pp_forecast_env) -> None:
        """Verifica che l'interpolazione spare-point produca un file BUFR.

        Esercita ``spare_point_interpolation`` (tools/spare_point_interpol.py) nel
        task ``data_extract``; fa skip se manca l'archivio dello shapefile.
        """
        # arrange
        request_id = pp_forecast_env.create_request()
        archive_path = require_spare_point_template_archive()
        upload_dir = pp_forecast_env.unzip_upload(archive_path)
        template_path = upload_dir / "template_for_spare_point.shp"

        # act
        pp_forecast_env.execute(
            request_id,
            filters=forecast_pressure_filter(),
            postprocessors=[spare_point_postprocessor(template_path)],
        )

        # assert
        output_path = pp_forecast_env.assert_success(request_id)
        assert output_path.suffix == ".bufr"
