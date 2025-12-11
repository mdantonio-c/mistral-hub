"""
S3 connector
"""

from typing import Any, Optional

import boto3
from mypy_boto3_s3.client import S3Client
from restapi.connectors import Connector, ExceptionsList
from restapi.env import Env
from restapi.exceptions import ServiceUnavailable
from restapi.utilities.logs import log

APP_MODE = Env.get("APP_MODE", "development")


class S3Ext(Connector):
    client: S3Client

    def __init__(self) -> None:
        super().__init__()

    def connect(self, **kwargs: Any) -> "S3Ext":
        log.debug("Connecting S3...")
        variables = self.variables.copy()
        variables.update(kwargs)

        if (host := variables.get("host")) is None:  # pragma: no cover
            raise ServiceUnavailable("Missing hostname")

        if (key_id := variables.get("key_id")) is None:  # pragma: no cover
            raise ServiceUnavailable("Missing key_id")

        if (access_key := variables.get("access_key")) is None:  # pragma: no cover
            raise ServiceUnavailable("Missing access_key")

        port = variables.get("port", "9000")
        # Set endpoint based on environment mode
        if APP_MODE == "development":
            endpoint = f"http://{host}:{port}"
            verify_ssl = False  # self-signed certs o HTTP
        else:
            endpoint = f"https://{host}:{port}"
            verify_ssl = True  # production: valid cert

        session = boto3.Session(
            aws_access_key_id=key_id,
            aws_secret_access_key=access_key,
            aws_session_token=None,
            botocore_session=None,
            profile_name=None,
        )

        self.client = session.client(
            "s3",
            endpoint_url=endpoint,
            verify=verify_ssl,
        )
        return self

    def is_connected(self) -> bool:
        return not self.disconnected

    def disconnect(self) -> None:
        self.disconnected = True

    @staticmethod
    def get_connection_exception() -> ExceptionsList:
        return None


instance = S3Ext()


def get_instance(
    verification: Optional[int] = None,
    expiration: Optional[int] = None,
    retries: int = 1,
    retry_wait: int = 0,
    **kwargs: str,
) -> "S3Ext":
    return instance.get_instance(
        verification=verification,
        expiration=expiration,
        retries=retries,
        retry_wait=retry_wait,
        **kwargs,
    )
