import glob
import os
import subprocess
from typing import Any, Dict, List, Optional
from zipfile import ZipFile

from flask import request
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi import decorators
from restapi.config import UPLOAD_PATH
from restapi.connectors import sqlalchemy
from restapi.exceptions import (
    BadRequest,
    Forbidden,
    NotFound,
    ServerError,
    Unauthorized,
)
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


class TemplatesFormatter(Schema):
    format = fields.Str(validate=validate.OneOf(["grib", "shp"]), required=False)
    perpage = fields.Integer(required=False)
    currentpage = fields.Integer(required=False)
    get_total = fields.Bool(required=False)


class Templates(EndpointResource, Uploader):
    labels = ["templates"]

    @staticmethod
    def get_extension(filepath):
        _, fileext = os.path.splitext(filepath)
        return fileext.strip(".")

    @decorators.auth.require()
    @decorators.endpoint(
        path="/templates",
        summary="Upload of templates for postprocessors",
        responses={202: "File uploaded", 400: "File cannot be uploaded"},
    )
    # 202: {'schema': {'$ref': '#/definitions/TemplateFile'}}
    def post(self):
        user = self.get_user()
        # allowed formats for uploaded file
        allowed_exts = [
            "shp",
            "shx",
            "geojson",
            "dbf",
            "zip",
            "grib",
        ]
        self.set_allowed_exts(allowed_exts)
        request_file = request.files["file"]
        f = request_file.filename.rsplit(".", 1)

        # check if the shapefile in the zip folder is complete
        if f[-1] == "zip":
            with ZipFile(request_file, "r") as zip:
                uploaded_files = zip.namelist()
                self.check_files_to_upload(
                    UPLOAD_PATH, user.uuid, uploaded_files, allowed_exts
                )
            request.files["file"].seek(0)

        # upload the files
        if f[-1] == "grib":
            subfolder = os.path.join(user.uuid, "uploads", "grib")
        else:
            subfolder = os.path.join(user.uuid, "uploads", "shp")

        # check the max number of templates the user is allowed to upload
        max_user_templates = SqlApiDbManager.get_user_permissions(
            user, param="templates"
        )
        if max_user_templates:
            if f[-1] == "grib":
                template_list = glob.glob(os.path.join(UPLOAD_PATH, subfolder, "*"))
            else:
                template_list = glob.glob(os.path.join(UPLOAD_PATH, subfolder, "*.shp"))
            if len(template_list) == int(max_user_templates):
                raise Unauthorized(
                    "user has reached the max number of templates of this kind"
                )

        log.debug("uploading in {}", subfolder)
        try:
            upload_res = self.upload(subfolder=subfolder)
            if type(upload_res) == tuple:
                upload_response = upload_res[0]
            else:
                upload_response = upload_res
            log.debug("upload response: {}", upload_response)
            upload_filename = upload_response["filename"]
            upload_filepath = os.path.join(UPLOAD_PATH, subfolder, upload_filename)
            log.debug("File uploaded. Filepath : {}", upload_filepath)
        except Exception as error:
            log.error(error)
            # delete all geojson or zip files in the directory in order to clean it
            # geojson and zip files are always deleted if the process doesn't
            # rise an exception. If there are such ind of files in the directory
            # means they were uploaded but the exception was risen
            subfolder_path = os.path.join(UPLOAD_PATH, subfolder)
            for i in os.listdir(subfolder_path):
                if i.endswith(".zip") or i.endswith(".geojson"):
                    file_to_remove = os.path.join(UPLOAD_PATH, subfolder, i)
                    os.remove(file_to_remove)
            raise ServerError("Unable to upload the template file")

        # if the file is a zip file extract the content in the upload folder
        if f[-1] == "zip":
            files = []
            with ZipFile(upload_filepath, "r") as zip:
                files = zip.namelist()
                log.debug("filelist: {}", files)
                if any(i.endswith("shp") for i in files) or any(
                    i.endswith("geojson") for i in files
                ):
                    subfolder = os.path.join(user.uuid, "uploads", "shp")
                if any(i.endswith("grib") for i in files):
                    subfolder = os.path.join(user.uuid, "uploads", "grib")
                zip_upload_path = os.path.join(UPLOAD_PATH, subfolder)
                zip.extractall(path=zip_upload_path)
            # remove the zip file
            os.remove(upload_filepath)
            # get .shp file filename
            for f in files:
                e = f.rsplit(".", 1)
                if e[-1] == "shp" or e[-1] == "grib":
                    upload_filepath = os.path.join(UPLOAD_PATH, subfolder, f)
                if e[-1] == "geojson":
                    upload_filepath = os.path.join(UPLOAD_PATH, subfolder, f)
                    upload_filepath = self.convert_to_shapefile(upload_filepath)

        # if the file is a geojson convert it to shapefile
        if f[-1] == "geojson":
            upload_filepath = self.convert_to_shapefile(upload_filepath)

        # check user quota
        user_dir = os.path.join(
            DOWNLOAD_DIR,
            user.uuid,
        )
        used_quota = int(subprocess.check_output(["du", "-sb", user_dir]).split()[0])
        # check for exceeding quota
        db = sqlalchemy.get_instance()
        max_user_quota = (
            db.session.query(db.User.disk_quota).filter_by(id=user.id).scalar()
        )
        file_size = os.path.getsize(upload_filepath)
        if used_quota + file_size > max_user_quota:
            filebase, fileext = os.path.splitext(upload_filepath)
            # delete all the files related to the template
            filelist = glob.glob(
                os.path.join(
                    UPLOAD_PATH,
                    user.uuid,
                    "uploads",
                    fileext.strip("."),
                    filebase + "*",
                )
            )
            for f in filelist:
                os.remove(f)
            raise Forbidden("Disk quota exceeded")

        r = {
            "filepath": upload_filepath,
            "format": self.get_extension(upload_filepath),
        }
        return self.response(r)

    @decorators.auth.require()
    @decorators.use_kwargs(TemplatesFormatter, location="query")
    @decorators.endpoint(
        path="/templates/<template_name>",
        summary="Get a template filepath",
        description="Returns a single template by name",
        responses={200: "Template filepath.", 404: "Template not found"},
    )
    @decorators.endpoint(
        path="/templates",
        summary="Get templates",
        description="Returns the user templates list",
        responses={200: "List of user templates"},
    )
    # 200: {'schema': {'$ref': '#/definitions/TemplateFile'}}
    def get(
        self,
        template_name=None,
        format=None,
        perpage=None,
        currentpage=None,
        get_total=False,
    ):
        user = self.get_user()

        if template_name is not None:
            # get the template extension to determine the folder where to find it
            filebase, fileext = os.path.splitext(template_name)

            filepath = os.path.join(
                UPLOAD_PATH, user.uuid, "uploads", fileext.strip("."), template_name
            )
            # check if the template exists
            if not os.path.exists(filepath):
                raise NotFound("The template doesn't exist")
            res = {}
            res["filepath"] = filepath
            res["format"] = fileext.strip(".")
        else:
            grib_templates = glob.glob(
                os.path.join(UPLOAD_PATH, user.uuid, "uploads", "grib", "*")
            )
            shp_templates = glob.glob(
                os.path.join(UPLOAD_PATH, user.uuid, "uploads", "shp", "*.shp")
            )
            # get total count for user templates
            if get_total:
                if format == "grib":
                    counter = len(grib_templates)
                elif format == "shp":
                    counter = len(shp_templates)
                else:
                    counter = len(grib_templates) + len(shp_templates)
                return self.response({"total": counter})

            # get max number of templates the user can upload
            max_user_templates = SqlApiDbManager.get_user_permissions(
                user, param="templates"
            )

            res: Optional[List[object]] = []
            grib_object: Optional[Dict[str, Any]] = {}
            grib_object["type"] = "grib"
            grib_object["files"] = []
            for t in grib_templates:
                grib_object["files"].append(t)
            if max_user_templates and len(grib_templates) >= int(max_user_templates):
                grib_object["max_allowed"] = True
            else:
                grib_object["max_allowed"] = False
            shp_object: Optional[Dict[str, Any]] = {}
            shp_object["type"] = "shp"
            shp_object["files"] = []
            for t in shp_templates:
                shp_object["files"].append(t)
            if max_user_templates and len(shp_templates) >= int(max_user_templates):
                shp_object["max_allowed"] = True
            else:
                shp_object["max_allowed"] = False
            if format == "grib":
                res.append(grib_object)
            elif format == "shp":
                res.append(shp_object)
            else:
                res.append(grib_object)
                res.append(shp_object)

        return self.response(res)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/templates/<template_name>",
        summary="Delete a template",
        responses={200: "Template is succesfully deleted", 404: "Template not found"},
    )
    def delete(self, template_name):
        user = self.get_user()
        # get the template extension to determine the folder where to find it
        filebase, fileext = os.path.splitext(template_name)

        filepath = os.path.join(
            UPLOAD_PATH, user.uuid, "uploads", fileext.strip("."), template_name
        )
        # check if the template exists
        if not os.path.exists(filepath):
            raise NotFound("The template doesn't exist")
        # get all the files related to the template to remove
        filelist = glob.glob(
            os.path.join(
                UPLOAD_PATH, user.uuid, "uploads", fileext.strip("."), filebase + "*"
            )
        )
        for f in filelist:
            os.remove(f)
        return self.response(
            f"File {template_name} succesfully deleted",
        )

    @staticmethod
    def check_files_to_upload(UPLOAD_PATH, user_uuid, files, allowed_exts):
        # create a dictionary to compare the uploaded files specs
        file_dict = {}
        for f in files:
            e = f.rsplit(".", 1)
            # check in the correct folder if the file was already uploaded
            subfolder = ""
            if e[-1] == "shp" or e[-1] == "geojson":
                subfolder = os.path.join(user_uuid, "uploads", "shp")
            if e[-1] == "grib":
                subfolder = os.path.join(user_uuid, "uploads", "grib")
            if os.path.exists(os.path.join(UPLOAD_PATH, subfolder, f)):
                # should be Conflict...
                raise BadRequest(f"File '{f}' already exists")

            file_dict[e[1]] = e[0]
        if "shp" in file_dict:
            # check if there is a file .shx and a file .dbf
            if "shx" not in file_dict:
                raise BadRequest("file .shx is missing")
            if "dbf" not in file_dict:
                raise BadRequest("file .dbf is missing")
            # check if the file .shx and the file .dbf are for the .shp file
            if file_dict["shp"] != file_dict["shx"]:
                raise BadRequest("file .shx and file .shp does not match")
            if file_dict["shp"] != file_dict["dbf"]:
                raise BadRequest("file .dbf and file .shp does not match")
        # if the file is not a shapefile, only grib and geojson are allowed
        else:
            for k in file_dict.keys():
                if k not in allowed_exts:
                    raise BadRequest("Wrong extension: File extension not allowed")

    @staticmethod
    def convert_to_shapefile(filepath):
        filebase, fileext = os.path.splitext(filepath)
        output_file = filebase + ".shp"
        cmd = ["ogr2ogr", "-f", "ESRI Shapefile", output_file, filepath]
        try:
            proc = subprocess.Popen(cmd)
            # wait for the process to terminate
            if proc.wait() != 0:
                raise ServerError("Errors in converting the uploaded file")
            else:
                return output_file
        finally:
            # remove the source file
            os.remove(filepath)
