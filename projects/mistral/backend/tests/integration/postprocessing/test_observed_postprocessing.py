"""Test di integrazione sull'estrazione observed e sui postprocessori in catena.

Esercitano il task Celery ``data_extract`` (tasks/data_extraction.py) sul
dataset ``agrmet`` con dati DBALLE reali.
"""

import pytest

from .support import (
    observed_chaining_filters,
    observed_derived_variable_filters,
    observed_derived_variable_postprocessor,
    observed_statistic_elaboration_filters,
    observed_statistic_elaboration_postprocessor,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


class TestObservedPostprocessing:
    """Verifica i casi di successo del postprocessing observed, semplice e in catena."""

    def test_simple_observed_extraction_creates_output(self, pp_observed_env) -> None:
        """Verifica che un'estrazione observed senza postprocessori produca un file.

        Esercita l'estrazione observed (``observed_extraction``) nel task
        ``data_extract``.
        """
        # arrange
        request_id = pp_observed_env.create_request()

        # act
        pp_observed_env.execute(request_id)

        # assert
        output_path = pp_observed_env.assert_success(request_id)
        assert output_path.exists()

    def test_observed_derived_variables_create_output(self, pp_observed_env) -> None:
        """Verifica che le variabili derivate observed riescano con gli input richiesti.

        Esercita ``tools/derived_variables.py`` dentro il task ``data_extract``.
        """
        # arrange
        request_id = pp_observed_env.create_request()

        # act
        pp_observed_env.execute(
            request_id,
            filters=observed_derived_variable_filters(),
            postprocessors=[observed_derived_variable_postprocessor()],
        )

        # assert
        output_path = pp_observed_env.assert_success(request_id)
        assert output_path.exists()

    def test_observed_statistic_elaboration_creates_output(
        self, pp_observed_env
    ) -> None:
        """Verifica che la statistica observed riesca con gli input richiesti.

        Esercita ``tools/statistic_elaboration.py`` dentro il task ``data_extract``.
        """
        # arrange
        request_id = pp_observed_env.create_request()

        # act
        pp_observed_env.execute(
            request_id,
            filters=observed_statistic_elaboration_filters(),
            postprocessors=[observed_statistic_elaboration_postprocessor()],
        )

        # assert
        output_path = pp_observed_env.assert_success(request_id)
        assert output_path.exists()

    def test_combined_observed_postprocessors_export_json(self, pp_observed_env) -> None:
        """Verifica che i postprocessori observed in catena possano esportare in JSON.

        Combina variabili derivate e statistica nel task ``data_extract``, con
        ``output_format="json"`` e ``only_reliable=True``.
        """
        # arrange
        request_id = pp_observed_env.create_request()
        postprocessors = [
            observed_derived_variable_postprocessor(),
            observed_statistic_elaboration_postprocessor(),
        ]

        # act
        pp_observed_env.execute(
            request_id,
            filters=observed_chaining_filters(),
            postprocessors=postprocessors,
            output_format="json",
            only_reliable=True,
        )

        # assert
        output_path = pp_observed_env.assert_success(request_id)
        assert output_path.suffix == ".json"