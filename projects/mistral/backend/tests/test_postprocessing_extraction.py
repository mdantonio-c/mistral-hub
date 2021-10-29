import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import dballe
import eccodes
import pytest
from faker import Faker
from flask import Flask
from mistral.endpoints import DOWNLOAD_DIR
from mistral.services.dballe import BeDballe
from mistral.services.sqlapi_db_manager import SqlApiDbManager
from restapi.connectors import sqlalchemy
from restapi.connectors.celery import Ignore
from restapi.tests import API_URI, BaseTests

# Workaround for typing FlaskClient copied by restapi.tests
FlaskClient = Any

TASK_NAME = "data_extract"

alchemy_user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")


class TestApp(BaseTests):
    def check_extraction_success(self, db, request_id, user_dir):
        # check extraction status
        request = db.Request.query.filter_by(id=request_id).first()
        assert request.status == "SUCCESS"
        # check that the fileoutput in db has been created
        out_file = request.fileoutput
        out_filename = out_file.filename
        assert out_file is not None
        # check the fileoutput exists and is not empty
        filepath = Path(user_dir, out_filename)
        assert filepath.exists()
        assert filepath.stat().st_size != 0
        # check there is only a file in the folder and all the temp files has been deleted
        assert len(list(Path(user_dir).glob("*"))) == 1
        return filepath

    def extract_w_postprocessor(
        self,
        faker,
        app,
        db,
        user_id,
        user_dir,
        datasets,
        pp_settings,
        filters={},
        test_failure=False,
        wrong_params={},
        output_format=None,
    ):
        request_name = faker.pystr()
        # try a postprocess that does not exists
        request = SqlApiDbManager.create_request_record(
            db,
            user_id,
            request_name,
            {},
        )
        if test_failure:
            # check the failure
            with pytest.raises(Ignore):
                self.send_task(
                    app,
                    TASK_NAME,
                    user_id,
                    datasets,
                    None,
                    wrong_params,
                    pp_settings,
                    output_format,
                    request.id,
                )
            request = db.Request.query.filter_by(id=request.id).first()
            assert request.status == "FAILURE"
            assert "Error in post-processing" in request.error_message
        # check the success
        self.send_task(
            app,
            TASK_NAME,
            user_id,
            datasets,
            None,
            filters,
            pp_settings,
            output_format,
            request.id,
        )
        request_filepath = self.check_extraction_success(db, request.id, user_dir)

        return request.id, request_filepath

    def check_grib_boundings(self, grib_file, min_lat, nx):
        with open(grib_file) as filein:
            while True:
                gid = eccodes.codes_grib_new_from_file(filein)
                assert (
                    eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees")
                    == min_lat
                )
                assert eccodes.codes_get(gid, "Ni") == nx
                break

    def delete_the_request(self, client, request_id):
        endpoint = API_URI + f"/requests/{request_id}"
        r = client.delete(endpoint, headers=self.get("user_header"))
        assert r.status_code == 200

    def test_postprocessing(
        self, app: Flask, faker: Faker, client: FlaskClient
    ) -> None:
        db = sqlalchemy.get_instance()
        forecast_dataset_name = "lm5"
        forecast_dataset = db.Datasets.query.filter_by(
            name=forecast_dataset_name
        ).first()
        observed_dataset_name = "agrmet"

        # create the user
        data: Dict[str, Any] = {}
        data["disk_quota"] = 1073741824
        data["max_output_size"] = 1073741824
        data["allowed_postprocessing"] = True
        data["open_dataset"] = True
        data["datasets"] = [str(forecast_dataset.id)]
        data["datasets"] = json.dumps(data["datasets"])
        uuid, data = self.create_user(client, data)
        # Will be used to delete the user after the tests
        self.save("user_uuid", uuid)
        user_header, _ = self.do_login(client, data.get("email"), data.get("password"))

        self.save("user_header", user_header)
        # create a request on the db
        user = db.User.query.filter_by(uuid=uuid).first()
        user_id = user.id
        user_dir = Path(DOWNLOAD_DIR, uuid, "outputs")

        # FORECASTS
        # simple forecast extraction
        request_name = faker.pystr()
        simple_request = SqlApiDbManager.create_request_record(
            db,
            user_id,
            request_name,
            {},
        )
        datasets = [forecast_dataset_name]

        self.send_task(
            app, TASK_NAME, user_id, datasets, None, None, [], None, simple_request.id
        )
        self.check_extraction_success(db, simple_request.id, user_dir)
        # delete the request
        self.delete_the_request(client, simple_request.id)

        # try a postprocess that does not exists
        pp1_request = SqlApiDbManager.create_request_record(
            db,
            user_id,
            request_name,
            {},
        )
        with pytest.raises(Ignore, match=r"Unknown post-processor"):
            self.send_task(
                app,
                TASK_NAME,
                user_id,
                datasets,
                None,
                None,
                [{"processor_type": faker.pystr()}],
                None,
                pp1_request.id,
            )
        request = db.Request.query.filter_by(id=pp1_request.id).first()
        assert request.status == "FAILURE"
        # TODO adjust error message in case of value exception
        # assert "Unknown post-processor" in request.error_message

        # try derived variable postprocessor
        derived_variable_pp = {
            "processor_type": "derived_variables",
            "variables": ["B13003"],
        }
        wrong_filters_for_derived_variable = {
            "product": [
                {
                    "s": "GRIB1",
                    "or": 80,
                    "pr": 1,
                    "ta": 2,
                    "desc": "P Pressure Pa",
                    "active": "true",
                }
            ]
        }
        filters = {
            "product": [
                {
                    "desc": "P Pressure Pa",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 1,
                    "active": "true",
                },
                {
                    "desc": "T Temperature K",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 11,
                    "active": "true",
                },
                {
                    "desc": "None Dew-point temperature K",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 17,
                    "active": "true",
                },
                {
                    "desc": "Q Specific humidity kg kg^-1",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 51,
                    "active": "true",
                },
            ]
        }
        dv_request_id, dv_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [derived_variable_pp],
            filters=filters,
            test_failure=True,
            wrong_params=wrong_filters_for_derived_variable,
        )

        # check extracted_grib_file
        dv_exists = False
        other_params_exists = False
        # open the file and search the derived variable in the results
        with open(dv_filepath) as filein:
            while True:
                gid = eccodes.codes_grib_new_from_file(filein)
                if eccodes.codes_get(gid, "shortName") == "relhum_2m":
                    dv_exists = True
                else:
                    other_params_exists = True
                if dv_exists and other_params_exists:
                    break
        assert dv_exists
        assert other_params_exists
        # delete the request
        self.delete_the_request(client, dv_request_id)

        # try statistic elaboration postprocessor
        statistic_elaboration_pp = {
            "processor_type": "statistic_elaboration",
            "input_timerange": 1,
            "output_timerange": 1,
            "interval": "hours",
            "step": 3,
        }
        wrong_filters_for_statistic_elaboration = {
            "product": [
                {
                    "desc": "TP Total precipitation kg m^-2",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 61,
                    "active": "true",
                }
            ],
            "timerange": [
                {
                    "s": "GRIB1",
                    "p1": 0,
                    "p2": 0,
                    "ty": 0,
                    "un": 1,
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - time unit 1",
                    "active": "true",
                }
            ],
        }
        filters = {
            "product": [
                {
                    "desc": "TP Total precipitation kg m^-2",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 61,
                    "active": "true",
                },
                {
                    "desc": "P Pressure Pa",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 1,
                    "active": "true",
                },
            ]
        }
        se_request_id, se_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [statistic_elaboration_pp],
            filters=filters,
            test_failure=True,
            wrong_params=wrong_filters_for_statistic_elaboration,
        )

        # check extracted_grib_file
        se_exists = False
        other_params_exists = False
        # open the file and search the derived variable in the results
        with open(se_filepath) as filein:
            while True:
                gid = eccodes.codes_grib_new_from_file(filein)
                if eccodes.codes_get(gid, "shortName") == "tp":
                    if eccodes.codes_get(gid, "stepRange") == "3-6":
                        se_exists = True
                elif (
                    eccodes.codes_get(gid, "shortName") == "sp"
                ):  # check if other params, like pressure, have been manteined
                    other_params_exists = True
                if se_exists and other_params_exists:
                    break
        assert se_exists and other_params_exists

        # delete the request
        self.delete_the_request(client, se_request_id)

        # try grid interpolation without template
        x_min = -15
        y_min = -10
        nx = faker.pyint(2, 100)
        grid_interpol_pp_no_template = {
            "processor_type": "grid_interpolation",
            "boundings": {
                "x_min": x_min,
                "x_max": 20,
                "y_min": y_min,
                "y_max": 10,
            },
            "nodes": {"nx": nx, "ny": nx},
            "trans_type": "inter",  # in the application this field is added in data.py endpoint
            "sub_type": "bilin",
        }
        filters = {
            "product": [
                {
                    "desc": "P Pressure Pa",
                    "s": "GRIB1",
                    "or": 80,
                    "ta": 2,
                    "pr": 1,
                    "active": "true",
                }
            ]
        }
        gi_request_id, gi_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [grid_interpol_pp_no_template],
            filters=filters,
        )
        # check extracted_grib_file
        self.check_grib_boundings(gi_filepath, y_min, nx)

        # copy the file in the uploads folder since i will use it as template for the grid interpolation postprocess in the next test
        upload_folder = Path(DOWNLOAD_DIR, uuid, "uploads")
        upload_folder.mkdir(parents=True, exist_ok=True)
        template_file = Path(upload_folder, "gi_template.grib")
        shutil.copyfile(gi_filepath, template_file)
        # delete the grid intepolation request without template
        self.delete_the_request(client, gi_request_id)

        # try grid interpolation with template
        grid_interpol_pp_template = {
            "processor_type": "grid_interpolation",
            "template": template_file,
            "trans_type": "inter",  # in the application this field is added in data.py endpoint
            "sub_type": "bilin",
        }
        gi_template_request_id, gi_template_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [grid_interpol_pp_template],
            filters=filters,
        )
        # check extracted_grib_file
        self.check_grib_boundings(gi_template_filepath, y_min, nx)

        # delete the grid intepolation request with template
        self.delete_the_request(client, gi_template_request_id)

        # try grid cropping postprocess
        initial_lon = -10
        initial_lat = -5
        grid_cropping_pp = {
            "processor_type": "grid_cropping",
            "boundings": {
                "ilon": initial_lon,
                "ilat": initial_lat,
                "flon": 10,
                "flat": 5,
            },
            "trans_type": "zoom",  # in the application this field is added in data.py endpoint
            "sub_type": "coord",
        }
        gc_request_id, gc_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [grid_cropping_pp],
            filters=filters,
        )
        # delete the request
        self.delete_the_request(client, gc_request_id)

        # try spare point postprocess
        # unzip the template in the user upload folder
        template_to_unzip = Path("/data/templates_for_pp/template_for_spare_point.zip")
        with zipfile.ZipFile(template_to_unzip, "r") as zip_ref:
            zip_ref.extractall(upload_folder)
        template_for_sp = Path(upload_folder, "template_for_spare_point.shp")
        spare_point_pp = {
            "processor_type": "spare_point_interpolation",
            "coord_filepath": template_for_sp,
            "file_format": "shp",
            "trans_type": "inter",  # in the application this field is added in data.py endpoint
            "sub_type": "bilin",
        }
        sp_request_id, sp_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [spare_point_pp],
            filters=filters,
        )
        # check fileformat for output file
        assert sp_filepath.suffix == ".bufr"
        # delete the request
        self.delete_the_request(client, sp_request_id)

        # check multiple postprocessors : derived variable,statistic,interpolation no template, cropping
        multiple_1_request_id, multiple_1_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [
                derived_variable_pp,
                statistic_elaboration_pp,
                grid_interpol_pp_no_template,
                grid_cropping_pp,
            ],
        )
        # check extracted_grib_file
        dv_exists = False
        se_exists = False
        with open(multiple_1_filepath) as filein:
            while True:
                gid = eccodes.codes_grib_new_from_file(filein)
                try:
                    msg_shortname = eccodes.codes_get(gid, "shortName")
                    if msg_shortname == "tp":
                        if eccodes.codes_get(gid, "stepRange") == "3-6":
                            se_exists = True
                    if msg_shortname == "relhum_2m":
                        dv_exists = True
                    if se_exists and dv_exists:
                        break
                    # check spatial postprocessing
                    assert eccodes.codes_get(gid, "Ni") == nx
                except BaseException:  # i think that when arrives at the end of the file an error is thrown
                    break
        assert dv_exists and se_exists
        # delete the request
        self.delete_the_request(client, multiple_1_request_id)

        # check multiple postprocessors: derived variable,statistic,spare point, output format
        multiple_2_request_id, multiple_2_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [derived_variable_pp, statistic_elaboration_pp, spare_point_pp],
            output_format="json",
        )
        # check that the output file is a json
        assert multiple_2_filepath.suffix == ".json"
        # delete the request
        self.delete_the_request(client, multiple_2_request_id)

        # OBSERVED DATA
        # change the variable LASTDAYS according to the reftime of the data in dballe
        dballe_db = dballe.DB.connect(
            "{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(
                engine=engine, user=alchemy_user, pw=pw, host=host, port=port
            )
        )
        with dballe_db.transaction() as tr:
            for row in tr.query_data({}):
                date_to_dt = (
                    datetime(
                        row["year"],
                        row["month"],
                        row["day"],
                        row["hour"],
                        row["min"],
                    )
                    + timedelta(hours=1)
                )
                date_from_dt = date_to_dt - timedelta(hours=1)
                today = datetime.now()
                last_dballe_date = date_from_dt - timedelta(days=1)
                time_delta = today - last_dballe_date
                BeDballe.LASTDAYS = time_delta.days
                break

        # simple observation extraction
        simple_request = SqlApiDbManager.create_request_record(
            db,
            user_id,
            request_name,
            {},
        )
        datasets = [observed_dataset_name]

        self.send_task(
            app, TASK_NAME, user_id, datasets, None, None, [], None, simple_request.id
        )
        self.check_extraction_success(db, simple_request.id, user_dir)
        # delete the request
        self.delete_the_request(client, simple_request.id)

        # try derived variable postprocessor
        obs_derived_variable_pp = {
            "processor_type": "derived_variables",
            "variables": ["B12103"],
        }
        obs_filters = {
            "product": [
                {
                    "code": "B12101",
                    "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                    "active": "true",
                },
                {"code": "B13003", "desc": "RELATIVE HUMIDITY", "active": "true"},
            ]
        }
        wrong_obs_filters_for_derived_variable = {
            "product": [
                {
                    "code": "B12101",
                    "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                    "active": "true",
                }
            ]
        }

        obs_dv_request_id, obs_dv_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [obs_derived_variable_pp],
            filters=obs_filters,
            test_failure=True,
            wrong_params=wrong_obs_filters_for_derived_variable,
        )
        # delete the request
        self.delete_the_request(client, obs_dv_request_id)

        # try statistic elaboration postprocessor
        obs_statistic_elaboration_pp = {
            "processor_type": "statistic_elaboration",
            "input_timerange": 1,
            "output_timerange": 1,
            "interval": "hours",
            "step": 1,
        }
        wrong_obs_filters_for_statistic_elaboration = {
            "product": [
                {
                    "code": "B12101",
                    "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                    "active": "true",
                }
            ]
        }
        obs_filters = {
            "product": [
                {
                    "code": "B12101",
                    "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                    "active": "true",
                },
                {
                    "code": "B13011",
                    "desc": "TOTAL PRECIPITATION / TOTAL WATER EQUIVALENT",
                    "active": "true",
                },
            ]
        }
        se_obs_request_id, se_obs_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [obs_statistic_elaboration_pp],
            filters=obs_filters,
            test_failure=True,
            wrong_params=wrong_obs_filters_for_statistic_elaboration,
        )
        # delete the request
        self.delete_the_request(client, se_obs_request_id)

        # check multiple postprocessors: derived variable,statistic, output format
        multiple_obs_request_id, multiple_obs_filepath = self.extract_w_postprocessor(
            faker,
            app,
            db,
            user_id,
            user_dir,
            datasets,
            [obs_derived_variable_pp, obs_statistic_elaboration_pp],
            output_format="json",
        )
        # check that the output file is a json
        assert multiple_obs_filepath.suffix == ".json"
        # delete the request
        self.delete_the_request(client, multiple_obs_request_id)

        # delete the user
        admin_headers, _ = self.do_login(client, None, None)
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
        # delete the user folder
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)
        # check folder deletion
        assert not dir_to_delete.exists()
