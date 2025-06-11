import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from mistral.endpoints import DOWNLOAD_DIR
from mistral.endpoints.schedules import SingleSchedule
from mistral.services.sqlapi_db_manager import SqlApiDbManager as repo
from restapi.connectors import celery, sqlalchemy
from restapi.services.authentication import User
from restapi.tests import API_URI, BaseTests, FlaskClient

__author__ = "Mattia Carello (m.carello@cineca.it)"


class TestApp(BaseTests):
    DATASET_FOR_TEST_NAME = "lm5"
    SECOND_MODEL_FOR_TEST_NAME = "lm2.2"

    # enable the test datasets to data_ready
    SingleSchedule.ON_DATA_READY_DATASETS = [
        DATASET_FOR_TEST_NAME,
        SECOND_MODEL_FOR_TEST_NAME,
    ]

    # use in case of mess
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

    def test_not_exported_on_filesystem(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "meucci",
            "rundate": "2023020217",
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        response = self.get_content(r)
        assert response == "1"

    def test_dataset_not_enabled_for_dataready(self, client: FlaskClient):
        # get dataset list
        admin_headers, _ = BaseTests.do_login(client, None, None)
        endpoint = API_URI + "/datasets"
        r = client.get(endpoint, headers=admin_headers)
        assert r.status_code == 200
        response_data = self.get_content(r)
        no_data_ready_dataset = None
        for dataset in response_data:
            if (
                dataset["id"] != self.DATASET_FOR_TEST_NAME
                and dataset["id"] != self.SECOND_MODEL_FOR_TEST_NAME
            ):
                no_data_ready_dataset = dataset["id"]
                break
        body = {
            "request_name": "test_no_dataready",
            "reftime": {
                "from": (datetime.now() - timedelta(hours=1)).strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                ),
                "to": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
            "dataset_names": [no_data_ready_dataset],
            "filters": {},
            "on-data-ready": True,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 400
        response = self.get_content(r)
        assert "Data-ready service is not available" in response

    def test_schedule_inactive(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=admin_headers)
        assert r.status_code == 200
        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # get time info for the schedule
        now_hour = datetime.now()
        now_minute = now_hour.minute
        now_hour = now_hour.hour
        body = {
            "request_name": "test_schedule_not_active",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {"hour": now_hour, "minute": now_minute},
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        endpoint = API_URI + "/schedules/" + str(schedule_id[0])
        body = {"is_active": False}
        body = json.dumps(body)
        r = client.patch(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 200

        rundate = ref_from.strftime("%Y%m%d%H")
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        response = self.get_content(r)
        assert response == "1"

        endpoint = API_URI + "/schedules/" + str(schedule_id[0])
        r = client.delete(endpoint, headers=admin_headers)
        assert r.status_code == 200

    def test_schedule_not_on_data_ready(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        endpoint = f"{API_URI}/fields?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=admin_headers)
        assert r.status_code == 200
        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # get time info for the schedule
        now_hour = datetime.now()
        now_minute = now_hour.minute
        now_hour = now_hour.hour
        body = {
            "request_name": "test_not_on_data_ready",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {"hour": now_hour, "minute": now_minute},
            "on-data-ready": False,
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        rundate = ref_from.strftime("%Y%m%d%H")
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        response = self.get_content(r)
        assert response == "1"

        endpoint = API_URI + "/schedules/" + str(schedule_id[0])
        r = client.delete(endpoint, headers=admin_headers)
        assert r.status_code == 200

    def test_model_different_dataset(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=admin_headers)
        assert r.status_code == 200
        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # get time info for the schedule
        now_hour = datetime.now()
        now_minute = now_hour.minute
        now_hour = now_hour.hour
        body = {
            "request_name": "test_different_model_dataset",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {"hour": now_hour, "minute": now_minute},
            "on-data-ready": True,
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        rundate = ref_from.strftime("%Y%m%d%H")
        body = {
            "Model": self.SECOND_MODEL_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        response = self.get_content(r)
        assert response == "1"

        endpoint = API_URI + "/schedules/" + str(schedule_id[0])
        r = client.delete(endpoint, headers=admin_headers)
        assert r.status_code == 200

    def test_schedule_request_wrong_runhour(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=admin_headers)
        assert r.status_code == 200
        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # get time info for the schedule
        now_hour = datetime.now()
        now_minute = now_hour.minute
        now_hour = now_hour.hour
        body = {
            "request_name": "test_runhour",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {"hour": now_hour, "minute": now_minute},
            "on-data-ready": True,
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        # set a different runhour
        rundate = "2021101917"  # 17 different run
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        response = self.get_content(r)
        assert response == "1"

        endpoint = API_URI + "/schedules/" + str(schedule_id[0])
        r = client.delete(endpoint, headers=admin_headers)
        assert r.status_code == 200

    def test_schedule_request_wrong_period(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        # create the user
        db = sqlalchemy.get_instance()
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
        user = db.User.query.filter_by(uuid=uuid).first()
        user_id = user.id
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

        # get info on dataset
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200

        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # define the  schedule
        body = {
            "request_name": "test_runhour",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "period-settings": {"every": 1, "period": "days"},
            "on-data-ready": True,
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        # create a request to simulate get_last_request - 2 days
        request = repo.create_request_record(
            db,
            user_id,
            "test_runhour",
            {
                "datasets": self.DATASET_FOR_TEST_NAME,
                "reftime": date_from,
                "filters": [],
                "postprocessors": [],
                "output_format": None,
                "only_reliable": True,
                "pushing_queue": None,
            },
            schedule_id[0],
            True,
        )
        request_id = request.id
        modified_sub_date = request.submission_date + timedelta(days=-2)
        request.submission_date = modified_sub_date
        db.session.add(request)
        db.session.commit()

        time.sleep(10)

        rundate = "2021101900"
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202

        # delete entities
        endpoint = API_URI + "/requests/" + str(request_id)
        r = client.delete(endpoint, headers=user_header)
        assert r.status_code == 200
        endpoint = API_URI + "/requests"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        for el in response:
            request_id = el.get("id")
            endpoint = API_URI + "/requests/" + str(request_id)
            r = client.delete(endpoint, headers=user_header)
            assert r.status_code == 200

        endpoint = API_URI + "/schedules/" + schedule_id[0]
        r = client.delete(endpoint, headers=user_header)
        r.status_code == 200

        # delete the user
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
        # delete the user folder
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)
        # check folder deletion
        assert not dir_to_delete.exists()

    def test_schedule_request_wrong_crontab(self, client: FlaskClient):
        admin_headers, _ = BaseTests.do_login(client, None, None)
        # create the user
        db = sqlalchemy.get_instance()
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

        # get info on dataset
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200

        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0], ref_from[1], ref_from[2], ref_from[3], ref_from[4]
        )
        ref_to = datetime(ref_to[0], ref_to[1], ref_to[2], ref_to[3], ref_to[4])
        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # define the  schedule
        body = {
            "request_name": "test_runhour",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {
                "minute": 59,
                "hour": 23,
                "day_of_week": 6,
                "day_of_month": 30,
                "month_of_year": 11,
            },
            "on-data-ready": True,
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        rundate = "2021101900"
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202

        # define the  schedule
        body = {
            "request_name": "test_runhour",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "crontab-settings": {
                "minute": 59,
                "hour": 23,
                "day_of_week": 2,
                "month_of_year": 11,
            },
            "on-data-ready": True,
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

        rundate = "2021101900"
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202

        # delete entities
        endpoint = API_URI + "/requests"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        for el in response:
            request_id = el.get("id")
            endpoint = API_URI + "/requests/" + str(request_id)
            r = client.delete(endpoint, headers=user_header)
            assert r.status_code == 200

        for el in schedule_id:
            endpoint = API_URI + "/schedules/" + el
            r = client.delete(endpoint, headers=user_header)
            r.status_code == 200

        # delete the user
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
        # delete the user folder
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)
        # check folder deletion
        assert not dir_to_delete.exists()

    def test_two_days_periodic(self, client: FlaskClient):

        admin_headers, _ = BaseTests.do_login(client, None, None)
        # create the user
        db = sqlalchemy.get_instance()
        # self.delete_all_schedules_requests_orphan_files(db)
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
        user = db.User.query.filter_by(uuid=uuid).first()
        user_id = user.id
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

        # get info on dataset
        endpoint = API_URI + "/fields"
        endpoint = f"{endpoint}?datasets={self.DATASET_FOR_TEST_NAME}"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200

        response = self.get_content(r)
        ref_from = response["items"]["summarystats"]["b"]
        ref_to = response["items"]["summarystats"]["e"]
        ref_run = response["items"]["run"]
        ref_from = datetime(
            ref_from[0],
            ref_from[1],
            ref_from[2],
            ref_from[3],
            ref_from[4],
            second=0,
            microsecond=1,
        )
        ref_to = datetime(
            ref_to[0],
            ref_to[1],
            ref_to[2],
            ref_to[3],
            ref_to[4],
            second=0,
            microsecond=1,
        )

        date_from = ref_from.strftime("%Y-%m-%dT%H:%M:%S.%f")
        date_to = ref_to.strftime("%Y-%m-%dT%H:%M:%S.%f")

        # define the  schedulerundate
        body = {
            "request_name": "test_periodic_days",
            "reftime": {"from": date_from, "to": date_to},
            "dataset_names": [self.DATASET_FOR_TEST_NAME],
            "filters": {"run": [ref_run[0]]},
            "period-settings": {"every": 2, "period": "days"},
            "on-data-ready": True,
            "opendata": True,
        }

        body = json.dumps(body)
        endpoint = API_URI + "/schedules"
        r = client.post(
            endpoint, headers=user_header, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        response = self.get_content(r)
        schedule_id = [response.get("schedule_id")]

        time.sleep(10)

        # delete first request associated to the schedule
        request = db.Request.query.filter_by(schedule_id=int(schedule_id[0])).first()
        if not request:
            print("wait a little bit more")
            time.sleep(30)
            request = db.Request.query.filter_by(
                schedule_id=int(schedule_id[0])
            ).first()
        request_id = request.id
        endpoint = API_URI + "/requests/" + str(request_id)
        r = client.delete(endpoint, headers=user_header)
        assert r.status_code == 200

        # create a fake request associated to the schedule
        request = repo.create_request_record(
            db,
            user_id,
            "test_periodic_days_2",
            {
                "datasets": self.DATASET_FOR_TEST_NAME,
                "reftime": date_from,
                "filters": [],
                "postprocessors": [],
                "output_format": None,
                "only_reliable": True,
                "pushing_queue": None,
            },
            schedule_id[0],
            True,
        )

        request_id = request.id
        modified_sub_date = ref_from + timedelta(days=-2)
        request.submission_date = modified_sub_date
        request.status = "SUCCESS"
        db.session.add(request)
        db.session.commit()

        # invoke data ready
        rundate = ref_from.strftime("%Y%m%d%H")

        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202

        time.sleep(30)

        endpoint = API_URI + "/schedules/" + schedule_id[0] + "/requests?last=False"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        n_response = sum(1 for d in response if isinstance(d, dict))
        request_ids = []
        for el in response:
            request_ids.append(el.get("id"))
        assert n_response == 2

        for el in range(len(request_ids)):
            endpoint = API_URI + "/requests/" + str(request_ids[el])
            r = client.delete(endpoint, headers=user_header)
            assert r.status_code == 200

        # create a fake request associated to the schedule
        request = repo.create_request_record(
            db,
            user_id,
            "test_periodic_days_3",
            {
                "datasets": self.DATASET_FOR_TEST_NAME,
                "reftime": date_from,
                "filters": [],
                "postprocessors": [],
                "output_format": None,
                "only_reliable": True,
                "pushing_queue": None,
            },
            schedule_id[0],
            True,
        )
        request_id = request.id
        modified_sub_date = ref_from + timedelta(days=-1)
        request.submission_date = modified_sub_date
        request.status = "SUCCESS"
        db.session.add(request)
        db.session.commit()

        # invoke data ready
        rundate = ref_from.strftime("%Y%m%d%H")
        body = {
            "Model": self.DATASET_FOR_TEST_NAME,
            "Cluster": "g100",
            "rundate": rundate,
        }
        body = json.dumps(body)
        endpoint = API_URI + "/data/ready"
        r = client.post(
            endpoint, headers=admin_headers, data=body, content_type="application/json"
        )
        assert r.status_code == 202
        time.sleep(5)

        endpoint = API_URI + "/schedules/" + schedule_id[0] + "/requests?last=False"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        n_response = sum(1 for d in response if isinstance(d, dict))
        assert n_response == 1

        endpoint = API_URI + "/requests/" + str(request_id)
        r = client.delete(endpoint, headers=user_header)
        assert r.status_code == 200

        # CANCELLA TUTTI I VARI COMMENTI E PRITNF DA TUTTI I FILE

        # delete requests associated to the user
        endpoint = API_URI + "/requests"
        r = client.get(endpoint, headers=user_header)
        assert r.status_code == 200
        response = self.get_content(r)
        for el in response:
            request_id = el.get("id")
            endpoint = API_URI + "/requests/" + str(request_id)
            r = client.delete(endpoint, headers=user_header)
            assert r.status_code == 200
        # delete schedule associated to the user
        for el in schedule_id:
            endpoint = API_URI + "/schedules/" + el
            r = client.delete(endpoint, headers=user_header)
            r.status_code == 200
        # delete the user
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204
        # delete the user folder
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)
        # check folder deletion
        assert not dir_to_delete.exists()
