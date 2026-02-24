import json
from mimetypes import MimeTypes
from pathlib import Path
from typing import Optional

import botocore
from flask import Response, jsonify
from mistral.connectors import s3
from mistral.endpoints.schemas import DatasetSchema
from mistral.services.access_key_service import validate_access_key_from_request
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import NotFound, Unauthorized
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log

BUCKET_NAME = "arco"
UNKNOWN = "UNKNOWN"


def guess_mime_type(path: str) -> Optional[str]:
    # guess_type expects a str as argument because
    # it is intended to be used with urls and not with paths
    mime_type = MimeTypes().guess_type(str(path))
    return mime_type[0]


class ArcoResource(EndpointResource):
    labels = ["arco"]

    @decorators.endpoint(
        path="/arco/<path:object_path>",
        summary="Access ARCO datasets",
        responses={200: "Data retrieved", 404: "Data not found"},
    )
    def get(self, object_path: str) -> Response:
        log.debug(f"Accessing ARCO dataset: {object_path}")

        # 1. Validate access key via Basic Auth
        authorized = validate_access_key_from_request()
        if not authorized:
            raise Unauthorized()

        # 2. Fetch S3 object
        try:
            conn = s3.get_instance()
            s3_object = conn.client.get_object(Bucket=BUCKET_NAME, Key=object_path)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise NotFound(f"The object '{object_path}' does not exist.") from e
            else:
                raise Exception from e

        # 3. return S3 data as HTTP response
        data = s3_object["Body"].read()
        filename = Path(object_path).name
        log.debug(f"Accessing ARCO dataset: {filename}")
        mime = guess_mime_type(filename)
        log.debug(f"Guessed mime type: {mime}")
        return Response(data, mimetype=mime)


class ArcoDatasetsResource(EndpointResource):
    labels = ["arco"]

    @decorators.marshal_with(DatasetSchema(many=True), code=200)
    @decorators.endpoint(
        path="/arco/datasets",
        summary="List ARCO datasets",
        responses={200: "Datasets retrieved"},
    )
    def get(self) -> Response:
        log.debug("Listing ARCO datasets")
        datasets = {}

        db = sqlalchemy.get_instance()

        attribution_by_name = {a.name: a for a in db.Attribution.query.all()}

        license_by_name = {lic.name: lic for lic in db.License.query.all()}

        conn = None
        try:
            conn = s3.get_instance()
            client = conn.client

            continuation_token = None
            while True:
                list_kwargs = {
                    "Bucket": BUCKET_NAME,
                    "Delimiter": "/",
                }
                if continuation_token:
                    list_kwargs["ContinuationToken"] = continuation_token

                response = client.list_objects_v2(**list_kwargs)

                # loop ONLY on first level prefixes
                for cp in response.get("CommonPrefixes", []):
                    prefix = cp["Prefix"]
                    if not prefix.endswith(".zarr/"):
                        continue

                    root = prefix.rstrip("/")

                    # Default Dataset structure
                    dataset = {
                        "id": root.replace(".zarr", ""),
                        "name": root.replace(".zarr", ""),
                        "category": "unknown",  # placeholder
                        "format": "zarr",
                        "source": "arco",
                        "is_public": True,
                        "authorized": True,
                    }

                    # Direct read .zmetadata
                    try:
                        zmetadata_key = f"{root}/.zmetadata"
                        raw = (
                            client.get_object(Bucket=BUCKET_NAME, Key=zmetadata_key)[
                                "Body"
                            ]
                            .read()
                            .decode("utf-8")
                        )
                        meta = json.loads(raw).get("metadata", {})
                        zattrs = meta.get(".zattrs")

                        # load bounding box
                        southern = zattrs.get("southernmost_latitude")
                        northern = zattrs.get("northernmost_latitude")
                        western = zattrs.get("westernmost_longitude")
                        eastern = zattrs.get("easternmost_longitude")

                        if all(
                            coord is not None
                            for coord in [southern, northern, western, eastern]
                        ):
                            # Creation of POLYGON WKT
                            polygon_wkt = (
                                f"POLYGON(("
                                f"{western} {southern}, "
                                f"{eastern} {southern}, "
                                f"{eastern} {northern}, "
                                f"{western} {northern}, "
                                f"{western} {southern}"
                                f"))"
                            )
                            dataset["bounding"] = polygon_wkt
                        else:
                            log.warning(
                                f"Missing bounding coordinates in .zattrs for {root}"
                            )

                        # Extract specific fields from zattrs
                        dataset["name"] = zattrs.get("product_name", dataset["name"])
                        dataset["description"] = zattrs.get("description")
                        dataset["category"] = zattrs.get(
                            "category", dataset["category"]
                        )
                        # --------------------
                        # Attribution
                        # --------------------
                        attr_name = zattrs.get("attribution")
                        if attr_name is None or attr_name.strip() == "":
                            dataset["attribution"] = UNKNOWN
                        else:
                            dataset["attribution"] = attr_name

                            attr_row = attribution_by_name.get(attr_name)
                            if attr_row:  # safe
                                dataset["attribution_description"] = attr_row.descr
                                dataset["attribution_url"] = attr_row.url
                            else:
                                log.warning(
                                    f"Unknown attribution {attr_name} for dataset {dataset['id']}"
                                )

                        # --------------------
                        # License
                        # --------------------
                        license_name = zattrs.get("license")

                        if not license_name:
                            dataset["license"] = UNKNOWN
                        else:
                            dataset["license"] = license_name

                            lic_row = license_by_name.get(license_name)
                            if lic_row:
                                dataset["license_description"] = lic_row.descr
                                dataset["license_url"] = lic_row.url

                                if lic_row.group_license:
                                    dataset[
                                        "group_license"
                                    ] = lic_row.group_license.name
                                    dataset[
                                        "group_license_description"
                                    ] = lic_row.group_license.descr
                            else:
                                log.warning(
                                    f"Unknown license {license_name} for dataset {dataset['id']}"
                                )

                        dataset["is_public"] = zattrs.get("is_public", True)
                        dataset["authorized"] = zattrs.get("authorized", True)

                    except client.exceptions.NoSuchKey:
                        log.warning(f"No .zmetadata found for {root}")
                    except Exception as e:
                        log.error(f"Error reading .zmetadata for {root}: {e}")

                    datasets[root] = dataset

                # Check if there are other prefixes to paginate
                if response.get("IsTruncated"):
                    continuation_token = response.get("NextContinuationToken")
                else:
                    break

        except botocore.exceptions.ClientError as e:
            log.error(f"Error accessing S3 Host<{conn.variables['host']}>: {e}")
            raise

        return self.response(datasets.values())
