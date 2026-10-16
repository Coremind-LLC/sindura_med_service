from decimal import Decimal
from unittest import mock

from django.http import Http404
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.enums import Status
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.serializers import InvoiceSerializer
from apps.invoice.services import InvoiceService
from apps.third_party.qpay.services import QPayService
from apps.third_party.qpay.tests import invoice_response
from helpers.tests_factories import AdminAPITestCase, make_examination, make_invoice, make_order, make_user


class InvoiceServiceCreateTests(APITestCase):
    def setUp(self):
        self.order = make_order(examination=make_examination(deposit_amount=Decimal("15000.00")), phone="99001122")
        self.request = mock.Mock(user=make_user())

    @mock.patch.object(QPayService, "create_invoice")
    def test_create_saves_invoice_from_qpay_response(self, create_invoice):
        create_invoice.return_value = (invoice_response("inv-77"), None)
        invoice, error = InvoiceService.create(self.order, self.request)
        self.assertIsNone(error)
        create_invoice.assert_called_once_with(Decimal("15000.00"), "99001122")
        invoice.refresh_from_db()
        self.assertEqual(invoice.order, self.order)
        self.assertEqual(invoice.amount, Decimal("15000.00"))
        self.assertEqual(invoice.qpay_invoice_id, "inv-77")
        self.assertEqual(invoice.stage, InvoiceStage.PENDING)
        self.assertEqual(invoice.created_by, self.request.user)

    @mock.patch.object(QPayService, "create_invoice", return_value=(None, "qpay down"))
    def test_create_returns_error_when_qpay_fails(self, _create_invoice):
        invoice, error = InvoiceService.create(self.order, self.request)
        self.assertIsNone(invoice)
        self.assertIn("QPay invoice not created", error)
        self.assertFalse(Invoice.objects.exists())


class InvoiceServiceStageTests(APITestCase):
    def test_approve_and_cancel_transitions(self):
        cases = [
            (InvoiceService.approve, InvoiceStage.PENDING, InvoiceStage.PAID),
            (InvoiceService.approve, InvoiceStage.PAID, InvoiceStage.PAID),
            (InvoiceService.cancel, InvoiceStage.PENDING, InvoiceStage.CANCELLED),
            (InvoiceService.cancel, InvoiceStage.CANCELLED, InvoiceStage.CANCELLED),
        ]
        for func, start, expected in cases:
            with self.subTest(func=func.__name__, start=start):
                invoice = make_invoice(stage=start)
                self.assertEqual(func(invoice.id).stage, expected)
                invoice.refresh_from_db()
                self.assertEqual(invoice.stage, expected)

    def test_delete_marks_invoice_deleted(self):
        invoice = make_invoice()
        InvoiceService.delete(invoice.id)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Status.DELETED)

    def test_get_by_id(self):
        invoice = make_invoice()
        self.assertEqual(InvoiceService.get_by_id(invoice.id), invoice)
        with self.assertRaises(Http404):
            InvoiceService.get_by_id(invoice.id + 1000)
        for missing in ("missing", "", None):
            with self.subTest(qpay_invoice_id=missing), self.assertRaises(Http404):
                InvoiceService.get_by_qpay_invoice_id(missing)

    def test_loaded_invoices_serialize_without_qpay(self):
        invoice = make_invoice(qpay_invoice_id="inv-db")
        found = InvoiceService.get_by_qpay_invoice_id("inv-db")
        self.assertEqual((found, found.order), (invoice, invoice.order))
        self.assertEqual([row["qpay"] for row in InvoiceService.get_all()], [None])
        data = InvoiceService.update(invoice.id, {"order": invoice.order_id, "amount": "700.00"}, None)
        self.assertEqual((data["amount"], data["qpay"]), (700, None))


class InvoiceSerializerTests(APITestCase):
    def test_qpay_field_exposes_attached_response(self):
        invoice = make_invoice()
        invoice.qpay = invoice_response("inv-9")
        data = InvoiceSerializer(invoice).data
        self.assertEqual(data["qpay"]["invoice_id"], "inv-9")
        self.assertEqual(data["order"], invoice.order_id)
        invoice.qpay = None
        self.assertIsNone(InvoiceSerializer(invoice).data["qpay"])

    def test_requires_order_and_amount(self):
        serializer = InvoiceSerializer(data={}, context={"request": None})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"order", "amount"})

    def test_create_with_anonymous_request_has_no_creator(self):
        order = make_order()
        request = mock.Mock(user=mock.Mock(is_anonymous=True))
        serializer = InvoiceSerializer(data={"order": order.id, "amount": "500.00"}, context={"request": request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        invoice = serializer.save()
        self.assertIsNone(invoice.created_by)
        self.assertEqual(invoice.amount, Decimal("500.00"))


class InvoiceViewSetTests(AdminAPITestCase):
    def setUp(self):
        super().setUp()
        self.invoice = make_invoice(qpay_invoice_id="inv-api")
        self.url = f"/invoices/{self.invoice.id}/"

    def test_list_and_retrieve_for_staff(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual((response.json()["qpayInvoiceId"], response.json()["qpay"]), ("inv-api", None))
        rows = self.results(self.client.get("/invoices/"))
        self.assertEqual([row["id"] for row in rows], [self.invoice.id])

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        for url in ("/invoices/", self.url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mutations_are_disabled(self):
        body = {"order": self.invoice.order_id, "amount": "1.00"}
        for method, url in [("post", "/invoices/"), ("put", self.url), ("patch", self.url), ("delete", self.url)]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, body, format="json")
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(list(Invoice.objects.filter(status=Status.ACTIVE)), [self.invoice])
