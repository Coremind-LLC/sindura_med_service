import os
import re
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from apps.auth.backends import AuthBackend
from apps.third_party.call_pro.tests import CALL_PRO_ENV
from helpers.tests_factories import TEST_PASSWORD, make_user

NEW_PASSWORD = "brand-new-pass-77"
INVALID_USERNAME = "Буруу утас эсвэл имэйл оруулсан байна"


class AuthAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = make_user(email="bat@example.com", phone="99001122")

    def post(self, name, **payload):
        return self.client.post(f"/auth/{name}/", payload, format="json")

    def assert_rejected(self, response, message, code=400):
        self.assertEqual(response.status_code, code)
        self.assertEqual(response.json()["message"], message)

    def check_rejections(self, name, table):
        for payload, message in table:
            with self.subTest(payload=payload):
                self.assert_rejected(self.post(name, **payload), message)


class LoginTests(AuthAPITestCase):
    def test_login_with_email_or_phone_returns_token(self):
        tokens = []
        for username in ("bat@example.com", "99001122"):
            with self.subTest(username=username):
                response = self.post("login", username=username, password=TEST_PASSWORD)
                self.assertEqual(response.status_code, 200)
                tokens.append(response.json()["token"])
        key = Token.objects.get(user=self.user).key
        self.assertEqual(tokens, [key, key])
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_login_reuses_existing_token(self):
        first = self.post("login", username="99001122", password=TEST_PASSWORD).json()["token"]
        second = self.post("login", username="99001122", password=TEST_PASSWORD).json()["token"]
        self.assertEqual(first, second)
        self.assertEqual(Token.objects.filter(user=self.user).count(), 1)

    def test_login_validation_errors(self):
        self.check_rejections(
            "login",
            [
                ({"password": TEST_PASSWORD}, "Нэвтрэх нэр оруулна уу"),
                ({"username": "99001122"}, "Нууц үг оруулна уу"),
                ({"username": "bad", "password": "x"}, INVALID_USERNAME),
                ({"username": "99001122", "password": "wrong"}, "Нууц үг буруу байна"),
                ({"username": "99999999", "password": TEST_PASSWORD}, "Нууц үг буруу байна"),
            ],
        )
        self.assertFalse(Token.objects.exists())

    def test_register_number_username_is_rejected_as_invalid(self):
        # Users have no register field, so a register can never authenticate.
        with mock.patch("apps.auth.views.authenticate") as authenticate:
            self.check_rejections(
                "login",
                [
                    ({"username": "1234567", "password": TEST_PASSWORD}, INVALID_USERNAME),
                    ({"username": "УБ90010112", "password": TEST_PASSWORD}, INVALID_USERNAME),
                ],
            )
        authenticate.assert_not_called()

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.post("login", username="bat@example.com", password=TEST_PASSWORD)
        self.assert_rejected(response, "Нууц үг буруу байна")


@mock.patch.dict(os.environ, CALL_PRO_ENV)
class AuthThrottleTests(AuthAPITestCase):
    def test_auth_endpoints_are_rate_limited_per_client(self):
        with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"auth": "2/minute"}):
            codes = [self.post("login", username="99001122", password="wrong").status_code for _ in range(3)]
        self.assertEqual(codes[2], 429)
        self.assertNotIn(429, codes[:2])


class PasswordResetTests(AuthAPITestCase):
    def request_otp(self, username="99001122", status_code=200, text="ok"):
        with mock.patch("requests.get", return_value=mock.Mock(status_code=status_code, text=text)) as post:
            response = self.post("forgot-password", username=username)
        return response, post

    def sent_otp(self):
        response, post = self.request_otp()
        self.assertEqual(response.json(), {"message": "OTP sent"})
        payload = post.call_args.kwargs["params"]
        self.assertEqual(payload["to"], "99001122")
        return re.search(r"code: (\d{4})\.", payload["text"]).group(1)

    def test_full_reset_flow_changes_password(self):
        otp = self.sent_otp()
        response = self.post("confirm-otp", username="99001122", otp=otp)
        self.assertEqual(response.status_code, 200)
        secret = response.json()["secret"]
        self.assertRegex(secret, r"^[A-Za-z0-9]{10}$")

        response = self.post("recover-password", username="99001122", secret=secret, newPassword=NEW_PASSWORD)
        self.assertEqual(response.json(), {"message": "Password reset successfully."})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

        reused = self.post("recover-password", username="99001122", secret=secret, newPassword="other-pass-1")
        self.assert_rejected(reused, "Secret has expired or is invalid")

    def test_forgot_password_validation(self):
        self.check_rejections(
            "forgot-password",
            [({}, "Нэвтрэх нэр оруулна уу"), ({"username": "abc"}, INVALID_USERNAME)],
        )

    def test_forgot_password_unknown_user_sends_nothing(self):
        for username in ("99999999", "nobody@example.com"):
            with self.subTest(username=username):
                response, post = self.request_otp(username=username)
                self.assert_rejected(response, "Утас эсвэл имэйл дээр хэрэглэгч олдсонгүй")
                post.assert_not_called()
                self.assertIsNone(cache.get(f"otp:{username}"))

    def test_forgot_password_by_email_is_not_supported_yet(self):
        response, post = self.request_otp(username="bat@example.com")
        self.assert_rejected(response, "Email connection not ready")
        post.assert_not_called()
        self.assertIsNone(cache.get("otp:bat@example.com"))

    def test_forgot_password_reports_sms_failure(self):
        response, _ = self.request_otp(status_code=500, text="gateway down")
        self.assert_rejected(response, "Failed to send OTP: gateway down", code=500)
        self.assertIsNone(cache.get("otp:99001122"))

    def test_user_lookup_failure_is_reported(self):
        lookup = mock.patch("apps.user.services.UserService.get_by_username", return_value=(None, "db down"))
        cache.set("secret:99001122", "s", timeout=60)
        requests = [
            ("forgot-password", {}),
            ("confirm-otp", {"otp": "1234"}),
            ("recover-password", {"secret": "s", "newPassword": NEW_PASSWORD}),
        ]
        with lookup:
            for name, payload in requests:
                with self.subTest(endpoint=name):
                    response = self.post(name, username="99001122", **payload)
                    self.assert_rejected(response, "Failed to find user: db down", code=500)

    def test_confirm_otp_validation(self):
        self.check_rejections(
            "confirm-otp",
            [
                ({"otp": "1234"}, "Username is required"),
                ({"username": "99001122"}, "OTP is required"),
                ({"username": "abc", "otp": "1234"}, "Invalid phone or email"),
                ({"username": "99001122", "otp": "1234"}, "OTP has expired or is invalid"),
                ({"username": "99999999", "otp": "1234"}, "Phone or email not found"),
                ({"username": "nobody@example.com", "otp": "1234"}, "Phone or email not found"),
            ],
        )

    def test_confirm_otp_rejects_wrong_code(self):
        otp = self.sent_otp()
        wrong = "0000" if otp != "0000" else "1111"
        self.assert_rejected(self.post("confirm-otp", username="99001122", otp=wrong), "Invalid OTP")

    def test_recover_password_validation(self):
        self.check_rejections(
            "recover-password",
            [
                ({"secret": "s", "newPassword": NEW_PASSWORD}, "Username is required"),
                ({"username": "99001122", "newPassword": NEW_PASSWORD}, "Secret is required"),
                ({"username": "99001122", "secret": "s"}, "New password is required"),
                ({"username": "abc", "secret": "s", "newPassword": NEW_PASSWORD}, "Invalid phone or email"),
                ({"username": "99001122", "secret": "s", "newPassword": NEW_PASSWORD}, "Secret has expired or is invalid"),
            ],
        )

    def test_recover_password_rejects_unknown_user(self):
        cache.set("secret:99999999", "s", timeout=60)
        response = self.post("recover-password", username="99999999", secret="s", newPassword=NEW_PASSWORD)
        self.assert_rejected(response, "Phone or email not found")

    def test_recover_password_by_email(self):
        cache.set("secret:bat@example.com", "mail-secret", timeout=60)
        response = self.post(
            "recover-password", username="bat@example.com", secret="mail-secret", newPassword=NEW_PASSWORD
        )
        self.assertEqual(response.json(), {"message": "Password reset successfully."})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertIsNone(cache.get("secret:bat@example.com"))

    def test_recover_password_rejects_wrong_secret(self):
        cache.set("secret:99001122", "right-secret", timeout=60)
        response = self.post("recover-password", username="99001122", secret="wrong", newPassword=NEW_PASSWORD)
        self.assert_rejected(response, "Invalid secret.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEST_PASSWORD))


class AuthBackendTests(TestCase):
    def setUp(self):
        self.user = make_user(email="nara@example.com", phone="99887766")
        self.backend = AuthBackend()

    def test_authenticates_by_email_and_phone(self):
        for username in ("nara@example.com", "99887766"):
            with self.subTest(username=username):
                self.assertEqual(self.backend.authenticate(None, username, TEST_PASSWORD), self.user)

    def test_rejects_wrong_password_unknown_user_and_inactive(self):
        self.assertIsNone(self.backend.authenticate(None, "nara@example.com", "nope"))
        self.assertIsNone(self.backend.authenticate(None, "nobody@example.com", TEST_PASSWORD))
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(self.backend.authenticate(None, "99887766", TEST_PASSWORD))
