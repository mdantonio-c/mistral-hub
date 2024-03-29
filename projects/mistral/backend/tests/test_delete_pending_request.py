import shutil
from datetime import datetime, timedelta
from pathlib import Path

from celery.states import READY_STATES
from faker import Faker
from flask import Flask
from mistral.endpoints import DOWNLOAD_DIR
from restapi.connectors import sqlalchemy
from restapi.env import Env
from restapi.tests import API_URI, BaseTests, FlaskClient

grace_period_days = Env.get_int("GRACE_PERIOD", 2)
GRACE_PERIOD = timedelta(days=grace_period_days)


class TestDeletePendingRequests(BaseTests):
    @staticmethod
    def create_requests_for_delete_tests(faker: Faker, db, user_id):
        """
        Creates two requests on the db, one deletable (submission date before grace period)
        one undeletable (submission date within grace period)
        """
        deletable_request_name = faker.pystr()
        undeletable_request_name = faker.pystr()

        forbidden_delete_time = datetime.now() - GRACE_PERIOD + timedelta(days=1)
        allowed_delete_time = datetime.now() - GRACE_PERIOD - timedelta(days=1)

        deletable_request = db.Request(
            user_id=user_id,
            name=deletable_request_name,
            args={},
            submission_date=allowed_delete_time,
            status="STARTED",
        )

        undeletable_request = db.Request(
            user_id=user_id,
            name=undeletable_request_name,
            args={},
            submission_date=forbidden_delete_time,
            status="PENDING",
        )
        db.session.add(deletable_request)
        db.session.add(undeletable_request)
        db.session.commit()

        return deletable_request, undeletable_request

    def test_delete_request(self, faker: Faker, client: FlaskClient) -> None:

        db = sqlalchemy.get_instance()
        uuid, data = self.create_user(client)
        user_header, _ = self.do_login(client, data.get("email"), data.get("password"))
        self.save("user_header", user_header)
        user = db.User.query.filter_by(uuid=uuid).first()
        user_id = user.id
        self.save("user_uuid", uuid)
        user_dir = Path(DOWNLOAD_DIR, uuid, "outputs")
        self.save("user_dir", user_dir)

        (
            deletable_request,
            undeletable_request,
        ) = TestDeletePendingRequests.create_requests_for_delete_tests(
            faker, db, user_id
        )

        deletable_req_response = self.delete_the_request(client, deletable_request.id)
        assert deletable_req_response.status_code == 200
        undeletable_req_response = self.delete_the_request(
            client, undeletable_request.id
        )
        assert undeletable_req_response.status_code == 403

        # delete undeletable request by sql query
        db.session.delete(undeletable_request)
        db.session.commit()

        undeletable_last_check = db.Request.query.get(undeletable_request.id)
        assert undeletable_last_check is None

    def delete_the_request(self, client, request_id):
        endpoint = API_URI + f"/requests/{request_id}"
        response = client.delete(endpoint, headers=self.get("user_header"))
        return response

    def test_requests_cleanup(
        self, app: Flask, faker: Faker, client: FlaskClient  # app: Flask,
    ) -> None:
        db = sqlalchemy.get_instance()
        uuid = self.get("user_uuid")
        user = db.User.query.filter_by(uuid=uuid).first()
        user_id = user.id

        (
            deletable_request,
            undeletable_request,
        ) = TestDeletePendingRequests.create_requests_for_delete_tests(
            faker, db, user_id
        )

        # We have to keep track of the just created requests.id before sending the celery task.
        # By sending the task, we may close the previous db session, detaching the created request instances the current
        # session
        del_req_id = deletable_request.id
        undel_req_id = undeletable_request.id

        self.send_task(app, "automatic_cleanup")

        deletable_req = db.Request.query.get(del_req_id)
        assert deletable_req.status == "FAILURE"

        undeletable_req = db.Request.query.get(undel_req_id)
        assert undeletable_req.status not in READY_STATES

        # delete the requests by sql query
        db.session.delete(deletable_req)
        db.session.delete(undeletable_req)
        db.session.commit()

        deletable_last_check = db.Request.query.get(deletable_req.id)
        assert deletable_last_check is None

        undeletable_last_check = db.Request.query.get(undeletable_req.id)
        assert undeletable_last_check is None

        # delete the user
        admin_headers, _ = self.do_login(client, None, None)
        r = client.delete(f"{API_URI}/admin/users/{uuid}", headers=admin_headers)
        assert r.status_code == 204

        # delete the user folder
        user_dir = self.get("user_dir")
        dir_to_delete = user_dir.parent
        shutil.rmtree(dir_to_delete, ignore_errors=True)

        # check folder deletion
        assert not dir_to_delete.exists()
