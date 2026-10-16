import datetime
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from apps.activity_log.models import ActivityLog
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.order.enums import OrderStage
from apps.order.models import Order
from apps.order.services import OrderService
from apps.order.tasks import check_order_stage
from apps.payment.services import PaymentService
from apps.third_party.call_pro.services import CallProService
from apps.third_party.qpay.enums import PaymentStatus
from apps.third_party.qpay.models import PaymentResponse
from apps.third_party.qpay.services import QPayService
from apps.third_party.qpay.tests import invoice_response, payment_page, payment_payload
from helpers.tests_factories import make_examination, make_examination_type, make_invoice, make_order


class CheckPaymentTests(APITestCase):
    def setUp(self):
        examination = make_examination(
            date=datetime.date(2030, 2, 3), time=datetime.time(10, 30), room="204",
            examination_type=make_examination_type(name="MRI"), is_lock=True,
        )
        self.order = make_order(examination=examination, phone="99887766")
        self.invoice = make_invoice(order=self.order, qpay_invoice_id="inv-check")
        self.url = f"/payments/check/{self.invoice.id}/"
        qpay = mock.patch.object(QPayService, "check_payment")
        sms = mock.patch.object(CallProService, "send", return_value=(None, None))
        self.check_payment = qpay.start()
        self.sms = sms.start()
        self.addCleanup(mock.patch.stopall)

    def assert_stages(self, invoice_stage, order_stage):
        self.invoice.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual((self.invoice.stage, self.order.stage), (invoice_stage, order_stage))

    def test_paid_rows_approve_invoice_and_order_and_notify(self):
        self.check_payment.return_value = (payment_page(PaymentStatus.PAID), None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "paid")
        self.check_payment.assert_called_once_with("inv-check")
        self.assert_stages(InvoiceStage.PAID, OrderStage.PAID)
        phone, text = self.sms.call_args.args
        self.assertEqual(phone, "99887766")
        for fragment in ("2030-02-03", "10:30", "MRI", "204"):
            self.assertIn(fragment, text)

    def test_any_paid_row_counts_as_paid(self):
        self.check_payment.return_value = (payment_page(PaymentStatus.FAILED, PaymentStatus.PAID), None)
        response = self.client.get(self.url)
        self.assertEqual(response.json(), {"message": "Төлбөр амжилттай төлөгдлөө", "status": "paid"})
        self.assert_stages(InvoiceStage.PAID, OrderStage.PAID)

    def test_unpaid_rows_leave_stages_untouched(self):
        for page in (payment_page(), payment_page(PaymentStatus.NEW)):
            with self.subTest(rows=len(page.rows)):
                self.check_payment.return_value = (page, None)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.json(), {"message": "Invoice not paid", "status": "not paid"})
        self.assert_stages(InvoiceStage.PENDING, OrderStage.PENDING)
        self.sms.assert_not_called()

    def set_stages(self, invoice_stage, order_stage):
        Invoice.objects.filter(pk=self.invoice.id).update(stage=invoice_stage)
        Order.objects.filter(pk=self.order.id).update(stage=order_stage)

    def test_already_paid_short_circuits_without_calling_qpay(self):
        cases = [
            ("invoice", InvoiceStage.PAID, OrderStage.PENDING, "Invoice paid"),
            ("order", InvoiceStage.PENDING, OrderStage.PAID, "Order paid"),
        ]
        for label, invoice_stage, order_stage, message in cases:
            with self.subTest(label):
                self.set_stages(invoice_stage, order_stage)
                response = self.client.get(self.url)
                self.assertEqual(response.json(), {"message": message, "status": "paid"})
        self.check_payment.assert_not_called()

    def test_qpay_error_returns_500(self):
        self.check_payment.return_value = (None, "qpay down")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()["message"], "qpay down")
        self.assert_stages(InvoiceStage.PENDING, OrderStage.PENDING)

    def test_unknown_invoice_returns_404(self):
        response = self.client.get(f"/payments/check/{self.invoice.id + 1000}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GetPaymentTests(APITestCase):
    url = "/payments/get_payment/"

    @mock.patch.object(QPayService, "get_payment")
    def test_rejected_requests(self, get_payment):
        cases = [
            ({}, None, "payment_id is required"),
            ({"payment_id": "p1"}, (None, "qpay down"), "qpay down"),
            ({"payment_id": "p1"}, (PaymentResponse(**payment_payload(payment_status="NEW")), None), "Invoice not paid"),
        ]
        for params, qpay_result, message in cases:
            with self.subTest(message=message):
                get_payment.return_value = qpay_result
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json(), {"message": message})

    @mock.patch.object(QPayService, "get_payment")
    def test_paid_payment_for_unknown_invoice_returns_404(self, get_payment):
        get_payment.return_value = (PaymentResponse(**payment_payload(object_id="nope")), None)
        response = self.client.get(self.url, {"payment_id": "p1"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        get_payment.assert_called_once_with("p1")


@mock.patch.object(CallProService, "send", return_value=(None, None))
@mock.patch.object(QPayService, "get_payment")
class PaidCallbackFlowTests(APITestCase):
    url = "/payments/get_payment/"

    def setUp(self):
        self.examination = make_examination()
        with mock.patch.object(QPayService, "create_invoice", return_value=(invoice_response("inv-flow"), None)), \
                mock.patch.object(check_order_stage, "apply_async"), self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/orders/", {
                "firstName": "Tuya", "lastName": "Gan", "phone": "99112233", "register": "УБ90010112",
                "examination": self.examination.id,
            }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.order = Order.objects.get(pk=response.json()["id"])
        self.invoice = Invoice.objects.get(order=self.order)

    def paid(self, get_payment, object_id="inv-flow"):
        get_payment.return_value = (PaymentResponse(**payment_payload(object_id=object_id)), None)
        return self.client.get(self.url, {"payment_id": "pay-1"})

    def test_paid_callback_approves_invoice_order_and_notifies(self, get_payment, send):
        response = self.paid(get_payment)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"message": "Payment is successfully"})
        self.invoice.refresh_from_db()
        self.order.refresh_from_db()
        self.examination.refresh_from_db()
        self.assertEqual((self.invoice.stage, self.order.stage), (InvoiceStage.PAID, OrderStage.PAID))
        self.assertTrue(self.examination.is_lock)
        self.assertTrue(ActivityLog.objects.filter(object_id=self.order.id, model="ORDER", action="APPROVE").exists())
        self.assertEqual(send.call_args.args[0], "99112233")
        again = self.paid(get_payment)
        self.assertEqual(again.json(), {"message": "Invoice paid"})
        self.assertEqual(send.call_count, 1)
        check = self.client.get(f"/payments/check/{self.invoice.id}/")
        self.assertEqual(check.json(), {"message": "Invoice paid", "status": "paid"})

    def test_late_payment_for_expired_order_relocks_examination(self, get_payment, _send):
        self.order.expire_at = None
        self.order.save(update_fields=["expire_at"])
        check_order_stage(self.order.id, self.invoice.id)
        self.examination.refresh_from_db()
        self.assertFalse(self.examination.is_lock)
        self.assertEqual(self.paid(get_payment).status_code, status.HTTP_200_OK)
        self.examination.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.examination.is_lock)
        self.assertEqual(self.order.stage, OrderStage.PAID)

    def test_approval_failure_rolls_back_invoice(self, get_payment, send):
        with mock.patch.object(OrderService, "approve", side_effect=RuntimeError("db down")):
            response = self.paid(get_payment)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.stage, InvoiceStage.PENDING)
        send.assert_not_called()

    def test_qpay_callback_parameter_name_is_accepted(self, get_payment, send):
        get_payment.return_value = (PaymentResponse(**payment_payload(object_id="inv-flow")), None)
        for method in ("get", "post"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(f"{self.url}?qpay_payment_id=pay-9")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
        get_payment.assert_called_with("pay-9")
        self.assertEqual(send.call_count, 1)

    def test_second_approval_of_same_invoice_is_a_no_op(self, _get_payment, send):
        self.assertIsNotNone(PaymentService.approve(self.invoice))
        self.assertIsNone(PaymentService.approve(self.invoice))
        self.assertEqual(ActivityLog.objects.filter(object_id=self.order.id, action="APPROVE").count(), 1)
        send.assert_not_called()

    def test_payment_without_object_id_returns_404(self, get_payment, _send):
        make_invoice(qpay_invoice_id="")
        self.assertEqual(self.paid(get_payment, object_id=None).status_code, status.HTTP_404_NOT_FOUND)
