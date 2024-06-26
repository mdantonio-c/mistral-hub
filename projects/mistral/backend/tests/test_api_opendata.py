import io
import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from zipfile import ZipFile

from faker import Faker
from mistral.endpoints import DOWNLOAD_DIR, OPENDATA_DIR
from restapi.connectors import sqlalchemy
from restapi.services.authentication import BaseAuthentication
from restapi.tests import API_URI, BaseTests, FlaskClient

__author__ = "Mattia Carello (m.carello@cineca.it)"


class TestApp(BaseTests):
    DATASET_FOR_TEST_NAME = "lm5"

    @staticmethod
    def delete_all_schedules_requests_orphan_files(db):
        requests_list = db.Request.query.all()
        for row in requests_list:
            request = db.Request.query.get(row.id)
            if request.fileoutput:
                db.session.delete(request.fileoutput)
            db.session.delete(request)
        schedule_list = db.Schedule.query.all()
        for row in schedule_list:
            schedule = db.Schedule.query.get(row.id)
            db.session.delete(schedule)
        db.session.commit()
        for dir in DOWNLOAD_DIR.iterdir():
            if dir.is_dir():
                user_dir = dir.joinpath("outputs")
                if user_dir.exists():
                    for f in user_dir.iterdir():
                        if f.is_file():
                            file_object = db.FileOutput.query.filter_by(
                                filename=f.name
                            ).first()
                            if not file_object:
                                f.unlink()
                                continue

    # check if a dataset does not exist
    def test_check_wrong_dataset_name(self, client: FlaskClient, faker: Faker):
        # fake name
        dataset_name = faker.name()
        db = sqlalchemy.get_instance()
        # get fake entry
        ds_entry = db.Datasets.query.filter_by(name=dataset_name).first()
        assert ds_entry is None
        # check the opendata api
        endpoint = f"{API_URI}/datasets/{dataset_name}/opendata"
        r = client.get(endpoint)
        assert r.status_code == 404
        # check the opendata download api
        endpoint = f"{API_URI}/opendata/{dataset_name}/download"
        r = client.get(endpoint)
        assert r.status_code == 404

    # check if a license is private
    def test_check_not_public_license(self, client: FlaskClient, faker: Faker):
        # get admin token
        admin_headers, _ = BaseTests.do_login(client, None, None)
        # create a new not open license group
        body = {"name": faker.name(), "descr": faker.name(), "is_public": "false"}
        body = json.dumps(body)

        # create an admin_root user
        db = sqlalchemy.get_instance()
        forecast_dataset = db.Datasets.query.filter_by(
            name=self.DATASET_FOR_TEST_NAME
        ).first()
        data: Dict[str, Any] = {}
        data["disk_quota"] = 1073741824
        data["max_output_size"] = 1073741824
        data["allowed_postprocessing"] = True
        data["open_dataset"] = True
        data["datasets"] = [str(forecast_dataset.id)]
        data["datasets"] = json.dumps(data["datasets"])
        uuid, data = self.create_user(client, data, ["admin_root"])
        # Will be used to delete the user after the tests
        self.save("user_uuid", uuid)
        user_header, _ = self.do_login(client, data.get("email"), data.get("password"))
        self.save("user_header", user_header)
        # create a request on the db
        user_dir = Path(DOWNLOAD_DIR, uuid, "outputs")

        # create the licensegroups
        endpoint = API_URI + "/admin/licensegroups"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 200
        id_license_group = self.get_content(r)
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response_data = self.get_content(r)
        for i in response_data:
            if i["id"] == id_license_group:
                assert i["is_open"] == "false"
        # create a not open license belonging to the previous group
        body = {
            "name": faker.name(),
            "descr": faker.pystr(),
            "group_license": str(id_license_group),
        }
        body = json.dumps(body)
        endpoint = API_URI + "/admin/licenses"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 200
        id_license = self.get_content(r)
        # create a not public dataset
        fake_name = faker.name()
        body = {
            "arkimet_id": fake_name,
            "name": fake_name,
            "description": "dataset_fake not public",
            "category": "OBS",
            "fileformat": "bufr",
            "license": str(id_license),
            "attribution": "18",
            "bounding": "POLYGON ((-17.5374014843514558 25.8214118125177627, -29.6618577019240988 49.1185603319763260, -18.1123487722656762 52.2082915170863942, -5.2841914142956252 54.2586288297216370, 8.3858281354571460 55.0739215029660087, 22.1519686504923001 54.5643432849449539, 35.2289961673372574 52.7869189178025664, 47.0956192803686022 49.9188746081732049, 47.1122744703592744 49.8885465483880779, 35.6138690063754808 26.3910672255853775, -17.5374014843514558 25.8214118125177627))",
        }
        body = json.dumps(body)
        endpoint = API_URI + "/admin/datasets"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 200
        dataset_id = self.get_content(r)
        # test if dataset is not public
        db = sqlalchemy.get_instance()
        ds_entry = db.Datasets.query.filter_by(name=fake_name).first()
        license = db.License.query.filter_by(id=ds_entry.license_id).first()
        group_license = db.GroupLicense.query.filter_by(
            id=license.group_license_id
        ).first()
        assert not group_license.is_public

        # check that opendata are not available for that dataset for unauthenticated users
        opendata_list_endpoint = f"{API_URI}/datasets/{fake_name}/opendata"
        r = client.get(opendata_list_endpoint)
        assert r.status_code == 401
        # check for unauthorized users
        r = client.get(opendata_list_endpoint, headers=user_header)
        assert r.status_code == 401

        # check the opendata download api for unauthenticated users
        opendata_download_endpoint = f"{API_URI}/opendata/{fake_name}/download"
        r = client.get(opendata_download_endpoint)
        assert r.status_code == 401
        # check for unauthorized users
        r = client.get(opendata_download_endpoint, headers=user_header)
        assert r.status_code == 401

        # create an opendata request in db
        # get admin user id
        admin_username = BaseAuthentication.load_default_user()
        if not admin_username:
            admin_username = BaseAuthentication.default_user
        db = sqlalchemy.get_instance()
        user = db.User.query.filter_by(email=admin_username).first()
        request_owner_id = user.id
        args = {
            "filters": None,
            "reftime": {
                "from": (datetime.now() - timedelta(hours=1)).strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                ),
                "to": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
            "datasets": [fake_name],
        }
        file_content = f"Dataset-{fake_name}_content"
        requests_to_delete = []
        self.save("request_to_delete_list", requests_to_delete)
        filename = self.create_fake_opendata_result(
            request_owner_id, args, file_content
        )
        # check download for file related to a not public dataset for unauthenticated users
        download_endpoint = f"{API_URI}/opendata/{filename}"
        r = client.get(download_endpoint)
        assert r.status_code == 401
        # check download for file related to a not public dataset for unauthorized users
        r = client.get(download_endpoint, headers=user_header)
        assert r.status_code == 401

        # authorize the user to the private dataset
        user_entry = db.User.query.filter_by(uuid=uuid).first()
        fake_dataset = db.Datasets.query.filter_by(name=fake_name).first()
        user_entry.datasets.append(fake_dataset)
        db.session.add(user_entry)
        db.session.commit()
        # check authorized user
        # get opendata list
        r = client.get(opendata_list_endpoint, headers=user_header)
        assert r.status_code == 200
        # get download by dataset
        r = client.get(opendata_download_endpoint, headers=user_header)
        assert r.status_code == 200
        # get file download
        r = client.get(download_endpoint, headers=user_header)
        assert r.status_code == 200

        # delete entities
        endpoint = API_URI + "/admin/datasets" + "/" + str(dataset_id)
        r = client.delete(endpoint, headers=user_header)
        assert r.status_code == 204
        endpoint = API_URI + "/admin/licenses" + "/" + str(id_license)
        r = client.delete(endpoint, headers=user_header)
        assert r.status_code == 204
        endpoint = API_URI + "/admin/licensegroups" + "/" + str(id_license_group)
        r = client.delete(endpoint, headers=user_header)
        assert r.status_code == 204
        # delete the request
        requests_to_delete = self.get("request_to_delete_list")
        for r_id in requests_to_delete:
            endpoint = API_URI + "/requests/" + str(r_id)
            r = client.delete(endpoint, headers=admin_headers)
            assert r.status_code == 200
        # delete the user
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
        # delete the user folder
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)
        # check folder deletion
        assert not dir_to_delete.exists()

    # check  file downloaded doesn't exist
    def test_opendata_download(self, faker: Faker):
        fake = Faker()
        assert not OPENDATA_DIR.joinpath(fake.name()).exists()

    # check metadata list
    def test_check_reftime_and_run(self, client: FlaskClient):
        # get admin token
        admin_headers, _ = BaseTests.do_login(client, None, None)
        # create admin user
        db = sqlalchemy.get_instance()
        # useful to delete all schedules and requests
        # self.delete_all_requests_orphan_files(db)
        forecast_dataset = db.Datasets.query.filter_by(
            name=self.DATASET_FOR_TEST_NAME
        ).first()
        data: Dict[str, Any] = {}
        data["disk_quota"] = 1073741824
        data["max_output_size"] = 1073741824
        data["allowed_postprocessing"] = True
        data["allowed_schedule"] = True
        data["open_dataset"] = True
        data["datasets"] = [str(forecast_dataset.id)]
        data["datasets"] = json.dumps(data["datasets"])
        uuid, data = self.create_user(client, data, ["admin_root"])
        # Will be used to delete the user after the tests
        self.save("user_uuid", uuid)
        user_header, _ = self.do_login(client, data.get("email"), data.get("password"))
        self.save("user_header", user_header)
        # create a request on the db
        user_dir = Path(DOWNLOAD_DIR, uuid, "outputs")

        # check if there are other schedules associated to the user, and in that case it deletes them
        endpoint = API_URI + "/schedules"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        if response:
            for e in response:
                schedule_id = e.get("schedule_id")
                endpoint = API_URI + "/schedules/" + str(schedule_id)
                r = client.delete(endpoint, headers=user_header)
                assert r.status_code == 200
            endpoint = API_URI + "/schedules"
            r = client.get(endpoint, headers=user_header)
            assert r.status_code == 200
            response = self.get_content(r)
            assert not response

        # check if there are other requests associated to the user, and in that case it deletes them
        endpoint = API_URI + "/requests"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        if response:
            for e in response:
                request_id = e.get("id")
                endpoint = API_URI + "/requests/" + str(request_id)
                r = client.delete(endpoint, headers=user_header)
                assert r.status_code == 200
            endpoint = API_URI + "/requests"
            r = client.get(endpoint, headers=user_header)
            assert r.status_code == 200
            response = self.get_content(r)
            assert not response

        # get metadata of the dataset
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)

        ref_from = response["items"]["summarystats"]["b"]  # 2023-06-14T00:00:00.000Z
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        # get time string for body request
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # get time info for the schedule
        now_hour = datetime.now()
        now_minute = now_hour.minute
        now_hour = now_hour.hour
        now_minute = now_minute + 1

        body = {
            "request_name": "test",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {"hour": now_hour, "minute": now_minute},
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        # get schedule id for delete
        schedule_id = [response.get("schedule_id")]

        now_hour = datetime.now()
        now_minute = now_hour.minute
        now_hour = now_hour.hour
        now_minute = now_minute + 1

        body = {
            "request_name": "test",
            "reftime": {"from": date_to, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[1]]},
            "crontab-settings": {"hour": now_hour, "minute": now_minute},
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id.append(response.get("schedule_id"))

        # wait for the request
        time.sleep(70)

        endpoint = API_URI + "/requests"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        requests_id = []
        for e in response:
            requests_id.append(e.get("id"))
        if not len(requests_id) == 2:
            print("wait a little bit more")
            time.sleep(40)
            r = client.get(endpoint, headers=user_header)
            assert r.status_code == 200
            response = self.get_content(r)
            requests_id = []
            for e in response:
                requests_id.append(e.get("id"))
        n_response_init = sum(1 for d in response if isinstance(d, dict))
        assert n_response_init == 2

        # test on open data

        # test only run
        q = "q=run:" + ref_run[0].get("style") + "," + ref_run[0].get("desc")[7:12]
        endpoint = f"{API_URI}/datasets/{self.DATASET_FOR_TEST_NAME}/opendata?{q}"
        # print("ENDPOINT:", endpoint)
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        n_response = sum(1 for d in response if isinstance(d, dict))
        assert n_response == 1

        # test only ref time
        date_from_2 = (ref_from + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
        date_to_2 = ref_to.strftime("%Y-%m-%d %H:%M")
        endpoint = (
            API_URI
            + "/datasets/{dataset}/opendata?q=reftime:>={date_from},<={date_to}".format(
                date_from=date_from_2,
                date_to=date_to_2,
                dataset=self.DATASET_FOR_TEST_NAME,
            )
        )

        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        n_response = sum(1 for d in response if isinstance(d, dict))
        assert n_response == 1

        # test ref time + run
        date_from_3 = ref_from.strftime("%Y-%m-%d %H:%M")
        date_to_3 = (ref_to - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
        endpoint = (
            API_URI
            + "/datasets/{dataset}/opendata?q=reftime:>={date_from},<={date_to};run:{minute},{run}".format(
                date_from=date_from_3,
                date_to=date_to_3,
                dataset=self.DATASET_FOR_TEST_NAME,
                minute=ref_run[0].get("style"),
                run=ref_run[1].get("desc")[7:12],
            )
        )

        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        n_response = sum(1 for d in response if isinstance(d, dict))
        assert n_response == 0

        # delete entities
        for i in range(len(schedule_id)):
            endpoint = API_URI + "/schedules/" + str(schedule_id[i])
            r = client.delete(endpoint, headers=user_header)
            assert r.status_code == 200

        for i in range(n_response_init):
            endpoint = API_URI + "/requests/" + str(requests_id[i])
            r = client.delete(endpoint, headers=user_header)
            assert r.status_code == 200

        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
        # delete the user folder
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)
        # check folder deletion
        assert not dir_to_delete.exists()

    def create_fake_opendata_result(self, request_owner_id, args, file_content):
        faker = Faker()
        # create the request
        db = sqlalchemy.get_instance()
        request_name = faker.pystr()
        r = db.Request(
            user_id=request_owner_id,
            name=request_name,
            args=args,
            status="SUCCESS",
            opendata=True,
        )
        db.session.add(r)
        db.session.commit()
        # get the request id
        request_in_db = db.Request.query.filter_by(name=request_name).first()
        request_id = request_in_db.id
        requests_to_delete = self.get("request_to_delete_list")
        requests_to_delete.append(request_id)
        self.save("request_to_delete_list", requests_to_delete)

        # create the fileoutput
        filename = f"{faker.pystr()}.grib"
        output_path = Path(OPENDATA_DIR, filename)
        with output_path.open("w") as f:
            f.write(file_content)
        # save the fileoutput record in db
        fileoutput_entry = db.FileOutput(
            user_id=request_owner_id,
            filename=filename,
            request_id=request_id,
        )
        db.session.add(fileoutput_entry)
        db.session.commit()
        return filename

    def create_environment_download_by_dataset(self, faker: Faker):
        reftime_1 = datetime.strptime(faker.date(), "%Y-%m-%d").strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        reftime_2 = datetime.strptime(faker.date(), "%Y-%m-%d").strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        run_00 = "00:00"
        filters_run_00 = {
            "run": [
                {
                    "s": "MINUTE",
                    "va": 0,
                    "desc": f"MINUTE({run_00})",
                    "value": 0,
                    "active": True,
                }
            ],
        }
        run_12 = "12:00"
        filters_run_12 = {
            "run": [
                {
                    "s": "MINUTE",
                    "va": 0,
                    "desc": f"MINUTE({run_12})",
                    "value": 0,
                    "active": True,
                }
            ],
        }

        # get admin user id
        admin_username = BaseAuthentication.load_default_user()
        if not admin_username:
            admin_username = BaseAuthentication.default_user
        db = sqlalchemy.get_instance()
        user = db.User.query.filter_by(email=admin_username).first()
        request_owner_id = user.id
        self.save("opendata_owner", request_owner_id)
        requests_to_delete = []
        self.save("request_to_delete_list", requests_to_delete)

        args_req_1 = {
            "filters": filters_run_00,
            "reftime": {"from": reftime_1, "to": reftime_1},
            "datasets": [self.DATASET_FOR_TEST_NAME],
        }
        opendata_content_1 = f"{self.DATASET_FOR_TEST_NAME}-{reftime_1}-{run_00}"
        # create the elements in db
        self.create_fake_opendata_result(
            request_owner_id, args_req_1, opendata_content_1
        )

        args_req_2 = {
            "filters": filters_run_12,
            "reftime": {"from": reftime_1, "to": reftime_1},
            "datasets": [self.DATASET_FOR_TEST_NAME],
        }
        opendata_content_2 = f"{self.DATASET_FOR_TEST_NAME}-{reftime_1}-{run_12}"
        self.create_fake_opendata_result(
            request_owner_id, args_req_2, opendata_content_2
        )

        args_req_3 = {
            "filters": filters_run_00,
            "reftime": {"from": reftime_2, "to": reftime_2},
            "datasets": [self.DATASET_FOR_TEST_NAME],
        }
        opendata_content_3 = f"{self.DATASET_FOR_TEST_NAME}-{reftime_2}-{run_00}"
        self.create_fake_opendata_result(
            request_owner_id, args_req_3, opendata_content_3
        )

        return (
            reftime_1,
            reftime_2,
            run_00,
            run_12,
            opendata_content_1,
            opendata_content_2,
            opendata_content_3,
        )

    def test_download_by_dataset(self, client: FlaskClient, faker: Faker):
        # check reftime validation
        wrong_reftime = datetime.strptime(faker.date(), "%Y-%m-%d").strftime("%Y/%d/%m")
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?reftime={wrong_reftime}"
        r = client.get(endpoint)
        assert r.status_code == 400
        response = self.get_content(r)
        assert response["reftime"]
        # check run validation
        wrong_run = "2500"
        endpoint = (
            f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?run={wrong_run}"
        )
        r = client.get(endpoint)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "run format not supported" in response["_schema"][0]

        # check response in case opendata are not available
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download"
        r = client.get(endpoint)
        assert r.status_code == 404
        response = self.get_content(r)
        assert "No opendata found" in response
        # create the test environment
        (
            reftime_1,
            reftime_2,
            run_00,
            run_12,
            opendata_content_1,
            opendata_content_2,
            opendata_content_3,
        ) = self.create_environment_download_by_dataset(faker)

        reftime_1_formatted = datetime.strptime(
            reftime_1, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).strftime("%Y-%m-%d")
        reftime_1_formatted_2 = datetime.strptime(
            reftime_1, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).strftime("%Y%m%d")
        reftime_2_formatted = datetime.strptime(
            reftime_2, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).strftime("%Y-%m-%d")

        # check opendata not found requested by reftime
        reftime_3_formatted = datetime.strptime(faker.date(), "%Y-%m-%d").strftime(
            "%Y%m%d"
        )
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?reftime={reftime_3_formatted}"
        r = client.get(endpoint)
        assert r.status_code == 404
        # check opendata not found requested by run
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?run=15:00"
        r = client.get(endpoint)
        assert r.status_code == 404
        # check opendata not found request by reftime and run
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?reftime={reftime_2_formatted}&run={run_12}"
        r = client.get(endpoint)
        assert r.status_code == 404

        # request all opendata of a dataset
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download"
        r = client.get(endpoint)
        assert r.status_code == 200
        # check it is a zipfile
        assert r.mimetype == "application/zip"
        # check filename
        zipfile_name = (
            r.headers["Content-Disposition"].split("filename=")[-1].strip('"')
        )
        assert zipfile_name == f"opendata_{self.DATASET_FOR_TEST_NAME}.zip"
        # check content
        resulting_file = io.BytesIO(r.get_data())
        with ZipFile(resulting_file, "r") as zip_file:
            file_list = zip_file.namelist()
            assert len(file_list) == 3

        # request opendata by reftime
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?reftime={reftime_1_formatted}"
        r = client.get(endpoint)
        assert r.status_code == 200
        # check it is a zipfile
        assert r.mimetype == "application/zip"
        # check filename
        zipfile_name = (
            r.headers["Content-Disposition"].split("filename=")[-1].strip('"')
        )
        assert (
            zipfile_name
            == f"opendata_{self.DATASET_FOR_TEST_NAME}_reftime_{reftime_1_formatted}.zip"
        )
        # check content
        resulting_file = io.BytesIO(r.get_data())
        with ZipFile(resulting_file, "r") as zip_file:
            file_list = zip_file.namelist()
            assert len(file_list) == 2

        # request opendata by run
        endpoint = (
            f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?run={run_00}"
        )
        r = client.get(endpoint)
        assert r.status_code == 200
        # check it is a zipfile
        assert r.mimetype == "application/zip"
        # check filename
        zipfile_name = (
            r.headers["Content-Disposition"].split("filename=")[-1].strip('"')
        )
        assert zipfile_name == f"opendata_{self.DATASET_FOR_TEST_NAME}_run_{run_00}.zip"
        # check content
        resulting_file = io.BytesIO(r.get_data())
        with ZipFile(resulting_file, "r") as zip_file:
            file_list = zip_file.namelist()
            assert len(file_list) == 2

        # request opendata by reftime and run
        endpoint = f"{API_URI}/opendata/{self.DATASET_FOR_TEST_NAME}/download?reftime={reftime_1_formatted_2}&run={run_12}"
        r = client.get(endpoint)
        assert r.status_code == 200
        # check it is a single file
        assert r.mimetype == "application/octet-stream"
        # check content
        response_content = r.get_data().decode("utf-8")
        assert response_content == opendata_content_2

        # delete all the fake requests and fake files
        admin_headers, _ = BaseTests.do_login(client, None, None)
        requests_to_delete = self.get("request_to_delete_list")
        for r_id in requests_to_delete:
            endpoint = API_URI + "/requests/" + str(r_id)
            r = client.delete(endpoint, headers=admin_headers)
            assert r.status_code == 200
