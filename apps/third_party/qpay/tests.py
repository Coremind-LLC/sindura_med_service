"""QPay client tests. Every outbound request is mocked; helpers here are reused by other apps' tests."""
import os
from decimal import Decimal
from unittest import mock

import requests
from django.conf import settings
from django.test import SimpleTestCase
from requests.auth import HTTPBasicAuth

from apps.third_party.qpay.enums import PaymentStatus
from apps.third_party.qpay.models import InvoiceResponse, PaymentPageResponse, PaymentResponse
from apps.third_party.qpay.services import QPayService

QPAY_HOST = "https://qpay.test"
QPAY_ENV = {
    "QPAY_HOST": QPAY_HOST,
    "QPAY_USER": "dummy-user",
    "QPAY_PASSWORD": "dummy-password",
    "QPAY_INVOICE_CODE": "DUMMY_INVOICE",
}


def fake_response(status_code=200, payload=None, text="error"):
    response = mock.Mock(status_code=status_code, text=text)
    response.json.return_value = payload if payload is not None else {}
    return response


def token_payload():
    return {
        "token_type": "bearer", "refresh_expires_in": 3600, "refresh_token": "dummy-refresh",
        "access_token": "dummy-token", "expires_in": 600, "scope": "profile",
        "session_state": "dummy-session", "not-before-policy": 0,
    }


def invoice_payload(invoice_id="qpay-inv-1"):
    return {"invoice_id": invoice_id, "qr_text": "qr", "qr_image": "img", "qPay_shortUrl": "https://s.test", "urls": []}


def invoice_response(invoice_id="qpay-inv-1"):
    return InvoiceResponse(**invoice_payload(invoice_id))


def payment_payload(**fields):
    data = {"payment_id": "pay-1", "payment_status": PaymentStatus.PAID.value, "object_id": "qpay-inv-1"}
    data.update(fields)
    return data


def payment_page(*statuses):
    rows = [PaymentResponse(**payment_payload(payment_status=s)) for s in statuses]
    return PaymentPageResponse(count=len(rows), rows=rows)


@mock.patch.dict(os.environ, QPAY_ENV)
class QPayLoginTests(SimpleTestCase):
    @mock.patch("requests.post")
    def test_login_returns_access_token(self, post):
        post.return_value = fake_response(payload=token_payload())
        self.assertEqual(QPayService.login(), ("dummy-token", None))
        post.assert_called_once_with(
            f"{QPAY_HOST}/v2/auth/token", auth=HTTPBasicAuth("dummy-user", "dummy-password"), timeout=30
        )

    @mock.patch("requests.post")
    def test_login_failures_return_error(self, post):
        cases = [
            (fake_response(status_code=401, text="unauthorized"), "unauthorized"),
            (requests.ConnectionError("network down"), "network down"),
        ]
        for effect, message in cases:
            with self.subTest(message=message):
                post.side_effect = [effect]
                self.assertEqual(QPayService.login(), (None, message))

    @mock.patch.object(QPayService, "login", return_value=(None, "login failed"))
    def test_operations_propagate_login_error(self, _login):
        calls = [
            (QPayService.create_invoice, (Decimal("100.00"), "99112233")),
            (QPayService.check_payment, ("qpay-inv-1",)),
            (QPayService.get_payment, ("pay-1",)),
        ]
        with mock.patch("requests.post") as post, mock.patch("requests.get") as get:
            for func, args in calls:
                with self.subTest(func=func.__name__):
                    self.assertEqual(func(*args), (None, "login failed"))
            post.assert_not_called()
            get.assert_not_called()


@mock.patch.dict(os.environ, QPAY_ENV)
@mock.patch.object(QPayService, "login", return_value=("dummy-token", None))
class QPayOperationTests(SimpleTestCase):
    def assert_bearer(self, call):
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer dummy-token")

    @mock.patch("requests.post")
    def test_create_invoice_posts_request_and_parses_response(self, post, _login):
        post.return_value = fake_response(payload=invoice_payload("inv-42"))
        result, error = QPayService.create_invoice(Decimal("10000.00"), "99112233")
        self.assertIsNone(error)
        self.assertEqual(result, invoice_response("inv-42"))
        self.assertEqual(post.call_args.args[0], f"{QPAY_HOST}/v2/invoice")
        self.assert_bearer(post.call_args)
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["amount"], "10000.00")
        self.assertEqual(body["invoice_code"], "DUMMY_INVOICE")
        self.assertEqual(body["invoice_receiver_code"], "99112233")
        self.assertEqual(body["callback_url"], f"{settings.API_HOST}/payments/get_payment/")
        self.assertEqual(len(body["sender_invoice_no"]), 8)

    @mock.patch("requests.post")
    def test_check_payment_parses_rows(self, post, _login):
        rows = [payment_payload(), payment_payload(payment_id="pay-2", payment_status="NEW", unmodelled_field="x")]
        post.return_value = fake_response(payload={"count": 2, "rows": rows, "paid_amount": 100})
        result, error = QPayService.check_payment("qpay-inv-1")
        self.assertIsNone(error)
        self.assertEqual(result.count, 2)
        self.assertEqual([r.payment_id for r in result.rows], ["pay-1", "pay-2"])
        self.assertEqual(result.paid_amount, 100)
        self.assertEqual(post.call_args.args[0], f"{QPAY_HOST}/v2/payment/check")
        self.assert_bearer(post.call_args)
        body = post.call_args.kwargs["json"]
        self.assertEqual((body["object_type"], body["object_id"]), ("INVOICE", "qpay-inv-1"))
        self.assertEqual(body["offset"], {"page_number": 1, "page_limit": 100})

    @mock.patch("requests.get")
    def test_get_payment_parses_response(self, get, _login):
        get.return_value = fake_response(payload=payment_payload(payment_name="extra key from QPay"))
        result, error = QPayService.get_payment("pay-1")
        self.assertIsNone(error)
        self.assertFalse(hasattr(result, "payment_name"))
        self.assertEqual(result.payment_status, PaymentStatus.PAID)
        self.assertEqual(result.object_id, "qpay-inv-1")
        self.assertEqual(get.call_args.args[0], f"{QPAY_HOST}/v2/payment/pay-1")
        self.assert_bearer(get.call_args)

    def test_http_errors_are_returned_not_raised(self, _login):
        cases = [
            ("requests.post", QPayService.create_invoice, (Decimal("1"), "99112233"), fake_response(400, text="bad")),
            ("requests.post", QPayService.check_payment, ("x",), fake_response(500, text="bad")),
            ("requests.get", QPayService.get_payment, ("x",), fake_response(404, payload={"message": "bad"})),
            ("requests.get", QPayService.get_payment, ("x",), requests.Timeout("bad")),
        ]
        for target, func, args, effect in cases:
            with self.subTest(func=func.__name__, effect=effect), mock.patch(target, side_effect=[effect]):
                self.assertEqual(func(*args), (None, "bad"))
