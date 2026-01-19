import logging

from rest_framework import serializers
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.common.enums import Status
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.serializers import InvoiceSerializer
from apps.order.models import Order
from apps.third_party.qpay.services import QPayService

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
    def create(order: Order, request):
        try:
            qpay_response, error = QPayService.create_invoice(order.examination.amount, order.phone)
            if error:
                raise serializers.ValidationError({"qpay": "QPay invoice not created."})

            invoice_data = {
                "order": order.id,
                "amount": order.examination.amount,
                "qpay_invoice_id": qpay_response.invoice_id,
                "stage": InvoiceStage.PENDING,
            }

            serializer = InvoiceSerializer(
                data=invoice_data,
                context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            instance.qpay = qpay_response

            return instance, None

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return None, str(e)

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
    def cancel(id: int):
        instance = get_object_or_404(Invoice, pk=id)

        if instance.stage == InvoiceStage.PAID:
            return instance

        instance.stage = InvoiceStage.CANCELLED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["stage", "updated_at"])
        return instance

    @staticmethod
    def delete(id: int):
        instance = get_object_or_404(Invoice, pk=id)
        instance.status = Status.DELETED
        instance.save(update_fields=["status"])