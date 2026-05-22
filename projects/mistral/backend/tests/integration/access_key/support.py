"""Named endpoint constants shared by access-key tests and fixtures.

Keeping these URLs in one place avoids repeating literal endpoint strings across
tests that exercise access-key creation, retrieval, regeneration, and validation.
"""

from restapi.tests import API_URI


ACCESS_KEY_ENDPOINT = f"{API_URI}/access-key"
"""Endpoint used to create, fetch, and regenerate the current user's access key."""


ACCESS_KEY_VALIDATE_ENDPOINT = f"{ACCESS_KEY_ENDPOINT}/validate"
"""Endpoint used to validate credentials presented as email plus access key."""