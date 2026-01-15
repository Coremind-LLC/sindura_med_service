from django.db import transaction
from rest_framework import serializers

from apps.examination.models import Examination
from apps.examination.services import ExaminationService
from apps.invoice.enums import InvoicePaymentCondition, InvoiceStage
from apps.invoice.models import Invoice
from apps.invoice.services import InvoiceService
from apps.order.models import Order

class OrderSerializer(serializers.ModelSerializer):
    examination = serializers.PrimaryKeyRelatedField(
        queryset=Examination.objects.all(), required=True
    )

    class Meta:
        model = Order
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        order = super().create(validated_data)

        invoice = {
            "order": order.id,
            "amount": order.total_amount,
            "payment_condition": InvoicePaymentCondition.QPAY,
            "stage": InvoiceStage.PENDING,
        }

        InvoiceService.create(invoice, request)
        ExaminationService.lock(order.examination)

        return order