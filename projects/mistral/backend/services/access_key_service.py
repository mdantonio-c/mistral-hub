from datetime import datetime, timezone

from flask import request
from mistral.models.sqlalchemy import AccessKey
from restapi.connectors import sqlalchemy
from restapi.exceptions import Unauthorized
from restapi.utilities.logs import log


def is_access_key_valid(key_record: AccessKey, provided_key: str) -> bool:
    """
    Checks if the provided key is valid.
    :param key_record:  current access key
    :param provided_key:  provided access key
    """

    # key_record must exist
    if not key_record:
        return False

    # Check expiration:
    #    - if expiration is None: key always valid
    #    - if expiration is in the past: key expired
    if key_record.expiration is not None:
        now = datetime.now(timezone.utc)
        if key_record.expiration < now:
            return False

    return key_record.key == provided_key


def access_key_get_by_user(user_email: str) -> AccessKey:
    """
    Returns the AccessKey record associated with this user_email.
    Returns None if user or key not found.
    """
    db = sqlalchemy.get_instance()

    user = db.User.query.filter_by(email=user_email).first()
    if not user:
        log.debug(f"User {user_email} does not exist")
        return None

    access_key = user.access_key
    if not access_key:
        log.debug(f"No access key found for user {user_email}")
        return None

    log.debug(f"Loaded access key metadata for user {user_email}")
    return access_key


def validate_access_key_from_request():
    """
    Validates the BasicAuth credentials from the current Flask request.
    Returns the user record if valid, otherwise raises Unauthorized().
    """
    auth = request.authorization
    if not auth:
        raise Unauthorized("Missing credentials")

    user_email = auth.username
    provided_key = auth.password

    key_record = access_key_get_by_user(user_email)
    if not key_record:
        raise Unauthorized("User or Access Key not found")

    if not is_access_key_valid(key_record, provided_key):
        raise Unauthorized("Invalid access key")

    log.debug(f"Access key for user '{user_email}' authorized")
    return key_record
