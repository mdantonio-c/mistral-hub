import glob
import os
import subprocess
from zipfile import ZipFile

from flask import request
from restapi import decorators
from restapi.confs import UPLOAD_PATH
from restapi.exceptions import RestApiException
from restapi.models import InputSchema, fields, validate
from restapi.rest.definition import EndpointResource
from restapi.services.uploader import Uploader
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log


class TemplatesFormatter(InputSchema):
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
                if format == "grib":
                    counter = len(grib_templates)
                elif format == "shp":
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
            if format == "grib":
                res.append(grib_object)
            elif format == "shp":
                res.append(shp_object)
            else:
                res.append(grib_object)
                res.append(shp_object)

        return self.response(res, code=hcodes.HTTP_OK_BASIC)

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
                if k not in allowed_exts:
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
