from restapi.flask_ext.flask_celery import CeleryExt
#from mistral.tasks.data_extraction  import data_extract
from restapi.tests import BaseTests, API_URI
from unittest.mock import patch
from restapi.utilities.htmlcodes import HTTP_BAD_UNAUTHORIZED


class TestApp(BaseTests):

    @patch.object(CeleryExt,'celery_app')
    def mock_celery (self, celery_app):
        with celery_app.app.app_context():
            return 1

    def test_mock_celery_works(self,app):
        r = self.mock_celery()
        assert r==1

    @patch.object(CeleryExt, 'data_extract', side_effect=mock_celery)
    def test_endpoint_without_login(self, mock_celery,client):
        endpoint = API_URI + '/data'
        r = client.post(endpoint)
        assert r.status_code == HTTP_BAD_UNAUTHORIZED

