"""Test di integrazione sui casi di errore del postprocessing forecast e observed.

Esercitano il task Celery ``data_extract`` (tasks/data_extraction.py) con
postprocessori sconosciuti o input incompleti.
"""

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
    """Verifica che un postprocessing configurato male faccia fallire la request."""

    def test_unknown_postprocessor_marks_request_as_failure(
        self, pp_forecast_env
    ) -> None:
        """Verifica che un postprocessore sconosciuto lasci la request in FAILURE.

        Il task ``data_extract`` rifiuta il ``processor_type`` non abilitato; il
        messaggio viene controllato solo sull'eccezione, perche su DB viene salvato
        il messaggio generico "Failed to extract data".
        """
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
        """Verifica che le variabili derivate forecast falliscano senza campi sorgente.

        Esercita ``tools/derived_variables.py`` dentro il task ``data_extract``.
        """
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
        """Verifica che la statistica forecast fallisca con un timerange non valido.

        Esercita ``tools/statistic_elaboration.py`` dentro il task ``data_extract``.
        """
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
        """Verifica che le variabili derivate observed falliscano senza campi sorgente.

        Esercita l'estrazione observed e ``tools/derived_variables.py`` nel task
        ``data_extract``.
        """
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
        """Verifica che la statistica observed fallisca se gli input sono incompleti.

        Esercita l'estrazione observed e ``tools/statistic_elaboration.py`` nel task
        ``data_extract``.
        """
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
