import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from faker import Faker
from mistral.endpoints import DOWNLOAD_DIR, OPENDATA_DIR
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient

__author__ = "Mattia Carello (m.carello@cineca.it)"


class TestApp(BaseTests):
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
    def test_check_wrong_dataset_name(self):
        fake = Faker()
        # fake name
        dataset_name = fake.name()
        db = sqlalchemy.get_instance()
        # get fake entry
        ds_entry = db.Datasets.query.filter_by(name=dataset_name).first()
        assert ds_entry is None

    # check if a license is private
    def test_check_not_plubic_license(self, client: FlaskClient, faker: Faker):
        # get admin token
        admin_headers, _ = BaseTests.do_login(client, None, None)
        fake = Faker()
        # create a new not open license group
        body = {"name": fake.name(), "descr": fake.name(), "is_public": "false"}
        body = json.dumps(body)

        # create an admin_root user
        db = sqlalchemy.get_instance()
        forecast_dataset_name = "lm5"
        forecast_dataset = db.Datasets.query.filter_by(
            name=forecast_dataset_name
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
        user = db.User.query.filter_by(uuid=uuid).first()
        user_id = user.id
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
            "name": fake.name(),
            "descr": fake.name(),
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
        fake_name = fake.name()
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
        forecast_dataset_name = "lm5"
        forecast_dataset = db.Datasets.query.filter_by(
            name=forecast_dataset_name
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

        # get metadata of the dataset
        endpoint = API_URI + "/fields"
        dataset_name = "lm5"
        question_mark = "?"
        endpoint = endpoint + question_mark + "datasets=" + dataset_name
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
            "dataset_names": [dataset_name],
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
            "dataset_names": [dataset_name],
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
        endpoint = (
            API_URI + "/datasets/" + dataset_name + "/opendata" + question_mark + q
        )
        print("ENDPOINT:", endpoint)
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
                date_from=date_from_2, date_to=date_to_2, dataset=dataset_name
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
                dataset=dataset_name,
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
