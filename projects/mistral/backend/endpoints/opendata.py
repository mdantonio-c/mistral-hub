import datetime
import os

from restapi import decorators
from restapi.exceptions import BadRequest, NotFound
from restapi.models import fields
from restapi.rest.definition import EndpointResource
from restapi.utilities.logs import log

OPENDATA_DIR = "/opendata"


class OpendataFileList(EndpointResource):

    labels = ["opendata_filelist"]

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
    def get(self, dataset_name):
        """ Get all the opendata filenames and metadata for that dataset"""
        log.debug("requested for {}", dataset_name)
        # check if the dataset exists
        db = self.get_service_instance("sqlalchemy")
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

        # get the list of the name of files in the opendata folder
        opendata_files = os.listdir(OPENDATA_DIR)

        res = []
        for f in opendata_files:
            # filter the files by requested dataset
            filebase, fileext = os.path.splitext(f)
            file_metadata = filebase.split("_")
            if file_metadata[0] != dataset_name:
                continue
            # create the model for the response
            el = {}
            el["date"] = file_metadata[1]
            el["run"] = file_metadata[2]
            el["filename"] = f
            res.append(el)
        # sort the elements by date
        res.sort(
            key=lambda x: datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            reverse=True,
        )
        return self.response(res)
