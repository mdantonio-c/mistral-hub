"""Integration tests for observed-data extraction and observed postprocessor chaining."""

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
    """Verify successful observed postprocessing flows for plain and chained requests."""

    def test_simple_observed_extraction_creates_output(self, pp_observed_env) -> None:
        """Verify that a plain observed extraction produces an output file."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_observed_env.create_request()

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_observed_env.execute(request_id)

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_observed_env.assert_success(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.exists()

    def test_observed_derived_variables_create_output(self, pp_observed_env) -> None:
        """Verify that observed derived-variable postprocessing succeeds with the required inputs."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_observed_env.create_request()

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_observed_env.execute(
            request_id,
            filters=observed_derived_variable_filters(),
            postprocessors=[observed_derived_variable_postprocessor()],
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_observed_env.assert_success(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.exists()

    def test_observed_statistic_elaboration_creates_output(
        self, pp_observed_env
    ) -> None:
        """Verify that observed statistic-elaboration postprocessing succeeds with the required inputs."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_observed_env.create_request()

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_observed_env.execute(
            request_id,
            filters=observed_statistic_elaboration_filters(),
            postprocessors=[observed_statistic_elaboration_postprocessor()],
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_observed_env.assert_success(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.exists()

    def test_combined_observed_postprocessors_export_json(self, pp_observed_env) -> None:
        """Verify that chaining observed postprocessors can export JSON output."""
        # arrange
        # Prepariamo lo scenario post-processing con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        request_id = pp_observed_env.create_request()
        postprocessors = [
            observed_derived_variable_postprocessor(),
            observed_statistic_elaboration_postprocessor(),
        ]

        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        pp_observed_env.execute(
            request_id,
            filters=observed_chaining_filters(),
            postprocessors=postprocessors,
            output_format="json",
            only_reliable=True,
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        output_path = pp_observed_env.assert_success(request_id)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert output_path.suffix == ".json"