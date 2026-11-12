"""Costanti con gli URL degli endpoint usati dai test e dalle fixture access key.

Tenere questi URL in un solo punto evita di ripetere le stringhe degli endpoint nei
test che verificano creazione, lettura, rigenerazione e validazione delle access key.

- ``ACCESS_KEY_ENDPOINT``: crea, legge e rigenera la chiave dell'utente corrente.
- ``ACCESS_KEY_VALIDATE_ENDPOINT``: valida le credenziali email piu access key.
"""

from restapi.tests import API_URI


ACCESS_KEY_ENDPOINT = f"{API_URI}/access-key"
"""Endpoint used to create, fetch, and regenerate the current user's access key."""


ACCESS_KEY_VALIDATE_ENDPOINT = f"{ACCESS_KEY_ENDPOINT}/validate"
"""Endpoint used to validate credentials presented as email plus access key."""