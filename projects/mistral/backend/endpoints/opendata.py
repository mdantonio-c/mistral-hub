import datetime
import os
from typing import Any, Dict

from flask import send_from_directory
from mistral.endpoints import OPENDATA_DIR
from mistral.services.arkimet import BeArkimet as arki
from restapi import decorators
from restapi.connectors import sqlalchemy
from restapi.exceptions import BadRequest, NotFound
from restapi.models import fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log


class OpendataFileList(EndpointResource):

    labels = ["opendata_filelist"]

    @decorators.use_kwargs({"q": fields.Str(required=False)}, location="query")
    @decorators.endpoint(
        path="/datasets/<dataset_name>/opendata",
        summary="Get opendata filename and metadata",
        description="Get the list of opendata files for that dataset",
        responses={
            200: "Filelist successfully retrieved",
            400: "Requested dataset is private",
            404: "Requested dataset not found",
        },
    )
    def get(self, dataset_name, q=""):
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
            raise BadRequest(f"Dataset {dataset_name} is not public")

        query: Dict[str, Any] = {}
        reftime = {}
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
                    for r in reftimes:
                        if r.startswith(">"):
                            date_min = r.strip(">=")
                            reftime["from"] = datetime.datetime.strptime(
                                date_min, "%Y-%m-%d %H:%M"
                            ).date()
                        if r.startswith("<"):
                            date_max = r.strip("<=")
                            reftime["to"] = datetime.datetime.strptime(
                                date_max, "%Y-%m-%d %H:%M"
                            ).date()
                        if r.startswith("="):
                            date = r.strip("=")
                            reftime["from"] = reftime[
                                "to"
                            ] = datetime.datetime.strptime(
                                date, "%Y-%m-%d %H:%M"
                            ).date()

        log.debug("opendata query {}", query)
        # get the available opendata requests
        opendata_req = db.Request.query.filter(
            db.Request.args.contains(query), db.Request.opendata is True
        )

        res = []
        for r in opendata_req:
            # create the model for the response
            el = {}
            # get the reftime
            reftime_from = datetime.datetime.strptime(
                r.args["reftime"]["from"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).date()
            reftime_to = datetime.datetime.strptime(
                r.args["reftime"]["to"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).date()
            # check if there is a requested reftime
            if reftime:
                if reftime_from < reftime["from"] or reftime_to > reftime["to"]:
                    continue

            if reftime_from == reftime_to:
                date = reftime_from.strftime("%Y-%m-%d")
            else:
                date = "from {} to {}".format(
                    reftime_from.strftime("%Y-%m-%d"), reftime_to.strftime("%Y-%m-%d")
                )
            el["date"] = date
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
                key=lambda x: datetime.datetime.strptime(x["date"], "%Y-%m-%d")
                if "from" not in x["date"]
                else datetime.datetime.strptime(x["date"].split(" ")[1], "%Y-%m-%d"),
                reverse=True,
            )
        return self.response(res)


class OpendataDownload(EndpointResource):

    labels = ["opendata_download"]

    @decorators.endpoint(
        path="/opendata/<filename>",
        summary="Download the opendata file",
        responses={
            200: "Found the file to download",
            404: "File not found",
        },
    )
    def get(self, filename):
        # check if the requested file exists
        if not os.path.exists(os.path.join(OPENDATA_DIR, filename)):
            raise NotFound("File not found")

        # download the file as a response attachment
        return send_from_directory(OPENDATA_DIR, filename, as_attachment=True)
