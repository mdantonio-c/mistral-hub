# -*- coding: utf-8 -*-

from flask import request
from restapi.rest.definition import EndpointResource
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.services.uploader import Uploader
from restapi.confs import UPLOAD_FOLDER
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import get_logger

import os
import subprocess
from zipfile import ZipFile

log = get_logger(__name__)


class Templates(EndpointResource, Uploader):
    # schema_expose = True
    labels = ['templates']
    POST = {
        '/templates': {
            'summary': 'Upload of templates for postprocessors',
            'consumes': ['multipart/form-data'],
            'parameters': [
                {
                    'name': 'file',
                    'in': 'formData',
                    'description': 'file to upload',
                    'type': 'file'
                }
            ],
            'responses': {
                '202': {
                    'description': 'file uploaded',
                    'schema': {'$ref': '#/definitions/TemplateFile'}
                },
                '400': {
                    'description': 'file cannot be uploaded'
                }
            },
        }
    }

    @catch_error()
    @authentication.required()
    def post(self):
        user = self.get_current_user()
        # allowed formats for uploaded file
        self.allowed_exts = ['shp', 'shx', 'geojson','dbf', 'zip', 'grib']
        request_file = request.files['file']
        f = request_file.filename.rsplit(".", 1)

        # check if the shapefile in the zip folder is complete
        if f[-1]== 'zip':
            with ZipFile(request_file, 'r') as zip:
                uploaded_files = zip.namelist()
                self.check_files_to_upload(UPLOAD_FOLDER,user.uuid,uploaded_files)
            request.files['file'].seek(0)

        # upload the files
        if f[-1]== 'grib':
            subfolder= os.path.join(user.uuid,'grib')
        else:
            subfolder=user.uuid
        upload_response = self.upload(subfolder=subfolder)

        if not upload_response.defined_content:
            # raise RestApiException(
            #     '{}'.format(next(iter(upload_response.errors))),
            #     status_code=hcodes.HTTP_BAD_REQUEST,
            # )
            raise RestApiException(
                 upload_response.errors,
                status_code=hcodes.HTTP_BAD_REQUEST,
            )

        upload_filename = upload_response.defined_content['filename']
        upload_filepath = os.path.join(UPLOAD_FOLDER, subfolder, upload_filename)
        log.debug('File uploaded. Filepath : {}'.format(upload_filepath))

        # if the file is a zip file extract the content in the upload folder
        if f[-1] == 'zip':
            files = []
            with ZipFile(upload_filepath, 'r') as zip:
                files = zip.namelist()
                log.debug('filelist: {}'.format(files))
                if any(i.endswith('shp') for i in files) or any(i.endswith('geojson') for i in files):
                    subfolder= os.path.join(user.uuid,'shp')
                if any(i.endswith('grib') for i in files):
                    subfolder = os.path.join(user.uuid, 'grib')
                upload_folder = os.path.join(UPLOAD_FOLDER,subfolder)
                zip.extractall(path=upload_folder)
            # remove the zip file
            os.remove(upload_filepath)
            # get .shp file filename
            for f in files:
                e = f.rsplit(".", 1)
                if e[-1]=='shp' or e[-1]=='grib':
                    upload_filepath = os.path.join(UPLOAD_FOLDER, subfolder, f)
                if e[-1] == 'geojson':
                    upload_filepath = os.path.join(UPLOAD_FOLDER, subfolder, f)
                    upload_filepath = self.convert_to_shapefile(upload_filepath)

        # if the file is a geojson convert it to shapefile
        if f[-1] == 'geojson':
            upload_filepath = self.convert_to_shapefile(upload_filepath)

        r = {}
        filename = self.split_dir_and_extension(upload_filepath)
        r['filepath'] = upload_filepath
        r['format'] = filename[1]
        return self.force_response(r)

    @staticmethod
    def check_files_to_upload(UPLOAD_FOLDER,user_uuid,files):
        # create a dictionary to compare the uploaded files specs
        file_dict = {}
        for f in files:
            e = f.rsplit(".", 1)

            # check in the correct folder if the file was already uploaded
            subfolder=''
            if e[-1]=='shp' or e[-1]=='geojson':
                subfolder = os.path.join(user_uuid, 'shp')
            if e[-1]=='grib':
                subfolder = os.path.join(user_uuid, 'grib')
            if os.path.exists(os.path.join(UPLOAD_FOLDER,subfolder,f)):
                raise RestApiException("File '" + f + "' already exists",
                                       status_code=hcodes.HTTP_BAD_REQUEST)

            file_dict[e[1]] = e[0]
        if 'shp' in file_dict:
            # check if there is a file .shx and a file .dbf
            if 'shx' not in file_dict:
                raise RestApiException('file .shx is missing',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
            if 'dbf' not in file_dict:
                raise RestApiException('file .dbf is missing',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
            # check if the file .shx and the file .dbf are for the .shp file
            if file_dict['shp'] != file_dict['shx']:
                raise RestApiException('file .shx and file .shp does not match',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
            if file_dict['shp'] != file_dict['dbf']:
                raise RestApiException('file .dbf and file .shp does not match',
                                       status_code=hcodes.HTTP_BAD_REQUEST)

    @staticmethod
    def convert_to_shapefile(filepath):
        filebase, fileext = os.path.splitext(filepath)
        output_file = filebase+'.shp'
        cmd = ['ogr2ogr','-f', "ESRI Shapefile",output_file,filepath]
        try:
            proc = subprocess.Popen(cmd)
            # wait for the process to terminate
            if proc.wait() != 0:
                raise RestApiException('Errors in converting the uploaded file',
                                       status_code=hcodes.HTTP_SERVER_ERROR)
            else:
                return output_file
        finally:
            # remove the source file
            os.remove(filepath)

