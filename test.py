from app import app
import unittest
from conversation_closed_example import json_for_tests
from mock import Mock




converastion_closed_webhook_example = json_for_tests

class FlaskTestCase(unittest.TestCase):

    def test_visit_home_page(self):
        client = app.test_client(self)
        response = client.get('/', content_type='html/text')
        self.assertEquals(response.status_code, 200)

    # def test_listener(self):
    #     client = app.test_client(self)
    #     mocked_post = Mock(status_code=201, json=)






