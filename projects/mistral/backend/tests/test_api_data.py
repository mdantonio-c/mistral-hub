# from unittest.mock import patch

# from restapi.connectors.celery import CeleryExt
from restapi.tests import API_URI, BaseTests
from restapi.utilities.htmlcodes import hcodes


class TestApp(BaseTests):
    # @patch.object(CeleryExt, "celery_app")
    # def mock_celery(self, celery_app):
    #     with celery_app.app.app_context():
    #         return 1

    # def test_mock_celery_works(self, app):
    #     r = self.mock_celery()
    #     assert r == 1

    # def test_endpoint_without_login(self, app, mock_celery, client):
    def test_endpoint_without_login(self, client):
        # detector.init_services(
        #     app=app, project_init=False, project_clean=False,
        # )

        # celery = detector.get_service_instance("celery")

        # patch.object(celery, "data_extract", side_effect=mock_celery)

        endpoint = f"{API_URI}/data"
        r = client.post(endpoint)
        assert r.status_code == hcodes.HTTP_BAD_UNAUTHORIZED
