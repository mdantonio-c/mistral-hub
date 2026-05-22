"""Integration tests for failure paths in forecast and observed postprocessing."""

import pytest
from restapi.connectors.celery import Ignore

from .support import (
    forecast_derived_variable_missing_filters,
    forecast_derived_variable_postprocessor,
    forecast_statistic_elaboration_missing_filters,
    forecast_statistic_elaboration_postprocessor,
    observed_derived_variable_missing_filters,
    observed_derived_variable_postprocessor,
    observed_statistic_elaboration_postprocessor,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


class TestPostprocessingErrorHandling:
    """Verify that invalid postprocessing configurations fail early and mark requests as failed."""

    def test_unknown_postprocessor_marks_request_as_failure(
        self, pp_forecast_env
    ) -> None:
        """Verify that an unknown processor type raises and leaves the request in failure state."""
        # arrange
        request_id = pp_forecast_env.create_request()
        postprocessor = {"processor_type": pp_forecast_env.faker.pystr()}

        # act
        with pytest.raises(Ignore, match="Unknown post-processor"):
            pp_forecast_env.execute(
                request_id,
                postprocessors=[postprocessor],
                expect_failure=True,
            )

        # assert
        pp_forecast_env.assert_failure(request_id, expected_message=None)

    def test_forecast_derived_variables_require_all_inputs(
        self, pp_forecast_env
    ) -> None:
        """Verify that forecast derived variables fail when required source fields are missing."""
        # arrange
        request_id = pp_forecast_env.create_request()

        # act
        with pytest.raises(Ignore):
            pp_forecast_env.execute(
                request_id,
                filters=forecast_derived_variable_missing_filters(),
                postprocessors=[forecast_derived_variable_postprocessor()],
                expect_failure=True,
            )

        # assert
        pp_forecast_env.assert_failure(request_id)

    def test_forecast_statistic_elaboration_requires_valid_timerange(
        self, pp_forecast_env
    ) -> None:
        """Verify that forecast statistic elaboration fails with an invalid timerange selection."""
        # arrange
        request_id = pp_forecast_env.create_request()

        # act
        with pytest.raises(Ignore):
            pp_forecast_env.execute(
                request_id,
                filters=forecast_statistic_elaboration_missing_filters(),
                postprocessors=[forecast_statistic_elaboration_postprocessor()],
                expect_failure=True,
            )

        # assert
        pp_forecast_env.assert_failure(request_id)

    def test_observed_derived_variables_require_all_inputs(
        self, pp_observed_env
    ) -> None:
        """Verify that observed derived variables fail when required source fields are missing."""
        # arrange
        request_id = pp_observed_env.create_request()

        # act
        with pytest.raises(Ignore):
            pp_observed_env.execute(
                request_id,
                filters=observed_derived_variable_missing_filters(),
                postprocessors=[observed_derived_variable_postprocessor()],
                expect_failure=True,
            )

        # assert
        pp_observed_env.assert_failure(request_id)

    def test_observed_statistic_elaboration_requires_all_inputs(
        self, pp_observed_env
    ) -> None:
        """Verify that observed statistic elaboration fails when mandatory inputs are incomplete."""
        # arrange
        request_id = pp_observed_env.create_request()

        # act
        with pytest.raises(Ignore):
            pp_observed_env.execute(
                request_id,
                filters=observed_derived_variable_missing_filters(),
                postprocessors=[observed_statistic_elaboration_postprocessor()],
                expect_failure=True,
            )

        # assert
        pp_observed_env.assert_failure(request_id)
