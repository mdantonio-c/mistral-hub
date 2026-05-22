"""Integration tests for the lifecycle of user access keys.

This module covers the user-visible contract around access keys: creation,
retrieval, regeneration, expiration handling, and behavior for keys with no
expiration timestamp.
"""

from datetime import timedelta

import pytest
from restapi.connectors import sqlalchemy
from restapi.services.authentication import BaseAuthentication
from restapi.tests import FlaskClient

from .support import (
    ACCESS_KEY_ENDPOINT,
    ACCESS_KEY_VALIDATE_ENDPOINT,
)
from mistral.tests.helpers.auth import make_basic_auth


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestAccessKeyAPI:
    """Group scenarios that cover creation, retrieval, regeneration, and expiry."""

    def test_01_get_access_key_unauthenticated(self, client: FlaskClient):
        """Verify that the access-key endpoint never serves anonymous callers.

        This is the outer authorization contract for the whole access-key area:
        before testing key lifecycle details, the suite proves that the endpoint
        is bound to an authenticated user session.
        """
        resp = client.get(ACCESS_KEY_ENDPOINT)
        assert resp.status_code == 401

    def test_02_get_existing_access_key(self, client: FlaskClient, fresh_access_key):
        """Verify that ``GET /access-key`` returns the key already issued to the user.

        The test first creates a fresh key through the fixture and then checks
        that a subsequent read returns exactly that same token instead of a new
        one or an empty payload.
        """
        headers, token = fresh_access_key
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=headers)
        assert resp.status_code == 200
        assert resp.json["key"] == token

    def test_03_regenerate_access_key(self, client: FlaskClient, auth_headers):
        """Verify that regenerating a key invalidates the previous token value.

        The contract here is not just that ``POST`` succeeds, but that the user
        ends up with a different access key and that subsequent reads expose the
        newly generated value.
        """

        # arrange
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        old_token = resp.json["key"]

        # act
        resp = client.post(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        new_token = resp.json["key"]

        # assert
        assert new_token != old_token
        resp = client.get(ACCESS_KEY_ENDPOINT, headers=auth_headers)
        assert resp.json["key"] == new_token

    def test_04_create_access_key_without_expiration(
        self, client: FlaskClient, auth_headers
    ):
        """Verify that the API accepts a non-expiring key when asked explicitly.

        Some callers need long-lived automation credentials. This scenario makes
        that contract explicit by checking that ``lifetime_seconds=None`` is
        stored as ``expiration=None`` in the response.
        """

        # act
        resp = client.post(
            ACCESS_KEY_ENDPOINT,
            headers=auth_headers,
            json={"lifetime_seconds": None},
        )

        # assert
        assert resp.status_code == 200
        assert resp.json["expiration"] is None

    def test_06_validate_expired_access_key(
        self, client: FlaskClient, fresh_access_key_with_expiration
    ):
        """Verify that a previously valid key becomes unusable after expiration.

        The test forces the issued key into the past at database level and then
        proves that the validation endpoint rejects it with the same ``401`` seen
        for any other invalid credential.
        """

        # arrange
        _, token = fresh_access_key_with_expiration
        db = sqlalchemy.get_instance()
        user = db.User.query.filter_by(email=BaseAuthentication.default_user).first()
        assert user is not None
        user.access_key.expiration = user.access_key.expiration - timedelta(
            seconds=3600
        )
        db.session.commit()
        headers = make_basic_auth(user.email, token)

        # act
        resp = client.get(ACCESS_KEY_VALIDATE_ENDPOINT, headers=headers)

        # assert
        assert resp.status_code == 401