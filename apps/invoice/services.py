import logging

from rest_framework import serializers
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList
from django.utils import timezone
from django.http import Http404
from django.shortcuts import get_object_or_404
from apps.common.enums import Status
from apps.invoice.enums import InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.serializers import InvoiceSerializer
from apps.order.models import Order
from apps.third_party.qpay.services import QPayService
from helpers.common_helper import CommonHelper

logger = logging.getLogger(__name__)

class InvoiceService:

    @staticmethod
    def get_all() -> ReturnList:
        queryset = Invoice.objects.all()
        serializer = InvoiceSerializer(queryset, many=True)
        return serializer.data

    @staticmethod
    def get_by_id(id: int) -> Invoice:
        return get_object_or_404(
            Invoice.objects.select_related("order__examination"),
            pk=id
        )

    @staticmethod
    def get_by_qpay_invoice_id(qpay_invoice_id: str | None) -> Invoice:
        qpay_invoice_id = CommonHelper.blank_if_none(qpay_invoice_id)
        if not qpay_invoice_id:
            raise Http404("Invoice not found")
        return get_object_or_404(
            Invoice.objects.select_related("order__examination"),
            qpay_invoice_id=qpay_invoice_id
        )

    @staticmethod
    def create(order: Order, request) -> tuple[Invoice | None, str | None]:
        try:
            qpay_response, error = QPayService.create_invoice(order.examination.deposit_amount, order.phone)
            if error:
                raise serializers.ValidationError({"qpay": "QPay invoice not created."})

            invoice_data = {
                "order": order.id,
                "amount": order.examination.deposit_amount,
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
            logger.exception(f"Failed to create invoice: {e}")
            return None, str(e)

    @staticmethod
    def update(id: int, data: dict, request) -> ReturnDict:
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
    def approve(id: int) -> Invoice:
        instance = get_object_or_404(Invoice, pk=id)

        if instance.stage == InvoiceStage.PAID:
            return instance

        instance.stage = InvoiceStage.PAID
        instance.updated_at = timezone.now()
        instance.save(update_fields=["stage", "updated_at"])
        return instance

    @staticmethod
    def cancel(id: int) -> Invoice:
        instance = get_object_or_404(Invoice, pk=id)

        if instance.stage == InvoiceStage.CANCELLED:
            return instance

        instance.stage = InvoiceStage.CANCELLED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["stage", "updated_at"])
        return instance

    @staticmethod
    def delete(id: int) -> None:
        instance = get_object_or_404(Invoice, pk=id)
        instance.status = Status.DELETED
        instance.updated_at = timezone.now()
        instance.save(update_fields=["status", "updated_at"])