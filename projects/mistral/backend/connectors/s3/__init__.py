"""
S3 connector
"""

from typing import Any, Optional

import boto3
from botocore.config import Config
from mypy_boto3_s3.client import S3Client
from restapi.connectors import Connector, ExceptionsList
from restapi.env import Env
from restapi.exceptions import ServiceUnavailable
from restapi.utilities.logs import log

APP_MODE = Env.get("APP_MODE", "development")


class S3Ext(Connector):
    client: Optional[S3Client]

    def __init__(self) -> None:
        super().__init__()
        self.client = None

    def connect(self, **kwargs: Any) -> "S3Ext":
        log.debug("Connecting S3...")
        variables = self.variables.copy()
        variables.update(kwargs)

        required = ("host", "key_id", "access_key")
        missing = [k for k in required if not variables.get(k)]
        if missing:
            raise ServiceUnavailable(f"Missing parameters: {', '.join(missing)}")

        host = variables["host"]
        key_id = variables["key_id"]
        access_key = variables["access_key"]

        endpoint = variables.get("endpoint") or None
        if endpoint is None:
            port = variables.get("port", 9000)
            scheme = variables.get("scheme", "https")
            endpoint = f"{scheme}://{host}:{port}"
        log.debug(f"S3 endpoint: {endpoint}")

        verify_ssl = Env.to_bool(
            variables.get("verify_ssl"),
            default=APP_MODE != "development",
        )
        log.debug(f"Verify SSL: {verify_ssl}")

        session = boto3.Session(
            aws_access_key_id=key_id,
            aws_secret_access_key=access_key,
        )

        config = Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=5,
            read_timeout=60,
        )

        self.client = session.client(
            "s3",
            endpoint_url=endpoint,
            verify=verify_ssl,
            config=config,
        )

        try:
            self.client.list_buckets()
        except Exception as exc:
            raise ServiceUnavailable("Unable to connect to S3") from exc

        return self

    def is_connected(self) -> bool:
        if self.disconnected or not hasattr(self, "client"):
            return False
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        self.client = None  # type: ignore
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
