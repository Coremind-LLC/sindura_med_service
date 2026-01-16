import logging

from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.common.enums import Status
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.serializers import InvoiceSerializer

logger = logging.getLogger(__name__)

class InvoiceService:

    @staticmethod
    def get_all():
        queryset = Invoice.objects.all()
        serializer = InvoiceSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int):
        instance = get_object_or_404(Invoice, pk=id)
        serializer = InvoiceSerializer(instance)
        return serializer.data

    @staticmethod
    def get_by_qpay_invoice_id(qpay_invoice_id: str):
        instance = get_object_or_404(Invoice, qpay_invoice_id=qpay_invoice_id)
        serializer = InvoiceSerializer(instance)
        return serializer.data

    @staticmethod
    def create(data: dict, request):
        try:
            serializer = InvoiceSerializer(
                data=data,
                context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            invoice = serializer.data

            return invoice

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return None, str(e)

    # @staticmethod
    # def create(order: Order):
    #     try:
    #         qpay_invoice, error = QPayService.create_invoice(
    #             order.partner, amount=order.amount
    #         )
    #         if error:
    #             return None, error
    #
    #         invoice = Invoice(
    #             order=order,
    #             payment_condition=InvoicePaymentCondition.CASH,
    #             stage=InvoiceStage.PENDING,
    #             amount=order.amount,
    #             qpay_invoice_id=qpay_invoice.invoice_id,
    #         )
    #
    #         invoice.created_at = timezone.now()
    #         invoice.created_by = user
    #
    #         invoice.save()
    #
    #         invoice.qpay = qpay_invoice
    #
    #         return invoice, None
    #     except Exception as e:
    #         logger.error(f"Failed to create invoice: {e}")
    #         return None, str(e)

    @staticmethod
    def update(id: int, data: dict, request):
        instance = get_object_or_404(Invoice, pk=id)
        serializer = InvoiceSerializer(
            instance,
            data=data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def approve(id: int):
        instance = get_object_or_404(Invoice, pk=id)

        if instance.stage == InvoiceStage.PAID:
            return instance

        instance.stage = InvoiceStage.PAID
        instance.updated_at = timezone.now()
        instance.save(update_fields=["stage", "updated_at"])
        return instance

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Invoice, pk=id)
        instance.status = Status.DELETED
        instance.save(update_fields=["status"])