import io
import zipfile
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from flask import send_file, send_from_directory
from marshmallow import ValidationError, pre_load
from mistral.endpoints import OPENDATA_DIR
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import BadRequest, NotFound, ServerError, Unauthorized
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log


class OpendataFileList(EndpointResource):

    labels = ["opendata_filelist"]

    @decorators.auth.optional()
    @decorators.use_kwargs({"q": fields.Str(required=False)}, location="query")
    @decorators.endpoint(
        path="/datasets/<dataset_name>/opendata",
        summary="Get opendata filename and metadata",
        description="Get the list of opendata files for that dataset",
        responses={
            200: "Filelist successfully retrieved",
            401: "Requested dataset is private",
            404: "Requested dataset not found",
        },
    )
    def get(self, user: Optional[User], dataset_name: str, q: str = "") -> Response:
        """Get all the opendata filenames and metadata for that dataset"""
        log.debug("requested for {}", dataset_name)
        # check if the dataset exists
        db = sqlalchemy.get_instance()
        ds_entry = db.Datasets.query.filter_by(name=dataset_name).first()
        if not ds_entry:
            raise NotFound(f"Dataset not found for name: {dataset_name}")
        # check if the dataset is public
        license = db.License.query.filter_by(id=ds_entry.license_id).first()
        group_license = db.GroupLicense.query.filter_by(
            id=license.group_license_id
        ).first()
        if not group_license.is_public:
            # check user authorization
            is_authorized = SqlApiDbManager.check_dataset_authorization(
                db, dataset_name, user
            )
            if not is_authorized:
                raise Unauthorized(f"Dataset {dataset_name} is not public")

        query: Dict[str, Any] = {}
        reftime: Dict[str, date] = {}
        # add dataset to query
        query["datasets"] = [ds_entry.arkimet_id]

        if q:
            # q=reftime: >=2019-06-21 00:00,<=2019-06-22 15:46;run:MINUTE,00:00
            # parse the query
            query_list = q.split(";")
            for e in query_list:
                # add the run param
                if e.startswith("run"):
                    val = e.split("run:")[1]
                    query["filters"] = {
                        "run": [{"desc": "{})".format(val.replace(",", "("))}]
                    }
                # parse the reftime
                if e.startswith("reftime"):
                    val = e.split("reftime:")[1]
                    reftimes = [x.strip() for x in val.split(",")]
                    for ref in reftimes:
                        if ref.startswith(">"):
                            date_min = ref.strip(">=")
                            log.info(date_min)
                            reftime["from"] = datetime.strptime(
                                date_min, "%Y-%m-%d %H:%M"
                            )
                        if ref.startswith("<"):
                            date_max = ref.strip("<=")
                            log.info(date_max)
                            reftime["to"] = datetime.strptime(
                                date_max, "%Y-%m-%d %H:%M"
                            )
                        if ref.startswith("="):
                            ref_date = ref.strip("=")
                            reftime["from"] = reftime["to"] = datetime.strptime(
                                ref_date, "%Y-%m-%d %H:%M"
                            )

        log.debug("opendata query {}", query)
        # get the available opendata requests
        opendata_req = db.Request.query.filter(
            db.Request.args.contains(query), db.Request.opendata.is_(True)
        )

        res = []
        for r in opendata_req:
            # create the model for the response
            el: Dict[str, Optional[str]] = {}
            # get the reftime
            reftime_from = datetime.strptime(
                r.args["reftime"]["from"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            reftime_to = datetime.strptime(
                r.args["reftime"]["to"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            # check if there is a requested reftime
            if reftime:
                if reftime_from < reftime["from"] or reftime_to > reftime["to"]:
                    continue

            if reftime_from == reftime_to:
                ref_date = reftime_from.strftime("%Y-%m-%d")
            else:
                ref_date = "from {} to {}".format(
                    reftime_from.strftime("%Y-%m-%d"), reftime_to.strftime("%Y-%m-%d")
                )
            el["date"] = ref_date
            # get the run
            run = None
            if r.args["filters"] and "run" in r.args["filters"]:
                values = r.args["filters"]["run"]
                if not isinstance(values, list):
                    values = [values]
                parsed_values = []
                for v in values:
                    decoded = arki.decode_run(v)
                    splitted = decoded.split(",")
                    parsed_values.append(splitted[1])
                run = ",".join(parsed_values)
            el["run"] = run
            # get the output filename
            if r.fileoutput is not None:
                el["filename"] = r.fileoutput.filename
                res.append(el)
        # sort the elements by date
        if res:
            res.sort(
                key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d")  # type: ignore
                if "from" not in x["date"]  # type: ignore
                else datetime.strptime(
                    x["date"].split(" ")[1], "%Y-%m-%d"  # type: ignore
                ),
                reverse=True,
            )
        return self.response(res)


class OpendataDownloadFile(EndpointResource):

    labels = ["opendata_download_file"]

    @decorators.auth.optional()
    @decorators.endpoint(
        path="/opendata/<filename>",
        summary="Download the opendata file",
        responses={
            200: "Found the file to download",
            404: "File not found",
        },
    )
    def get(self, user: Optional[User], filename: str) -> Response:
        # check the dataset related to the opendata file
        db = sqlalchemy.get_instance()
        fileoutput_entry = db.FileOutput.query.filter_by(filename=filename).first()
        if not fileoutput_entry:
            raise NotFound("File not found")
        opendata_req_id = fileoutput_entry.request_id
        opendata_req_entry = db.Request.query.get(opendata_req_id)
        if not opendata_req_entry:
            raise ServerError(f"Opendata request related to file {filename} not found")
        datasets_names = opendata_req_entry.args.get("datasets")
        for d in datasets_names:
            is_authorized = SqlApiDbManager.check_dataset_authorization(db, d, user)
            if not is_authorized:
                raise Unauthorized(f"Dataset {d} is not public")

        # TODO check if the opendata is public, if not check if the user can access it
        OPENDATA_DIR.joinpath(filename)
        # check if the requested file exists
        if not OPENDATA_DIR.joinpath(filename).exists():
            raise NotFound("File not found")

        # download the file as a response attachment
        return send_from_directory(OPENDATA_DIR, filename, as_attachment=True)


class Reftime(fields.Date):
    # from string to date using two different supported formats
    def _deserialize(self, value, attr, data, **kwargs):
        if value:
            try:
                # string with format YYYYmmdd are supported
                valid_reftime = datetime.strptime(value, "%Y%m%d").date()
                value = valid_reftime
            except Exception:
                try:
                    # string with format YYYY-mm-dd are supported
                    valid_reftime = datetime.strptime(value, "%Y-%m-%d").date()
                    value = valid_reftime
                except Exception:
                    raise ValidationError(
                        "reftime format not supported. Supported formats are YYYYMMDD or YYYY-mm-dd"
                    )
        return value


class OpenDataDownloadQuery(Schema):
    reftime = Reftime(required=False)
    run = fields.Str(required=False)

    @pre_load
    def validate_run(self, data, **kwargs):
        run = data.get("run", None)
        if run:
            try:
                # check if the string is a valid time
                run_time = datetime.strptime(run, "%H:%M").time()
                log.debug(run_time)
            except Exception:
                raise ValidationError(
                    "run format not supported. Supported format is HH:MM"
                )
        return data


class OpendataDownload(EndpointResource):

    labels = ["opendata_download"]

    @decorators.auth.optional()
    @decorators.use_kwargs(OpenDataDownloadQuery, location="query")
    @decorators.endpoint(
        path="/opendata/<dataset_name>/download",
        summary="Download opendata related to a dataset",
        responses={
            200: "Found files to download",
            404: "No files to download for the requested dataset",
        },
    )
    def get(
        self,
        user: Optional[User],
        dataset_name: str,
        reftime: Optional[date] = None,
        run: Optional[str] = None,
    ) -> Response:
        log.debug(f"request for {dataset_name}, reftime: {reftime}, run: {run}")
        # check if the dataset exists
        db = sqlalchemy.get_instance()
        ds_entry = db.Datasets.query.filter_by(name=dataset_name).first()
        if not ds_entry:
            raise NotFound(f"Dataset not found for name: {dataset_name}")
        # check if the dataset is public
        license = db.License.query.filter_by(id=ds_entry.license_id).first()
        group_license = db.GroupLicense.query.filter_by(
            id=license.group_license_id
        ).first()
        if not group_license.is_public:
            # check user authorization
            is_authorized = SqlApiDbManager.check_dataset_authorization(
                db, dataset_name, user
            )
            if not is_authorized:
                raise Unauthorized(f"Dataset {dataset_name} is not public")

        # create the query for the db
        query: Dict[str, Any] = {}

        query["datasets"] = [ds_entry.arkimet_id]
        if run:
            query["filters"] = {"run": [{"desc": f"MINUTE({run})"}]}

        opendata_req = db.Request.query.filter(
            db.Request.args.contains(query),
            db.Request.opendata.is_(True),
            db.Request.archived.is_(False),
        )
        filenames: Optional[List[str]] = []
        # if no reftime and no run is specified return all the opendata of the specified dataset all zipped
        # if only reftime or only run are specified return all the opendata with the requested reftime or the requested run all zipped
        for r in opendata_req:
            if reftime:
                # check if reftime from and to correspond to the requested reftime
                reftime_from = datetime.strptime(
                    r.args["reftime"]["from"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).date()
                reftime_to = datetime.strptime(
                    r.args["reftime"]["to"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).date()
                if reftime_from == reftime and reftime_to == reftime:
                    filenames.append(r.fileoutput.filename)
            else:
                filenames.append(r.fileoutput.filename)

        if not filenames:
            raise NotFound("No opendata found for the requested query")
        elif len(filenames) == 1:
            # download the single file as a response attachment
            OPENDATA_DIR.joinpath(filenames[0])
            if not OPENDATA_DIR.joinpath(filenames[0]).exists():
                raise NotFound("Requested opendata file not found")
            return send_from_directory(OPENDATA_DIR, filenames[0], as_attachment=True)
        else:
            # create a zipfile in memory containing all the requested opendata and download it as a response attachment
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename in filenames:
                    filepath = OPENDATA_DIR.joinpath(filename)
                    if not filepath.exists():
                        log.warning(f"File {filepath} not found for {filename}")
                        continue
                    zip_file.write(filepath, arcname=filename)
            # restore the pointer to the beginning
            zip_buffer.seek(0)
            zipfile_name = f"opendata_{dataset_name}{f'_reftime_{reftime}'if reftime else ''}{f'_run_{run}'if run else ''}.zip"
            return send_file(
                zip_buffer,
                download_name=zipfile_name,
                as_attachment=True,
                mimetype="application/zip",
            )
