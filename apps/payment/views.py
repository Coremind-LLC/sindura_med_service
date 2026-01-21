import logging
from http import HTTPStatus
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from apps.invoice.enums import InvoiceStage
from apps.invoice.services import InvoiceService
from apps.order.enums import OrderStage
from apps.order.services import OrderService
from apps.third_party.call_pro.services import CallProService
from apps.third_party.qpay.enums import PaymentStatus
from apps.third_party.qpay.services import QPayService

logger = logging.getLogger(__name__)


class PaymentViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["get_payment", "check_payment"]:
            return [permissions.AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def get_payment(self, request):
        payment_id = request.query_params.get("payment_id")
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
        if invoice is None:
            return Response(
                {"message": "Invoice not found"}, status=HTTPStatus.BAD_REQUEST
            )

        if invoice.stage == InvoiceStage.PAID:
            return Response({"message": "Invoice paid"}, status=HTTPStatus.OK)

        if invoice.order.stage == OrderStage.PAID:
            return Response({"message": "Order paid"}, status=HTTPStatus.OK)

        # invoice, error = InvoiceService.approve(invoice.id)
        # if error:
        #     return Response({"message": error}, status=HTTPStatus.BAD_REQUEST)
        invoice = InvoiceService.approve(invoice.id)

        # order, error = OrderService.approve(invoice.order.id)
        # if error:
        #     return Response({"message": error}, status=HTTPStatus.BAD_REQUEST)
        OrderService.approve(invoice.order.id)

        return Response({"message": "Payment is successfully"}, status=HTTPStatus.OK)

    @action(detail=False, methods=["get"], url_path="check/(?P<invoice_id>\d+)")
    def check_payment(self, request, invoice_id):
        if not invoice_id:
            return Response(
                {"message": "Invoice id is required"},
                status=HTTPStatus.BAD_REQUEST,
            )

        invoice = InvoiceService.get_by_id(invoice_id)
        if invoice is None:
            return Response(
                {"message": "Invoice not found"}, status=HTTPStatus.BAD_REQUEST
            )

        if invoice.stage == InvoiceStage.PAID:
            return Response({"message": "Invoice paid"}, status=HTTPStatus.OK)

        if invoice.order.stage == OrderStage.PAID:
            return Response({"message": "Order paid"}, status=HTTPStatus.OK)

        response, error = QPayService.check_payment(invoice.qpay_invoice_id)
        if error:
            return Response({"message": error}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        if (len(response.rows) == 0 or response.rows[0].payment_status != PaymentStatus.PAID):
            return Response({"message": "Invoice not paid"}, status=HTTPStatus.OK)

        # _, error = InvoiceService.approve(invoice.id)
        # if error:
        #     return Response({"message": error}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        InvoiceService.approve(invoice.id)

        # _, error = OrderService.approve(invoice.order.id)
        # if error:
        #     return Response({"message": error}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        OrderService.approve(invoice.order.id)

        CallProService.send(invoice.order.phone, "Таны захиалга баталгаажлаа")

        return Response({"message": "Төлбөр амжилттай төлөгдлөө"}, status=HTTPStatus.OK)
