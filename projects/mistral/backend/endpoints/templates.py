import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from zipfile import ZipFile

from flask import request
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from osgeo import gdal
from restapi import decorators
from restapi.config import DATA_PATH
from restapi.connectors import sqlalchemy
from restapi.exceptions import (
    BadRequest,
    Forbidden,
    NotFound,
    ServerError,
    Unauthorized,
)
from restapi.models import Schema, fields, validate
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


class TemplatesFormatter(Schema):
    format = fields.Str(validate=validate.OneOf(["grib", "shp"]), required=False)
    perpage = fields.Integer(required=False)
    currentpage = fields.Integer(required=False)
    get_total = fields.Bool(required=False)


class Templates(EndpointResource):
    labels = ["templates"]

    @decorators.auth.require()
    @decorators.use_kwargs(TemplatesFormatter, location="query")
    @decorators.endpoint(
        path="/templates",
        summary="Get templates",
        description="Returns the user templates list",
        responses={200: "List of user templates"},
    )
    # 200: {'schema': {'$ref': '#/definitions/TemplateFile'}}
    def get(
        self,
        user: User,
        format: Optional[str] = None,
        perpage: Optional[int] = None,
        currentpage: Optional[int] = None,
        get_total: bool = False,
    ) -> Response:

        grib_templates = list(
            DATA_PATH.joinpath(user.uuid, "uploads", "grib").glob("*")
        )
        shp_templates = list(
            DATA_PATH.joinpath(user.uuid, "uploads", "shp").glob("*.shp")
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

        res: List[Optional[object]] = []

        grib_object: Dict[str, Any] = {}
        grib_object["type"] = "grib"
        grib_object["files"] = grib_templates
        if max_user_templates and len(grib_templates) >= int(max_user_templates):
            grib_object["max_allowed"] = True
        else:
            grib_object["max_allowed"] = False

        shp_object: Dict[str, Any] = {}
        shp_object["type"] = "shp"
        shp_object["files"] = shp_templates
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


class Template(EndpointResource, Uploader):
    labels = ["templates"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/templates",
        summary="Upload of templates for postprocessors",
        responses={202: "File uploaded", 400: "File cannot be uploaded"},
    )
    # 202: {'schema': {'$ref': '#/definitions/TemplateFile'}}
    def post(self, user: User) -> Response:

        request_file = request.files["file"]
        if not request_file.filename:
            raise ServerError("Unable to upload the template file")

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

        file_extension = Path(request_file.filename).suffix.strip(".")

        # check if the shapefile in the zip folder is complete
        if file_extension == "zip":
            with ZipFile(request_file, "r") as zip:
                uploaded_files = zip.namelist()
                self.check_files_to_upload(
                    DATA_PATH, user.uuid, uploaded_files, allowed_exts
                )
            request.files["file"].seek(0)

        # upload the files
        if file_extension == "grib":
            ext = "grib"
        else:
            ext = "shp"

        subfolder = DATA_PATH.joinpath(user.uuid, "uploads", ext)
        # check the max number of templates the user is allowed to upload
        max_user_templates = SqlApiDbManager.get_user_permissions(
            user, param="templates"
        )
        if max_user_templates:
            if file_extension == "grib":
                template_list = subfolder.glob("*")
            else:
                template_list = subfolder.glob("*.shp")
            if len(list(template_list)) == int(max_user_templates):
                raise Unauthorized(
                    "user has reached the max number of templates of this kind"
                )

        log.debug("uploading in {}", subfolder)
        try:
            upload_response = self.upload(subfolder=subfolder)
            log.debug("upload response: {}", upload_response)
            upload_filename = upload_response[0]["filename"]  # type: ignore
            upload_filepath = subfolder.joinpath(upload_filename)
            log.debug("File uploaded. Filepath : {}", upload_filepath)
        except Exception as error:
            log.error(error)
            # delete all geojson or zip files in the directory in order to clean it
            # geojson and zip files are always deleted if the process doesn't
            # rise an exception. If there are such ind of files in the directory
            # means they were uploaded but the exception was risen
            for i in subfolder.iterdir():
                if i.name.endswith(".zip") or i.name.endswith(".geojson"):
                    i.unlink()
            raise ServerError("Unable to upload the template file")

        # if the file is a zip file extract the content in the upload folder
        if file_extension == "zip":
            zip_files = []
            with ZipFile(upload_filepath, "r") as zip:
                zip_files = zip.namelist()
                log.debug("filelist: {}", zip_files)

                ext = "INVALID_EXT"
                for z in zip_files:
                    if z.endswith("grib"):
                        ext = "grib"
                        break
                    if z.endswith("shp"):
                        ext = "shp"
                        break
                    if z.endswith("geojson"):
                        ext = "shp"
                        break

                zip_upload_path = DATA_PATH.joinpath(user.uuid, "uploads", ext)
                zip.extractall(path=zip_upload_path)
            # remove the zip file
            upload_filepath.unlink()

            for ff in zip_files:
                upload_filepath = zip_upload_path.joinpath(ff)
                ff_ext = Path(ff).suffix.strip(".")
                if ff_ext == "geojson":
                    upload_filepath = self.convert_to_shapefile(upload_filepath)

        # if the file is a geojson convert it to shapefile
        if file_extension == "geojson":
            upload_filepath = self.convert_to_shapefile(upload_filepath)

        # check user quota
        user_dir = DOWNLOAD_DIR.joinpath(user.uuid)
        used_quota = int(subprocess.check_output(["du", "-sb", user_dir]).split()[0])
        # check for exceeding quota
        db = sqlalchemy.get_instance()
        max_user_quota = (
            db.session.query(db.User.disk_quota).filter_by(id=user.id).scalar()
        )
        file_size = upload_filepath.stat().st_size
        if used_quota + file_size > max_user_quota:
            filebase = upload_filepath.stem

            # delete all the files related to the template
            for f in zip_upload_path.parent.glob(f"{filebase}*"):
                f.unlink()

            raise Forbidden("Disk quota exceeded")

        r = {
            "filepath": upload_filepath,
            "format": upload_filepath.suffix.strip("."),
        }
        return self.response(r)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/templates/<template_name>",
        summary="Get a template filepath",
        description="Returns a single template by name",
        responses={200: "Template filepath.", 404: "Template not found"},
    )
    # 200: {'schema': {'$ref': '#/definitions/TemplateFile'}}
    def get(self, template_name: str, user: User) -> Response:

        # get the template extension to determine the folder where to find it
        fileext = Path(template_name).suffix.strip(".")

        filepath = DATA_PATH.joinpath(user.uuid, "uploads", fileext, template_name)
        # check if the template exists
        if filepath.exists():
            raise NotFound("The template doesn't exist")

        res = {
            "filepath": filepath,
            "format": fileext,
        }

        return self.response(res)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/templates/<template_name>",
        summary="Delete a template",
        responses={200: "Template is succesfully deleted", 404: "Template not found"},
    )
    def delete(self, template_name: str, user: User) -> Response:

        # get the template extension to determine the folder where to find it
        template = Path(template_name)
        fileext = template.suffix.strip(".")

        filepath = DATA_PATH.joinpath(user.uuid, "uploads", fileext, template_name)
        if not filepath.exists():
            raise NotFound("The template doesn't exist")

        filebase = template.stem
        for f in filepath.parent.glob(f"{filebase}*"):
            f.unlink()

        return self.response(
            f"File {template_name} succesfully deleted",
        )

    @staticmethod
    def check_files_to_upload(
        DATA_PATH: Path, user_uuid: str, files: List[str], allowed_exts: List[str]
    ) -> None:
        # create a dictionary to compare the uploaded files specs
        file_dict = {}
        for f in files:
            ff = Path(f)
            f_ext = ff.suffix.strip(".")

            # check in the correct folder if the file was already uploaded
            if f_ext == "shp" or f_ext == "geojson":
                ext = "shp"
            elif f_ext == "grib":
                ext = "grib"
            else:
                ext = "INVALID_EXT"

            path = DATA_PATH.joinpath(user_uuid, "uploads", ext, f)
            if path.exists():
                # should be Conflict...
                raise BadRequest(f"File '{f}' already exists")

            file_dict[f_ext] = ff.stem

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
    def convert_to_shapefile(filepath: Path) -> Path:
        output_file = filepath.with_suffix(".shp")
        try:
            gdal.VectorTranslate(
                str(output_file), str(filepath), format="ESRI Shapefile"
            )
            return output_file
        except Exception:
            raise ServerError("Errors in converting the uploaded file")

        finally:
            # remove the source file
            filepath.unlink()
