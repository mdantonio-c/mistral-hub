import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from celery.states import READY_STATES
from restapi.connectors import Connector
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


class TestFilterValidationEndpoints(BaseTests):
    PREFERRED_DATASETS = {
        "grib": ("lm5", "ICON_2I_SURFACE_PRESSURE_LEVELS"),
        "bufr": ("agrmet", "dpcn-basilicata"),
    }
    REQUEST_READY_TIMEOUT_SECONDS = 120
    REQUEST_READY_POLL_SECONDS = 5

    VALID_GRIB_FILTERS = {
        "product": [
            {
                "desc": "P Pressure Pa",
                "style": "GRIB1",
                "origin": 80,
                "table": 2,
                "product": 1,
                "active": "true",
            }
        ]
    }

    VALID_BUFR_FILTERS = {
        "product": [
            {
                "code": "B12101",
                "desc": "TEMPERATURE/DRY-BULB TEMPERATURE",
                "active": "true",
            }
        ]
    }

    def _get_auth_headers(self, client: FlaskClient):
        auth = Connector.get_authentication_instance()
        auth.init_auth_db({"force_user": True, "force_group": True})
        headers, _ = self.do_login(client, None, None)
        assert headers is not None
        return headers

    @staticmethod
    def _recent_reftime():
        now = datetime.now(timezone.utc)
        return {
            "from": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }

    @staticmethod
    def _build_schedule_payload(dataset_name, filters, reftime=None):
        payload = {
            "request_name": "invalid_schedule_filters",
            "dataset_names": [dataset_name],
            "filters": filters,
            "period-settings": {"every": 1, "period": "hours"},
        }
        if reftime is not None:
            payload["reftime"] = reftime
        return payload

    @staticmethod
    def _submit_data_request(client: FlaskClient, auth_headers, payload):
        return client.post(
            f"{API_URI}/data",
            headers=auth_headers,
            data=json.dumps(payload),
            content_type="application/json",
        )

    @staticmethod
    def _submit_schedule_request(client: FlaskClient, auth_headers, payload):
        return client.post(
            f"{API_URI}/schedules",
            headers=auth_headers,
            data=json.dumps(payload),
            content_type="application/json",
        )

    @staticmethod
    def _delete_schedule(client: FlaskClient, auth_headers, schedule_id):
        return client.delete(f"{API_URI}/schedules/{schedule_id}", headers=auth_headers)

    @staticmethod
    def _delete_request(client: FlaskClient, auth_headers, request_id):
        return client.delete(f"{API_URI}/requests/{request_id}", headers=auth_headers)

    def _wait_for_request_ready(self, request_id):
        db = sqlalchemy.get_instance()
        attempts = self.REQUEST_READY_TIMEOUT_SECONDS // self.REQUEST_READY_POLL_SECONDS

        for _ in range(attempts):
            db.session.expire_all()
            request = db.Request.query.get(request_id)
            assert request is not None
            if request.status in READY_STATES:
                return request.status
            time.sleep(self.REQUEST_READY_POLL_SECONDS)

        pytest.fail(
            f"Request {request_id} did not reach a ready state within "
            f"{self.REQUEST_READY_TIMEOUT_SECONDS} seconds"
        )

    def _get_dataset_name_for_format(
        self, client: FlaskClient, auth_headers, dataset_format: str
    ) -> str:
        response = client.get(f"{API_URI}/datasets", headers=auth_headers)
        assert response.status_code == 200
        datasets = self.get_content(response)

        for preferred_dataset in self.PREFERRED_DATASETS.get(dataset_format, ()): 
            if any(item.get("id") == preferred_dataset for item in datasets):
                return preferred_dataset

        dataset = next(
            (
                item
                for item in datasets
                if item.get("format", "").lower() == dataset_format
                and item.get("id") not in {"error", "duplicates"}
            ),
            None,
        )
        assert dataset is not None
        return dataset["id"]

    def test_data_submission_accepts_valid_grib_filters(
        self,
        client: FlaskClient,
    ) -> None:
        auth_headers = self._get_auth_headers(client)
        dataset_name = self._get_dataset_name_for_format(client, auth_headers, "grib")
        payload = {
            "request_name": "valid_grib_filters",
            "reftime": self._recent_reftime(),
            "dataset_names": [dataset_name],
            "filters": self.VALID_GRIB_FILTERS,
        }

        request_id = None
        try:
            response = self._submit_data_request(client, auth_headers, payload)

            assert response.status_code == 202
            content = self.get_content(response)
            assert isinstance(content, dict)
            request_id = content.get("request_id")
            assert request_id
            assert content.get("task_id")
        finally:
            if request_id is not None:
                self._wait_for_request_ready(request_id)
                delete_response = self._delete_request(
                    client, auth_headers, request_id
                )
                assert delete_response.status_code == 200

    def test_data_submission_accepts_valid_bufr_filters(
        self,
        client: FlaskClient,
    ) -> None:
        auth_headers = self._get_auth_headers(client)
        dataset_name = self._get_dataset_name_for_format(client, auth_headers, "bufr")
        payload = {
            "request_name": "valid_bufr_filters",
            "reftime": self._recent_reftime(),
            "dataset_names": [dataset_name],
            "filters": self.VALID_BUFR_FILTERS,
            "force_obs_download": True,
        }

        request_id = None
        try:
            response = self._submit_data_request(client, auth_headers, payload)

            assert response.status_code == 202
            content = self.get_content(response)
            assert isinstance(content, dict)
            request_id = content.get("request_id")
            assert request_id
            assert content.get("task_id")
        finally:
            if request_id is not None:
                self._wait_for_request_ready(request_id)
                delete_response = self._delete_request(
                    client, auth_headers, request_id
                )
                assert delete_response.status_code == 200

    def test_schedule_submission_accepts_valid_grib_filters(
        self,
        client: FlaskClient,
    ) -> None:
        auth_headers = self._get_auth_headers(client)
        dataset_name = self._get_dataset_name_for_format(client, auth_headers, "grib")
        payload = self._build_schedule_payload(
            dataset_name,
            self.VALID_GRIB_FILTERS,
            reftime=self._recent_reftime(),
        )

        schedule_id = None
        try:
            response = self._submit_schedule_request(client, auth_headers, payload)

            assert response.status_code == 202
            content = self.get_content(response)
            assert isinstance(content, dict)
            schedule_id = content.get("schedule_id")
            assert schedule_id
        finally:
            if schedule_id is not None:
                delete_response = self._delete_schedule(
                    client, auth_headers, schedule_id
                )
                assert delete_response.status_code == 200

    def test_schedule_submission_accepts_valid_bufr_filters(
        self,
        client: FlaskClient,
    ) -> None:
        auth_headers = self._get_auth_headers(client)
        dataset_name = self._get_dataset_name_for_format(client, auth_headers, "bufr")
        payload = self._build_schedule_payload(
            dataset_name,
            self.VALID_BUFR_FILTERS,
            reftime=self._recent_reftime(),
        )

        schedule_id = None
        try:
            response = self._submit_schedule_request(client, auth_headers, payload)

            assert response.status_code == 202
            content = self.get_content(response)
            assert isinstance(content, dict)
            schedule_id = content.get("schedule_id")
            assert schedule_id
        finally:
            if schedule_id is not None:
                delete_response = self._delete_schedule(
                    client, auth_headers, schedule_id
                )
                assert delete_response.status_code == 200

    @pytest.mark.parametrize(
        "dataset_format,filters,expected_message",
        [
            (
                "grib",
                {"level": [{"value": [850]}]},
                "missing 'style' key",
            ),
            (
                "grib",
                {"network": [{"code": "SYNOP"}]},
                "is not valid for GRIB datasets",
            ),
            (
                "bufr",
                {"network": [{"value": "SYNOP"}]},
                "missing required 'code' key",
            ),
            (
                "bufr",
                {"area": [{"code": "45,10,46,11"}]},
                "is not valid for BUFR datasets",
            ),
            (
                "bufr",
                {"product": [{"code": "   "}]},
                "'code' must not be empty",
            ),
        ],
    )
    def test_data_submission_rejects_invalid_filters(
        self,
        client: FlaskClient,
        dataset_format: str,
        filters,
        expected_message: str,
    ) -> None:
        auth_headers = self._get_auth_headers(client)
        dataset_name = self._get_dataset_name_for_format(
            client, auth_headers, dataset_format
        )
        payload = {
            "request_name": "invalid_filters",
            "reftime": self._recent_reftime(),
            "dataset_names": [dataset_name],
            "filters": filters,
        }

        response = self._submit_data_request(client, auth_headers, payload)

        assert response.status_code == 400
        error = self.get_content(response)
        assert expected_message in error

    @pytest.mark.parametrize(
        "dataset_format,filters,expected_message",
        [
            (
                "grib",
                {"level": [{"value": [850]}]},
                "missing 'style' key",
            ),
            (
                "grib",
                {"network": [{"code": "SYNOP"}]},
                "is not valid for GRIB datasets",
            ),
            (
                "bufr",
                {"network": [{"value": "SYNOP"}]},
                "missing required 'code' key",
            ),
            (
                "bufr",
                {"area": [{"code": "45,10,46,11"}]},
                "is not valid for BUFR datasets",
            ),
            (
                "bufr",
                {"product": [{"code": "   "}]},
                "'code' must not be empty",
            ),
        ],
    )
    def test_schedule_submission_rejects_invalid_filters(
        self,
        client: FlaskClient,
        dataset_format: str,
        filters,
        expected_message: str,
    ) -> None:
        auth_headers = self._get_auth_headers(client)
        dataset_name = self._get_dataset_name_for_format(
            client, auth_headers, dataset_format
        )
        payload = self._build_schedule_payload(
            dataset_name, filters, reftime=self._recent_reftime()
        )

        response = self._submit_schedule_request(client, auth_headers, payload)

        assert response.status_code == 400
        error = self.get_content(response)
        assert expected_message in error