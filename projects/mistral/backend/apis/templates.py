import glob
import os
import subprocess
from zipfile import ZipFile

from flask import request
from restapi import decorators
from restapi.confs import UPLOAD_PATH
from restapi.exceptions import RestApiException
from restapi.rest.definition import EndpointResource
from restapi.services.uploader import Uploader
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class Templates(EndpointResource, Uploader):
    labels = ["templates"]
    GET = {
        "/templates/<template_name>": {
            "summary": "Get a template filepath",
            "description": "Returns a single template by name",
            "tags": ["templates"],
            "responses": {
                "200": {
                    "description": "template filepath.",
                    "schema": {"$ref": "#/definitions/TemplateFile"},
                },
                "401": {
                    "description": "This endpoint requires a valid authorization token"
                },
                "404": {"description": "template not found"},
            },
            "parameters": [
                {
                    "in": "path",
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "template name",
                },
            ],
        },
        "/templates": {
            "summary": "Get templates",
            "description": "Returns the user templates list",
            "tags": ["templates"],
            "responses": {
                "200": {
                    "description": "List of user templates",
                    "schema": {"$ref": "#/definitions/TemplateList"},
                },
                "401": {
                    "description": "This endpoint requires a valid authorization token"
                },
            },
            "parameters": [
                {
                    "name": "format",
                    "in": "query",
                    "description": "format to filter the templates",
                    "type": "string",
                    "enum": ["grib", "shp"],
                },
                {
                    "name": "perpage",
                    "in": "query",
                    "description": "Number of files returned",
                    "type": "integer",
                },
                {
                    "name": "currentpage",
                    "in": "query",
                    "description": "Page number",
                    "type": "integer",
                },
                {
                    "name": "get_total",
                    "in": "query",
                    "description": "Retrieve total number of templates",
                    "type": "boolean",
                    "default": False,
                },
            ],
        },
    }
    POST = {
        "/templates": {
            "summary": "Upload of templates for postprocessors",
            "consumes": ["multipart/form-data"],
            "parameters": [
                {
                    "name": "file",
                    "in": "formData",
                    "description": "file to upload",
                    "type": "file",
                }
            ],
            "responses": {
                "202": {
                    "description": "file uploaded",
                    "schema": {"$ref": "#/definitions/TemplateFile"},
                },
                "400": {"description": "file cannot be uploaded"},
            },
        }
    }
    DELETE = {
        "/templates/<template_name>": {
            "summary": "delete a template",
            "parameters": [
                {
                    "in": "path",
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "template name",
                }
            ],
            "responses": {
                "200": {"description": "template is succesfully deleted"},
                "404": {"description": "template not found"},
            },
        }
    }

    @decorators.catch_errors()
    @decorators.auth.required()
    def post(self):
        user = self.get_current_user()
        # allowed formats for uploaded file
        allowed_ext = self.allowed_exts = [
            "shp",
            "shx",
            "geojson",
            "dbf",
            "zip",
            "grib",
        ]
        request_file = request.files["file"]
        f = request_file.filename.rsplit(".", 1)

        # check if the shapefile in the zip folder is complete
        if f[-1] == "zip":
            with ZipFile(request_file, "r") as zip:
                uploaded_files = zip.namelist()
                self.check_files_to_upload(
                    UPLOAD_PATH, user.uuid, uploaded_files, allowed_ext
                )
            request.files["file"].seek(0)

        # upload the files
        if f[-1] == "grib":
            subfolder = os.path.join(user.uuid, "uploads", "grib")
        else:
            subfolder = os.path.join(user.uuid, "uploads", "shp")
        log.debug("uploading in {}", subfolder)
        upload_response = self.upload(subfolder=subfolder)

        upload_filename = upload_response.get_json()["filename"]
        upload_filepath = os.path.join(UPLOAD_PATH, subfolder, upload_filename)
        log.debug("File uploaded. Filepath : {}", upload_filepath)

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

        r = {}
        filename = self.split_dir_and_extension(upload_filepath)
        r["filepath"] = upload_filepath
        r["format"] = filename[1]
        return self.response(r)

    @decorators.catch_errors()
    @decorators.auth.required()
    def get(self, template_name=None):
        param = self.get_input()
        format_filter = param.get("format")
        get_total = param.get("get_total", False)
        if not get_total:
            page, limit = self.get_paging()
            # offset = (current_page - 1) * limit
            log.debug("paging: page {0}, limit {1}", page, limit)
        # come uso page e limit? nell'altro endpoint usa un metodo apposta per il db

        user = self.get_current_user()

        if template_name is not None:
            # get the template extension to determine the folder where to find it
            filebase, fileext = os.path.splitext(template_name)

            filepath = os.path.join(
                UPLOAD_PATH, user.uuid, "uploads", fileext.strip("."), template_name
            )
            # check if the template exists
            if not os.path.exists(filepath):
                raise RestApiException(
                    "The template doesn't exist", status_code=hcodes.HTTP_BAD_NOTFOUND
                )
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
                if format_filter == "grib":
                    counter = len(grib_templates)
                elif format_filter == "shp":
                    counter = len(shp_templates)
                else:
                    counter = len(grib_templates) + len(shp_templates)
                return self.response({"total": counter})
            res = []
            grib_object = {}
            grib_object["type"] = "grib"
            grib_object["files"] = []
            for t in grib_templates:
                grib_object["files"].append(t)
            shp_object = {}
            shp_object["type"] = "shp"
            shp_object["files"] = []
            for t in shp_templates:
                shp_object["files"].append(t)
            if format_filter == "grib":
                res.append(grib_object)
            elif format_filter == "shp":
                res.append(shp_object)
            else:
                res.append(grib_object)
                res.append(shp_object)

        return self.response(res, code=hcodes.HTTP_OK_BASIC)

    @decorators.catch_errors()
    @decorators.auth.required()
    def delete(self, template_name):
        user = self.get_current_user()
        # get the template extension to determine the folder where to find it
        filebase, fileext = os.path.splitext(template_name)

        filepath = os.path.join(
            UPLOAD_PATH, user.uuid, "uploads", fileext.strip("."), template_name
        )
        # check if the template exists
        if not os.path.exists(filepath):
            raise RestApiException(
                "The template doesn't exist", status_code=hcodes.HTTP_BAD_NOTFOUND
            )
        # get all the files related to the template to remove
        filelist = glob.glob(
            os.path.join(
                UPLOAD_PATH, user.uuid, "uploads", fileext.strip("."), filebase + "*"
            )
        )
        for f in filelist:
            os.remove(f)
        return self.response(
            f"File {template_name} succesfully deleted", code=hcodes.HTTP_OK_BASIC,
        )

    @staticmethod
    def check_files_to_upload(UPLOAD_PATH, user_uuid, files, allowed_ext):
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
                raise RestApiException(
                    "File '" + f + "' already exists",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )

            file_dict[e[1]] = e[0]
        if "shp" in file_dict:
            # check if there is a file .shx and a file .dbf
            if "shx" not in file_dict:
                raise RestApiException(
                    "file .shx is missing", status_code=hcodes.HTTP_BAD_REQUEST
                )
            if "dbf" not in file_dict:
                raise RestApiException(
                    "file .dbf is missing", status_code=hcodes.HTTP_BAD_REQUEST
                )
            # check if the file .shx and the file .dbf are for the .shp file
            if file_dict["shp"] != file_dict["shx"]:
                raise RestApiException(
                    "file .shx and file .shp does not match",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
            if file_dict["shp"] != file_dict["dbf"]:
                raise RestApiException(
                    "file .dbf and file .shp does not match",
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # if the file is not a shapefile, only grib and geojson are allowed
        else:
            for k in file_dict.keys():
                if k not in allowed_ext:
                    raise RestApiException(
                        "Wrong extension: File extension not allowed",
                        status_code=hcodes.HTTP_BAD_REQUEST,
                    )

    @staticmethod
    def convert_to_shapefile(filepath):
        filebase, fileext = os.path.splitext(filepath)
        output_file = filebase + ".shp"
        cmd = ["ogr2ogr", "-f", "ESRI Shapefile", output_file, filepath]
        try:
            proc = subprocess.Popen(cmd)
            # wait for the process to terminate
            if proc.wait() != 0:
                raise RestApiException(
                    "Errors in converting the uploaded file",
                    status_code=hcodes.HTTP_SERVER_ERROR,
                )
            else:
                return output_file
        finally:
            # remove the source file
            os.remove(filepath)
