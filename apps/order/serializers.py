from django.db import transaction
from rest_framework import serializers

from apps.examination.models import Examination
from apps.examination.services import ExaminationService
from apps.invoice.enums import InvoiceStage
from apps.invoice.services import InvoiceService
from apps.order.models import Order
from apps.third_party.qpay.services import QPayService

class OrderSerializer(serializers.ModelSerializer):
    examination = serializers.PrimaryKeyRelatedField(
        queryset=Examination.objects.all(), required=True
    )
    examination_amount = serializers.DecimalField(
        source="examination.amount", read_only=True, max_digits=20, decimal_places=2
    )
    invoice = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"

    def get_invoice(self, obj):
        invoice = getattr(obj, "_invoice", None)
        if not invoice:
            return None

        return {
            # "id": invoice.id,
            "amount": invoice.amount,
            "qpay_invoice_id": invoice.qpay_invoice_id,
            "stage": invoice.stage,
        }

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        order = super().create(validated_data)

        qpay_response, error = QPayService.create_invoice(order.examination.amount, order.phone)
        if error:
            raise serializers.ValidationError(
                "QPay invoice not created."
            )

        invoice_data = {
            "order": order.id,
            "amount": order.examination.amount,
            "qpay_invoice_id": qpay_response.invoice_id,
            "stage": InvoiceStage.PENDING,
        }

        invoice = InvoiceService.create(invoice_data, request)
        ExaminationService.lock(order.examination.id)

        order._invoice = invoice

        return order