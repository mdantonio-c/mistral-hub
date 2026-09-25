"""
Template guida comune per i test Meteo-Hub
==========================================

Questo file NON viene collezionato da pytest (non è un test_*.py).
Serve come riferimento strutturale per chiunque scriva o rifattorizzi test.

Schema canonico di un file di test
----------------------------------

Ordine dei blocchi:

1. Import strettamente necessari.
2. pytestmark per area funzionale o tipologia di test.
3. Eventuali fixture locali leggere, solo se davvero specifiche del modulo.
4. Eventuali helper locali piccoli, solo se non hanno valore riusabile cross-file.
5. Test raggruppati per contratto o scenario omogeneo.
6. Ogni test scritto sempre nello stesso ordine logico: arrange, act, assert.
7. Cleanup delegato al cleanup registry, non disperso inline.

Template logico di un singolo test
-----------------------------------
"""

# ─── Esempio strutturale (NON eseguibile, solo guida) ────────────────────────

import pytest  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.example_area]


class TestExampleArea:
    """
    Gruppo test per un singolo contratto o endpoint.
    Ogni metodo verifica un solo comportamento atteso.
    """

    def test_happy_path_returns_expected_status(self, cleanup_registry):
        """
        Esempio minimo di test scritto con la forma canonica della suite.

        Il metodo non verifica nulla di reale: esiste solo per mostrare dove va
        raccontata la preparazione dello scenario, dove va eseguita l'azione
        sotto test e dove devono stare le asserzioni finali.
        """
        # arrange ─ preparazione dati, utenti, payload
        # (usare fixture, factory, builder)
        payload = {"key": "value"}

        # act ─ una sola azione sotto test
        # response = api.post_json("/endpoint", body=payload, headers=headers)

        # assert ─ verifica dell'effetto atteso
        # assert response.status_code == 201
        # cleanup_registry.add_path(temp_output_dir)  # registra per cleanup
        pass

    def test_invalid_input_returns_error(self, cleanup_registry):
        """Example placeholder showing how to document a validation-error test."""
        # arrange
        # Prepariamo lo scenario helper condivisi con dati minimi e controllati, cosi la
        # verifica successiva resta legata a un comportamento preciso.
        bad_payload = {"key": None}

        # act
        # response = api.post_json("/endpoint", body=bad_payload, headers=headers)

        # assert
        # assert response.status_code == 400
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        pass


# ─── Regole di adozione ──────────────────────────────────────────────────────
#
# 1. Un test deve verificare un solo contratto o un solo motivo di fallimento.
# 2. Naming: test_<behavior>_<expected_outcome>.
# 3. I blocchi arrange / act / assert devono essere riconoscibili.
# 4. Le fixture incapsulano setup e cleanup; il corpo del test non è un framework.
# 5. Payload ripetuti → factory/builder quando ricorrono in più di un file.
# 6. Niente sleep: usare polling osservabile (helpers/polling.py quando serve).
# 7. Niente self.save/get cross-test: lo stato condiviso è fuori standard.
# 8. Se una deviazione è necessaria, motivarla con un commento tecnico nel file.
#
# Varianti ammesse:
# - Test endpoint/integrazione: usa env, api client, builder, polling, cleanup.
# - Test logica pura: stessa forma arrange/act/assert, senza env o api client.
