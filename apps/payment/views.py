import logging
from http import HTTPStatus
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.services import InvoiceService
from apps.order.enums import OrderStage
from apps.payment.services import PaymentService
from apps.third_party.qpay.enums import PaymentStatus
from apps.third_party.qpay.services import QPayService

logger = logging.getLogger(__name__)


def _already_paid_message(invoice: Invoice) -> str | None:
    if invoice.stage == InvoiceStage.PAID:
        return "Invoice paid"
    if invoice.order.stage == OrderStage.PAID:
        return "Order paid"
    return None


def _approve(invoice: Invoice) -> Response | None:
    """Approve invoice + order and send the SMS; returns an error response on failure."""
    try:
        order = PaymentService.approve(invoice)
    except Exception as e:
        logger.exception(f"Failed to approve invoice/order {invoice.id}: {e}")
        return Response({"message": f"Failed to approve invoice/order: {e}"},
                        status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if order is not None:
        PaymentService.notify(order)
    return None


class PaymentViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ["get_payment", "check_payment"]:
            return [permissions.AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["get", "post"])
    def get_payment(self, request) -> Response:
        # QPay's callback appends ?qpay_payment_id=...; payment_id is kept for manual calls.
        payment_id = request.query_params.get("qpay_payment_id") or request.query_params.get("payment_id")
        if not payment_id:
            return Response(
                {"message": "payment_id is required"}, status=HTTPStatus.BAD_REQUEST
            )

        response, error = QPayService.get_payment(payment_id)
        if error:
            return Response({"message": error}, status=HTTPStatus.BAD_REQUEST)

        if response.payment_status != PaymentStatus.PAID:
            return Response(
                {"message": "Invoice not paid"}, status=HTTPStatus.BAD_REQUEST
            )

        invoice = InvoiceService.get_by_qpay_invoice_id(response.object_id)

        message = _already_paid_message(invoice)
        if message:
            return Response({"message": message}, status=HTTPStatus.OK)

        failure = _approve(invoice)
        if failure:
            return failure

        return Response({"message": "Payment is successfully"}, status=HTTPStatus.OK)

    @action(detail=False, methods=["get"], url_path=r"check/(?P<invoice_id>\d+)")
    def check_payment(self, request, invoice_id) -> Response:
        invoice = InvoiceService.get_by_id(invoice_id)

        message = _already_paid_message(invoice)
        if message:
            return Response({"message": message, "status": "paid"}, status=HTTPStatus.OK)

        response, error = QPayService.check_payment(invoice.qpay_invoice_id)
        if error:
            return Response({"message": error}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not PaymentService.is_paid(response):
            return Response({"message": "Invoice not paid", "status": "not paid"}, status=HTTPStatus.OK)

        failure = _approve(invoice)
        if failure:
            return failure

        return Response({"message": "Төлбөр амжилттай төлөгдлөө", "status": "paid"}, status=HTTPStatus.OK)
