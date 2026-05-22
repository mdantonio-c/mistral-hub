"""Integration tests for the access-key validation endpoint.

These scenarios check which combinations of email and access key are accepted or
rejected when credentials are presented through HTTP Basic authentication.
"""

import pytest
from restapi.services.authentication import BaseAuthentication
from restapi.tests import FlaskClient

from .support import (
    ACCESS_KEY_ENDPOINT,
    ACCESS_KEY_VALIDATE_ENDPOINT,
)
from mistral.tests.helpers.auth import make_basic_auth


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAccessKeyValidationAPI:
    """Group scenarios that verify which credentials the validation endpoint accepts."""

    def test_01_missing_credentials(self, client: FlaskClient):
        """Reject a validation request that does not carry any credentials."""
        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT)

        # assert
        assert resp.status_code == 401

    def test_02_invalid_email(self, client: FlaskClient):
        """Reject a validation request when the user email does not exist."""
        # arrange
        headers = make_basic_auth("nonexistent@example.com", "whatever")

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 401

    def test_03_invalid_access_key(self, client: FlaskClient, fresh_access_key):
        """Reject a validation request when the presented key does not match the user."""
        # arrange
        _, _ = fresh_access_key
        email = BaseAuthentication.default_user
        headers = make_basic_auth(email, "WRONG-KEY")

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 401

    def test_04_valid_access_key(self, client: FlaskClient, fresh_access_key):
        """Accept a validation request when email and access key match."""
        # arrange
        _, valid_key = fresh_access_key
        email = BaseAuthentication.default_user
        headers = make_basic_auth(email, valid_key)

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 200
        assert resp.json["status"] == "OK"

    def test_05_validate_access_key_without_expiration(
        self, client: FlaskClient, auth_headers
    ):
        """Verify that a key created without expiration remains acceptable.

        This complements the creation-side test by checking the user-facing
        behavior of the validation endpoint, not just the shape of the creation
        response.
        """

        # arrange
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=auth_headers,
            json={"lifetime_seconds": None},
        )
        token = resp.json["key"]
        email = BaseAuthentication.default_user
        headers = make_basic_auth(email, token)

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 200
        assert resp.json["status"] == "OK"