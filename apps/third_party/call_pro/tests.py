import os
from unittest import mock

import requests
from django.test import SimpleTestCase

from apps.third_party.call_pro.services import CallProService

CALL_PRO_ENV = {
    "CALL_PRO_URL": "https://sms.example.test/send",
    "CALL_PRO_KEY": "dummy-key",
    "CALL_PRO_FROM": "7000",
}


@mock.patch.dict(os.environ, CALL_PRO_ENV)
class CallProServiceTests(SimpleTestCase):
    def send_with(self, **post_kwargs):
        with mock.patch("requests.post", **post_kwargs) as post:
            result = CallProService.send(to="99112233", text="hello")
        return result, post

    def test_success_posts_payload_and_returns_no_error(self):
        result, post = self.send_with(return_value=mock.Mock(status_code=200, text="ok"))
        self.assertEqual(result, (None, None))
        post.assert_called_once_with(
            "https://sms.example.test/send",
            json={"key": "dummy-key", "from": "7000", "to": "99112233", "text": "hello"},
            timeout=30,
        )

    def test_non_200_response_returns_body_as_error(self):
        result, _ = self.send_with(return_value=mock.Mock(status_code=403, text="forbidden"))
        self.assertEqual(result, (None, "forbidden"))

    def test_network_failure_is_reported_as_error_string(self):
        result, _ = self.send_with(side_effect=requests.exceptions.ConnectionError("unreachable"))
        self.assertIsNone(result[0])
        self.assertIn("unreachable", result[1])
